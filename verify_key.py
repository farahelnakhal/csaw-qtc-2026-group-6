#!/usr/bin/env python3

import json, math, re, sys, time
from pathlib import Path

ROOT = Path.cwd()
while not (ROOT / "cases.json").is_file() and ROOT != ROOT.parent:
    ROOT = ROOT.parent
CACHE = Path.cwd() / "nomask"; CACHE.mkdir(exist_ok=True)

def load(p):
    t = Path(p).read_text().strip()
    try: raw = json.loads(t)
    except json.JSONDecodeError: raw = eval(t)
    return {w.replace(" ", ""): int(n) for w, n in raw.items()}

def constants(counts, m, L):
    """(dormant shadow const, active mirror const, dormant branch value)."""
    W = [(int(w, 2), n) for w, n in counts.items()]
    sz = {u: sum(n for w, n in W if (w >> m) & 1 == u) for u in (0, 1)}
    d = 0 if sz[0] >= sz[1] else 1
    pick = lambda u, f: ({tuple(f(w, i) for i in range(m + 1, L))
                          for w, _ in W if (w >> m) & 1 == u})
    sh = pick(d, lambda w, i: (w >> i) & 1)
    mi = pick(1 - d, lambda w, i: ((w >> i) ^ (w >> (2 * m - i))) & 1)
    return (next(iter(sh)) if len(sh) == 1 else None,
            next(iter(mi)) if len(mi) == 1 else None, d, sz)

def key_from_counts(case):
    L = case["key_bits"]; m = (L - 1) // 2
    sup = load(ROOT / case["measurements"])
    S, M, d, sz = constants(sup, m, L)
    assert S and M, "branch constants are not constant"
    pol = re.findall(rf"if\s*\(\s*(!?)\s*c\[{m}\]\s*\)",
                     (ROOT / case["circuit"]).read_text())
    beta = 0 if pol and pol[0] == "!" else 1
    k = [0] * L
    for j, i in enumerate(range(m + 1, L)):
        k[i] = S[j]
        k[2 * m - i] = k[i] ^ M[j]
    k[m] = (1 - d) ^ beta
    return k, beta, sz

def mask_gates(text):
    """Classical bit -> True if an `x` sits immediately before its final
    measurement.  Returns also the line numbers of those x gates."""
    lines = text.splitlines()
    last = {}
    for ln, l in enumerate(lines):
        mm = re.match(r"\s*c\[(\d+)\] = measure q\[(\d+)\];", l)
        if mm: last[int(mm.group(1))] = (ln, int(mm.group(2)))
    D, drop = set(), set()
    for i, (ln, q) in last.items():
        for j in range(ln - 1, -1, -1):
            if re.search(rf"\bq\[{q}\]", lines[j]):
                if re.fullmatch(rf"\s*x q\[{q}\];", lines[j]):
                    D.add(i); drop.add(j)
                break
    return D, drop, lines

def simulate(cid, src, shots):
    f = CACHE / f"{cid}.json"
    if f.is_file(): return load(f)
    from qiskit import qasm3, transpile
    from qiskit_aer import AerSimulator
    sim = AerSimulator(method="statevector", max_parallel_threads=0, max_parallel_shots=0)
    t = time.time()
    raw = sim.run(transpile(qasm3.loads(src), sim, optimization_level=0),
                  shots=shots, seed_simulator=2026).result().get_counts()
    out = {w.replace(" ", ""): n for w, n in raw.items()}
    f.write_text(json.dumps(out))
    print(f"  simulated mask-stripped circuit, {shots} shots, {time.time()-t:.0f}s")
    return out

def check(case, shots):
    cid, L = case["id"], case["key_bits"]; m = (L - 1) // 2
    print(f"\n=== {cid}  (L={L}, m={m})")
    k, beta, sz = key_from_counts(case)
    key = "".join(str(k[i]) for i in range(L - 1, -1, -1))
    print(f"  key from counts : {key}")
    print(f"  trigger         : c[{m}] == {beta},  branch sizes {sz}")

    text = (ROOT / case["circuit"]).read_text()
    D, drop, lines = mask_gates(text)
    agree = sum((k[i] == 1) == (i in D) for i in range(L))
    z = (agree - L / 2) / math.sqrt(L / 4)
    missing = sorted(i for i in range(L) if k[i] == 1 and i not in D)
    print(f"  explicit x before final measure agrees with key on {agree}/{L}"
          f"  (z = {z:.1f})")
    print(f"  key says 1 but no explicit x: {missing}")

    stripped = "\n".join(l for j, l in enumerate(lines) if j not in drop)
    cts = simulate(cid, stripped, shots)
    v2, b2, d2, sz2 = constants(cts, m, L)
    if v2 is None or b2 is None:
        print(f"  INCONCLUSIVE: branch constants not constant (branch sizes {sz2};"
              f" raise --shots)"); return None

    pv = [k[i] ^ (i in D) for i in range(m + 1, L)]
    pb = [pv[j] ^ (k[2*m-i] ^ (2*m-i in D)) for j, i in enumerate(range(m + 1, L))]
    s = lambda t: "".join(map(str, map(int, t)))
    ok = s(v2) == s(pv) and s(b2) == s(pb)
    print(f"  after deleting {len(drop)} x gates:")
    print(f"    dormant shadow  observed {s(v2)}")
    print(f"                    predicted {s(pv)}")
    print(f"    mirror parity   observed {s(b2)}")
    print(f"                    predicted {s(pb)}")
    print(f"  --> {'PASS' if ok else 'FAIL'}: residual flips sit exactly where "
          f"the key says 1 with no explicit x" if ok else "  --> FAIL")
    return ok

if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    shots = int(sys.argv[sys.argv.index("--shots") + 1]) if "--shots" in sys.argv else 48
    cases = {c["id"]: c for c in json.loads((ROOT / "cases.json").read_text())["cases"]}
    res = {cid: check(cases[cid], shots) for cid in (args or cases)}
    print("\n" + "=" * 46)
    for cid, ok in res.items():
        print(f"  {cid}: {'PASS' if ok else 'INCONCLUSIVE' if ok is None else 'FAIL'}")
    print("  all pass:", all(v is True for v in res.values()))