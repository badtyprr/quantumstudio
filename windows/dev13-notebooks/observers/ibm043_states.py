"""Keep the first product state and both partial measurements before reuse."""
_ibm043_first = psi.data.copy()
_ibm043_measurements = []
_ibm043_display = display

def _ibm043_observe(value):
    if "w" in globals() and "result" in globals():
        _ibm043_measurements.append((result, state.data.copy()))
    return _ibm043_display(value)

display = _ibm043_observe
