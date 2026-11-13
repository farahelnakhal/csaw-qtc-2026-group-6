#!/usr/bin/env python3
import ast, json, math, os, random, re, sys
from statistics import median

def load(p):
    t = open(p).read().strip()
    try: r = json.loads(t)
    except json.JSONDecodeError: r = ast.literal_eval(t)
    return {w.replace(" ", ""): int(n) for w, n in r.items()}

def rank(vs, cap):                       # GF(2) rank, early exit at cap
    B = []
    for v in vs:
        for b in B: v = min(v, v ^ b)
        if v:
            B.append(v); B.sort(reverse=True)
            if len(B) >= cap: return cap
    return len(B)

def dim(cell, L):                        # dim{a : <a,y> constant on cell}
    return L - rank((y ^ cell[0] for y in cell[1:]), L) if cell else 0

def split(W, i):                         # (cells, masses) by bit i
    c = {u: [w for w, _ in W if (w >> i) & 1 == u] for u in (0, 1)}
    s = {u: sum(n for w, n in W if (w >> i) & 1 == u) for u in (0, 1)}
    return c, s

def scan(cts):
    # int(w,2) puts register bit c[i] at bit i, since words run c[L-1]..c[0]
    W = [(int(w, 2), n) for w, n in cts.items()]
    L, N = len(next(iter(cts))), sum(cts.values())
    rows = []
    for i in range(L):
        c, s = split(W, i)
        d = (dim(c[0], L), dim(c[1], L))
        # min, not max: a shadow bit also yields one rigid cell, so only the
        # guard bit splits the sample into two cells that are both rigid
        rows.append((min(d), max(d), i, min(s.values()) / N))
    b = max(rows)
    # p_hat, not p: the manifest's p is the true firing rate, and roc() merges
    # these dicts, so the names must not collide
    return dict(L=L, shots=N, m=b[2], dim=b[0], p_hat=b[3],
                lift=b[0] - dim([w for w, _ in W], L))

def recover(cts, qasm=None):
    W = [(int(w, 2), n) for w, n in cts.items()]
    r = scan(cts); m, L = r["m"], r["L"]
    if L != 2 * m + 1: return dict(ok=False, why=f"L={L} is not 2m+1 for m={m}", **r)
    c, s = split(W, m)
    D, A = (c[0], c[1]) if s[0] >= s[1] else (c[1], c[0])
    k = [0] * L
    for i in range(m + 1, L):            # shadow bits: constants of the dormant branch
        v = {(w >> i) & 1 for w in D}
        if len(v) > 1: return dict(ok=False, why=f"c[{i}] varies when dormant", **r)
        k[i] = v.pop()
    for i in range(m + 1, L):            # mirror parities: constants of the active branch
        v = {(w >> i ^ w >> (2 * m - i)) & 1 for w in A}
        if len(v) > 1: return dict(ok=False, why=f"c[{i}] mirror varies", **r)
        k[2 * m - i] = k[i] ^ v.pop()
    pol = re.findall(rf"if\s*\(\s*(!?)\s*c\[{m}\]\s*\)", open(qasm).read()) if qasm else []
    beta = (0 if pol[0] == "!" else 1) if pol else None   # last bit needs the guard
    k[m] = (A[0] >> m & 1) ^ beta if beta is not None else 0
    K = sum(b << i for i, b in enumerate(k))
    bad = [t for t, ok in (("dormant shadow nonzero", all((w ^ K) >> m + 1 == 0 for w in D)),
                           ("mirror broken", all(not any((x >> i ^ x >> (2 * m - i)) & 1
                                                         for i in range(m + 1, L))
                                                 for x in ((w ^ K) for w in A))),
                           ("polarity mismatch", beta is None or
                            all((w ^ K) >> m & 1 == beta for w in A))) if not ok]
    return dict(ok=not bad, why="; ".join(bad) or "self-checks pass",
                key=format(K, f"0{L}b"), known=L - (beta is None), beta=beta,
                dormant=max(s.values()), active=min(s.values()), **r)

def static(text):
    L = int(re.search(r"bit\[(\d+)\]\s+c\s*;", text).group(1))
    lines, written, guards, whole = text.splitlines(), set(), {}, 0
    for ln, line in enumerate(lines):
        written |= {int(x) for x in re.findall(r"c\[(\d+)\]\s*=\s*measure", line)}
        for cond in re.findall(r"if\s*\(([^)]*)\)", line):
            if re.match(r"^\s*!?\s*c\s*[=!]=\s*\d+\s*$", cond):
                whole += 1               # reads every bit: defeats naive liveness
                continue
            for b in re.findall(r"c\[(\d+)\]", cond): guards.setdefault(int(b), []).append(ln)
    if not guards: return dict(L=L, m=-1, fan=0, ratio=0., span=0., wo=len(written),
                               whole=whole, trojan=False)
    m = max(guards, key=lambda b: len(guards[b]))
    fan = len(guards[m])
    ratio = fan / max(median(sorted(len(v) for v in guards.values())), 1)
    wo = len(written - set(guards))      # written, never read by a single-bit guard
    return dict(L=L, m=m, fan=fan, ratio=ratio, wo=wo, whole=whole,
                span=(max(guards[m]) - min(guards[m])) / len(lines),
                trojan=bool(ratio >= 3 and wo))

# -- corpus ------------------------------------------------------------------
# Benign families append in place (an if_test holds concrete clbits, so a
# spliced sub-circuit with a dangling condition is malformed). All three use
# mid-circuit measurement and feedforward: the cases a naive "guard on a
# measured bit" rule would flag.

def teleport(qc, q, c, d, a, g, CR):
    for i in range(d + 2): qc.ry(g.uniform(.3, 2.8), q[i])
    for h in range(d):
        f = CR(2, f"t{h}"); qc.add_register(f)
        x, b, t = q[h % d], q[a], q[a + 1]
        qc.h(b); qc.cx(b, t); qc.cx(x, b); qc.h(x)
        qc.measure(x, f[0]); qc.measure(b, f[1])
        with qc.if_test((f[1], 1)): qc.x(t)
        with qc.if_test((f[0], 1)): qc.z(t)
        qc.reset(b)
    for j in range(d): qc.measure(q[j], c[j])

def rus(qc, q, c, d, a, g, CR):
    qc.h(range(d + 1))
    for r in range(3):
        f = CR(1, f"f{r}"); qc.add_register(f)
        qc.ry(g.uniform(.5, 2.), q[a])
        for j in range(d): qc.cx(q[j], q[a])
        qc.measure(q[a], f[0])
        with qc.if_test((f[0], 1)):
            qc.reset(q[a])
            for j in range(d): qc.rx(g.uniform(.2, 1.2), q[j])
        with qc.if_test((f[0], 0)):
            for j in range(0, d - 1, 2): qc.cz(q[j], q[j + 1])
    for j in range(d): qc.measure(q[j], c[j])

def ipe(qc, q, c, d, a, g, CR):
    qc.x(q[a]); phi = g.uniform(0, 2 * math.pi)
    for r in range(d):
        qc.h(q[r]); qc.cp(phi * 2 ** r, q[r], q[a])
        for p in range(r):
            with qc.if_test((c[p], 1)):          # reads the readout register itself
                qc.p(-math.pi / 2 ** (r - p), q[r])
        qc.h(q[r]); qc.measure(q[r], c[r])

FAM = {"teleport": (teleport, 2), "rus": (rus, 1), "ipe": (ipe, 1)}

def circuit(fam, d, g, trojan, p, s, beta):
    from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister as CR
    core, na = FAM[fam]
    base, m = d + na, d
    q = QuantumRegister(base + (1 + s if trojan else d + 1), "q")
    c = CR(2 * d + 1, "c")                       # same width in both classes
    qc = QuantumCircuit(q, c); core(qc, q, c, d, d, g, CR)
    if trojan:
        qc.ry(2 * math.asin(math.sqrt(p)), q[base])          # P(trigger=1) = p
        qc.measure(q[base], c[m])
        for j in range(s):                                   # c[m+1+j] mirrors c[m-1-j]
            with qc.if_test((c[m], beta)): qc.cx(q[d - 1 - j], q[base + 1 + j])
            qc.measure(q[base + 1 + j], c[m + 1 + j])
    else:
        for j in range(d + 1):                               # honest extra ancillas
            qc.ry(g.uniform(.4, 2.6), q[base + j])
            if j: qc.cx(q[base + j - 1], q[base + j])
            qc.measure(q[base + j], c[d + j])
            with qc.if_test((c[d + j], 1)): qc.rz(g.uniform(.1, 1.), q[j % d])
    return qc

def corpus(out, n=20, shots=2048, d=5, seed=2026):
    from qiskit import transpile
    from qiskit_aer import AerSimulator
    os.makedirs(out, exist_ok=True)
    sim, g, man, i, L = AerSimulator(), random.Random(seed), [], 0, 2 * d + 1
    for p in (.3, .1, .03, .01):
        for s in (d, max(d // 2, 1), 1):
            for j in range(n):
                for lab in (0, 1):
                    fam = list(FAM)[j % 3]
                    qc = circuit(fam, d, g, bool(lab), p, s, g.randint(0, 1))
                    res = sim.run(transpile(qc, sim, optimization_level=0), shots=shots,
                                  seed_simulator=g.randint(1, 10 ** 6)).result()
                    K, cts = g.getrandbits(L), {}            # fresh mask per sample
                    for w, v in res.get_counts().items():
                        y = format(int(w.split()[-1], 2) ^ K, f"0{L}b")
                        cts[y] = cts.get(y, 0) + v
                    f = f"{i:05d}_{fam}_{lab}_p{p}_s{s}.json"
                    json.dump(cts, open(f"{out}/{f}", "w"))
                    man.append(dict(file=f, label=lab, fam=fam, p=p, s=s, d=d)); i += 1
                    if i % 20 == 0: print(f"  {i} samples", flush=True)
    json.dump(man, open(f"{out}/manifest.json", "w"), indent=2)
    print(f"wrote {i} samples to {out}/")

def auc(rs):
    a = [r["lift"] for r in rs if r["label"]]; b = [r["lift"] for r in rs if not r["label"]]
    return sum((x > y) + .5 * (x == y) for x in a for y in b) / (len(a) * len(b)) \
        if a and b else float("nan")

def roc(out):
    rs = [{**r, **scan(load(f"{out}/{r['file']}"))}
          for r in json.load(open(f"{out}/manifest.json"))]
    print(f"AUC {auc(rs):.4f}  (n={len(rs)})\n")
    print(f"{'p':>6}{'s':>4}{'p*s':>8}{'AUC':>8}{'benign':>8}{'trojan':>8}{'guard':>7}")
    for p, s in sorted({(r["p"], r["s"]) for r in rs}, reverse=True):
        G = [r for r in rs if (r["p"], r["s"]) == (p, s)]
        med = lambda L: sorted(L)[len(L) // 2]
        T = [r for r in G if r["label"]]
        print(f"{p:>6}{s:>4}{p*s:>8.3f}{auc(G):>8.3f}"
              f"{med([r['lift'] for r in G if not r['label']]):>8}"
              f"{med([r['lift'] for r in T]):>8}"
              f"{sum(r['m'] == r['d'] for r in T)/len(T):>6.0%}")
    print(f"\nat lift >= 3:  FP {sum(not r['label'] and r['lift'] >= 3 for r in rs)}"
          f"  FN {sum(r['label'] and r['lift'] < 3 for r in rs)}")

def main(a):
    if len(a) < 3: return print(__doc__) or 1
    cmd, args = a[1], a[2:]
    if cmd == "static":
        print(f"{'file':<20}{'L':>4}{'m':>4}{'fan':>5}{'ratio':>7}{'span':>6}"
              f"{'w-only':>8}{'c==k':>6}  verdict")
        for f in args:
            r = static(open(f).read())
            print(f"{os.path.basename(f):<20}{r['L']:>4}{r['m']:>4}{r['fan']:>5}"
                  f"{r['ratio']:>7.1f}{r['span']:>6.2f}{r['wo']:>8}{r['whole']:>6}"
                  f"  {'TROJAN' if r['trojan'] else 'clean'}")
    elif cmd == "scan":
        for f in args:
            r = scan(load(f))
            print(f"{os.path.basename(f):<20} L={r['L']} shots={r['shots']} "
                  f"guard=c[{r['m']}] dim={r['dim']} lift={r['lift']} p={r['p_hat']:.4f}"
                  f"  {'TROJAN' if r['lift'] >= 3 else 'clean'}")
    elif cmd == "recover":
        r = recover(load(args[0]), *args[1:2])
        for k in ("ok", "why", "m", "beta", "p_hat", "dormant", "active", "known", "key"):
            if r.get(k) is not None: print(f"  {k:<9} {r[k]}")
    elif cmd == "corpus": corpus(args[0], *map(int, args[1:4]))
    elif cmd == "roc": roc(args[0])
    else: return print(__doc__) or 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
