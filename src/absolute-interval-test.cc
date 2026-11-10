// GPL-2.0-or-later; see COPYING.
#include "Calculator.h"
#include <cmath>
#include <iostream>
#include <stdexcept>

int main() {
	try {
		Calculator calculator;
		if(!calculator.loadGlobalDefinitions()) throw std::runtime_error("Definitions unavailable");
		calculator.setPrecision(30);
		EvaluationOptions eo;
		eo.approximation = APPROXIMATION_APPROXIMATE;
		struct Case { const char *expression; double lower; double upper; };
		const Case cases[] = {
			{"abs(uncertainty(0,1e-20,0))", 0, 1e-20},
			{"abs(interval(-1e-20,1e-20))", 0, 1e-20},
			{"abs(uncertainty(1,1e-20,0)-1)", 0, 1e-20},
			{"abs(interval(-2,1))", 0, 2},
			{"abs(interval(-1,2))", 0, 2},
			{"abs(interval(-2,-1))", 1, 2},
			{"abs(interval(1,2))", 1, 2},
			{"abs(0)", 0, 0},
			{"abs(3+4i)", 5, 5}
		};
		for(const Case &test : cases) {
			MathStructure value = calculator.calculate(test.expression, eo);
			if(calculator.message()) throw std::runtime_error(std::string("Diagnostic: ") + test.expression);
			if(!value.isNumber() || !value.number().isReal() || value.number().includesInfinity())
				throw std::runtime_error(std::string("Nonfinite/nonreal result: ") + test.expression);
			double lower = value.number().lowerEndPoint().floatValue();
			double upper = value.number().upperEndPoint().floatValue();
			double scale = test.upper == 0 ? 1 : test.upper;
			if(!std::isfinite(lower) || !std::isfinite(upper) || lower < 0 ||
				std::abs(lower-test.lower) > scale*1e-8 || std::abs(upper-test.upper) > scale*1e-8)
				throw std::runtime_error(std::string("Incorrect interval endpoints: ") + test.expression);
		}
		std::cout << "PASS: 9 absolute-value interval checks\n";
		return 0;
	} catch(const std::exception &error) {
		std::cerr << error.what() << '\n';
		return 1;
	}
}
