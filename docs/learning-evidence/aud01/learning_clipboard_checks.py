"""Prepare and verify actual Windows sessions for named exact-result cases."""
import hashlib
import json

def clipboard_checks(worker,directory,report_path,cases,expected_count,details,*,sessions_only=False):
    if not __debug__: raise RuntimeError("Assertions must be enabled.")
    inputs = [[key,expr,"0"] for key,(expr,_) in cases.items()]
    path = directory/"inputs.json"
    if not report_path:
        directory.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(inputs),"utf8")
    else:
        assert json.loads(path.read_bytes())==inputs
        records = json.loads((directory/"records.json").read_text("utf-8-sig"))
        result = json.loads((directory/"result.json").read_text("utf-8-sig"))
        assert result["passed"] and result["sessionsOnly"]==sessions_only
        if not sessions_only:
            assert result["clipboardRestored"]
        assert len(records)==result["calls"]==len(inputs)==expected_count
        for (key,expr,_),record in zip(inputs,records):
            session=json.loads((directory/(key+".qsession")).read_text("utf-8-sig"))
            assert session["Expression"]==expr and session["Mode"]==0
            assert record["id"]==key and record["restored_same"]
            if sessions_only:
                assert record["label"]==record["reentry_label"]=="EXACT RESULT"
                assert record["copy_text"]==record["reentry_text"]==cases[key][1],key
            else:
                assert record["copy"]==record["second_copy"]==cases[key][1],key
        session_counts = dict(windows_sessions=len(inputs),clipboard_verified=False) if sessions_only else dict(clipboard_sessions=len(inputs))
        report=dict(worker_sha256=hashlib.sha256(worker.read_bytes()).hexdigest(),**details,
                    **session_counts,windows_checks=result["checks"])
        report_path.write_text(json.dumps(report,indent=2)+"\n","utf8")
