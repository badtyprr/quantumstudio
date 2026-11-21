"""Prepare and verify actual Windows sessions for named exact-result cases."""
import hashlib
import json

def clipboard_checks(worker,directory,report_path,cases,expected_count,details):
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
        assert result["passed"] and result["clipboardRestored"] and not result["sessionsOnly"]
        assert len(records)==result["calls"]==len(inputs)==expected_count
        for (key,expr,_),record in zip(inputs,records):
            session=json.loads((directory/(key+".qsession")).read_text("utf-8-sig"))
            assert session["Expression"]==expr and session["Mode"]==0
            assert record["id"]==key and record["restored_same"]
            assert record["copy"]==record["second_copy"]==cases[key][1],key
        report=dict(worker_sha256=hashlib.sha256(worker.read_bytes()).hexdigest(),**details,
                    clipboard_sessions=len(inputs),windows_checks=result["checks"])
        report_path.write_text(json.dumps(report,indent=2)+"\n","utf8")
