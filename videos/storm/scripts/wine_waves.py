"""v6: what the wine really does when one drop lands in it.

Not key-framed shapes. The free surface of the wine in the glass is solved as linear capillary-gravity waves in a
circular container (radius R, wall = no-flux), started by the pressure impulse of the drop at its point of impact
(pressure-impulse theory: surface velocity = k * impulse per mode, so the liquid pushed out of the crater rises as a
rim right next to it and no volume is lost); (which is 5 mm off the glass axis, so the pattern is not rotationally symmetric and reflects off the wall
unevenly, as in a real glass:

    eta(r, th, t) = sum_mn  b_mn / w_mn * sin(w_mn t) * exp(-2 nu k_mn^2 t) * J_m(k_mn r) cos(m th)
    w^2 = g k + (sigma / rho) k^3            (deep-water capillary-gravity dispersion)
    J_m'(k_mn R) = 0                         (wall)

Wine: rho 990 kg/m3, sigma 0.047 N/m, nu 1.6e-6 m2/s. Drop: 6 mm. The impulse is scaled so that the crater reaches
CRATER m at its deepest: a gentle impact (no crown sheet, no jet pinch-off - those need an order of magnitude more energy).
What the solution gives by itself: crater -> closing -> a low, broad rebound mound that sinks back -> rings of capillary
waves with the short ones running ahead (dispersion) -> reflection at the wall -> viscous decay.
Pure numpy (the render runners' Blender python has no scipy)."""
import math
import numpy as np

G, SIGMA, RHO, NU = 9.81, 0.047, 990.0, 1.6e-6
R_WALL = 0.0390          # free-surface radius of the pour in this glass
A_IMP = 0.0036           # radius of the momentum patch (drop radius 3 mm, spread at contact)
CRATER = 0.0034          # deepest point of the crater, m
M_MAX, KR_MAX = 14, 150.0

_cache = {}


def _jtab(m, xmax, n=30000):
    """J_m on a fine grid via the integral representation (1/pi) int_0^pi cos(m tau - x sin tau) dtau"""
    x = np.linspace(0.0, xmax, n); tau = (np.arange(256) + 0.5) * math.pi / 256
    out = np.empty(n)
    for i in range(0, n, 3000):
        xs = x[i:i + 3000, None]
        out[i:i + 3000] = np.cos(m * tau[None, :] - xs * np.sin(tau)[None, :]).mean(1)
    return x, out


def _modes(x0):
    key = round(x0, 6)
    if key in _cache:
        return _cache[key]
    xmax = KR_MAX + 5
    nr, nt = 360, 192
    r = (np.arange(nr) + 0.5) / nr * R_WALL; th = (np.arange(nt) + 0.5) / nt * 2 * math.pi
    rr, tt = np.meshgrid(r, th, indexing="ij"); dA = rr * (R_WALL / nr) * (2 * math.pi / nt)
    d2 = rr ** 2 + x0 ** 2 - 2 * rr * x0 * np.cos(tt)          # distance^2 to the impact point (on the th = 0 axis)
    v0 = -np.exp(-d2 / A_IMP ** 2)                             # pressure impulse of the impact (Gaussian patch)
    ms, ks, bs, tabs = [], [], [], {}
    for m in range(M_MAX + 1):
        x, j = _jtab(m, xmax); tabs[m] = (x, j)
        dj = np.gradient(j, x); sg = np.sign(dj); idx = np.where(sg[:-1] * sg[1:] < 0)[0]
        roots = x[idx] - dj[idx] * (x[idx + 1] - x[idx]) / (dj[idx + 1] - dj[idx])
        roots = roots[(roots > 0.5) & (roots < KR_MAX)]
        cm = np.cos(m * th)
        for kr in roots:
            k = kr / R_WALL
            phi = np.interp(k * r, x, j)[:, None] * cm[None, :]
            b = k * (v0 * phi * dA).sum() / (phi * phi * dA).sum()   # impulse P -> surface velocity: d(phi)/dz = k * phi
            ms.append(m); ks.append(k); bs.append(b)
    ms, ks, bs = np.array(ms), np.array(ks), np.array(bs)
    w = np.sqrt(G * ks + SIGMA / RHO * ks ** 3); gam = 2 * NU * ks ** 2
    # scale: deepest crater at the impact point = CRATER
    tcs = np.linspace(0.002, 0.06, 59); jm0 = np.array([np.interp(k * x0, *tabs[m]) for m, k in zip(ms, ks)])
    depth = np.array([(bs / w * np.sin(w * t) * np.exp(-gam * t) * jm0).sum() for t in tcs])
    scale = CRATER / -depth.min()
    _cache[key] = (ms, ks, bs * scale, w, gam, tabs, float(tcs[depth.argmin()]))
    return _cache[key]


def eta(xl, yl, t, impact=(0.004, -0.003)):
    """surface height (m) at glass-local points xl, yl (arrays), t seconds after contact"""
    x0 = math.hypot(*impact); a0 = math.atan2(impact[1], impact[0])
    ms, ks, bs, w, gam, tabs, _ = _modes(x0)
    r = np.minimum(np.hypot(xl, yl), R_WALL); th = np.arctan2(yl, xl) - a0
    amp = bs / w * np.sin(w * t) * np.exp(-gam * t)
    out = np.zeros_like(r)
    for m in range(M_MAX + 1):
        sel = np.where(ms == m)[0]
        if not len(sel):
            continue
        x, j = tabs[m]; cm = np.cos(m * th); acc = np.zeros_like(r)
        for i in sel:
            if abs(amp[i]) > 2e-8:
                acc += amp[i] * np.interp(ks[i] * r, x, j)
        out += acc * cm
    # the drop itself, while it is being swallowed (6 ms): a rounded cap that sinks into the forming crater
    d2 = (xl - impact[0]) ** 2 + (yl - impact[1]) ** 2
    out += 0.0030 * math.exp(-t / 0.0035) * np.exp(-d2 / 0.0026 ** 2)
    return out


def t_crater(impact=(0.004, -0.003)):
    return _modes(math.hypot(*impact))[6]


if __name__ == "__main__":                                   # physics check without Blender
    xs = np.linspace(-0.039, 0.039, 157); ys = np.zeros_like(xs) - 0.003
    print("deepest crater at %.1f ms" % (t_crater() * 1000))
    for t in (0.004, 0.012, 0.02, 0.035, 0.05, 0.07, 0.10, 0.15, 0.22, 0.4):
        e = eta(xs, ys, t); i0 = np.argmin(np.abs(xs - 0.004))
        print("t=%5.0f ms  centre %+6.2f mm   max %+5.2f mm at r=%4.1f mm   min %+5.2f mm" % (
            t * 1000, e[i0] * 1000, e.max() * 1000, abs(xs[e.argmax()] - 0.004) * 1000, e.min() * 1000))
