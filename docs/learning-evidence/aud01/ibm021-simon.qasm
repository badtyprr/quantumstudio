OPENQASM 3.0;
include "stdgates.inc";

// Reversible XOR oracle for the eight function values printed in the lesson.
// a0 and b0 are the least significant bits of the input and output words.
gate simon a0, a1, a2, b0, b1, b2, b3, b4 {
    x b0;
    x b1;
    x b4;
    cx a0, b1;
    cx a0, b2;
    cx a0, b4;
    cx a1, b1;
    cx a1, b2;
    cx a1, b4;
    cx a2, b0;
    cx a2, b3;
    ccx a0, a2, b0;
    ccx a0, a2, b2;
    ccx a0, a2, b3;
    ccx a1, a2, b0;
    ccx a1, a2, b2;
    ccx a1, a2, b3;
}

qubit[3] a;
qubit[5] b;
bit[3] y;

h a;
simon a[0], a[1], a[2], b[0], b[1], b[2], b[3], b[4];
h a;
y = measure a;
