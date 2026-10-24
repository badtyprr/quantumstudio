OPENQASM 3.0;
include "stdgates.inc";
const int n = 2;
def parity(bit[n] cin) -> bit {
  bit c;
  for int i in [0: n - 1] {
    c ^= cin[i];
  }
  return c;
}
qubit q;
qubit r;
bit c;
bit c2;
output bit result;
h q;
h r;
c = measure q;
c2 = measure r;
result = parity(c ++ c2);
