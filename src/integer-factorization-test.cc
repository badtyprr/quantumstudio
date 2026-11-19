// GPL-2.0-or-later; see COPYING.
#include "Calculator.h"
#include "Number.h"

#include <initializer_list>
#include <iostream>

static bool check(const char *input, std::initializer_list<const char *> expected) {
	std::vector<Number> factors;
	Number n(input);
	if(!n.factorize(factors) || factors.size() != expected.size()) return false;
	size_t i = 0;
	for(const char *prime : expected) {
		if(!factors[i++].equals(Number(prime))) return false;
	}
	return true;
}

int main() {
	Calculator calculator;
	if(!check("-12", {"-1", "2", "2", "3"}) ||
	   !check("1", {"1"}) ||
	   !check("1000006000009", {"1000003", "1000003"}) ||
	   !check("5073729280707932631243580787", {"5073729280707932631243580787"}) ||
	   !check("3402823669209384634633740743176823109843098343",
	          {"3", "3", "74519450661011221", "5073729280707932631243580787"})) {
		std::cerr << "Incorrect integer factorization" << std::endl;
		return 1;
	}
	// The product of the Mersenne primes 2^107-1 and 2^127-1.
	Number hard("27606985387162255149739023449107931668458716142620601169954803000803329");
	std::vector<Number> factors;
	calculator.startControl(10);
	bool finished = hard.factorize(factors);
	bool aborted = calculator.aborted();
	calculator.stopControl();
	if(finished || !aborted || !factors.empty() || !check("15", {"3", "5"})) {
		std::cerr << "Factorization failed to abort and recover" << std::endl;
		return 1;
	}
	return 0;
}
