# Quantum Trojan Challenge — solution write-up

## Method

Two passes, deliberately independent of each other. The first reads only the
QASM and never executes it. The second reads only the counts and never looks at
the circuit. They agree on the trigger bit in all six cases.

**Static pass: classical def-use:** We parse the OpenQASM 3 text and build,
for the readout register `c`, the set of bits that are written by a measurement
and the set that are read by a guard. Two things stand out in every case: about
half the measured bits are never read by any single-bit guard, and exactly one
bit guards 15–20 conditional blocks when every other guard bit controls one.
Each program also contains 13 whole-register comparisons of the form
`if (c == k)`. These are decoys: they syntactically read every bit, so a naive
liveness check reports no write-only bits at all. We therefore count
single-bit reads and register-wide reads separately.

**Dynamic pass: conditional invariant codes:** The mask is a translation of
$\mathbb{F}_2^L$, and translation commutes with conditioning on an observed
coordinate. So splitting the shots by the observed value of a bit reproduces
the two branches of a conditional Trojan, even though the key is unknown. For
each candidate bit we split the sample and compute the dimension of the
empirical invariant code of each half,

$$\dim \mathcal{A} = L - \operatorname{rank}_{\mathbb{F}_2}\{\,y \oplus y_0\,\},$$

that is, the number of independent linear functionals of the word that are
constant across the branch. Background laws give dimension 0. The guard bit is
the one maximising `min(dim₀, dim₁)`, not the max, because a shadow bit
also produces one rigid cell, and only the guard bit splits the sample into two
cells that are each internally rigid. Across the six cases the lift over the
unconditioned dimension is 16–21.

With the guard at index $m$ and $L = 2m+1$:

1. the dormant branch is the majority branch; on it the shadow bits
   $c[m{+}1..2m]$ are exactly constant, and since they unmask to zero the
   observed constant is the key on those bits;
2. on the active branch each parity $c[i] \oplus c[2m{-}i]$ is exactly
   constant, which gives $k_i \oplus k_{2m-i}$ and hence the data bits;
3. the trigger bit comes from the guard polarity in the QASM together with the
   fact that the Trojan fires on a minority of shots.

No key search anywhere: the attack is $O(NL)$ arithmetic where brute force would
be $2^{41}$.

**Self-check:** The recovered key must satisfy three identities on every one of
the 8192 shots; shadow block unmasks to zero on all dormant shots, every
mirror pair unmasks to equality on all active shots, and the trigger unmasks to
its polarity on exactly the active shots. All six pass with no exceptions.

### Running the code

`solution.py` is self-contained, no dependencies for the recovery path:

```bash
python solution.py static  challenges/01_silent_witness/circuits/*.qasm
python solution.py scan    challenges/01_silent_witness/measurements/*.txt
python solution.py recover challenges/01_silent_witness/measurements/circuit4.txt \
                           challenges/01_silent_witness/circuits/circuit4.qasm
```

`verify_key.py` performs the circuit-side confirmation described under
Limitations and needs qiskit and qiskit-aer:

```bash
python verify_key.py            # all six, ~48 shots each
```

The notebook reproduces the same results cell by cell.

### Environment, seeds, and circuit modifications

- Simulation seed 2026 throughout (`seed_simulator`, and
  `seed_transpiler=2026` where a transpile pass is involved),
  `optimization_level=0`, `AerSimulator(method='statevector')`.
- 48 shots per case for the verification simulations. The constants being
  verified are deterministic, so shots are needed only to populate both
  branches: at a firing rate near 0.1, 48 shots miss the active branch with
  probability 0.6%.
- **Circuit modifications:** The supplied files were not altered. For the
  verification in the Limitations section we build a modified copy of each
  circuit in memory, with the `x` gates that sit immediately before a bit's
  final measurement deleted, and simulate that copy. Nothing else is changed.
- Note that the 21-qubit cases cost roughly 1–2 s per shot; dynamic circuits
  cannot use Aer's sampling shortcut, so shots are the unit of cost.

## Per-circuit findings

Every case has the same structure: readout width $L = 2m+1$, one guard bit at
index $m$, a data block below it and a shadow block above it, and a payload
that mirrors the data block about the guard.

| case | $L$ | guard | blocks | fires | rate | invariant lift | key |
|---|---|---|---|---|---|---|---|
| circuit1 | 41 | `if (c[20])` | 20 | 873/8192 | 0.1066 | 21 | `01011011010100000110011010010001001101100` |
| circuit2 | 33 | `if (c[16])` | 16 | 828/8192 | 0.1011 | 17 | `111001001101111100011000100010101` |
| circuit3 | 41 | `if (c[20])` | 20 | 822/8192 | 0.1003 | 21 | `11010101000000000111000101110110010000001` |
| circuit4 | 31 | `if (!c[15])` | 15 | 816/8192 | 0.0996 | 16 | `1101011000100110111100011100011` |
| circuit5 | 41 | `if (!c[20])` | 20 | 816/8192 | 0.0996 | 21 | `11101010000010101000010000101001111100110` |
| circuit6 | 35 | `if (c[17])` | 17 | 816/8192 | 0.0996 | 18 | `00111001111100000010101100011010010` |

Keys are in displayed order, from `c[L-1]` down to `c[0]`, leading zeros
preserved.

**Trigger:** In every case the trigger is the single classical bit `c[m]`,
measured mid-circuit from an ancilla prepared so that it reads the activating
value on about one shot in ten. The activation condition is `c[m] == 1` for
circuits 1, 2, 3 and 6, and `c[m] == 0` for circuits 4 and 5, matching the
polarity of the guard as written in the QASM.

**Payload:** On the activating branch, the guarded blocks copy application data
into otherwise unused classical bits in the computational basis:
`c[m+1+j]` receives a copy of `c[m-1-j]` for $j = 0..m-1$. The shadow block is
therefore the mirror image of the data block by reflection about the trigger
bit. On the dormant branch those bits are never written. The leak is
$p \cdot m \approx 1.5$–$2$ bits per shot, and it is invisible in the
application's own marginals, because the Trojan writes only into bits the
application does not read.

**Why the mask does not hide it:** Masking is a translation, so it cancels in a
parity. The copies survive as constant values of `c[i] ⊕ c[2m-i]` on the
activating branch regardless of the key, and the never-written bits unmask to
zero on the dormant branch. Together these give $L-1$ key bits with no
reference to the program at all.

## Limitations


**One bit is not determined by the counts:** The counts determine the key
exactly modulo $\langle e_m\rangle$: the two parameter settings
$(\beta, k_m)$ and $(\bar\beta, k_m \oplus 1)$ induce identical masked laws.
Resolving it needs the guard polarity from the program text plus the assumption
that the Trojan fires on a minority of shots. Both hold here and both are
stated rather than assumed silently.

**The constants are not separately identifiable:.** The recovery above assumes
the shadow block unmasks to zero when dormant and that the mirror is exact. In 
general a Trojan could write a fixed non-zero vector $v$ when dormant and mirror 
with an offset $b$, and those constants are absorbed into the key: masked counts 
cannot separate $k$ from $k \oplus v$. The self-checks cannot detect this, because 
they verify consistency under the normalisation $v = b = 0$, which is unfalsifiable 
from counts alone. We examined this directly. Simulating the supplied circuits shows
non-zero $v$ and $b$ in all six cases, which naively suggests the key is zero
and the counts unmasked. That reading is wrong: the mask is compiled into the
circuits as bit flips before readout, so simulating the shipped circuit
reproduces masked data and the apparent zero key is vacuous. The distinguishing evidence 
is in the QASM. Across the six circuits, an `x` gate sits immediately before a bit's
final measurement at 163 of 222 bit positions, precisely where the recovered
key says 1-73% against a 50% baseline, $z \approx 7$, and 6 of 6 on the
trigger bits. The remaining flips are absorbed into adjacent `rz`/`sx`
rotations by transpilation. We then made a falsifiable prediction: deleting
those `x` gates and re-simulating must shift the branch constants to
$v'_i = k_i \oplus [\,i \in D\,]$, leaving residual ones exactly on the bits
where the key says 1 but no explicit `x` exists. All six cases match the
prediction bit for bit, 216 predicted bits with no misses. `verify_key.py`
reproduces this.

**What remains unprovable:** This establishes that the
recovered key is the set of pre-readout flips compiled into each circuit. If
the generator applied additional classical masking on top of those flips, no
analysis of circuit and counts could detect it, since both would carry the
extra layer. Nothing in the structure suggests it; the stripped circuits
behave exactly as a clean application plus a plain copy Trojan should, with
shadow bits at zero and exact mirrors; but it is the limit of what can be shown 
without the generator.

**Scope:** We did not regenerate the full 8192-shot batches; verification 
simulations used 48 shots per case. Noise is not modelled: the recovery relies 
on exact constancy, and under readout noise the relations become biased parities 
requiring a majority test over $O(\varepsilon^{-2}\log m)$ shots, with $\varepsilon = (1-2\eta)^2$.
