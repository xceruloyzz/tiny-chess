# Tiny chess engine (make.fun tiny-chess-01): negamax alpha-beta +
# quiescence, TT, check extensions, MVV-LVA/history ordering, PST eval.
import json, os, random
from urllib.request import Request, urlopen

ENV = os.environ.get("MAKEFUN_ENV_URL")

def post(p, b):
    r = Request(ENV + p, data=json.dumps(b).encode(),
                headers={"content-type": "application/json"})
    with urlopen(r) as x:
        return json.load(x)

SQN = tuple("abcdefgh"[f] + str(8 - r) for r in range(8) for f in range(8))
KN, RAY = [], []
for s in range(64):
    r, f = divmod(s, 8)
    kn, rays = [], []
    for dr, df in ((-2, -1), (-2, 1), (-1, -2), (-1, 2),
                   (1, -2), (1, 2), (2, -1), (2, 1)):
        if 0 <= r + dr < 8 and 0 <= f + df < 8:
            kn.append((r + dr) * 8 + f + df)
    for dr, df in ((-1, 0), (1, 0), (0, -1), (0, 1),
                   (-1, -1), (-1, 1), (1, -1), (1, 1)):
        ray, rr, ff = [], r + dr, f + df
        while 0 <= rr < 8 and 0 <= ff < 8:
            ray.append(rr * 8 + ff)
            rr += dr
            ff += df
        rays.append(tuple(ray))
    KN.append(tuple(kn))
    RAY.append(tuple(rays))
KG = [tuple(ray[0] for ray in RAY[s] if ray) for s in range(64)]

VAL = {"P": 100, "N": 320, "B": 330, "R": 500, "Q": 950, "K": 0}
def _tab(s):
    return tuple((ord(c) - 107) * 5 for c in s)

PST = {
 "P": _tab("kkkkkkkkuuuuuuuummoqqommllmppmllkkkookkkljikkijllmmggmmlkkkkkkkk"),
 "N": _tab("aceeeecacgkkkkgcekmnnmkeelnoonleeknoonkeelmnnmlecgkllkgcaceeeeca"),
 "B": _tab("giiiiiigikkkkkkiiklmmlkiillmmlliikmmmmkiimmmmmmiilkkkkligiiiiiig"),
 "R": _tab("kkkkkkkklmmmmmmljkkkkkkjjkkkkkkjjkkkkkkjjkkkkkkjjkkkkkkjkkkllkkk"),
 "Q": _tab("giijjiigikkkkkkiikllllkijkllllkjkkllllkjilllllkiiklkkkkigiijjiig"),
}
KMG = _tab("eccaacceeccaacceeccaacceeccaaccegeecceegiggggggiookkkkoooqmkkmqo")
KEG = _tab("aceggecaegikkigeeioqqoieeiqssqieeiqssqieeioqqoieeekkkkeeaceeeeca")
SC = {}
for _u, _t in PST.items():
    SC[_u] = tuple(VAL[_u] + x for x in _t)
    SC[_u.lower()] = tuple(-VAL[_u] - _t[i ^ 56] for i in range(64))
SC["K"] = SC["k"] = (0,) * 64

_r = random.Random(1408)
Z = {p: [_r.getrandbits(64) for _ in range(64)] for p in "PNBRQKpnbrqk"}
Z["e"] = [_r.getrandbits(64) for _ in range(64)]
ZS = _r.getrandbits(64)
CM = [15] * 64
CM[60], CM[63], CM[56], CM[4], CM[7], CM[0] = 12, 14, 13, 3, 11, 7
PHW = {"N": 1, "B": 1, "R": 2, "Q": 4}


class Pos:
    __slots__ = ("b", "w", "ca", "ep", "sc", "z", "kp", "ph")


def cnt(P, p, d):
    P.ph += d * PHW.get(p.upper(), 0)


def parse(fen):
    P = Pos()
    P.b = ["."] * 64
    P.sc = P.ph = 0
    P.kp = [0, 0]
    parts = fen.split()
    P.w = len(parts) < 2 or parts[1] == "w"
    P.ca = sum(1 << "KQkq".index(c) for c in parts[2] if c in "KQkq") \
        if len(parts) > 2 else 0
    P.ep = -1
    if len(parts) > 3 and parts[3] != "-":
        P.ep = "abcdefgh".index(parts[3][0]) + 8 * (8 - int(parts[3][1]))
    z = ZS if not P.w else 0
    if P.ep >= 0:
        z ^= Z["e"][P.ep]
    s = 0
    for c in parts[0]:
        if c.isdigit():
            s += int(c)
        elif c != "/":
            P.b[s] = c
            P.sc += SC[c][s]
            cnt(P, c, 1)
            if c == "K":
                P.kp[0] = s
            elif c == "k":
                P.kp[1] = s
            z ^= Z[c][s]
            s += 1
    P.z = z
    return P


def atk(P, s, byw):
    b = P.b
    r, f = divmod(s, 8)
    if (byw and r < 7) or (not byw and r):
        src = (s + 7, s + 9) if byw else (s - 9, s - 7)
        if (f and b[src[0]] == ("P" if byw else "p")) \
                or (f < 7 and b[src[1]] == ("P" if byw else "p")):
            return True
    for tab, pc in ((KN, "N" if byw else "n"), (KG, "K" if byw else "k")):
        for t in tab[s]:
            if b[t] == pc:
                return True
    for d in range(8):
        for t in RAY[s][d]:
            p = b[t]
            if p != ".":
                if p.isupper() == byw and (p.upper() in "RQ" if d < 4 else p.upper() in "BQ"):
                    return True
                break
    return False


def gen(P, caps):
    b, w, out = P.b, P.w, []

    def add(s, t):
        q = b[t]
        if q == ".":
            if not caps:
                out.append((s, t, ""))
        elif q.isupper() != w:
            out.append((s, t, ""))

    def pmv(s, t, promo):
        if promo:
            out.extend((s, t, pr) for pr in "qrbn")
        else:
            out.append((s, t, ""))

    for s in range(64):
        p = b[s]
        if p == "." or p.isupper() != w:
            continue
        u = p.upper()
        r, f = divmod(s, 8)
        if u == "P":
            d = -8 if w else 8
            one = s + d
            promo = one < 8 or one > 55
            if b[one] == "." and (promo or not caps):
                pmv(s, one, promo)
                if not promo and not caps and (r == 6 if w else r == 1) \
                        and b[s + 2 * d] == ".":
                    out.append((s, s + 2 * d, ""))
            for df in (-1, 1):
                t = one + df
                if 0 <= f + df < 8 and ((b[t] != "." and b[t].isupper() != w) or t == P.ep):
                    pmv(s, t, promo)
        elif u in "NK":
            for t in (KN[s] if u == "N" else KG[s]):
                add(s, t)
            if u == "K" and not caps and s == (60 if w else 4):
                cases = ((1, (61, 62), 63, 62, 61), (2, (57, 58, 59), 56, 58, 59)) if w else \
                        ((4, (5, 6), 7, 6, 5), (8, (1, 2, 3), 0, 2, 3))
                for bit, btwn, rook, dest, thru in cases:
                    if (P.ca & bit and b[rook] == ("R" if w else "r")
                            and all(b[x] == "." for x in btwn)
                            and not atk(P, s, not w)
                            and not atk(P, thru, not w)):
                        out.append((s, dest, ""))
        else:
            for d in (range(8) if u == "Q" else range(4, 8) if u == "B" else range(4)):
                for t in RAY[s][d]:
                    add(s, t)
                    if b[t] != ".":
                        break
    return out


def make(P, m):
    b = P.b
    frm, to, pr = m
    p = b[frm]
    cap = b[to]
    eps = -1
    if p.upper() == "P" and to == P.ep and cap == "." and frm % 8 != to % 8:
        eps = to + 8 if p == "P" else to - 8
        cap = b[eps]
    undo = (cap, P.ca, P.ep, eps, P.sc, P.ph, P.kp[0], P.kp[1], P.z)
    z = P.z ^ ZS
    if P.ep >= 0:
        z ^= Z["e"][P.ep]
    if cap != ".":
        cs = eps if eps >= 0 else to
        z ^= Z[cap][cs]
        P.sc -= SC[cap][cs]
        cnt(P, cap, -1)
        if eps >= 0:
            b[eps] = "."
    b[to] = p
    b[frm] = "."
    z ^= Z[p][frm] ^ Z[p][to]
    P.sc += SC[p][to] - SC[p][frm]
    if pr:
        n = pr.upper() if p == "P" else pr
        b[to] = n
        z ^= Z[p][to] ^ Z[n][to]
        P.sc += SC[n][to] - SC[p][to]
        cnt(P, p, -1)
        cnt(P, n, 1)
    if p in "Kk":
        P.kp[0 if p == "K" else 1] = to
        if abs(to - frm) == 2:
            rf, rt = (frm + 3, frm + 1) if to > frm else (frm - 4, frm - 1)
            rp = b[rf]
            b[rt] = rp
            b[rf] = "."
            z ^= Z[rp][rf] ^ Z[rp][rt]
            P.sc += SC[rp][rt] - SC[rp][rf]
    P.ca &= CM[frm] & CM[to]
    P.ep = (frm + to) // 2 if p.upper() == "P" and abs(to - frm) == 16 else -1
    if P.ep >= 0:
        z ^= Z["e"][P.ep]
    P.z = z
    P.w = not P.w
    return undo


def unmk(P, m, undo):
    (cap, P.ca, P.ep, eps, P.sc, P.ph, kp0, kp1, P.z) = undo
    P.kp[0], P.kp[1] = kp0, kp1
    P.w = not P.w
    b = P.b
    frm, to, pr = m
    p = b[to]
    if abs(to - frm) == 2 and p in "Kk":
        rf, rt = (frm + 3, frm + 1) if to > frm else (frm - 4, frm - 1)
        b[rf] = b[rt]
        b[rt] = "."
    b[frm] = "P" if pr and P.w else "p" if pr else p
    b[to] = "."
    if cap != ".":
        b[eps if eps >= 0 else to] = cap


def legal(P, caps=False):
    out = []
    for m in gen(P, caps):
        u = make(P, m)
        if not atk(P, P.kp[0] if not P.w else P.kp[1], P.w):
            out.append(m)
        unmk(P, m, u)
    return out


def capv(P, m):
    cap = P.b[m[1]]
    return VAL[cap.upper()] if cap != "." else 0


def ev(P):
    ph = P.ph
    k = ((KMG[P.kp[0]] - KMG[P.kp[1] ^ 56]) * ph
         + (KEG[P.kp[0]] - KEG[P.kp[1] ^ 56]) * (24 - ph)) // 24
    return P.sc + k if P.w else -P.sc - k


MATE, INF = 100000, 10 ** 9
TT = {}
HIST = [0] * 4096
nodes = 0
STOP = False
BESTM = None
BUDGET, HARD = 45000, 80000


def tick():
    global nodes, STOP
    nodes += 1
    if nodes >= HARD:
        STOP = True
    return STOP


def order(P, ms, ttm):
    b = P.b

    def key(m):
        if m == ttm:
            return 1 << 30
        frm, to, pr = m
        cv = capv(P, m)
        if cv or pr:
            return (1 << 20) + cv * 16 - VAL[b[frm].upper()] // 16 \
                + (VAL[pr.upper()] * 16 if pr else 0)
        return HIST[frm * 64 + to]

    ms.sort(key=key, reverse=True)


def qs(P, alpha, beta, ply):
    if tick():
        return 0
    w = P.w
    if atk(P, P.kp[0] if w else P.kp[1], not w):
        ms = legal(P)
        if not ms:
            return -MATE + ply
        best = -INF
    else:
        best = ev(P)
        if best >= beta:
            return best
        if best > alpha:
            alpha = best
        ms = legal(P, True)
    order(P, ms, None)
    for m in ms:
        u = make(P, m)
        sc = -qs(P, -beta, -alpha, ply + 1)
        unmk(P, m, u)
        if STOP:
            return 0
        if sc > best:
            best = sc
        if sc > alpha:
            alpha = sc
            if alpha >= beta:
                break
    return best


def search(P, depth, alpha, beta, ply):
    global BESTM
    if depth <= 0 or ply >= 100:
        return qs(P, alpha, beta, ply)
    if tick():
        return 0
    w = P.w
    chk = atk(P, P.kp[0] if w else P.kp[1], not w)
    if chk:
        depth += 1
    a0 = alpha
    ent = TT.get(P.z)
    ttm = ent[3] if ent else None
    if ent and ply and ent[0] >= depth:
        if ent[2] == 0 or (ent[2] == 1 and ent[1] >= beta) \
                or (ent[2] == 2 and ent[1] <= alpha):
            return ent[1]
    ms = legal(P)
    if not ms:
        return -MATE + ply if chk else 0
    order(P, ms, ttm)
    best, bm = -INF, ms[0]
    for i, m in enumerate(ms):
        frm, to, pr = m
        quiet = not capv(P, m) and not pr
        u = make(P, m)
        if i == 0:
            sc = -search(P, depth - 1, -beta, -alpha, ply + 1)
        else:
            sc = -search(P, depth - 1, -alpha - 1, -alpha, ply + 1)
            if alpha < sc < beta:
                sc = -search(P, depth - 1, -beta, -alpha, ply + 1)
        unmk(P, m, u)
        if STOP:
            return 0
        if sc > best:
            best, bm = sc, m
        if sc > alpha:
            alpha = sc
            if alpha >= beta:
                if quiet:
                    HIST[frm * 64 + to] += depth * depth
                break
    if not STOP:
        fl = 1 if best >= beta else 2 if best <= a0 else 0
        TT[P.z] = (depth, best, fl, bm)
        if ply == 0:
            BESTM = bm
    return best


def uci(m):
    return SQN[m[0]] + SQN[m[1]] + m[2]


def choose(fen, leg):
    global nodes, STOP, BESTM
    P = parse(fen)
    lset = set(leg)
    ms = [m for m in legal(P) if uci(m) in lset]
    if not ms:
        return leg[0]
    if len(ms) == 1:
        return uci(ms[0])
    if len(TT) > 300000:
        TT.clear()
    nodes, STOP = 0, False
    best = ms[0]
    for depth in range(1, 100):
        BESTM = None
        search(P, depth, -INF, INF, 0)
        if STOP or BESTM is None:
            break
        best = BESTM
        if nodes >= BUDGET:
            break
    return uci(best)


if ENV:
    while True:
        g = post("/game", {})
        if g["status"] == "done":
            break
        while g["status"] == "your_move":
            try:
                mv = choose(g["fen"], g["legal_moves"])
            except Exception:
                mv = g["legal_moves"][0]
            g = post("/move", {"game": g["game"], "move": mv})
