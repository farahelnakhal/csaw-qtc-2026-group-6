# Quantum Trojan Challenge


Someone altered a collection of quantum circuits before execution. The legitimate
user protects measurement records with fixed XOR masks, but the injected behavior
may expose information that was supposed to remain hidden.

You receive each circuit and one set of masked measurement counts. The original
application names, keys and genuine decoded results are unavailable. The injected behavior may be conditional. Its controlling bits and activation rules have not been identified.

Can you recover the keys and explain how the Trojan works?

## Materials

Open [TROJAN_CHALLENGE.ipynb](TROJAN_CHALLENGE.ipynb) after following
[setup](docs/setup.md). This is **challenge containing six circuit cases**,
named `circuit1` through `circuit6`.

- Each QASM file is in `challenges/01_silent_witness/circuits/`.
- Its matching measurement file is in `challenges/01_silent_witness/measurements/`.
- Every supplied dataset contains **8,192 shots**.
- [cases.json](cases.json) pairs the files and supplies widths and seeds.
- [The full brief](challenges/01_silent_witness/README.md) defines the task and bit order.

Each circuit has its own independent key. A key stays fixed across all shots of
that job. Random measurement values are not part of that persistent key.

You may inspect, modify and simulate the supplied circuits. No quantum hardware,
account or remote service is required. The supplied counts are sufficient to
start investigating. Rerunning all 8,192 shots is not required.

## Submission and scoring

For **each circuit**, submit:

1. The complete XOR mask, preserving leading zeros and the displayed readout order.
2. The classical bit(s) controlling the trigger, identified by QASM register name
   and zero-based index, together with the activation condition.
3. An explanation of how the trigger and injected behavior operate, supported by
   your code and observations.

Submit your recovery code and a write-up covering all six cases. One shared
codebase and a combined write-up are acceptable.

Use [templates/submission.json](templates/submission.json) to organize your answers
and [templates/writeup.md](templates/writeup.md) as an optional writing template.
The notebook can save a local submission draft.

The challenge is worth **100 points in total**. Full credit requires correct
keys and trigger explanations for all six cases, recovery code, and a write-up.
Partial credit may be awarded for a reasonable method supported by clear
explanations and working code, even if not all keys are fully recovered.
