"""Authored summary and controls, distinct from original notebook outputs."""
import json

if __name__ == "__main__":
    _timing_report = _timing_observer.summary()
    _timing_report['authored_layout_controls'] = authored_layout_controls(_timing_observer, _timing_reference)
    print(json.dumps(_timing_report, allow_nan=False))
