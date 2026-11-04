"""Offline qBraid SDK-derived protocol adapter, with no submission capability.

Only bounded deterministic injected transports are supported. This synchronous
module cannot preempt a hung transport. No SDK, credentials or network are used.
"""

import copy
import json
import math


STATUSES = frozenset(("INITIALIZING", "QUEUED", "VALIDATING", "RUNNING",
                      "CANCELLING", "CANCELLED", "COMPLETED", "FAILED", "UNKNOWN", "HOLD"))
TERMINAL = frozenset(("COMPLETED", "CANCELLED", "FAILED"))
HANDLE_FIELDS = frozenset(("schema", "source_id", "provider", "device_id", "job_id",
                           "client_correlation_id", "submission_state"))
HTTP_ERRORS = {401: "authentication", 403: "access", 404: "not_found", 429: "throttled"}


class TransportError(Exception):
    """Typed fixture error. Arbitrary messages are never copied into evidence."""

    def __init__(self, status_code=None):
        super().__init__("transport request failed")
        self.status_code = status_code


def _identity(value, nullable=False):
    if nullable and value is None:
        return
    if (type(value) is not str or not 1 <= len(value) <= 256
            or not value.strip() or any(ord(c) < 32 or ord(c) == 127 for c in value)):
        raise ValueError("invalid identity field")


def _handle(value):
    if type(value) is not dict or set(value) != HANDLE_FIELDS:
        raise ValueError("invalid handle fields")
    if type(value["schema"]) is not int or value["schema"] != 1:
        raise ValueError("unsupported handle schema")
    if value["provider"] != "qbraid-sdk":
        raise ValueError("unsupported provider")
    for key in ("source_id", "device_id"):
        _identity(value[key])
    for key in ("job_id", "client_correlation_id"):
        _identity(value[key], nullable=True)
    state = value["submission_state"]
    if state == "submitted":
        _identity(value["job_id"])
    elif state == "outcome_unknown":
        _identity(value["client_correlation_id"])
    else:
        raise ValueError("invalid submission state")
    return dict(value)


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate handle field")
        result[key] = value
    return result


def _positive(value):
    try:
        return type(value) in (int, float) and math.isfinite(value) and value > 0
    except OverflowError:
        return False


def _finite(value):
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def _counts(data, spec):
    if type(spec) is not dict or set(spec) != {"width", "shots", "encoding", "bit_order"}:
        raise ValueError("invalid count specification")
    width, encoding, order = spec["width"], spec["encoding"], spec["bit_order"]
    if type(width) is not int or not 1 <= width <= 4096:
        raise ValueError("invalid count width")
    if encoding not in ("binary", "decimal") or order not in ("msb_left", "lsb_left"):
        raise ValueError("explicit count encoding and result bit order required")

    def one(histogram, shots):
        if type(histogram) is not dict or not histogram:
            raise ValueError("counts unavailable or unsupported shape")
        if type(shots) is not int or shots <= 0:
            raise ValueError("invalid shot total")
        converted = []
        for key, count in histogram.items():
            if type(count) is not int or count < 0:
                raise ValueError("invalid count")
            if encoding == "binary":
                if type(key) is not str or len(key) != width or any(c not in "01" for c in key):
                    raise ValueError("invalid binary key")
                bits = key
            else:
                if type(key) is not int or not 0 <= key < (1 << width):
                    raise ValueError("invalid decimal key")
                bits = format(key, f"0{width}b")
            converted.append((bits if order == "msb_left" else bits[::-1], count))
        if sum(c for _, c in converted) != shots:
            raise ValueError("shot total mismatch; postselection unsupported")
        return {"original": tuple(histogram.items()), "canonical": tuple(sorted(converted)),
                "width": width, "shots": shots, "encoding": encoding, "bit_order": order}

    if type(data) is list:
        if not data or type(spec["shots"]) is not list or len(data) != len(spec["shots"]):
            raise ValueError("batch shot totals required")
        return {"shape": "batch", "circuits": tuple(one(h, s) for h, s in zip(data, spec["shots"]))}
    return {"shape": "single", "circuits": (one(data, spec["shots"]),)}


class OfflineJob:
    """Own observations for a durable identity; never create a remote job.

    transport supplies get_job, cancel_job and get_job_result. clock and sleeper
    are injected to make fixture polling deterministic. snapshot returns a copy.
    """

    def __init__(self, handle, transport, clock, sleeper):
        self._handle = _handle(handle)
        self._transport, self._clock, self._sleep = transport, clock, sleeper
        self._state = {"remote_state": None, "local_wait_state": "idle",
                       "result_state": "not_requested", "cancellation_request": "not_requested",
                       "history": [], "last_error": None, "result_attempt_error": None,
                       "count_evidence": None}

    @classmethod
    def from_handle(cls, encoded, transport, clock, sleeper):
        if type(encoded) is not str or len(encoded) > 8192:
            raise ValueError("invalid encoded handle")
        try:
            value = json.loads(encoded, object_pairs_hook=_unique_object)
        except (ValueError, RecursionError):
            raise ValueError("invalid encoded handle") from None
        return cls(value, transport, clock, sleeper)

    @classmethod
    def record_submission_unknown(cls, *, source_id, device_id, client_correlation_id,
                                  transport, clock, sleeper):
        return cls({"schema": 1, "source_id": source_id, "provider": "qbraid-sdk",
                    "device_id": device_id, "job_id": None,
                    "client_correlation_id": client_correlation_id,
                    "submission_state": "outcome_unknown"}, transport, clock, sleeper)

    def export_handle(self):
        return json.dumps(self._handle, sort_keys=True, ensure_ascii=False)

    def snapshot(self):
        return copy.deepcopy(self._state)

    def _error(self, category, code=None):
        self._state["last_error"] = {"category": category, "http_status": code}
        return self._state["last_error"]

    def _request(self, operation):
        if self._handle["job_id"] is None:
            self._error("identity_unresolved")
            return False, None
        try:
            return True, getattr(self._transport, operation)(self._handle["job_id"])
        except TransportError as error:
            code = error.status_code if type(error.status_code) is int else None
            self._error(HTTP_ERRORS.get(code, "transport"), code if code in HTTP_ERRORS else None)
        except Exception:
            self._error("transport")
        return False, None

    def poll(self, timeout, interval, max_polls):
        if (not _positive(timeout) or not _positive(interval)
                or type(max_polls) is not int or max_polls <= 0):
            raise ValueError("invalid polling limits")
        start = self._clock()
        if not _finite(start) or not _finite(start + timeout):
            raise ValueError("invalid monotonic clock")
        deadline = start + timeout
        self._state["local_wait_state"] = "waiting"
        self._state["last_error"] = None
        previous_time = start
        for index in range(max_polls):
            now = self._clock()
            if not _finite(now) or now < previous_time:
                self._error("invalid_clock")
                self._state["local_wait_state"] = "error"
                break
            if now >= deadline:
                self._state["local_wait_state"] = "deadline"
                break
            ok, response = self._request("get_job")
            if not ok:
                self._state["local_wait_state"] = "error"
                break
            if (type(response) is not dict or set(response) != {"status"}
                    or type(response["status"]) is not str or response["status"] not in STATUSES):
                self._error("invalid_status")
                self._state["local_wait_state"] = "error"
                break
            observed = response["status"]
            self._state["history"].append(observed)
            old = self._state["remote_state"]
            if old in TERMINAL and old != observed:
                self._error("conflicting_status")
                self._state["local_wait_state"] = "conflict"
                break
            self._state["remote_state"] = observed
            after = self._clock()
            if not _finite(after) or after < now:
                self._error("invalid_clock")
                self._state["local_wait_state"] = "error"
                break
            previous_time = after
            if after >= deadline:
                self._state["local_wait_state"] = "deadline"
                break
            if observed in TERMINAL or observed == "HOLD":
                self._state["local_wait_state"] = "attention" if observed == "HOLD" else "finished"
                break
            if index + 1 == max_polls:
                self._state["local_wait_state"] = "poll_limit"
                break
            self._sleep(min(interval, deadline - after))
        return self.snapshot()

    def cancel(self):
        if self._state["remote_state"] in TERMINAL:
            return self.snapshot()
        self._state["last_error"] = None
        ok, response = self._request("cancel_job")
        if (ok and type(response) is dict and set(response) == {"acknowledged"}
                and response["acknowledged"] is True):
            self._state["cancellation_request"] = "acknowledged"
        else:
            if ok:
                self._error("invalid_cancel_response")
            category = self._state["last_error"]["category"]
            self._state["cancellation_request"] = (
                "rejected" if category in ("authentication", "access", "not_found", "throttled", "identity_unresolved")
                else "outcome_unknown")
        return self.snapshot()

    def fetch_counts(self, spec):
        self._state["last_error"] = None
        self._state["result_attempt_error"] = None
        if self._state["remote_state"] != "COMPLETED":
            self._error("not_completed")
            self._state["result_attempt_error"] = self._state["last_error"]
            if self._state["count_evidence"] is None:
                self._state["result_state"] = "unavailable"
            return self.snapshot()
        ok, response = self._request("get_job_result")
        if ok:
            try:
                if (type(response) is not dict or set(response) != {"experiment_type", "measurement_counts"}
                        or response["experiment_type"] != "gate_model"):
                    raise ValueError("unsupported result shape")
                evidence = _counts(response["measurement_counts"], spec)
            except (ValueError, TypeError):
                self._error("invalid_result")
                failed_state = "invalid"
            else:
                self._state["count_evidence"] = evidence
                self._state["result_state"] = "available"
                return self.snapshot()
        else:
            failed_state = "unavailable"
        self._state["result_attempt_error"] = self._state["last_error"]
        if self._state["count_evidence"] is None:
            self._state["result_state"] = failed_state
        return self.snapshot()
