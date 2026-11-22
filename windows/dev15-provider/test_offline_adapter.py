"""Forty source-bound, authored scenarios. No live service or SDK imports."""

import copy
import hashlib
import json
from pathlib import Path
import unittest

from offline_adapter import OfflineJob, TransportError


FIXTURE_DIGEST = "704b22b2cec12857518b217c9fc47c423eb0d285f0b30410a83d6d5ca2a34361"
DOCUMENT = json.loads(Path(__file__).with_name("fixtures.json").read_text(encoding="utf-8"))
FIXTURES = DOCUMENT["payload"]
actual_digest = hashlib.sha256(json.dumps(FIXTURES, sort_keys=True, separators=(",", ":"),
                                        ensure_ascii=False).encode()).hexdigest()
if actual_digest != FIXTURE_DIGEST or DOCUMENT["payload_sha256"] != FIXTURE_DIGEST:
    raise ValueError("fixture manifest mismatch")
SPEC = {"width": 2, "shots": 10, "encoding": "binary", "bit_order": "msb_left"}


def result(counts):
    return {"experiment_type": "gate_model", "measurement_counts": counts}


class Clock:
    def __init__(self, constant=False):
        self.time, self.constant, self.sleeps = 0, constant, []

    def now(self):
        return self.time

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        if not self.constant:
            self.time += seconds


class Transport:
    """Finite fixture queues; exhaustion raises instead of hiding extra requests."""
    def __init__(self, states=(), results=(), cancellations=()):
        self.queues = {"get_job": list(states), "get_job_result": list(results),
                       "cancel_job": list(cancellations)}
        self.calls = []

    def take(self, operation, job_id):
        self.calls.append((operation, job_id))
        value = self.queues[operation].pop(0)
        if isinstance(value, Exception):
            raise value
        return value

    def get_job(self, job_id):
        value = self.take("get_job", job_id)
        return {"status": value} if isinstance(value, str) else value

    def get_job_result(self, job_id):
        return self.take("get_job_result", job_id)

    def cancel_job(self, job_id):
        return self.take("cancel_job", job_id)


class Cases(unittest.TestCase):
    def make(self, states=(), results=(), cancellations=(), constant=False):
        self.clock = Clock(constant)
        self.transport = Transport(states, results, cancellations)
        self.job = OfflineJob(copy.deepcopy(FIXTURES["handle"]), self.transport,
                              self.clock.now, self.clock.sleep)
        return self.job

    def complete(self, counts=None):
        self.make(["COMPLETED"], [result(FIXTURES["binary_counts"] if counts is None else counts)])
        self.job.poll(10, 1, 10)

    def calls(self, *operations):
        self.assertEqual(self.transport.calls, [(op, "fixture-job") for op in operations])

    def test_L01_history(self):
        states = ["INITIALIZING", "QUEUED", "RUNNING", "COMPLETED"]
        self.make(states)
        s = self.job.poll(10, 1, 10)
        self.assertEqual(s["history"], states)
        self.assertEqual(s["local_wait_state"], "finished")
        self.calls(*(["get_job"] * 4))

    def test_L02_deadline_preserves_handle(self):
        self.make(["RUNNING"] * 2)
        handle = self.job.export_handle()
        s = self.job.poll(2, 1, 10)
        self.assertEqual((s["local_wait_state"], s["remote_state"]), ("deadline", "RUNNING"))
        self.assertEqual(self.job.export_handle(), handle)
        self.assertEqual(self.clock.sleeps, [1, 1])
        self.calls("get_job", "get_job")
        with self.subTest(response="after deadline"):
            self.make(["COMPLETED"])
            original_get = self.transport.get_job
            def delayed_get(job_id):
                self.clock.time += 3
                return original_get(job_id)
            self.transport.get_job = delayed_get
            s = self.job.poll(2, 1, 10)
            self.assertEqual((s["remote_state"], s["local_wait_state"]), ("COMPLETED", "deadline"))
            self.assertEqual(self.clock.sleeps, [])
            self.calls("get_job")

    def test_L03_constant_clock(self):
        self.make(["RUNNING"] * 3, constant=True)
        self.assertEqual(self.job.poll(10, 1, 3)["local_wait_state"], "poll_limit")
        self.calls(*(["get_job"] * 3))

    def test_L04_bad_limits(self):
        for field in ("timeout", "interval", "max_polls"):
            values = [0, -1, True, None, "1", float("inf"), float("nan")]
            if field != "max_polls":
                values += [10 ** 400]
            if field == "max_polls":
                values += [1.5]
            for value in values:
                with self.subTest(field=field, value=value):
                    self.make()
                    args = dict(timeout=10, interval=1, max_polls=10)
                    args[field] = value
                    with self.assertRaises(ValueError):
                        self.job.poll(**args)
                    self.calls()

    def test_L05_pending_then_cancelled(self):
        self.make(["CANCELLING", "CANCELLED"], cancellations=[{"acknowledged": True}])
        s = self.job.cancel()
        self.assertIsNone(s["remote_state"])
        self.assertEqual(s["cancellation_request"], "acknowledged")
        s = self.job.poll(10, 1, 1)
        self.assertEqual((s["remote_state"], s["local_wait_state"]), ("CANCELLING", "poll_limit"))
        self.assertEqual(self.job.poll(10, 1, 1)["remote_state"], "CANCELLED")
        self.calls("cancel_job", "get_job", "get_job")

    def test_L06_completion_race(self):
        self.make(["COMPLETED"], [result({"01": 10})], [{"acknowledged": True}])
        self.job.cancel()
        self.job.poll(10, 1, 10)
        s = self.job.fetch_counts(SPEC)
        self.assertEqual((s["remote_state"], s["result_state"]), ("COMPLETED", "available"))
        self.calls("cancel_job", "get_job", "get_job_result")

    def test_L07_terminal_cancel(self):
        for status in ("COMPLETED", "CANCELLED", "FAILED"):
            with self.subTest(status=status):
                self.make([status])
                self.job.poll(10, 1, 10)
                self.assertEqual(self.job.cancel()["cancellation_request"], "not_requested")
                self.calls("get_job")

    def test_L08_lost_cancel_response(self):
        self.make(["RUNNING"], cancellations=[TimeoutError("SECRET")])
        self.job.poll(10, 1, 1)
        s = self.job.cancel()
        self.assertEqual((s["remote_state"], s["cancellation_request"]), ("RUNNING", "outcome_unknown"))
        self.assertNotIn("SECRET", repr(s))
        self.calls("get_job", "cancel_job")
        for response in [{"acknowledged": 1}, {"acknowledged": False}, None]:
            with self.subTest(malformed_ack=response):
                self.make(cancellations=[response])
                self.assertEqual(self.job.cancel()["cancellation_request"], "outcome_unknown")
                self.calls("cancel_job")

    def test_L09_terminal_conflicts(self):
        for status in ("RUNNING", "FAILED"):
            with self.subTest(status=status):
                self.make(["COMPLETED", status])
                self.job.poll(10, 1, 10)
                s = self.job.poll(10, 1, 10)
                self.assertEqual((s["remote_state"], s["local_wait_state"]), ("COMPLETED", "conflict"))
                self.assertEqual(s["history"], ["COMPLETED", status])
                self.calls("get_job", "get_job")

    def test_L10_resolve_hold(self):
        self.make(["HOLD", "RUNNING", "COMPLETED"])
        self.assertEqual(self.job.poll(10, 1, 10)["local_wait_state"], "attention")
        self.assertEqual(self.job.poll(10, 1, 10)["remote_state"], "COMPLETED")
        self.calls("get_job", "get_job", "get_job")

    def test_C01_original_asymmetry(self):
        self.complete()
        s = self.job.fetch_counts(SPEC)
        evidence = s["count_evidence"]["circuits"][0]
        self.assertEqual(evidence["original"], (("01", 7), ("10", 3), ("00", 0)))
        self.assertEqual(evidence["canonical"], (("00", 0), ("01", 7), ("10", 3)))
        self.calls("get_job", "get_job_result")

    def test_C02_reverse_bits(self):
        self.complete()
        s = self.job.fetch_counts(dict(SPEC, bit_order="lsb_left"))
        self.assertEqual(s["count_evidence"]["circuits"][0]["canonical"], (("00", 0), ("01", 3), ("10", 7)))
        self.calls("get_job", "get_job_result")

    def test_C03_decimal_padding(self):
        for order, expected in [("msb_left", (("001", 7), ("010", 3))),
                                ("lsb_left", (("010", 3), ("100", 7)))]:
            with self.subTest(order=order):
                self.complete({1: 7, 2: 3})
                s = self.job.fetch_counts(dict(SPEC, encoding="decimal", width=3, bit_order=order))
                self.assertEqual(s["count_evidence"]["circuits"][0]["canonical"], expected)
                self.calls("get_job", "get_job_result")

    def test_C04_batch_positions(self):
        self.complete([{"01": 3}, {"10": 7}])
        s = self.job.fetch_counts(dict(SPEC, shots=[3, 7]))
        self.assertEqual(s["count_evidence"]["shape"], "batch")
        self.assertEqual([c["canonical"] for c in s["count_evidence"]["circuits"]],
                         [(("01", 3),), (("10", 7),)])
        self.calls("get_job", "get_job_result")

    def invalid_result(self, data, spec):
        self.complete(data)
        s = self.job.fetch_counts(spec)
        self.assertEqual((s["remote_state"], s["result_state"]), ("COMPLETED", "invalid"))
        self.assertIsNone(s["count_evidence"])
        self.calls("get_job", "get_job_result")

    def test_C05_bad_keys(self):
        for encoding, keys in [("binary", ["1", "001", "0 1", "0b01", "０１", "02", 1, True]),
                               ("decimal", [-1, 4, "1", True, 1.0])]:
            for key in keys:
                with self.subTest(encoding=encoding, key=key):
                    self.invalid_result({key: 10}, dict(SPEC, encoding=encoding))

    def test_C06_bad_counts_and_shots(self):
        for value in [-1, True, 10.0, "10", None, 9, 11]:
            with self.subTest(count=value):
                self.invalid_result({"01": value}, SPEC)
        for shots in [0, -1, True, 10.0, "10", None]:
            with self.subTest(shots=shots):
                self.invalid_result({"01": 10}, dict(SPEC, shots=shots))

    def test_C07_bad_shapes_and_specs(self):
        for data, shots in [({}, 10), ([], []), (({"01": 10},), 10),
                            ([[{"01": 10}]], [10]), ([{"01": 10}], []),
                            ([{"01": 10}], 10), ({"01": 10}, [10])]:
            with self.subTest(data=data, shots=shots):
                self.invalid_result(data, dict(SPEC, shots=shots))
        for field, values in [("width", [0, 4097, True, 2.0, None]),
                              ("encoding", ["hex", None]), ("bit_order", [None, "auto"])]:
            for value in values:
                with self.subTest(field=field, value=value):
                    self.invalid_result({"01": 10}, dict(SPEC, **{field: value}))
        with self.subTest(missing="width"):
            self.invalid_result({"01": 10}, {k: v for k, v in SPEC.items() if k != "width"})
        with self.subTest(data="null"):
            self.make(["COMPLETED"], [result(None)])
            self.job.poll(10, 1, 10)
            self.assertEqual(self.job.fetch_counts(SPEC)["result_state"], "invalid")
            self.calls("get_job", "get_job_result")

    def test_C08_immutable_evidence(self):
        data = {"01": 10}
        self.make(["COMPLETED"], [result(data), result({"01": -1})])
        self.job.poll(10, 1, 10)
        first = self.job.fetch_counts(SPEC)
        expected = copy.deepcopy(first["count_evidence"])
        data["01"] = 0
        first["count_evidence"]["shape"] = "tampered"
        second = self.job.fetch_counts(SPEC)
        self.assertEqual(second["count_evidence"], expected)
        self.assertEqual(second["result_state"], "available")
        self.assertEqual(second["result_attempt_error"]["category"], "invalid_result")
        self.calls("get_job", "get_job_result", "get_job_result")

    def test_H01_roundtrip(self):
        self.make()
        restored = OfflineJob.from_handle(self.job.export_handle(), self.transport, self.clock.now, self.clock.sleep)
        self.assertEqual(json.loads(restored.export_handle()), FIXTURES["handle"])
        self.calls()

    def test_H02_unknown_submission(self):
        self.make()
        job = OfflineJob.record_submission_unknown(source_id="QB-SYNTHETIC", device_id="fixture-device",
            client_correlation_id="fixture-correlation", transport=self.transport,
            clock=self.clock.now, sleeper=self.clock.sleep)
        self.assertEqual(job.poll(10, 1, 10)["last_error"]["category"], "identity_unresolved")
        self.assertEqual(job.cancel()["cancellation_request"], "rejected")
        self.assertEqual(job.fetch_counts(SPEC)["result_state"], "unavailable")
        self.assertFalse(hasattr(job, "submit"))
        self.assertEqual(json.loads(job.export_handle())["submission_state"], "outcome_unknown")
        self.calls()

    def reject_handle(self, value):
        self.make()
        with self.assertRaises(ValueError) as caught:
            OfflineJob(value, self.transport, self.clock.now, self.clock.sleep)
        self.assertNotIn("SECRET", str(caught.exception))
        self.calls()

    def test_H03_schema_and_sensitive_fields(self):
        for field, value in [("schema", 2), ("schema", True), ("headers", "SECRET"),
                             ("token", "SECRET"), ("credentials", "SECRET")]:
            with self.subTest(field=field, value=value):
                self.reject_handle(dict(FIXTURES["handle"], **{field: value}))
        with self.subTest(duplicate="schema"):
            self.make()
            with self.assertRaises(ValueError):
                OfflineJob.from_handle('{"schema":1,"schema":2}', self.transport, self.clock.now, self.clock.sleep)
            self.calls()

    def test_H04_invalid_identity(self):
        for field in ("source_id", "device_id", "job_id"):
            for value in [None, "", " ", "x" * 257, 1, "bad\nidentity"]:
                with self.subTest(field=field, value=value):
                    self.reject_handle(dict(FIXTURES["handle"], **{field: value}))
        for value in [dict(FIXTURES["handle"], submission_state="unknown"),
                      dict(FIXTURES["handle"], submission_state="outcome_unknown", client_correlation_id=None),
                      {k: v for k, v in FIXTURES["handle"].items() if k != "device_id"}]:
            with self.subTest(handle=value):
                self.reject_handle(value)

    def test_H05_restore_does_not_confirm(self):
        self.make(["RUNNING"])
        restored = OfflineJob.from_handle(self.job.export_handle(), self.transport, self.clock.now, self.clock.sleep)
        self.assertIsNone(restored.snapshot()["remote_state"])
        self.calls()
        self.assertEqual(restored.poll(10, 1, 1)["remote_state"], "RUNNING")
        self.calls("get_job")

    def test_E05_result_unavailable(self):
        self.make(["COMPLETED"], [TransportError(404)])
        self.job.poll(10, 1, 10)
        s = self.job.fetch_counts(SPEC)
        self.assertEqual((s["remote_state"], s["result_state"]), ("COMPLETED", "unavailable"))
        self.assertIsNone(s["count_evidence"])
        self.calls("get_job", "get_job_result")

    def test_E06_explicit_read_retry(self):
        self.make(["COMPLETED"], [TransportError(404), result({"01": 10})])
        self.job.poll(10, 1, 10)
        self.job.fetch_counts(SPEC)
        self.calls("get_job", "get_job_result")
        self.assertEqual(self.job.fetch_counts(SPEC)["result_state"], "available")
        self.calls("get_job", "get_job_result", "get_job_result")

    def test_E07_unknown_and_unsupported(self):
        for response in ["FUTURE_STATE", {"status": []}, RuntimeError("SECRET")]:
            with self.subTest(response=repr(response)):
                self.make(["COMPLETED", response], [result({"01": 10})])
                self.job.poll(10, 1, 10)
                before = self.job.fetch_counts(SPEC)["count_evidence"]
                s = self.job.poll(10, 1, 10)
                self.assertEqual(s["local_wait_state"], "error")
                self.assertEqual(s["count_evidence"], before)
                self.assertNotIn("SECRET", repr(s))
                self.calls("get_job", "get_job_result", "get_job")
        with self.subTest(result="analog"):
            self.make(["COMPLETED"], [result({"01": 10}), {"experiment_type": "analog", "measurement_counts": {"01": 10}}])
            self.job.poll(10, 1, 10)
            before = self.job.fetch_counts(SPEC)["count_evidence"]
            s = self.job.fetch_counts(SPEC)
            self.assertEqual(s["count_evidence"], before)
            self.assertEqual(s["result_attempt_error"]["category"], "invalid_result")
            self.calls("get_job", "get_job_result", "get_job_result")


def status_case(status, expected):
    def run(self):
        self.make([status] * 2)
        s = self.job.poll(2, 1, 10)
        self.assertEqual((s["remote_state"], s["local_wait_state"]), (status, expected))
        self.assertEqual(s["result_state"], "not_requested")
        self.assertEqual(s["cancellation_request"], "not_requested")
        self.calls(*(["get_job"] * (2 if expected == "deadline" else 1)))
    return run


def error_case(code, category):
    def run(self):
        error = TransportError(code)
        error.args = ("SECRET",)
        self.make([error])
        before = self.job.export_handle()
        s = self.job.poll(10, 1, 10)
        self.assertEqual(s["last_error"], {"category": category, "http_status": code})
        self.assertEqual(s["local_wait_state"], "error")
        self.assertIsNone(s["remote_state"])
        self.assertEqual(self.job.export_handle(), before)
        self.assertNotIn("SECRET", repr(s))
        self.assertEqual(self.clock.sleeps, [])
        self.calls("get_job")
    return run


for scenario, status, expected in FIXTURES["statuses"]:
    setattr(Cases, f"test_{scenario}_{status}", status_case(status, expected))
for scenario, code, category in FIXTURES["errors"]:
    setattr(Cases, f"test_{scenario}_{category}", error_case(code, category))


class VerboseSubtests(unittest.TextTestResult):
    def addSubTest(self, test, subtest, err):
        super().addSubTest(test, subtest, err)
        if err is None:
            self.stream.writeln(f"  PASS {subtest.id()}")


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(Cases)
    identifiers = sorted(test.id().split("test_", 1)[1].split("_", 1)[0] for test in suite)
    if identifiers != sorted(FIXTURES["scenario_ids"]):
        raise ValueError("scenario coverage differs from frozen matrix")
    outcome = unittest.TextTestRunner(verbosity=2, resultclass=VerboseSubtests).run(suite)
    raise SystemExit(not outcome.wasSuccessful())
