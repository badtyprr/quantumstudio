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

bit_domain=run(rows[72]["literal"])
for values,expected in [([0],"1"),([2],"0"),([1,0,1],"1"),([1,2,0],"0")]:
    bindings=[('"r"',str(len(values)))]
    bindings.extend((f'"a_{index}"',str(value)) for index,value in enumerate(values,1))
    assert bind(bit_domain,bindings)==expected,(values,expected)
print("Verified indexed bit membership with singleton and multi-element domains.")
fixed=run(rows[7]["literal"])
definition=run(rows[13]["literal"])
for state,expected in (("|00>","1"),("|01>","0"),("|10>","0"),("|11>","0")):
    generators=[('"r"',"2"),('"P_1"',"Z@I"),('"P_2"',"I@Z")]
    actual=bind(fixed,generators+[('qnamedket("ψ")',state)])
    assert actual==expected,(state,actual)
    space="qfixedspace(vector(Z@I,I@Z))"
    assert run(f"qmember({state},{space})")==expected
assert bind(definition,generators+[('"C"',space)])=="1"
print("Verified the fixed-space definition and membership of all four two-qubit basis states.")

def condition(row, generators, probe=None):
    bindings=[('"r"',str(len(generators)))]
    bindings.extend((f'"P_{i}"',g) for i,g in enumerate(generators,1))
    if probe is not None:bindings.append(('"E"',probe))
    return bind(run(rows[row-1]["literal"]),bindings)

assert condition(4,["Z@I","I@Z"])=="1"
assert condition(4,["X","Z"])=="0"
assert condition(5,["X","Z"])=="1"
assert condition(5,["X","Z","X*Z"])=="0"
assert condition(5,["Z","-Z"])=="1"
for error,signed,logical,anti in [("Z@I","1","0","0"),("-(Z@I)","1","0","0"),
                                   ("I@Z","0","1","0"),("X@I","0","0","1")]:
    assert condition(165,["Z@I"],error)==signed
    assert condition(170,["Z@I"],error)==logical
    assert condition(175,["Z@I"],error)==anti
print("Verified quantified generator commutation, phase-sensitive independence and the three error classes.")

for gates in (["Z@I"],["Z@I","I@Z"]):
    space="qfixedspace(vector("+",".join(gates)+"))"
    for row in (89,91,102):
        expression=run(rows[row-1]["literal"])
        supplied=[('"r"',str(len(gates))),("n","2"),('"C"',space)]
        supplied.extend((f'"P_{i}"',g) for i,g in enumerate(gates,1))
        supplied.extend((f'"Π_{i}"',f"((I@I)+({g}))/2") for i,g in enumerate(gates,1))
        assert bind(expression,supplied)=="1",(row,gates)
assert run("qbinarypowersum(vector(X,Z))==(I+X)*(I+Z)")=="1"
assert run("qbinarypowersum(vector(X,Z))==(I+Z)*(I+X)")=="0"
assert run("qspacedimension(qfixedspace(vector(X,Z)))")=="0"
assert run("qspacedimension(qfixedspace(vector(Z,-Z)))")=="0"
print("Verified both projector derivations and the dimension chain for one and two generators.")
