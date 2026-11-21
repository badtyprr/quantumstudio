import pathlib,json,os,subprocess,sys
path=pathlib.Path(sys.argv[1]).resolve()
env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(path.parent/"data"))
def run(x):
    p=subprocess.run([path,"--json"],input=("quantum:"+x).encode(),capture_output=True,env=env,timeout=30)
    assert p.returncode==0,(x,p.stderr.decode())
    return json.loads(p.stdout)["copy_text"]
rows=json.loads((pathlib.Path(__file__).parent/"ibm060-inventory.json").read_bytes())["rows"]
for row,rank in ((44,8),(45,6),(53,4),(201,6)):
    data=run(rows[row-1]["literal"])
    assert run(f"qcompactrank({data})")==str(rank)
    assert run(f"qcompactdimension({data})")=="2"
    assert run(f"qcompactdistance({data},3)")=="3"
print("Verified the Shor, Steane and five-qubit generator tables have dimension two and distance three.")

def bind(expression, bindings):
    for name,value in bindings:
        expression=run(f"replace(({expression}),{name},{value})")
    return expression

signed_operator=run(rows[112]["literal"])
for target,expected in (("Z","1"),("-Z","1"),("X","0")):
    assert bind(signed_operator,[('"U"',"H"),('"P"',"X"),('"Q"',target)])==expected
signed_state=run(rows[178]["literal"])
for state,expected in (("|0>","1"),("|1>","1"),("|+>","0")):
    assert bind(signed_state,[('"E"',"Z"),('qnamedket("ψ")',state)])==expected
print("Verified both allowed signs of the operator and state equations and rejected incorrect images.")
product=run(rows[71]["literal"])
for bits,wanted in [((0,0),"I"),((1,0),"X"),((0,1),"Z"),((1,1),"X*Z")]:
    factors=[('"r"',"2"),('"P_1"',"X"),('"P_2"',"Z"),('"a_1"',str(bits[0])),('"a_2"',str(bits[1]))]
    actual=bind(product,factors)
    assert run(f"({actual})==({wanted})")=="1",(bits,actual)
    if bits==(1,1):assert run(f"({actual})==(Z*X)")=="0"
print("Verified the indexed matrix product preserves exponent selection and noncommuting factor order.")
