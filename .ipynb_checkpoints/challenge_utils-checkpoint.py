import ast
from collections import Counter
import json
from pathlib import Path


def load_counts(path):
    text = Path(path).read_text().strip()
    try:
        raw = json.loads(text)
    except json.JSONDecodeError:
        raw = ast.literal_eval(text)
    if not isinstance(raw, dict) or not raw:
        raise ValueError("Expected nonempty measurement counts")
    counts = Counter()
    for word, frequency in raw.items():
        if not isinstance(word, str) or not word or set(word) - {"0", "1"}:
            raise ValueError("Counts must use binary-string keys, preserving leading zeros")
        if type(frequency) is not int or frequency <= 0:
            raise ValueError("Counts must be positive integers")
        counts[word] += frequency
    if len({len(word) for word in counts}) != 1:
        raise ValueError("Outcome widths differ")
    return dict(counts)


def load_cases(root):
    root = Path(root)
    cases = json.loads((root / "cases.json").read_text())["cases"]
    if len(cases) != 6 or len({c["id"] for c in cases}) != 6:
        raise ValueError("Expected six distinct circuit identifiers")
    for case in cases:
        for field in ("circuit", "measurements"):
            if not (root / case[field]).is_file():
                raise FileNotFoundError(root / case[field])
        counts = load_counts(root / case["measurements"])
        if sum(counts.values()) != case["shots"] or len(next(iter(counts))) != case["key_bits"]:
            raise ValueError(f"Unexpected count size for {case['id']}")
    return {case["id"]: case for case in cases}


def project_register_counts(circuit, counts, name="c"):
    register = next((r for r in circuit.cregs if r.name == name), None)
    if register is None:
        raise ValueError(f"No classical register named {name}")
    indices = [circuit.find_bit(bit).index for bit in register]
    result = Counter()
    for word, n in counts.items():
        bits = word.replace(" ", "")[::-1]
        if len(bits) != circuit.num_clbits:
            raise ValueError("Simulator output width does not match the circuit")
        result["".join(bits[i] for i in reversed(indices))] += n
    return dict(result)


def validate_answer(answer, key_bits):
    """This only does syntax check. It won't check your answer against the real key."""
    key = answer.get("key", "")
    if not isinstance(key, str) or len(key) != key_bits or set(key) - {"0", "1"}:
        raise ValueError(f"Key must contain exactly {key_bits} binary digits")
    trigger = answer.get("trigger", {})
    if not isinstance(trigger, dict) or not trigger.get("bits"):
        raise ValueError("Specify the classical bit(s) you identify as controlling the trigger")
    for bit in trigger["bits"]:
        if not isinstance(bit.get("register"), str) or not bit["register"] or type(bit.get("index")) is not int or bit["index"] < 0:
            raise ValueError("Each trigger bit needs a register name and a nonnegative integer index")
    if not isinstance(trigger.get("activation_condition"), str) or not trigger["activation_condition"].strip():
        raise ValueError("Describe the activation condition")
    if not isinstance(trigger.get("explanation"), str) or not trigger["explanation"].strip():
        raise ValueError("Explain how the trigger and injected behavior work")
    return answer
