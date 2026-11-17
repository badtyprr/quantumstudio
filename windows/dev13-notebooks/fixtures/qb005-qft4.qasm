OPENQASM 3.0;
include "stdgates.inc";
qubit[4] qb;
bit[4] cb;
gate QFT4S aa, ab, ac, ad {
  h aa;
  cp(pi / 2) aa, ab;
  cp(pi / 4) aa, ac;
  cp(pi / 8) aa, ad;
  h ab;
  cp(pi / 2) ab, ac;
  cp(pi / 4) ab, ad;
  h ac;
  cp(pi / 2) ac, ad;
  h ad;
  swap ad, aa;
  swap ac, ab;
}
QFT4S qb[0], qb[1], qb[2], qb[3];
