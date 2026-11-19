"""Check both outcome branches of IBM-024's deferred-measurement diagram."""
import json
from pathlib import Path
import subprocess
import sys

worker = Path(sys.argv[1]).resolve()


def equal(left, right):
    result = subprocess.run([worker, "--json"], input=f"quantum:({left})=({right})".encode(),
                            capture_output=True, check=True, timeout=15)
    answer = json.loads(result.stdout)
    assert not answer["approximate"] and answer["copy_text"] == "1", (left, right, answer)


# Their density matrices span the real space of Hermitian 2-by-2 matrices.
# Equality on these four inputs establishes equality of the linear branch maps.
for ket in ("|0>", "|1>", "|+>", "([1;i]/sqrt(2))"):
    copied = f"CNOT*({ket}@|0>)"
    for bit in (0, 1):
        projector = f"density(|{bit}>)"
        branch = f"({projector}*density({ket})*{projector})"
        readout = f"(I@{projector})"
        # The trace of this subnormalized joint state is the outcome probability.
        equal(f"density({readout}*{copied})", f"{branch}@{projector}")
        # Delay the bottom-wire readout past H on the data and a Z controlled
        # by the record. Compare with conditioning Z on the classical result.
        gate = "I" if bit == 0 else "Z"
        equal(f"density({readout}*CZ*(H@I)*{copied})",
              f"({gate}*H*{branch}*H*{gate})@{projector}")

print("Verified both outcome branches for four spanning input states, before and after controlled feedback.")
