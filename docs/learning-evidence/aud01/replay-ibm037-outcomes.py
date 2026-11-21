"""Check the named-outcome examples against the lesson's two explicit basis states."""
import argparse
from learning_clipboard_checks import clipboard_checks
import json
import os
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("worker", type=Path)
parser.add_argument("--windows",type=Path,help="Prepare inputs for the Windows clipboard replay.")
parser.add_argument("--group",choices=("functions","matrices"),default="functions")
parser.add_argument("--report",type=Path,help="Verify the Windows records and write a report.")
args = parser.parse_args()
if not __debug__: raise RuntimeError("Assertions must be enabled.")
if args.report and not args.windows: parser.error("--report requires --windows")
worker = args.worker.resolve()
environment = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent / "data"))

def evaluate(source, field="copy_text"):
    process = subprocess.run([worker, "--json"], input=source.encode(), capture_output=True,
                             check=True, timeout=30, env=environment)
    result = json.loads(process.stdout)
    assert not result["approximate"], source
    return result[field]

inventory = json.loads(Path(__file__).with_name("ibm037-inventory.json").read_text(encoding="utf-8"))
heads, tails = evaluate("quantum:|0>"), evaluate("quantum:|1>")
assert heads == "matrix(2,1,[1,0])" and tails == "matrix(2,1,[0,1])"
for number in range(52, 58):
    row = inventory["rows"][number - 1]
    assert row["id"].endswith(f"M{number:03}")
    copied = evaluate("quantum:" + row["literal"])
    if number in (52, 54):
        for heads_value, expected in [(heads, "1"), (tails, "0")]:
            bound = copied
            for name in ("qnamedket", "qketstate"):
                bound = bound.replace(f'{name}("heads")', heads_value)
                bound = bound.replace(f'{name}("tails")', tails)
            assert evaluate(bound) == expected, row["id"]
    elif number == 53:
        assert evaluate(copied) == 'qset(vector(qoutcome("heads"),qoutcome("tails")))'
    else:
        assert evaluate(copied) == 'qketstate("tails")'
print("Verified six named-outcome examples and both negative controls")
coordinates = evaluate("quantum:" + inventory["rows"][96]["literal"])
assert coordinates == "qtuple(vector('b','a'))"
assert evaluate("quantum:(3,2)") == "qtuple(vector(3,2))"

# The fourth truth table sends both input bits to one.
chain = evaluate("quantum:" + inventory["rows"][106]["literal"])
assert chain.startswith("qequalchain(")
for zero_image, expected in [(tails, "1"), (heads, "0")]:
    bound = chain.replace('"M_4"', "matrix(2,2,[0,0,1,1])")
    bound = bound.replace('qstatecall("f_4",0)', zero_image)
    bound = bound.replace('qstatecall("f_4",1)', tails)
    assert evaluate(bound) == expected
print("Verified ordered coordinates and the constant-one map")
tables = evaluate("quantum:" + inventory["rows"][66]["literal"])
assert evaluate(tables) == tables
expected_tables = []
for number, (at_zero, at_one) in enumerate([(0,0), (0,1), (1,0), (1,1)], 1):
    expected_tables.append(f"""matrix(3,2,['a',"f_{number}(a)",0,{at_zero},1,{at_one}])""")
assert tables == "vector(" + ",".join(expected_tables) + ")"
print("Verified all eight function values and their table headings")
composition = evaluate("quantum:" + inventory["rows"][147]["literal"])
matrix_cases = {"M148":(inventory["rows"][147]["literal"],composition)}
assert evaluate("quantum:" + composition) == composition
reset = "matrix(2,2,[1,1,0,0])"
flip = "matrix(2,2,[0,1,1,0])"
for first, second, expected in [(reset,flip,"matrix(2,2,[0,0,1,1])"), (flip,reset,reset)]:
    assigned = f'replace(replace({composition},"M_1",{first}),"M_2",{second})'
    assert evaluate(f"quantum:replace({assigned},n,2)") == expected
    assert evaluate(f"quantum:replace({assigned},n,1)") == first
    label = "reset-first" if first==reset else "flip-first"
    for n,value in ((1,first),(2,expected)):
        matrix_cases[f"M148-{label}-{n}"]=(f"replace({assigned},n,{n})",value)
print("Verified ordered matrix composition, reversed order and single-map bounds")

# M021 defines the classical system's four possible outcomes. Keep each
# complete printed word distinct from the product of its component letters.
outcome_definition = inventory["rows"][20]
assert outcome_definition["id"].endswith("M021")
definition = evaluate("quantum:" + outcome_definition["literal"])
domain_source = outcome_definition["literal"].strip("$").split("=")[1]
domain = evaluate("quantum:$" + domain_source + "$")
assert domain == 'qset(vector(qoutcome("high"),qoutcome("medium"),qoutcome("low"),qoutcome("off")))' and domain in definition
assert evaluate(domain) == domain
displayed = evaluate(domain, "display_text")
assert evaluate("quantum:" + displayed) == domain
assert evaluate(f"qmember(0,{domain})") == "0"
for name in ("high", "medium", "low", "off"):
    assert evaluate(fr"quantum:$\mathrm{{{name}}}\in {domain_source}$") == "1"
assert evaluate(fr"quantum:$\mathrm{{other}}\in {domain_source}$") == "0"
assert evaluate(f'quantum:cardinality({domain})') == "4"
print("Verified all four named outcomes from M021, including Copy re-entry")

# Bind the function names to the graphs printed in M067. Toggling both
# outputs produces a counterexample on each input, including constant maps.
functions = [(0,0), (0,1), (1,0), (1,1)]
windows_cases = {"M067": (inventory["rows"][66]["literal"],tables)}
for row_number, function_number, inputs in [(68,1,[0,1]), (69,4,[0,1]), (72,2,[0,1]),
                                           (75,3,[0]), (76,3,[1])]:
    row = inventory["rows"][row_number - 1]
    assert row["id"].endswith(f"M{row_number:03}")
    copied = evaluate("quantum:" + row["literal"])
    windows_cases[row["id"]] = (row["literal"],copied)
    for bit in inputs:
        for toggle in (0,1):
            zero, one = (value ^ toggle for value in functions[function_number-1])
            graph = f"qset(vector(tuple(0,{zero}),tuple(1,{one})))"
            bound = f'replace(({copied}),"f_{function_number}",{graph})'
            if "(a)" in row["literal"]:
                bound = f"replace({bound},a,{bit})"
            assert evaluate("quantum:" + bound) == str(1-toggle), (row["id"],bit,toggle)
            windows_cases[f'M{row_number:03}-bit-{bit}-toggle-{toggle}'] = (bound,str(1-toggle))
for pairs, key in [("tuple(0,0),tuple(0,1)",0), ("tuple(0,1),tuple(1,0)",2)]:
    expr = f"quantum:qfiniteapply(qset(vector({pairs})),{key})"
    process = subprocess.run([worker,"--json"],input=expr.encode(),env=environment,capture_output=True,timeout=30)
    assert process.returncode == 2 and process.stderr.strip(), expr
print("Verified the five indexed function equations on all eight inputs, including changed and invalid graphs")

# Substitute the column and the map(s) together. Both operand orders must
# remain distinct when the expression is copied before any assignments.
def bind_maps(value, bindings):
    for name, replacement in bindings:
        value = f'replace(({value}),{name},{replacement})'
    return value

column = ("u","[3/5;2/5]")
forward = [('"M_1"',reset),('"M_2"',flip)]
reverse = [('"M_1"',flip),('"M_2"',reset)]
for number, normal, swapped in [(138, "matrix(2,1,[1,0])", "matrix(2,1,[2 ∕ 5,3 ∕ 5])"),
                                (140, "1", "1"),
                                (143, "matrix(2,2,[0,0,1,1])", reset),
                                (150, "1", "0")]:
    source = inventory["rows"][number-1]["literal"]
    result = evaluate("quantum:" + source)
    matrix_cases[f"M{number}"]=(source,result)
    for maps,expected in [(forward,normal),(reverse,swapped)]:
        bindings = maps[:1] + [column] if number==138 else maps + [column] if number==140 else maps
        for direction,order in (("direct",bindings),("reversed",reversed(bindings))):
            expr=bind_maps(result,order)
            assert evaluate("quantum:"+expr)==expected,number
            label="reset-first" if maps==forward else "flip-first"
            matrix_cases[f"M{number}-{label}-{direction}"]=(expr,expected)
    if number==140:
        changed = evaluate("quantum:" + source.replace("M_2 M_1","M_1 M_2"))
        expr=bind_maps(changed,forward+[column])
        assert evaluate("quantum:"+expr)=="0"
        matrix_cases["M140-reversed-product"]=(expr,"0")
print("Verified four ordered matrix expressions with both map assignments")
if args.windows:
    if args.group=="matrices":
        windows_cases=matrix_cases
        details=dict(source_spans=[138,140,143,148,150],bound_expressions=21)
    else:
        details=dict(source_spans=[67,68,69,72,75,76],finite_inputs=8,changed_graph_controls=8,invalid_graph_controls=2)
    clipboard_checks(worker,args.windows,args.report,windows_cases,26 if args.group=="matrices" else 22,details)
