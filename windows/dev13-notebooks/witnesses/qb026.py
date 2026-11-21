"""Recalculate Quobly's published benchmark metrics directly from cached counts."""
import json
import math


def verify(rows, axes, metrics):
    expected_keys = {(n, noise) for n in range(2, 10) for noise in (False, True)}
    if len(rows) != len(expected_keys) or {(r["n"], r["noise"]) for r in rows} != expected_keys:
        raise AssertionError("Expected clean and noisy samples for widths two through nine")
    populations = {False: {}, True: {}}
    for row in rows:
        n, counts, shots = row["n"], row["counts"], row["shots"]
        if shots != 200 or sum(counts.values()) != shots or any(
            len(k) != n or set(k) - {"0", "1"} or type(v) is not int or v < 0 for k, v in counts.items()
        ):
            raise AssertionError("Invalid width or counts")
        p0, p1 = (counts.get(bit * n, 0) / shots for bit in ("0", "1"))
        population = p0 + p1
        fidelity = (population + 2 * math.sqrt(p0 * p1)) / 2
        values = dict(ghz_pop=population, leakage=1-population, hellinger_fidelity=fidelity)
        calculated = metrics(counts, n, shots)
        if any(not math.isclose(result[key], value, abs_tol=1e-12, rel_tol=0)
               for result in (row, calculated) for key, value in values.items()):
            raise AssertionError("Cached metric disagrees with counts")
        populations[row["noise"]][n] = population
    if len(axes.lines) != 2:
        raise AssertionError("Expected both population curves")
    for noise, line in zip((False, True), axes.lines):
        if list(line.get_xdata()) != list(range(2, 10)) or any(
            abs(y - populations[noise][n]) > 1e-12 for n, y in zip(range(2, 10), line.get_ydata(), strict=True)
        ):
            raise AssertionError("Plotted population disagrees with counts")
    return dict(accepted=True, cached_runs=len(rows), measured_shots=sum(r["shots"] for r in rows),
                noisy_population_at_nine=populations[True][9])


if __name__ == "__main__":
    print(json.dumps(verify(rows, ax, metrics), allow_nan=False))
