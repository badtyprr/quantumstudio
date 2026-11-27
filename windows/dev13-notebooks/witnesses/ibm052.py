"""Check the observed communication outcomes and both CHSH strategies."""
import json
import math
from qiskit.quantum_info import Statevector


def check_uniform_messages(counts, expected_keys):
    # Four equiprobable pairs, 1,024 shots; familywise tail probability below 1e-9.
    tolerance = math.sqrt(math.log(8e9) / (2 * 1024))
    if set(counts) != expected_keys or sum(counts.values()) != 1024:
        raise ValueError("Missing or unexpected measurement outcomes")
    if any(abs(n / 1024 - 0.25) > tolerance for n in counts.values()):
        raise ValueError("The two-bit message distribution is inconsistent with two fair bits")


def winning_probability(circuit, x, y):
    unitary = circuit.remove_final_measurements(inplace=False)
    distribution = Statevector.from_instruction(unitary).probabilities_dict()
    # The local marginals are uniform. Check each joint outcome as well as the win rate.
    win = 0.0
    for bits in ("00", "01", "10", "11"):
        wins = (int(bits[0]) ^ int(bits[1])) == (x & y)
        expected = (1 + (1 if wins else -1) / math.sqrt(2)) / 4
        probability = float(distribution.get(bits, 0))
        if abs(probability - expected) > 1e-13:
            raise ValueError(f"Unexpected CHSH probability for inputs {x},{y} and output {bits}")
        if wins:
            win += probability
    return win


if __name__ == "__main__":
    if filtered_statistics != {"0": 1024}:
        raise ValueError("The inverse gate did not recover the teleported input")
    if _ibm052_fixed_message != {_ibm052_expected_message: 1024}:
        raise ValueError("The fixed message did not survive superdense coding")
    bits = ("0", "1")
    check_uniform_messages(_ibm052_bell_outcomes, {f"0 {a} {b}" for a in bits for b in bits})
    check_uniform_messages(statistics, {f"{c} {d} {c} {d}" for c in bits for d in bits})

    quantum_wins, quantum_games = _ibm052_quantum_games
    if quantum_games != 1000 or NUM_GAMES != 1000:
        raise ValueError("Incomplete CHSH trial")
    inputs = [(x, y) for x in (0, 1) for y in (0, 1)]
    win_probabilities = [winning_probability(chsh_circuit(x, y), x, y) for x, y in inputs]
    expected = (2 + math.sqrt(2)) / 4
    if any(abs(p - expected) > 1e-13 for p in win_probabilities):
        raise ValueError("CHSH input distribution differs from the analytic strategy")
    classical_wins = 0
    for x, y in inputs:
        a, b = classical_strategy(x, y)
        classical_wins += (int(a) ^ int(b)) == (x & y)
    if classical_wins != 3:
        raise ValueError("The classical strategy must win exactly three of four inputs")
    # Hoeffding's inequality, familywise false rejection at most 1e-9 for both trials.
    tolerance = math.sqrt(math.log(4e9) / (2 * NUM_GAMES))
    if abs(quantum_wins / quantum_games - expected) > tolerance or abs(TOTAL_SCORE / NUM_GAMES - .75) > tolerance:
        raise ValueError("Observed CHSH win frequency outside sampling tolerance")
    print(json.dumps(dict(accepted=True, teleportation=filtered_statistics,
                          bell_outcomes=_ibm052_bell_outcomes, fixed_message=_ibm052_fixed_message, random_messages=statistics,
                          quantum_wins=int(quantum_wins), classical_wins=int(TOTAL_SCORE),
                          games_per_strategy=NUM_GAMES, quantum_per_input=win_probabilities,
                          classical_winning_inputs=classical_wins), allow_nan=False))
