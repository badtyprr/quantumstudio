"""Independent integer checks for the original factoring and GCD examples."""
import json


def euclid(left, right):
    while right:
        left, right = right, left % right
    return left


if __name__ == "__main__":
    divisor = euclid(N, M)
    if divisor != RSA1024 or RSA250 != p * q:
        raise ValueError("Published composite or common divisor differs")
    if len(str(RSA250)) != 250 or RSA1024.bit_length() != 1024:
        raise ValueError("Unexpected integer size")
    print(json.dumps(dict(accepted=True, rsa250_digits=len(str(RSA250)),
                          gcd_bits=divisor.bit_length(), coprime_quotients=euclid(N // divisor, M // divisor) == 1)))
