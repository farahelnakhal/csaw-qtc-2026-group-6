# Silent Witness

A collection of quantum jobs has been intercepted. Someone injected a Trojan
before execution, while the legitimate user applied fixed XOR masks to protect
measurement records. The same mask is used for every shot of a given job, but
different jobs have independent keys.

You have both the altered circuits and their masked measurement counts. You do
not know which recorded bits are application data, auxiliary records, or involved
in an activation condition. Determine what the injected behavior exposes and use
your findings to recover the keys.

## Evidence

There are six cases: `circuit1` through `circuit6`. For each case:

- `circuits/circuitN.qasm` is the OpenQASM 3 circuit.
- `measurements/circuitN.txt` contains 8,192 masked measurement counts.


## Count and key conventions

The supplied counts and submitted XOR key correspond to the **final values of
classical register `c`**.

Each entry maps one observed word to its shot frequency.

For this readout:

```text
pre-mask readout word = observed readout word XOR key
```

The key has one bit per displayed outcome position. Its leftmost bit applies to
the outcome's leftmost bit. A displayed Qiskit word is ordered from the
highest-index register bit down to `c[0]`.

Your trigger description must use **QASM register indices**, although we will consider wrong order of bits too as long as the explanation is correct. 

## Local experiments

You may analyze the counts, inspect or simplify the circuit, and run experiments
on modified copies. The simulator’s final `c` readout uses the same bit order
as the supplied counts.

Use simulation seed **2026** for repeatable local experiments. The shared counts
are a fixed reference sample.

Large dynamic circuits can take time to simulate. Start with a small shot count.
You are not required to regenerate the full supplied batch.

## Required answers

For every case, provide the full key, identify the trigger bit(s), specify when
the injected behavior activates, and explain how it works. Include your recovery
code and a write-up. Correctly guessing a key without explaining the trigger is
not a complete solution. 
