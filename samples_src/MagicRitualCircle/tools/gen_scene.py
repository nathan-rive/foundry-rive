#!/usr/bin/env python3
"""Generates scene.rml for the MagicRitualCircle tile.

Layout: 600x600 artboard = 6x6 grid units of 100px.
Ritual sites sit centred in grid cells (4,4), (0,3) and (3,0); the central
circle sits at their centroid, so all three conduits are the same length.

Run:  python3 tools/gen_scene.py   (writes ../scene.rml)
"""
import math, os, random

UNIT = 100
W = H = 6 * UNIT
SITES = [  # (name, cell col, cell row, sigil rune)
    ("Site 1", 4, 4, "z"),
    ("Site 2", 0, 3, "t"),
    ("Site 3", 3, 0, "ng"),
]
SITE_POS = [((c + 0.5) * UNIT, (r + 0.5) * UNIT) for _, c, r, _ in SITES]
CX = sum(p[0] for p in SITE_POS) / 3
CY = sum(p[1] for p in SITE_POS) / 3
SITE_ANG = [math.atan2(y - CY, x - CX) for x, y in SITE_POS]

# palette (ARGB)
ENGRAVE_DARK = "A0120D0A"
ENGRAVE_LIGHT = "30FFF4E0"
GLOW_OUTER = "705B3CFF"   # violet halo
GLOW_MID = "C03FD8FF"     # arcane cyan
GLOW_CORE = "FFE9FDFF"    # white-hot core

# ---------------------------------------------------------------- ids
_next = [10]
def nid():
    _next[0] += 1
    return f"0:{_next[0]}"

def f(v):
    return f"{v:.3f}".rstrip("0").rstrip(".") if isinstance(v, float) else str(v)

# ---------------------------------------------------------------- runes
# Futhark-like glyphs, normalised: x in ~[-.3,.3], y in [-.5,.5] (y=-.5 is "up")
STEM = [(0, -.5), (0, .5)]
RUNES = {
    "f": [STEM, [(0, -.15), (.3, -.45)], [(0, .1), (.3, -.2)]],
    "u": [[(-.25, .5), (-.25, -.5), (.25, -.2), (.25, .5)]],
    "th": [STEM, [(0, -.25), (.25, 0), (0, .25)]],
    "a": [STEM, [(0, -.5), (.3, -.25)], [(0, -.2), (.3, .05)]],
    "r": [STEM, [(0, -.5), (.25, -.27), (0, -.04), (.27, .5)]],
    "k": [[(.25, -.5), (-.2, 0), (.25, .5)]],
    "g": [[(-.3, -.5), (.3, .5)], [(.3, -.5), (-.3, .5)]],
    "w": [STEM, [(0, -.5), (.25, -.3), (0, -.1)]],
    "h": [[(-.25, -.5), (-.25, .5)], [(.25, -.5), (.25, .5)], [(-.25, -.15), (.25, .15)]],
    "n": [STEM, [(-.25, -.15), (.25, .15)]],
    "i": [STEM],
    "ei": [STEM, [(0, -.5), (.22, -.28)], [(0, .5), (-.22, .28)]],
    "p": [[(-.2, -.5), (-.2, .5)], [(-.2, -.5), (.2, -.25)], [(-.2, .5), (.2, .25)]],
    "z": [STEM, [(0, -.1), (-.3, -.5)], [(0, -.1), (.3, -.5)]],
    "s": [[(.22, -.5), (-.22, -.12), (.22, .12), (-.22, .5)]],
    "t": [STEM, [(-.3, -.22), (0, -.5), (.3, -.22)]],
    "b": [STEM, [(0, -.5), (.25, -.25), (0, 0), (.25, .25), (0, .5)]],
    "e": [[(-.25, .5), (-.25, -.5), (0, -.2), (.25, -.5), (.25, .5)]],
    "m": [[(-.25, .5), (-.25, -.5), (.25, 0)], [(.25, .5), (.25, -.5), (-.25, 0)]],
    "l": [STEM, [(0, -.5), (.25, -.25)]],
    "ng": [[(0, -.45), (.27, 0), (0, .45), (-.27, 0), (0, -.45)]],
    "d": [[(-.25, -.5), (.25, .5), (.25, -.5), (-.25, .5), (-.25, -.5)]],
    "o": [[(-.3, .5), (.2, -.12), (0, -.45), (-.2, -.12), (.3, .5)]],
}
RUNE_KEYS = [k for k in RUNES if k not in ("i",)]
rng = random.Random(7)

def rune_polys(key, cx, cy, ang, h):
    """Glyph centred at (cx,cy), its 'up' pointing along angle ang (radians)."""
    ux, uy = math.cos(ang), math.sin(ang)      # up direction (outward)
    tx, ty = -uy, ux                           # tangent
    out = []
    for poly in RUNES[key]:
        pts = []
        for x, y in poly:
            pts.append((cx + (-y * h) * ux + (x * h) * tx, cy + (-y * h) * uy + (x * h) * ty))
        out.append(pts)
    return out

def ring_runes(r, h, angles, keys=None):
    polys = []
    for i, a in enumerate(angles):
        k = keys[i] if keys else rng.choice(RUNE_KEYS)
        polys += rune_polys(k, r * math.cos(a), r * math.sin(a), a, h)
    return polys

# ---------------------------------------------------------------- geometry xml
def poly_xml(pts, closed=False, ind="    "):
    cl = ' isClosed="true"' if closed else ""
    s = f'{ind}<PointsPath{cl} name="P" id="{nid()}">\n'
    for x, y in pts:
        s += f'{ind}    <StraightVertex x="{f(float(x))}" y="{f(float(y))}" id="{nid()}"/>\n'
    return s + f'{ind}</PointsPath>\n'

def ellipse_xml(r, x=0.0, y=0.0, ind="    "):
    pos = f' x="{f(float(x))}" y="{f(float(y))}"' if (x or y) else ""
    return f'{ind}<Ellipse{pos} width="{f(2.0*r)}" height="{f(2.0*r)}" name="Circle" id="{nid()}"/>\n'

def geom_xml(geom, ind):
    s = ""
    for g in geom:
        if g[0] == "circle":
            s += ellipse_xml(g[1], *(g[2:] if len(g) > 2 else ()), ind=ind)
        elif g[0] == "poly":
            s += poly_xml(g[1], ind=ind)
        elif g[0] == "closed":
            s += poly_xml(g[1], closed=True, ind=ind)
    return s

def solid(c, ind):
    return f'{ind}<SolidColor colorValue="{c}" name="Color" id="{nid()}"/>\n'

def dash_xml(on, off, ind, dash_id=None):
    did = dash_id or nid()
    return (f'{ind}<DashPath name="Dashes" id="{did}">\n'
            f'{ind}    <Dash length="{f(float(on))}" name="On" id="{nid()}"/>\n'
            f'{ind}    <Dash length="{f(float(off))}" name="Off" id="{nid()}"/>\n'
            f'{ind}</DashPath>\n')

def stroke(th, color, ind, feather=None, fx=0, fy=0, dash=None, dash_id=None, name="Stroke"):
    s = f'{ind}<Stroke thickness="{f(float(th))}" cap="round" join="round" name="{name}" id="{nid()}">\n'
    s += solid(color, ind + "    ")
    if dash:
        s += dash_xml(dash[0], dash[1], ind + "    ", dash_id)
    if feather:
        off = (f' offsetX="{f(float(fx))}" offsetY="{f(float(fy))}"' if (fx or fy) else "")
        s += f'{ind}    <Feather strength="{f(float(feather))}"{off} name="Feather" id="{nid()}"/>\n'
    return s + f'{ind}</Stroke>\n'

def engraved(name, geom, th=1.8, ind="        ", x=0, y=0):
    """Dull carved line: soft light lip offset down-right under a dark groove."""
    pos = f' x="{f(float(x))}" y="{f(float(y))}"' if (x or y) else ""
    s = f'{ind}<Shape{pos} name="{name}" id="{nid()}">\n'
    s += geom_xml(geom, ind + "    ")
    s += stroke(th + 0.8, ENGRAVE_LIGHT, ind + "    ", feather=1.2, fx=1.1, fy=1.1, name="Lip")
    s += stroke(th, ENGRAVE_DARK, ind + "    ", name="Groove")
    return s + f'{ind}</Shape>\n'

def glowing(name, geom, th=1.8, ind="        ", x=0, y=0, sid=None, dash=None, dash_id=None,
            halo=7.0, opacity=None):
    pos = f' x="{f(float(x))}" y="{f(float(y))}"' if (x or y) else ""
    op = f' opacity="{f(float(opacity))}"' if opacity is not None else ""
    sid = sid or nid()
    s = f'{ind}<Shape{pos}{op} name="{name}" id="{sid}">\n'
    s += geom_xml(geom, ind + "    ")
    # first paint = bottom; last = top
    s += stroke(th * 2.6, GLOW_OUTER, ind + "    ", feather=halo, dash=dash, name="Halo")
    s += stroke(th * 1.5, GLOW_MID, ind + "    ", feather=2.0, dash=dash, name="Light")
    s += stroke(max(th * 0.7, 0.9), GLOW_CORE, ind + "    ", dash=dash, dash_id=dash_id, name="Core")
    return s + f'{ind}</Shape>\n'

def radial_shape(name, r, stops, ind, x=0, y=0, sid=None, geom=None):
    pos = f' x="{f(float(x))}" y="{f(float(y))}"' if (x or y) else ""
    s = f'{ind}<Shape{pos} name="{name}" id="{sid or nid()}">\n'
    s += geom_xml(geom or [("circle", r)], ind + "    ")
    s += f'{ind}    <Fill name="Fill" id="{nid()}">\n'
    s += f'{ind}        <RadialGradient startX="0" startY="0" endX="{f(float(r))}" endY="0" name="Gradient" id="{nid()}">\n'
    for c, p in stops:
        s += f'{ind}            <GradientStop colorValue="{c}" position="{f(float(p))}" id="{nid()}"/>\n'
    s += f'{ind}        </RadialGradient>\n{ind}    </Fill>\n{ind}</Shape>\n'
    return s

def node_open(name, ind, x=0, y=0, opacity=None, nid_=None):
    pos = f' x="{f(float(x))}" y="{f(float(y))}"' if (x or y) else ""
    op = f' opacity="{f(float(opacity))}"' if opacity is not None else ""
    return f'{ind}<Node{pos}{op} name="{name}" id="{nid_ or nid()}">\n'

# ---------------------------------------------------------------- the design
R_BAND_OUT, R_BAND_IN = 142, 118
R_BAND_MID = (R_BAND_OUT + R_BAND_IN) / 2
R_INCIRCLE = R_BAND_IN / 2           # incircle of the triangles
R_INNER_OUT, R_INNER_IN = 50, 39
R_CORE = 27
SITE_R_OUT, SITE_R_IN = 44, 33
deg = math.radians

def wrap(a):
    while a < -math.pi: a += 2 * math.pi
    while a > math.pi: a -= 2 * math.pi
    return a

# sector boundaries: midway between neighbouring site directions
order = sorted(range(3), key=lambda i: SITE_ANG[i])
bounds = {}
for k, i in enumerate(order):
    prev_i = order[(k - 1) % 3]; next_i = order[(k + 1) % 3]
    a0 = SITE_ANG[i] - wrap(SITE_ANG[i] - SITE_ANG[prev_i]) / 2
    a1 = SITE_ANG[i] + wrap(SITE_ANG[next_i] - SITE_ANG[i]) / 2
    bounds[i] = (a0, a1)

def sector_slots(i, n=13, gap=deg(6)):
    a0, a1 = bounds[i]
    a0 += gap; a1 -= gap
    return [a0 + (a1 - a0) * k / (n - 1) for k in range(n)]

sector_runes, sector_anchor = [], []
for i in range(3):
    slots = sector_slots(i)
    mid = len(slots) // 2
    runes_here = [a for k, a in enumerate(slots) if k != mid]
    sector_runes.append(ring_runes(R_BAND_MID, 14.0, runes_here))
    am = slots[mid]
    sector_anchor.append((R_BAND_MID * math.cos(am), R_BAND_MID * math.sin(am)))

separators = []
for i in range(3):
    a = bounds[i][1]
    cx_, cy_ = R_BAND_MID * math.cos(a), R_BAND_MID * math.sin(a)
    separators += rune_polys("ng", cx_, cy_, a, 12.0)

base = SITE_ANG[0]
tri_up = [(R_BAND_IN * math.cos(base + k * 2 * math.pi / 3), R_BAND_IN * math.sin(base + k * 2 * math.pi / 3)) for k in range(4)]
tri_dn = [(R_BAND_IN * math.cos(base + math.pi / 3 + k * 2 * math.pi / 3), R_BAND_IN * math.sin(base + math.pi / 3 + k * 2 * math.pi / 3)) for k in range(4)]

inner_runes = ring_runes((R_INNER_OUT + R_INNER_IN) / 2, 8.0,
                         [base + k * 2 * math.pi / 12 + math.pi / 12 for k in range(12)])
spokes = []
for k in range(6):
    a = base + k * math.pi / 3
    spokes.append([(R_INNER_OUT * math.cos(a), R_INNER_OUT * math.sin(a)),
                   (R_INCIRCLE * math.cos(a), R_INCIRCLE * math.sin(a))])
star = []
for k in range(7):
    a = base + k * 2 * math.pi / 6 * 1  # hexagonal star via two triangles
star_up = [(R_CORE * math.cos(base + k * 2 * math.pi / 3), R_CORE * math.sin(base + k * 2 * math.pi / 3)) for k in range(4)]
star_dn = [(R_CORE * math.cos(base + math.pi / 3 + k * 2 * math.pi / 3), R_CORE * math.sin(base + math.pi / 3 + k * 2 * math.pi / 3)) for k in range(4)]

G_BAND = [("circle", R_BAND_OUT), ("circle", R_BAND_IN)] + [("poly", p) for p in separators]
G_SIGIL = [("poly", tri_up), ("poly", tri_dn), ("circle", R_INCIRCLE)]
G_INNER = [("circle", R_INNER_OUT), ("circle", R_INNER_IN)] + [("poly", p) for p in inner_runes] + [("poly", p) for p in spokes]
G_CORE = [("poly", star_up), ("poly", star_dn), ("circle", 9)]

def G_SECTOR(i):
    ax, ay = sector_anchor[i]
    return [("poly", p) for p in sector_runes[i]] + [("circle", 5.5, ax, ay)]

def site_geom(i):
    _, _, _, sig = SITES[i]
    g = [("circle", SITE_R_OUT), ("circle", SITE_R_IN)]
    a_in = math.atan2(CY - SITE_POS[i][1], CX - SITE_POS[i][0])
    angs = [a_in + math.pi / 10 + k * 2 * math.pi / 10 for k in range(10)]
    g += [("poly", p) for p in ring_runes((SITE_R_OUT + SITE_R_IN) / 2, 7.0, angs)]
    # sigil points toward the centre so a caster "faces" the circle
    g += [("poly", p) for p in rune_polys(sig, 0, 0, a_in + math.pi, 30.0)]
    return g

def conduit_pts(i):
    sx, sy = SITE_POS[i]
    a = math.atan2(CY - sy, CX - sx)
    p0 = (sx + (SITE_R_OUT + 2) * math.cos(a), sy + (SITE_R_OUT + 2) * math.sin(a))
    d = math.hypot(CX - sx, CY - sy)
    p1 = (sx + (d - R_BAND_OUT - 2) * math.cos(a), sy + (d - R_BAND_OUT - 2) * math.sin(a))
    return p0, p1, a

# --------------------------------------------------------------- ids used by animations
ID = {k: nid() for k in [
    "artboard", "style", "sm", "vm", "vmi",
    "p1", "p2", "p3",
    "bandGlow", "sigilGlow", "innerGlow", "coreGlow", "bloom", "rays", "sparks",
    "sparksSpin", "floatRing", "floatSpin", "innerFloat", "innerFloatSpin", "shock", "raysSpin",
    "ember",
]}
for i in range(3):
    for k in ["siteGlow", "siteRing", "siteRingSpin", "sectorGlow", "conduitGlow", "flowDash"]:
        ID[f"{k}{i}"] = nid()
PROP = [ID["p1"], ID["p2"], ID["p3"]]

# --------------------------------------------------------------- scene
I1, I2, I3 = "        ", "            ", "                "
scene = ""

# ===== Center (drawn above the conduits and sites) =====
scene += node_open("Ritual Center", "    ", CX, CY)
# -- light effects, top-most
scene += radial_shape("Ember", 34, [("993FD8FF", 0), ("005B3CFF", 1)], I1, sid=ID["ember"])
shock = glowing("Shockwave", [("circle", R_BAND_OUT)], th=2.4, ind=I2, halo=14)
scene += node_open("Shockwave", I1, opacity=0, nid_=ID["shock"]) + shock + f"{I1}</Node>\n"
# orbiting sparks
scene += node_open("Sparks", I1, opacity=0, nid_=ID["sparks"])
scene += node_open("Sparks Spin", I2, nid_=ID["sparksSpin"])
for k in range(6):
    a = base + k * math.pi / 3 + math.pi / 6
    rr = 84 if k % 2 == 0 else 100
    scene += radial_shape(f"Spark {k+1}", 9, [("FFFFFFFF", 0), ("CC3FD8FF", 0.35), ("005B3CFF", 1)],
                          I3, x=rr * math.cos(a), y=rr * math.sin(a))
scene += f"{I2}</Node>\n{I1}</Node>\n"
# rays
ray_geom = []
for k in range(12):
    a = base + k * math.pi / 6 + math.pi / 12
    L = 190 if k % 2 == 0 else 128
    w = deg(2.2)
    ray_geom.append(("closed", [(22 * math.cos(a - w * 3), 22 * math.sin(a - w * 3)),
                                (L * math.cos(a), L * math.sin(a)),
                                (22 * math.cos(a + w * 3), 22 * math.sin(a + w * 3))]))
scene += node_open("Rays", I1, opacity=0, nid_=ID["rays"])
scene += node_open("Rays Spin", I2, nid_=ID["raysSpin"])
scene += radial_shape("Ray Fan", 190, [("D9FFFFFF", 0), ("803FD8FF", 0.35), ("405B3CFF", 0.7), ("005B3CFF", 1)],
                      I3, geom=ray_geom)
scene += f"{I2}</Node>\n{I1}</Node>\n"
# bloom
scene += node_open("Bloom", I1, opacity=0, nid_=ID["bloom"])
scene += radial_shape("Bloom Light", 110, [("F2FFFFFF", 0), ("B33FD8FF", 0.18), ("555B3CFF", 0.5), ("005B3CFF", 1)], I2)
scene += f"{I1}</Node>\n"
# floating (projected) light rings - no engraving under them
scene += node_open("Float Ring", I1, opacity=0, nid_=ID["floatRing"])
scene += node_open("Float Ring Spin", I2, nid_=ID["floatSpin"])
fr_ticks = []
for k in range(24):
    a = k * 2 * math.pi / 24
    fr_ticks.append(("poly", [(156 * math.cos(a), 156 * math.sin(a)), (166 * math.cos(a), 166 * math.sin(a))]))
scene += glowing("Float Ring Light", [("circle", 161)], th=0.8, ind=I3, dash=(2, 7), halo=4)
scene += glowing("Float Ring Ticks", fr_ticks, th=1.0, ind=I3, halo=5)
scene += f"{I2}</Node>\n{I1}</Node>\n"
scene += node_open("Inner Float Ring", I1, opacity=0, nid_=ID["innerFloat"])
scene += node_open("Inner Float Spin", I2, nid_=ID["innerFloatSpin"])
scene += glowing("Inner Float Light", [("circle", 92)], th=1.2, ind=I3, dash=(0.5, 11), halo=4)
scene += f"{I2}</Node>\n{I1}</Node>\n"
# -- glowing carved tiers
scene += glowing("Core Glow", G_CORE, th=1.8, ind=I1, sid=ID["coreGlow"], opacity=0)
scene += glowing("Inner Ring Glow", G_INNER, th=1.3, ind=I1, sid=ID["innerGlow"], opacity=0)
scene += glowing("Sigil Glow", G_SIGIL, th=2.0, ind=I1, sid=ID["sigilGlow"], opacity=0)
for i in range(3):
    scene += glowing(f"Sector {i+1} Runes Glow", G_SECTOR(i), th=1.5, ind=I1, sid=ID[f"sectorGlow{i}"], opacity=0)
scene += glowing("Band Glow", G_BAND, th=2.2, ind=I1, sid=ID["bandGlow"], opacity=0)
# -- engravings (bottom)
scene += engraved("Core Carving", G_CORE, th=1.8, ind=I1)
scene += engraved("Inner Ring Carving", G_INNER, th=1.3, ind=I1)
scene += engraved("Sigil Carving", G_SIGIL, th=2.0, ind=I1)
for i in range(3):
    scene += engraved(f"Sector {i+1} Runes Carving", G_SECTOR(i), th=1.5, ind=I1)
scene += engraved("Band Carving", G_BAND, th=2.2, ind=I1)
scene += "    </Node>\n"

# ===== Ritual sites =====
for i, (nm, c, r, _) in enumerate(SITES):
    sx, sy = SITE_POS[i]
    g = site_geom(i)
    scene += node_open(f"{nm} (cell {c},{r})", "    ", sx, sy)
    scene += node_open("Site Light Ring", I1, opacity=0, nid_=ID[f"siteRing{i}"])
    scene += node_open("Site Ring Spin", I2, nid_=ID[f"siteRingSpin{i}"])
    scene += glowing("Ring Light", [("circle", 48)], th=0.9, ind=I3, dash=(5, 7), halo=4)
    scene += f"{I2}</Node>\n{I1}</Node>\n"
    scene += glowing("Site Glow", g, th=1.5, ind=I1, sid=ID[f"siteGlow{i}"], opacity=0)
    scene += engraved("Site Carving", g, th=1.5, ind=I1)
    scene += "    </Node>\n"

# ===== Conduits (bottom-most) =====
for i in range(3):
    p0, p1, a = conduit_pts(i)
    mx, my = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2
    geom = [("poly", [p0, p1])] + [("poly", p) for p in rune_polys("ng", mx, my, a, 10.0)]
    scene += node_open(f"Conduit {i+1}", "    ")
    scene += node_open("Conduit Light", I1, opacity=0, nid_=ID[f"conduitGlow{i}"])
    scene += glowing("Energy Flow", [("poly", [p0, p1])], th=1.6, ind=I2, dash=(10, 20),
                     dash_id=ID[f"flowDash{i}"], halo=6)
    scene += glowing("Channel Glow", geom, th=1.2, ind=I2, halo=5, opacity=0.55)
    scene += f"{I1}</Node>\n"
    scene += engraved("Channel Carving", geom, th=1.4, ind=I1)
    scene += "    </Node>\n"

# --------------------------------------------------------------- animations
def kf(frames, ease="cubic", ind="                "):
    s = ""
    for fr, v in frames:
        if ease == "cubic":
            s += (f'{ind}<KeyFrameDouble value="{f(float(v))}" frame="{fr}" interpolationType="cubic" id="{nid()}">\n'
                  f'{ind}    <CubicEaseInterpolator x1="0.42" y1="0" x2="0.58" y2="1" id="{nid()}"/>\n'
                  f'{ind}</KeyFrameDouble>\n')
        else:
            s += f'{ind}<KeyFrameDouble value="{f(float(v))}" frame="{fr}" interpolationType="{ease}" id="{nid()}"/>\n'
    return s

def anim(name, duration, tracks, loop="loop", aid=None):
    """tracks: list of (objectId, property, frames, ease)"""
    aid = aid or nid()
    s = f'        <LinearAnimation loopValue="{loop}" duration="{duration}" name="{name}" id="{aid}">\n'
    byobj = {}
    for oid, prop, frames, ease in tracks:
        byobj.setdefault(oid, []).append((prop, frames, ease))
    for oid, props in byobj.items():
        s += f'            <KeyedObject objectId="{oid}" id="{nid()}">\n'
        for prop, frames, ease in props:
            s += f'                <KeyedProperty property="{prop}" id="{nid()}">\n'
            s += kf(frames, ease, "                    ")
            s += '                </KeyedProperty>\n'
        s += '            </KeyedObject>\n'
    s += '        </LinearAnimation>\n'
    return aid, s

def const(v, d):
    return [(0, v), (d, v)]

def pulse(lo, hi, d, n=1, phase=0.0):
    """n full lo->hi->lo cycles across d frames; phase shifts start toward hi."""
    pts = []
    steps = n * 2
    for k in range(steps + 1):
        fr = round(d * k / steps)
        v = lo if k % 2 == 0 else hi
        pts.append((fr, v))
    if phase:
        # swap so the track starts high
        pts = [(fr, hi if v == lo else lo) for fr, v in pts]
    return pts

CENTER_OBJS = ["ember", "bandGlow", "sigilGlow", "innerGlow", "coreGlow", "bloom", "rays",
               "sparks", "floatRing", "innerFloat", "shock"]

def center_anim(name, d, spec):
    """spec: obj -> frames (opacity) ; plus optional scale entries 'bloom.scale','rays.scale','shock.scale'"""
    tracks = []
    for o in CENTER_OBJS:
        tracks.append((ID[o], "opacity", spec.get(o, const(0, d)), "cubic"))
    for o in ["bloom", "rays", "shock"]:
        sc = spec.get(o + ".scale", const(1, d))
        tracks.append((ID[o], "scaleX", sc, "cubic"))
        tracks.append((ID[o], "scaleY", sc, "cubic"))
    return anim(name, d, tracks)

anims = ""
A = {}
A["s0"], s = center_anim("Center 0 - Dormant", 300, {
    "ember": pulse(0.0, 0.12, 300),
})
anims += s
A["s1"], s = center_anim("Center 1 - Stirring", 240, {
    "ember": pulse(0.15, 0.3, 240),
    "bandGlow": pulse(0.22, 0.5, 240),
    "coreGlow": pulse(0.08, 0.2, 240),
})
anims += s
A["s2"], s = center_anim("Center 2 - Awakened", 150, {
    "ember": pulse(0.3, 0.55, 150),
    "bandGlow": pulse(0.65, 0.95, 150),
    "sigilGlow": pulse(0.85, 0.4, 150),
    "coreGlow": pulse(0.35, 0.6, 150),
    "bloom": pulse(0.12, 0.28, 150),
    "bloom.scale": pulse(0.65, 0.75, 150),
    "floatRing": pulse(0.2, 0.4, 150),
})
anims += s
d3 = 120
A["s3"], s = center_anim("Center 3 - Full Ritual", d3, {
    "ember": const(0.8, d3),
    "bandGlow": pulse(0.85, 1.0, d3, 2),
    "sigilGlow": pulse(1.0, 0.75, d3, 2),
    "innerGlow": pulse(0.75, 1.0, d3, 2),
    "coreGlow": const(1.0, d3),
    "bloom": [(0, 0.95), (10, 0.6), (60, 0.85), (70, 0.6), (120, 0.95)],
    "bloom.scale": [(0, 1.18), (14, 0.9), (60, 1.05), (74, 0.9), (120, 1.18)],
    "rays": [(0, 0.85), (15, 0.25), (35, 0.6), (60, 0.2), (80, 0.75), (100, 0.3), (120, 0.85)],
    "rays.scale": [(0, 1.08), (60, 0.92), (120, 1.08)],
    "sparks": pulse(0.75, 1.0, d3, 4),
    "floatRing": pulse(0.75, 1.0, d3, 1),
    "innerFloat": pulse(0.9, 0.55, d3, 2),
    "shock": [(0, 0.9), (55, 0.0), (120, 0.0)],
    "shock.scale": [(0, 0.35), (55, 1.32), (119, 1.32), (120, 0.35)],
})
anims += s

SITE_OBJS = ["siteGlow", "siteRing", "sectorGlow", "conduitGlow"]
for i in range(3):
    A[f"on{i}"], s = anim(f"Site {i+1} On", 120, [
        (ID[f"siteGlow{i}"], "opacity", pulse(0.7, 1.0, 120), "cubic"),
        (ID[f"siteRing{i}"], "opacity", pulse(0.9, 0.55, 120), "cubic"),
        (ID[f"sectorGlow{i}"], "opacity", pulse(0.65, 1.0, 120), "cubic"),
        (ID[f"conduitGlow{i}"], "opacity", pulse(0.8, 1.0, 120), "cubic"),
    ])
    anims += s
    A[f"off{i}"], s = anim(f"Site {i+1} Off", 60, [
        (ID[f"{o}{i}"], "opacity", const(0, 60), "linear") for o in SITE_OBJS
    ], loop="oneShot")
    anims += s

# always-on motion: spins and energy flow
SPIN_D = 1440
TAU = 2 * math.pi
spin_tracks = [
    (ID["floatSpin"], "rotation", [(0, 0), (SPIN_D, TAU)], "linear"),
    (ID["innerFloatSpin"], "rotation", [(0, 0), (SPIN_D, -2 * TAU)], "linear"),
    (ID["sparksSpin"], "rotation", [(0, 0), (SPIN_D, 3 * TAU)], "linear"),
    (ID["raysSpin"], "rotation", [(0, 0), (SPIN_D, -TAU / 2)], "linear"),
]
for i in range(3):
    spin_tracks.append((ID[f"siteRingSpin{i}"], "rotation", [(0, 0), (SPIN_D, (2 if i % 2 == 0 else -2) * TAU)], "linear"))
    # dash period 30px; 32 periods over 24s => 40px/s toward the centre
    spin_tracks.append((ID[f"flowDash{i}"], "offset", [(0, 0), (SPIN_D, -30 * 32)], "linear"))
A["spin"], s = anim("Ambient Motion", SPIN_D, spin_tracks)
anims += s

# --------------------------------------------------------------- state machine
def cond(prop_id, val, ind):
    return (f'{ind}<TransitionViewModelCondition opValue="equal" id="{nid()}">\n'
            f'{ind}    <TransitionPropertyViewModelComparator id="{nid()}">\n'
            f'{ind}        <BindablePropertyBoolean>\n'
            f'{ind}            <DataBindContext sourcePathIds="{ID["vm"]}-{prop_id}" propertyKey="634" id="{nid()}"/>\n'
            f'{ind}        </BindablePropertyBoolean>\n'
            f'{ind}    </TransitionPropertyViewModelComparator>\n'
            f'{ind}    <TransitionValueBooleanComparator value="{"true" if val else "false"}" id="{nid()}"/>\n'
            f'{ind}</TransitionViewModelCondition>\n')

combos = [(a, b, c) for a in (0, 1) for b in (0, 1) for c in (0, 1)]
st = {k: nid() for k in ["s0", "s1", "s2", "s3"]}
sm = f'        <StateMachine name="Ritual" id="{ID["sm"]}">\n'
# center layer
sm += f'            <StateMachineLayer name="Center Power" id="{nid()}">\n'
sm += f'                <AnyState x="0" y="-150" id="{nid()}"/>\n'
sm += f'                <ExitState x="900" y="-150" id="{nid()}"/>\n'
sm += f'                <EntryState x="0" y="0" id="{nid()}">\n                    <StateTransition stateToId="{st["s0"]}" id="{nid()}"/>\n                </EntryState>\n'
for lvl in range(4):
    sm += f'                <AnimationState x="{200 + lvl * 220}" y="{0 if lvl % 2 == 0 else 160}" animationId="{A[f"s{lvl}"]}" id="{st[f"s{lvl}"]}">\n'
    for cb in combos:
        tgt = sum(cb)
        if tgt == lvl:
            continue
        sm += f'                    <StateTransition stateToId="{st[f"s{tgt}"]}" duration="{700 if tgt > lvl else 1100}" id="{nid()}">\n'
        for k in range(3):
            sm += cond(PROP[k], cb[k], "                        ")
        sm += '                    </StateTransition>\n'
    sm += '                </AnimationState>\n'
sm += '            </StateMachineLayer>\n'
# site layers
for i in range(3):
    on_id, off_id = nid(), nid()
    sm += f'            <StateMachineLayer name="Site {i+1}" id="{nid()}">\n'
    sm += f'                <AnyState x="0" y="-150" id="{nid()}"/>\n'
    sm += f'                <ExitState x="600" y="-150" id="{nid()}"/>\n'
    sm += f'                <EntryState x="0" y="0" id="{nid()}">\n                    <StateTransition stateToId="{off_id}" id="{nid()}"/>\n                </EntryState>\n'
    sm += f'                <AnimationState x="200" y="0" animationId="{A[f"off{i}"]}" id="{off_id}">\n'
    sm += f'                    <StateTransition stateToId="{on_id}" duration="450" id="{nid()}">\n'
    sm += cond(PROP[i], 1, "                        ")
    sm += '                    </StateTransition>\n                </AnimationState>\n'
    sm += f'                <AnimationState x="420" y="0" animationId="{A[f"on{i}"]}" id="{on_id}">\n'
    sm += f'                    <StateTransition stateToId="{off_id}" duration="1000" id="{nid()}">\n'
    sm += cond(PROP[i], 0, "                        ")
    sm += '                    </StateTransition>\n                </AnimationState>\n'
    sm += '            </StateMachineLayer>\n'
# ambient layer
amb = nid()
sm += f'            <StateMachineLayer name="Ambient" id="{nid()}">\n'
sm += f'                <AnyState x="0" y="-150" id="{nid()}"/>\n'
sm += f'                <ExitState x="400" y="-150" id="{nid()}"/>\n'
sm += f'                <EntryState x="0" y="0" id="{nid()}">\n                    <StateTransition stateToId="{amb}" id="{nid()}"/>\n                </EntryState>\n'
sm += f'                <AnimationState x="200" y="0" animationId="{A["spin"]}" id="{amb}"/>\n'
sm += '            </StateMachineLayer>\n'
sm += '        </StateMachine>\n'

# --------------------------------------------------------------- document
vm = f'''    <ViewModel defaultInstanceId="{ID["vmi"]}" name="RitualCircle" id="{ID["vm"]}">
        <ViewModelPropertyBoolean name="site1Active" id="{ID["p1"]}"/>
        <ViewModelPropertyBoolean name="site2Active" id="{ID["p2"]}"/>
        <ViewModelPropertyBoolean name="site3Active" id="{ID["p3"]}"/>
        <ViewModelInstance exports="true" name="Default" id="{ID["vmi"]}">
            <ViewModelInstanceBoolean propertyValue="true" viewModelPropertyId="{ID["p1"]}" id="{nid()}"/>
            <ViewModelInstanceBoolean propertyValue="true" viewModelPropertyId="{ID["p2"]}" id="{nid()}"/>
            <ViewModelInstanceBoolean propertyValue="true" viewModelPropertyId="{ID["p3"]}" id="{nid()}"/>
        </ViewModelInstance>
    </ViewModel>
'''

backdrop = ""
if os.environ.get("PREVIEW_BG"):  # preview-only solid backdrop, never in the shipped file
    backdrop = f'        <Fill name="Preview Backdrop" id="{nid()}">\n' + solid(os.environ["PREVIEW_BG"], "            ") + "        </Fill>\n"
OUT = os.environ.get("OUT_RML")

doc = f'''<Rive version="1" kind="fragment">
    <!-- GENERATED by tools/gen_scene.py - edit the generator, not this file. -->
    <!-- 600x600 = 6x6 grid squares of 100px. Sites: cells (4,4), (0,3), (3,0). -->
    <Artboard defaultStateMachineId="{ID["sm"]}" viewModelId="{ID["vm"]}" viewModelInstanceId="{ID["vmi"]}" styleId="{ID["style"]}" width="{W}" height="{H}" name="Ritual Circle" id="{ID["artboard"]}">
        <LayoutComponentStyle name="Artboard Style" id="{ID["style"]}"/>
{backdrop}{sm}
{scene}
{anims}    </Artboard>

{vm}</Rive>
'''

out = OUT or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scene.rml")
with open(out, "w") as fh:
    fh.write(doc)
print("wrote", os.path.normpath(out), "center", (round(CX, 2), round(CY, 2)),
      "conduit lengths", [round(math.hypot(CX - x, CY - y) - R_BAND_OUT - SITE_R_OUT, 1) for x, y in SITE_POS])
