import ctypes, subprocess, tempfile, os, sys, random, math, wave, json
from array import array
R = "/Users/petr/Development/pixel-p747"
OUT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, R + "/engine/tests")
from crackle_lib import CCrackle
MAXS, MAXE = 16, 24
class Field(ctypes.Structure):
    _fields_ = [("w", ctypes.c_int32), ("h", ctypes.c_int32), ("heat", ctypes.POINTER(ctypes.c_uint8)),
                ("cooling", ctypes.POINTER(ctypes.c_uint8)), ("rng", ctypes.c_uint32), ("map_row", ctypes.c_int32),
                ("fast_map_row", ctypes.c_int32)] + [(n, ctypes.c_int32) for n in
                ("decay","cool","sway","spots","spread","fast","embers","fade")] + [("spot_x", ctypes.c_int32*MAXS)] + \
               [(n, ctypes.c_int32*MAXE) for n in ("ember_x","ember_y","ember_vx","ember_vy","ember_heat")] + \
               [("base", ctypes.c_int32), ("filter", ctypes.c_int32), ("born", ctypes.c_int32)]
tmp = tempfile.mkdtemp(); so = tmp + "/f.so"
subprocess.run(["clang","-std=c99","-O2","-shared","-fPIC","-I",R+"/engine/driver/src","-I",R+"/engine/core","-o",so,R+"/engine/core/fx_fire.c"],check=True)
lib = ctypes.CDLL(so)
W, H = 160, 120
LOOK = (33, 24, 1, 12, 16, 128, 40, 4)
RATE, SR, SECS = 25, 16000, 15
SPS = SR // RATE  # 640 samples a step

def run(seed, bodies=False):
    heat = (ctypes.c_uint8 * (W*H))(); cool = (ctypes.c_uint8 * (256*32))()
    f = Field(); lib.fx_fire_init(ctypes.byref(f), heat, cool, W, H, seed)
    lib.fx_fire_set_look(ctypes.byref(f), *LOOK)
    if bodies: f.base = 0
    random.seed(seed); wind = target = 0; gust = 0
    rec = []; prev = bytes(W*H); ms = 1000 // RATE
    bd = [[random.randrange(20, W-20), random.uniform(0, 2.2)] for _ in range(4)]  # x, phase s
    for n in range(RATE * (SECS + 2)):
        gust -= ms
        if gust <= 0:
            target = random.randrange(-60, 61); gust = 1500 + random.randrange(1500)
        for _ in range(3):  # the frame's 16 ms ease, about 2.5 frames a step
            d = target - wind; wind += d // 8 if d < 0 else (d + 7) // 8
        flare = 0.0; burned = 0
        if bodies:
            for b in bd:
                b[1] += 1.0 / RATE
                T = 0.3 + 0.1 * (int(b[0]) % 5)  # fall time s; v_hit = 400 / T px/s
                if b[1] < T:
                    y = int(H * (b[1] / T) ** 2)
                elif b[1] < T + 1.5:
                    y = H - 6
                    if b[1] - 1.0/RATE < T:
                        v = 400 / T
                        if v >= 600:
                            r = int(v) // 150; flare = max(flare, r)
                            lib.fx_fire_burn(ctypes.byref(f), b[0], y, b[0], y, r, 255)
                else:
                    b[1] = 0; b[0] = random.randrange(20, W-20); continue
                lib.fx_fire_burn(ctypes.byref(f), b[0], min(y, H-1), b[0], min(y, H-1), 3, 200); burned += 1
        lib.fx_fire_step(ctypes.byref(f), 1, wind)
        b = bytes(heat)
        births = []
        if f.born:
            for i in range(MAXE):
                if f.ember_heat[i] == 243 and f.ember_y[i] // 256 >= H - 8:
                    vx, vy = f.ember_vx[i], f.ember_vy[i]
                    births.append(dict(vy=-vy / 256, speed=math.hypot(vx, vy) / 256))
            f.born = 0
        T = 128
        tot = sum(b); area = sum(1 for v in b if v > T)
        top = H
        for y in range(H):
            if max(b[y*W:(y+1)*W]) > T: top = y; break
        dl1 = sum(abs(x - y) for x, y in zip(b, prev)); prev = b
        rec.append(dict(total=tot, area=area, height=H - top, change=dl1, wind=wind, births=births, flare=flare, burned=burned))
    return rec[2 * RATE:]  # the first 2 s warm up the empty field

def pct(vals, p=0.98):
    s = sorted(vals); return max(1e-9, s[int(p * (len(s)-1))])
def norm(rec, key, lo=None):
    v = [r[key] for r in rec]; m = pct(v); mn = min(v) if lo is None else lo
    return [min(1.0, max(0.0, (x - mn) / (m - mn + 1e-9))) for x in v]
def interp(c, n):  # control per step -> per sample, linear
    out = []
    for i in range(len(c)):
        a = c[i]; b = c[min(i+1, len(c)-1)]
        out += [a + (b-a) * k / SPS for k in range(SPS)]
    return out[:n]
class Noise:
    def __init__(s, seed): s.r = random.Random(seed)
    def __call__(s): return s.r.uniform(-1, 1)
def lp(a):  # one-pole coefficient from cutoff Hz
    return 1 - math.exp(-2 * math.pi * a / SR)

def lapping(rec, seed, floor=0.0):
    n = len(rec) * SPS; tot = interp(norm(rec, "total"), n); hgt = interp(norm(rec, "height"), n)
    ch = interp(norm(rec, "change"), n); nz = Noise(seed); nm = Noise(seed+1)
    o = []; a1 = a2 = a3 = a4 = 0.0; m1 = m2 = 0.0
    for i in range(n):
        x = nz()
        fc = 90 + 260 * hgt[i]  # taller flame, higher cutoff
        c = lp(fc)
        a1 += (x - a1) * c; a2 += (a1 - a2) * c; a3 += (a2 - a3) * c  # 3 poles, steeper than the C roar's 2
        m1 += (nm() - m1) * lp(6); m2 += (m1 - m2) * lp(6)  # flutter 0..~6 Hz
        flut = max(0.0, 0.5 + 6.0 * m2)  # centred, then squared as Farnell does
        flut = flut * flut
        lev = (0.25 + 0.75 * tot[i]) * (0.35 + 0.65 * min(1.0, flut)) * (0.7 + 0.5 * ch[i])
        o.append(a3 * lev)
    return o
def hiss(rec, seed):
    n = len(rec) * SPS; area = interp(norm(rec, "area"), n); ch = interp(norm(rec, "change"), n)
    nz = Noise(seed); nm = Noise(seed+1); o = []; hp = 0.0; m1 = m2 = 0.0
    for i in range(n):
        x = nz(); hp += (x - hp) * lp(2500); y = x - hp
        m1 += (nm() - m1) * lp(9); m2 += (m1 - m2) * lp(9)
        g = max(0.0, 0.5 + 7.0 * m2); g = g ** 4  # Farnell: 4th power, short bursts with silence
        o.append(y * min(1.0, g) * (0.15 + 0.85 * area[i]) * (0.6 + 0.6 * ch[i]))
    return o
def crackle(rec, n, look, rng=1):
    c = CCrackle(rng, look); out = array("h")
    births = []
    for r in rec: births.append(len(r["births"]))
    i = 0; pend = 0
    for blk in range(n // 256):
        t = blk * 256 // SPS
        while i <= t and i < len(births): pend += births[i]; i += 1
        c.add_pops(pend); pend = 0
        b = array("h", bytes(512)); c.render(b); out.extend(b)
    return list(out), c.counts()
def ember_pops(rec, n, seed, sized=True, wood=False):
    o = [0.0] * (n + 8000); rg = random.Random(seed)
    for s, r in enumerate(rec):
        for e in r["births"]:
            q = (e["vy"] - 2) / 3.0 if sized else rg.random()  # 0..1; vy is 2..5 rows a step, so 36..90 rows of climb
            amp = 0.18 + 0.82 * q * q
            dec = 0.9965 - 0.0035 * q  # bigger: longer
            sh = lp(1500 + 4500 * q)  # bigger: brighter
            t0 = s * SPS + rg.randrange(0, SPS); v = 0.0; env = amp * 14000
            for k in range(5200):
                v += (rg.uniform(-1, 1) - v) * sh
                o[t0 + k] += v * env; env *= dec
                if env < 8: break
    return o[:n]
def thump(rec, n):
    o = [0.0] * (n + 12000)
    for s, r in enumerate(rec):
        if r["flare"]:
            amp = 9000 * min(1.0, r["flare"] / 9.0); t0 = s * SPS; ph = 0.0
            for k in range(9000):
                fr = 55 + 60 * math.exp(-k / 700.0); ph += 2 * math.pi * fr / SR
                o[t0 + k] += amp * math.sin(ph) * math.exp(-k / 1500.0)
                o[t0 + k] += amp * 0.5 * random.uniform(-1, 1) * math.exp(-k / 400.0) * 0.4
    return o[:n]
def burn_crackle(rec, n, seed):  # sparse, woody: rate follows the trail burn count and the heat change
    o = [0.0] * (n + 8000); rg = random.Random(seed)
    ch = norm(rec, "change")
    for s, r in enumerate(rec):
        rate = 0.015 + 0.25 * ch[s] * (1 if r["burned"] else 0.3)  # pops a step
        if rg.random() < rate:
            f = rg.uniform(500, 3000); q = rg.random(); amp = (0.2 + 0.8 * q) * 9000
            dec = rg.uniform(0.992, 0.998); t0 = s * SPS + rg.randrange(SPS); ph = 0.0; v = 0.0
            for k in range(2500):
                ph += 2*math.pi*f/SR; v += (rg.uniform(-1,1)-v)*0.5
                o[t0+k] += (0.6*v + 0.4*math.sin(ph)) * amp; amp *= dec
                if amp < 5: break
    return o[:n]
def write(name, x, target=2000):
    rms = math.sqrt(sum(v*v for v in x)/len(x)); g = target / rms
    L = 0.9 * 32767
    y = [int(L * math.tanh(v * g / L)) if abs(v * g) > 0.5 * L else int(v * g) for v in x]  # soft limit above 45 %
    # tanh limits to 90 %; re-aim the RMS once more
    r = math.sqrt(sum(v*v for v in y)/len(y)); g2 = target / r
    y = [int(max(-L, min(L, v * g2))) for v in y]
    rms2 = math.sqrt(sum(v*v for v in y)/len(y)); pk2 = max(abs(v) for v in y)
    p = f"{OUT}/{name}"; w = wave.open(p, "wb"); w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes(array("h", y).tobytes()); w.close()
    print(f"{p} rms {rms2:.0f} peak {pk2} ({pk2/32767*100:.0f}%)"); return rms2, pk2

if __name__ == "__main__":
    rec = run(595); n = len(rec) * SPS
    json.dump(rec, open(OUT + "/steps.json", "w"))
    for k in ("total","area","height","change","wind"):
        v = [r[k] for r in rec]; print(k, "min", min(v), "max", max(v), "mean", sum(v)//len(v))
    nb = [len(r["births"]) for r in rec]; print("births", sum(nb), "per s", sum(nb)/SECS)
    vys = [e["vy"] for r in rec for e in r["births"]]; print("vy of births", sorted(set(round(v,2) for v in vys)))
    LK = (6, 24, 6000, 12000, 28400, 31600, 3, 4000, 224)
    a, cnt = crackle(rec, n, LK); print("crackle counts", cnt); write("p750-a-today.wav", a)
    NOROAR = (6, 0, 6000, 12000, 28400, 31600, 3, 4000, 224)
    cr, cnt = crackle(rec, n, NOROAR); print("crackle noroar counts", cnt)
    lap = lapping(rec, 7); hs = hiss(rec, 9)
    def mix(lapg, hissg, crg, pops=None, popg=0):
        base = [lapg * l * 40000 + hissg * h * 25000 for l, h in zip(lap, hs)]
        base = [b + crg * c * 0.6 for b, c in zip(base, cr)]
        if pops: base = [b + popg * p for b, p in zip(base, pops)]
        return base
    write("p750-b-layers.wav", mix(1.0, 0.5, 1.0))
    pops = ember_pops(rec, n, 11, sized=True)
    # (c): replace the C pops by the sized pops; keep the C crackle's roar off and its pops off as well
    write("p750-c-sized-pops.wav", [l*40000 + h*12000 + p for l, h, p in zip(lap, hs, pops)])
    write("p750-c0-unsized-pops.wav", [l*40000 + h*12000 + p for l, h, p in zip(lap, hs, ember_pops(rec, n, 11, sized=False))])
    # (d) burning bodies
    rb = run(596, bodies=True); json.dump(rb, open(OUT + "/steps_burning.json", "w"))
    for k in ("total","area","height","change"):
        v = [r[k] for r in rb]; print("burning", k, "min", min(v), "max", max(v), "mean", sum(v)//len(v))
    print("flares", sum(1 for r in rb if r["flare"]))
    lb = lapping(rb, 21); hb = hiss(rb, 23); bc = burn_crackle(rb, n, 25); th = thump(rb, n)
    write("p750-d-burning-object.wav", [l*33000 + h*9000 + c + t for l, h, c, t in zip(lb, hb, bc, th)])
