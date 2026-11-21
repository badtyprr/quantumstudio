import pathlib,json,os,subprocess,sys
path=pathlib.Path(sys.argv[1]).resolve()
env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(path.parent/"data"))
def run(x):
    p=subprocess.run([path,"--json"],input=("quantum:"+x).encode(),capture_output=True,env=env,check=True,timeout=30)
    return json.loads(p.stdout)["copy_text"]
rows=json.loads((pathlib.Path(__file__).parent/"ibm060-inventory.json").read_bytes())["rows"]
for row,rank in ((44,8),(45,6),(53,4),(201,6)):
    data=run(rows[row-1]["literal"])
    assert run(f"qcompactrank({data})")==str(rank)
    assert run(f"qcompactdimension({data})")=="2"
    assert run(f"qcompactdistance({data},3)")=="3"
print("Verified the Shor, Steane and five-qubit generator tables have dimension two and distance three.")
