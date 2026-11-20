import sys, math, random, wave, importlib.util
from array import array
sys.dont_write_bytecode = True
P = "/private/tmp/claude-501/-Users-petr-Development-firebeetle-games/42053813-a780-4e73-8e84-3f6b69758cd3/scratchpad/p750r2"
spec = importlib.util.spec_from_file_location("demo", "/Users/petr/Development/pixel-sound/docs/discovery/2026-11-09-sound/p750/demo.py")
D = importlib.util.module_from_spec(spec); spec.loader.exec_module(D)
SR, SPS = D.SR, D.SPS
rec = D.run(595); N = len(rec) * SPS   # real fx_fire kernel, same seed as round 1
lp = D.lp

def write(name, x, target=2000):
    L = 0.9 * 32767
    rms = math.sqrt(sum(v*v for v in x)/len(x)); g = target / rms
    y = [L*math.tanh(v*g/L) for v in x]
    for _ in range(8):
        r = math.sqrt(sum(v*v for v in y)/len(y)); g = g*target/r
        y = [L*math.tanh(v*g/L) for v in x]
    y = [int(v) for v in y]
    rms2 = math.sqrt(sum(v*v for v in y)/len(y)); pk = max(abs(v) for v in y)
    w = wave.open(f"{P}/{name}", "wb"); w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes(array("h", y).tobytes()); w.close()
    print(f"{P}/{name} rms {rms2:.0f} peak {pk} ({pk/32767*100:.0f}%)")

def slow(seed, hz, n):  # slow random signal, ~unit std after 2 poles, mean 0
    r = random.Random(seed); a = b = 0.0; c = lp(hz); o = []
    for _ in range(n):
        a += (r.uniform(-1, 1) - a) * c; b += (a - b) * c; o.append(b)
    s = math.sqrt(sum(v*v for v in o)/n); return [v/s for v in o]

def resonate(out, t0, fc, q, amp, dur, rg, modes=1):
    # Farnell-style: impulse into a 2-pole band-pass, square-law envelope; modes>1 adds inharmonic partials (woody)
    for m in range(modes):
        f = fc * (1.0 if m == 0 else rg.uniform(1.6, 2.9)); g = amp * (1.0 if m == 0 else 0.5)
        th = 2*math.pi*f/SR; rr = math.exp(-math.pi*f/q/SR)
        c1 = 2*rr*math.cos(th); c2 = rr*rr; y1 = y2 = 0.0; L = int(dur*SR)
        for k in range(L):
            x = g * (rg.uniform(-1, 1) if k < 8 else 0.0)  # short noise burst as the "fracture"
            y = x + c1*y1 - c2*y2; y2 = y1; y1 = y
            e = 1 - k/L
            if t0+k < len(out): out[t0+k] += y * e * e

def bed_flutter(seed):
    lap = D.lapping(rec, seed)
    return lap

def make_e():
    rg = random.Random(5); o = [0.0]*(N+4000)
    m = slow(31, 0.8, N); heat = D.interp(D.norm(rec, "total"), N); ch = D.interp(D.norm(rec, "change"), N)
    # dense small crackles: rate follows slow random signal (squared) and heat; clustering by follow-ups
    i = 0
    while i < N:
        rate = (25 + 220*max(0.0, 0.4 + 0.9*m[i])**2) * (0.5 + 0.8*heat[i])  # per second
        i += 1
        if rg.random() < rate/SR:
            t = i
            for _ in range(1 + (rg.random() < 0.35)*rg.randrange(1, 4)):  # cluster
                u = rg.random(); amp = 900 * u**3 + 60     # many tiny, few mid
                fc = math.exp(rg.uniform(math.log(500), math.log(4500)))
                resonate(o, t, fc, rg.uniform(5, 14), amp, rg.uniform(0.004, 0.014), rg, modes=2 if u > 0.5 else 1)
                t += int(rg.uniform(0.004, 0.04)*SR)
    # ember snaps sized by rise speed
    for s, r in enumerate(rec):
        for e in r["births"]:
            q = (e["vy"]-2)/3.0; t0 = s*SPS + rg.randrange(SPS)
            fc = 700 + 1800*(1-q) + rg.uniform(-150, 150)   # bigger: lower, woodier
            resonate(o, t0, fc, 6 + 6*q, 9000*(0.25+0.75*q*q), 0.012 + 0.03*q, rg, modes=3)
            for _ in range(int(2 + 4*q)):   # afterburst of small crackles
                resonate(o, t0 + int(rg.uniform(0.01, 0.12)*SR), rg.uniform(900, 3500), 8, rg.uniform(300, 1500), 0.008, rg, modes=2)
    # bed: flutter lapping (low) + sizzle made of very dense tiny ticks, all gated by the slow signal
    lap = D.lapping(rec, 7); n = N
    sz = [0.0]*(N+400)
    for i in range(N):
        if rg.random() < (1500/SR)*(0.3 + 0.7*max(0.0, 0.5+0.8*m[i])):
            a = rg.random()**4 * 700; sz[i] += a; sz[i+1] -= a*0.6
    # band-limit sizzle gently
    v = 0.0; szl = []
    for i in range(N): v += (sz[i]-v)*0.55; szl.append(sz[i]-v*0.5)
    bed = [lap[i]*14000 + szl[i]*1.0 for i in range(N)]
    return [o[i] + bed[i] for i in range(N)], o[:N], bed

# --- recording ---
def load(p):
    w = wave.open(p); a = array("h"); a.frombytes(w.readframes(w.getnframes())); return [v/32768 for v in a]
src = load(P + "/source/fire16k.wav")
def onsets(x, win=48):  # energy per 3 ms; onset where energy jumps >6x over the mean of the previous 20 ms and is above a floor
    E = [sum(v*v for v in x[i:i+win])/win for i in range(0, len(x)-win, win)]
    floor = sorted(E)[int(len(E)*0.5)]*4 + 1e-9; on = []; last = -99
    for k in range(7, len(E)):
        prev = sum(E[k-7:k-1])/6 + 1e-9
        if E[k] > 6*prev and E[k] > floor and k-last > 12: on.append(k*win); last = k
    return on
ons = onsets(src); print("recording", len(src)/SR, "s,", len(ons), "onsets")
def hann(L): return [0.5-0.5*math.cos(2*math.pi*k/(L-1)) for k in range(L)]
def peak_of(g): return max(abs(v) for v in g)
crack = []   # (grain, strength)
for t in ons:
    g = src[max(0, t-40):t+int(0.12*SR)]; L = len(g)
    fo = [g[k]*(1.0 if k < 80 else math.exp(-(k-80)/(0.05*SR))) for k in range(L)]
    crack.append((fo, peak_of(fo)))
crack.sort(key=lambda c: c[1])
free = [True]*len(src)
for t in ons:
    for k in range(max(0, t-200), min(len(src), t+int(0.2*SR))): free[k] = False
def bed_grains(rg, n, hz_density=14):
    o = [0.0]*(n+SR); t = 0
    while t < n:
        L = int(rg.uniform(0.05, 0.3)*SR); 
        for _ in range(30):
            p = rg.randrange(0, len(src)-L)
            if all(free[p:p+L:40]): break
        sp = rg.uniform(0.85, 1.15); w = hann(L); gain = rg.uniform(0.6, 1.0)
        for k in range(L):
            j = p + k*sp; ji = int(j)
            if ji+1 >= len(src): break
            o[t+k] += (src[ji]*(1-(j-ji)) + src[ji+1]*(j-ji)) * w[k] * gain
        t += L//2   # 50% overlap, Hann = crossfade
    return o[:n]
def make_f():
    rg = random.Random(3)
    # bed: 3 layers of grains, level follows heat and the slow signal so it is not steady
    bed = bed_grains(rg, N); heat = D.interp(D.norm(rec, "total"), N); m = slow(41, 0.7, N)
    lev = [(0.5+0.5*heat[i])*(0.55+0.45*min(1.5, max(0.0, 0.8+0.7*m[i]))) for i in range(N)]
    o = [bed[i]*lev[i]*6000 for i in range(N)] + [0.0]*40000
    for s, r in enumerate(rec):
        for e in r["births"]:
            q = (e["vy"]-2)/3.0; idx = min(len(crack)-1, int(q*(len(crack)-0.01)))   # louder grain for faster ember
            g, pk = crack[idx]; amp = (0.3+0.7*q*q)*22000/pk; t0 = s*SPS + rg.randrange(SPS)
            for k, v in enumerate(g): o[t0+k] += v*amp
    return o[:N]
if __name__ == "__main__":
    e, e_cr, e_bed = make_e(); write("p750r2-e-farnell.wav", e)
    f = make_f(); write("p750r2-f-grains.wav", f)
    # g: hybrid. grains bed (real texture) + Farnell dense crackles and woody snaps; no synthetic bed
    g = [f[i]*0.8 + e_cr[i]*0.9 + e_bed[i]*0.15 for i in range(N)]
    write("p750r2-g-hybrid.wav", g)
