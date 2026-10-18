#!/usr/bin/env python3
"""Generates scene.rml for the AnimatedScroll Rive project.

Everything procedural lives here: torn paper outlines, rune glyphs, the arcane
diagram, and the baked unroll / roll-up physics (spring-driven roll travel,
roll radius shrinking as paper pays out, roll surface rotation).
"""
import math, random, sys

random.seed(7)

# ----------------------------------------------------------------------------
# ids / xml helpers
# ----------------------------------------------------------------------------
_next = [100]
def nid():
    _next[0] += 1
    return f"0:{_next[0]}"

def f(v):
    s = f"{v:.3f}".rstrip('0').rstrip('.')
    return "0" if s in ("-0", "") else s

def attrs(d):
    return " ".join(f'{k}="{v}"' for k, v in d.items() if v is not None)

def argb(hexrgb, a=1.0):
    return f"{int(round(max(0, min(1, a)) * 255)):02X}{hexrgb}"

# ----------------------------------------------------------------------------
# scene constants
# ----------------------------------------------------------------------------
W, H = 600, 800
CX, CY = 300, 400
PAGE_HW = 190          # half width of the paper
PAGE_HH = 336          # half height of paper (runs under the rolls when open)
R0, R1 = 34.0, 20.0    # roll radius rolled up / fully open
RU = 20.0              # unit radius roll bodies are authored at (scaled in Y)
D = 300.0              # travel of each roll centre from closed to open
# closed: roll centres at CY -/+ R0 ; open: CY -/+ (R0 + D)
OPEN_HALF = R0 + D     # 334 -> rolls at y=66 and 734

def radius_at(s):
    s = max(0.0, min(D, s))
    return math.sqrt(R0 * R0 - (R0 * R0 - R1 * R1) * s / D)

def phi_at(s):
    # surface rotation angle = integral ds / R(s) (closed form)
    # R^2 = R0^2 - k s, k=(R0^2-R1^2)/D  ->  int ds/R = (2/k)(R0 - R(s))
    k = (R0 * R0 - R1 * R1) / D
    return (2.0 / k) * (R0 - radius_at(s))

# ----------------------------------------------------------------------------
# geometry helpers -> xml
# ----------------------------------------------------------------------------
def poly_xml(pts, closed=False, cw=True, name="Path"):
    vs = "".join(f'<StraightVertex x="{f(x)}" y="{f(y)}"/>' for x, y in pts)
    return (f'<PointsPath isClosed="{str(closed).lower()}" isClockwise="{str(cw).lower()}" '
            f'name="{name}">{vs}</PointsPath>')

def smooth_poly_xml(pts, closed=True, name="Path"):
    """closed curvy path through pts using mirrored cubic vertices."""
    n = len(pts)
    out = []
    for i, (x, y) in enumerate(pts):
        px, py = pts[(i - 1) % n]
        nx, ny = pts[(i + 1) % n]
        ang = math.atan2(ny - py, nx - px)
        dist = math.hypot(nx - px, ny - py) / 6.0
        out.append(f'<CubicMirroredVertex x="{f(x)}" y="{f(y)}" rotation="{f(ang)}" distance="{f(dist)}"/>')
    return f'<PointsPath isClosed="{str(closed).lower()}" name="{name}">{"".join(out)}</PointsPath>'

def ellipse_xml(w, h, x=0, y=0, name="Ring"):
    return f'<Ellipse x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" name="{name}"/>'

def geom_xml(items):
    out = []
    for it in items:
        if it[0] == 'poly':
            out.append(poly_xml(it[1], it[2]))
        elif it[0] == 'ellipse':
            out.append(ellipse_xml(it[3], it[4], it[1], it[2]))
    return "".join(out)


def blob_shape(name, sid, x, y, w, h, color, extra="", hard=0.25):
    """soft-edged elliptical blob: a circle with a radial gradient fading to
    transparent, stretched by the shape's scaleX. Renders identically on every
    backend (unlike feathered fills)."""
    a = color[:2]; rgb = color[2:]
    mid = f"{int(int(a, 16) * 0.55):02X}{rgb}"
    st = [(0, color), (hard, color), (0.62, mid), (1, "00" + rgb)]
    return (f'<Shape x="{f(x)}" y="{f(y)}" scaleX="{f(w / h)}" {extra} name="{name}" id="{sid}">'
            f'<Ellipse width="{f(h)}" height="{f(h)}" name="Path"/>'
            f'<Fill name="Fill">{rad_grad(0, 0, h / 2, st)}</Fill></Shape>')

def solid(c, cid=None, name="Color"):
    return f'<SolidColor {attrs({"colorValue": c, "name": name, "id": cid})}/>'

def lin_grad(x0, y0, x1, y1, stops, name="Gradient"):
    st = "".join(f'<GradientStop colorValue="{c}" position="{f(p)}"/>' for p, c in stops)
    return f'<LinearGradient startX="{f(x0)}" startY="{f(y0)}" endX="{f(x1)}" endY="{f(y1)}" name="{name}">{st}</LinearGradient>'

def rad_grad(x0, y0, r, stops, name="Gradient"):
    st = "".join(f'<GradientStop colorValue="{c}" position="{f(p)}"/>' for p, c in stops)
    return f'<RadialGradient startX="{f(x0)}" startY="{f(y0)}" endX="{f(x0 + r)}" endY="{f(y0)}" name="{name}">{st}</RadialGradient>'

def noise1d(seed, octaves=((0.05, 1.0), (0.13, 0.5), (0.37, 0.25))):
    rnd = random.Random(seed)
    ph = [(fr, amp, rnd.uniform(0, 6.283)) for fr, amp in octaves]
    def n(t):
        return sum(a * math.sin(t * fr + p) for fr, a, p in ph)
    return n

# ----------------------------------------------------------------------------
# rune glyphs (Elder Futhark style + a few arcane marks), unit box 0.6 x 1
# ----------------------------------------------------------------------------
S = [(0, 0), (0, 1)]
GLYPHS = [
    [S, [(0, .35), (.5, .05)], [(0, .62), (.5, .32)]],                    # fehu
    [[(0, 1), (0, 0), (.5, .3), (.5, 1)]],                                 # uruz
    [S, [(0, .22), (.45, .5), (0, .78)]],                                  # thurisaz
    [S, [(0, 0), (.5, .25)], [(0, .3), (.5, .55)]],                        # ansuz
    [S, [(0, 0), (.45, .22), (0, .45), (.5, 1)]],                          # raido
    [[(.5, .2), (.05, .45), (.5, .7)]],                                    # kaunan
    [[(0, 0), (.6, 1)], [(.6, 0), (0, 1)]],                                # gebo
    [S, [(0, 0), (.42, .2), (0, .4)]],                                     # wunjo
    [S, [(.5, 0), (.5, 1)], [(0, .35), (.5, .62)]],                        # hagalaz
    [[(.3, 0), (.3, 1)], [(.05, .32), (.55, .62)]],                        # naudiz
    [[(.25, .1), (0, .35), (.25, .6)], [(.35, .4), (.6, .65), (.35, .9)]], # jera
    [[(.3, 0), (.3, 1)], [(.3, 0), (.55, .18)], [(.3, 1), (.05, .82)]],    # eihwaz
    [S, [(0, 0), (.45, .25), (.45, .02)], [(0, 1), (.45, .75), (.45, .98)]],  # perthro
    [[(.3, 0), (.3, 1)], [(.3, .45), (0, 0)], [(.3, .45), (.6, 0)]],       # algiz
    [[(.5, 0), (.05, .38), (.5, .62), (.05, 1)]],                          # sowilo
    [[(.3, 0), (.3, 1)], [(0, .3), (.3, 0), (.6, .3)]],                    # tiwaz
    [S, [(0, 0), (.45, .25), (0, .5), (.45, .75), (0, 1)]],                # berkanan
    [[(0, 1), (0, 0), (.3, .3), (.6, 0), (.6, 1)]],                        # ehwaz
    [S, [(.6, 0), (.6, 1)], [(0, 0), (.6, .42)], [(.6, 0), (0, .42)]],     # mannaz
    [S, [(0, 0), (.45, .3)]],                                              # laguz
    [[(.3, .15), (.6, .5), (.3, .85), (0, .5), (.3, .15)]],                # ingwaz
    [S, [(.6, 0), (.6, 1)], [(0, 0), (.6, 1)], [(.6, 0), (0, 1)]],         # dagaz
    [[(0, 1), (.55, .42), (.3, .08), (.05, .42), (.6, 1)]],                # othala
    [[(.3, 0), (.3, 1)], [(.05, .25), (.55, .25)], [(.05, .75), (.55, .75)]],  # arcane cross
    [[(0, .2), (.3, 0), (.6, .2)], [(.3, 0), (.3, 1)], [(0, .8), (.3, 1), (.6, .8)]],  # arcane
]

def glyph_polys(gi, x, y, h, rot=0.0, slant=0.0):
    """glyph gi with its top-left at x,y (before rotation about glyph centre)."""
    g = GLYPHS[gi % len(GLYPHS)]
    w = 0.6 * h
    cx, cy = x + w / 2, y + h / 2
    c, s_ = math.cos(rot), math.sin(rot)
    out = []
    for stroke in g:
        pts = []
        for u, v in stroke:
            px = x + u * h + (0.5 - v) * slant * h
            py = y + v * h
            dx, dy = px - cx, py - cy
            pts.append((cx + dx * c - dy * s_, cy + dx * s_ + dy * c))
        out.append(('poly', pts, False))
    return out

def rune_line(y, half_width, h, rnd, words=None):
    """a centred line of rune 'words'. returns geometry items."""
    gw = 0.6 * h
    adv = gw + h * 0.32
    space = h * 0.75
    seq = []
    total = 0
    while True:
        n = rnd.randint(2, 5)
        wlen = n * adv - h * 0.32
        if total + wlen > 2 * half_width:
            break
        seq.append(n)
        total += wlen + space
    total -= space
    x = -total / 2
    items = []
    for n in seq:
        for _ in range(n):
            gi = rnd.randrange(len(GLYPHS))
            hh = h * rnd.uniform(0.92, 1.06)
            items += glyph_polys(gi, x, y - hh / 2 + rnd.uniform(-0.6, 0.6), hh,
                                 rot=rnd.uniform(-0.05, 0.05), slant=rnd.uniform(-0.04, 0.08))
            x += adv
        x += space - h * 0.32
    return items

# ----------------------------------------------------------------------------
# glowing element: Node(Core, Halo, Ink) sharing geometry
# ----------------------------------------------------------------------------
GLOW_CORE = "E6FCFF"
GLOW_HALO = "12A8E6"
INK = "3A2412"

class Glow:
    all = []
    def __init__(self, name, items, x=0, y=0, w=1.0, ey=None, halo=None, group='rune'):
        self.name, self.items, self.x, self.y, self.w = name, items, x, y, w
        self.group = group
        self.node = nid(); self.core = nid(); self.halo = nid(); self.halo_col = nid()
        self.ey = ey if ey is not None else y     # vertical position for reveal timing
        self.halo_w = halo if halo is not None else 4.5 * w
        Glow.all.append(self)
    def xml(self):
        g = geom_xml(self.items)
        w = self.w
        return (
            f'<Node x="{f(self.x)}" y="{f(self.y)}" name="{self.name}" id="{self.node}">'
            f'<Shape opacity="0" name="Core" id="{self.core}">{g}'
            f'<Stroke thickness="{f(1.5 * w)}" cap="round" join="round" name="Core Stroke">{solid(argb(GLOW_CORE))}</Stroke></Shape>'
            f'<Shape opacity="0" name="Halo" id="{self.halo}">{g}'
            f'<Stroke thickness="{f(self.halo_w)}" cap="round" join="round" name="Halo Stroke">'
            f'{solid(argb(GLOW_HALO), self.halo_col)}<Feather strength="{f(5 * w)}" name="Bloom"/></Stroke>'
            f'<Stroke thickness="{f(2.8 * w)}" cap="round" join="round" name="Inner Glow">'
            f'{solid(argb("3FD2FF", 0.85))}<Feather strength="{f(1.6 * w)}" name="Bloom"/></Stroke></Shape>'
            f'<Shape name="Ink" id="{nid()}">{g}'
            f'<Stroke thickness="{f(1.9 * w)}" cap="round" join="round" name="Ink Stroke">{solid(argb(INK, 0.82))}</Stroke></Shape>'
            f'</Node>')

# ----------------------------------------------------------------------------
# page content
# ----------------------------------------------------------------------------
rnd = random.Random(11)

def build_glyph_content():
    Glow.all.clear()
    # title
    t_items = []
    x = -(7 * 0.6 * 26 + 6 * 9) / 2
    for gi in [17, 3, 20, 13, 6, 15, 22]:
        t_items += glyph_polys(gi, x, -268, 26, rot=rnd.uniform(-.03, .03))
        x += 0.6 * 26 + 9
    Glow("Title", t_items, w=1.35, ey=-255)

    for i, y in enumerate([-206, -182]):
        Glow(f"Verse {i + 1}", rune_line(y, 150, 13, rnd), ey=y)

    # diagram ----------------------------------------------------------
    DY = 2
    # outer ring with runic band (rotates)
    ring = [('ellipse', 0, 0, 236, 236), ('ellipse', 0, 0, 206, 206)]
    n = 22
    for k in range(n):
        a = 2 * math.pi * k / n
        gi = rnd.randrange(len(GLYPHS))
        h = 10
        # place glyph centred at radius 110.5, upright along the radius
        cx, cy = 110.5 * math.cos(a), 110.5 * math.sin(a)
        rot = a + math.pi / 2
        ring += glyph_polys(gi, cx - 0.3 * h, cy - h / 2, h, rot=rot)
    for k in range(44):  # tick marks on outer edge
        a = 2 * math.pi * (k + .5) / 44
        r0, r1 = 118, 123 if k % 2 == 0 else 120.5
        ring.append(('poly', [(r0 * math.cos(a), r0 * math.sin(a)), (r1 * math.cos(a), r1 * math.sin(a))], False))
    Glow("Outer Ring", ring, y=0, group="diagram", ey=DY, w=1.0)

    # heptagram {7/3} + node circles (counter-rotates)
    star = []
    pts = [(92 * math.cos(-math.pi / 2 + 2 * math.pi * k / 7), 92 * math.sin(-math.pi / 2 + 2 * math.pi * k / 7)) for k in range(7)]
    order = [(3 * k) % 7 for k in range(8)]
    star.append(('poly', [pts[i] for i in order], True))
    for (px, py) in pts:
        star.append(('ellipse', px, py, 11, 11))
    star.append(('ellipse', 0, 0, 132, 132))
    Glow("Heptagram", star, y=0, group="diagram", ey=DY, w=1.05)

    # inner seal: triangles, circle, eye (slow spin)
    inner = [('ellipse', 0, 0, 72, 72)]
    tri = [(34 * math.cos(-math.pi / 2 + 2 * math.pi * k / 3), 34 * math.sin(-math.pi / 2 + 2 * math.pi * k / 3)) for k in range(3)]
    inner.append(('poly', tri, True))
    tri2 = [(-x, -y) for x, y in tri]
    inner.append(('poly', tri2, True))
    for k in range(12):
        a = 2 * math.pi * k / 12
        inner.append(('poly', [(40 * math.cos(a), 40 * math.sin(a)), (47 * math.cos(a), 47 * math.sin(a))], False))
    Glow("Inner Seal", inner, y=0, group="diagram", ey=DY, w=1.0)

    eye = [('poly', [(-14, 0), (-7, -5.5), (0, -7), (7, -5.5), (14, 0), (7, 5.5), (0, 7), (-7, 5.5)], True),
           ('ellipse', 0, 0, 6.5, 6.5)]
    Glow("Eye", eye, y=0, group="diagram", ey=DY, w=1.1)

    # cardinal marks around the diagram (static)
    marks = []
    for k in range(4):
        a = math.pi / 2 * k
        r = 133
        cx, cy = r * math.cos(a), r * math.sin(a)
        c, s_ = math.cos(a), math.sin(a)
        dia = [(cx + 7 * c, cy + 7 * s_), (cx - 4 * s_, cy + 4 * c), (cx - 7 * c, cy - 7 * s_), (cx + 4 * s_, cy - 4 * c)]
        marks.append(('poly', dia, True))
    for k in range(4):
        a = math.pi / 4 + math.pi / 2 * k
        marks.append(('ellipse', 131 * math.cos(a), 131 * math.sin(a), 3.5, 3.5))
    Glow("Cardinals", marks, y=0, group="diagram", ey=DY, w=1.0)

    # side columns flanking the diagram
    for side, nm in [(-1, "Left Column"), (1, "Right Column")]:
        items = []
        for k in range(5):
            gi = rnd.randrange(len(GLYPHS))
            h = 12
            items += glyph_polys(gi, side * 158 - 0.3 * h, -60 + k * 26 - h / 2 + DY, h)
        Glow(nm, items, ey=DY)

    for i, y in enumerate([170, 194, 218]):
        Glow(f"Verse {i + 3}", rune_line(y, 150 if i < 2 else 110, 13, rnd), ey=y)

    # closing sigil: small circle + crossed lines
    sig = [('ellipse', 0, 0, 22, 22), ('poly', [(-18, 0), (18, 0)], False), ('poly', [(0, -18), (0, 18)], False),
           ('poly', [(-8, -8), (8, 8)], False), ('poly', [(8, -8), (-8, 8)], False)]
    Glow("Sigil", sig, y=256, ey=256, w=1.0)

# paper outline -------------------------------------------------------------
def torn_edge(x0, sign, seed, tears):
    """points along a vertical torn edge from top to bottom (sign=+1 right edge)."""
    nz = noise1d(seed)
    rr = random.Random(seed)
    pts = []
    y = -PAGE_HH
    while y <= PAGE_HH:
        x = x0 + sign * (nz(y) * 1.8 + rr.uniform(-0.9, 0.9))
        for (ty, depth, span) in tears:
            d = abs(y - ty)
            if d < span:
                k = 1 - d / span
                x -= sign * depth * (k ** 1.6) * rr.uniform(0.75, 1.0)
        pts.append((x, y))
        y += rr.uniform(4, 8)
    pts.append((x0 + sign * nz(PAGE_HH) * 1.8, PAGE_HH))
    return pts

def paper_outline():
    right = torn_edge(PAGE_HW, +1, 3, [(-140, 11, 9), (95, 7, 6), (205, 17, 22), (262, 5, 5)])
    left = torn_edge(-PAGE_HW, -1, 5, [(-232, 8, 7), (-30, 14, 12), (60, 5, 5), (150, 9, 8)])
    pts = right + list(reversed(left))
    return pts

# ----------------------------------------------------------------------------
# rolls
# ----------------------------------------------------------------------------
BAND_N = 11

class Roll:
    def __init__(self, name, sign, seed):
        self.name, self.sign, self.seed = name, sign, seed
        self.node, self.body, self.hit = nid(), nid(), nid()
        rr = random.Random(seed)
        self.bands = []
        for i in range(BAND_N):
            seam = (i == 0)
            w = 372 if seam else rr.uniform(50, 300)
            x = 0 if seam else rr.uniform(-182 + w / 2, 182 - w / 2)
            dark = seam or rr.random() < 0.65
            col = "5E3F20" if dark else "F6E7C2"
            a = 0.85 if seam else (rr.uniform(0.35, 0.6) if dark else rr.uniform(0.35, 0.55))
            hgt = 1.5 if seam else rr.uniform(0.8, 2.2)
            th = 2 * math.pi * i / BAND_N + rr.uniform(-0.15, 0.15)
            self.bands.append(dict(id=nid(), x=x, w=w, col=col, a=a, h=hgt, th=th, blot=False))
        for i in range(12):   # grime blotches that travel round the roll with the fibres
            w = rr.uniform(30, 120)
            x = rr.uniform(-175 + w / 2, 175 - w / 2)
            self.bands.append(dict(id=nid(), x=x, w=w, col=rr.choice(["6A4522", "7A5028", "5A3A1C"]),
                                   a=rr.uniform(0.5, 0.8), h=rr.uniform(6, 13), th=rr.uniform(0, 2 * math.pi), blot=True))

    def xml(self):
        nzl, nzr = noise1d(self.seed + 1), noise1d(self.seed + 2)
        # body silhouette in unit space (y in -RU..RU)
        top = [(-188 + nzl(-RU) * 1.5, -RU), (188 + nzr(-RU) * 1.5, -RU)]
        rightside = [(189 + nzr(y * 9) * 2.2 + random.uniform(-.6, .6), y) for y in [-16, -10, -5, 0, 5, 10, 16]]
        bot = [(188 + nzr(RU) * 1.5, RU), (-188 + nzl(RU) * 1.5, RU)]
        leftside = [(-189 - nzl(y * 9) * 2.2 + random.uniform(-.6, .6), y) for y in [16, 10, 5, 0, -5, -10, -16]]
        body_pts = top + rightside + bot + leftside
        grad = lin_grad(0, -RU, 0, RU, [
            (0.0, "FF4E361D"), (0.12, "FF8E6B40"), (0.3, "FFD9BD86"), (0.4, "FFF1DEAF"),
            (0.55, "FFD7B984"), (0.78, "FF9C7A4C"), (0.92, "FF6A4B2A"), (1.0, "FF3E2914")])
        bands = []
        for b in self.bands:
            if b['blot']:
                bands.append(blob_shape("Grime", b["id"], b["x"], 0, b["w"], b["h"], argb(b["col"], b["a"])))
                continue
            bands.append(
                f'<Shape x="{f(b["x"])}" y="0" name="Fiber" id="{b["id"]}">'
                f'<Rectangle width="{f(b["w"])}" height="{f(b["h"])}" cornerRadiusTL="1" name="Path"/>'
                f'<Fill name="Fill">{solid(argb(b["col"], b["a"]))}</Fill></Shape>')
        # end faces: the coiled paper edge seen at each end of the roll
        ends = []
        for sx in (-1, 1):
            ex = sx * 189
            ends.append(
                f'<Shape x="{f(ex)}" name="Roll End" id="{nid()}">'
                f'<Ellipse width="7" height="{f(2 * RU - 1)}" name="Path"/>'
                f'<Ellipse width="3.5" height="{f(2 * RU * 0.62)}" name="Path"/>'
                f'<Stroke thickness="0.8" name="Coil">{solid("AA4A3018")}</Stroke>'
                f'<Fill name="Fill">{lin_grad(0, -RU, 0, RU, [(0, "FF5A3F22"), (0.4, "FFB8955F"), (1, "FF4A321A")])}</Fill></Shape>')
        body = (
            f'<Node name="Body" id="{self.body}">'
            + "".join(ends)
            + "".join(
                f'<Shape x="{f(sx * 186)}" y="{f(fy)}" name="Loose Layer" id="{nid()}">'
                + poly_xml([(0, -fh), (sx * fw, -fh * 0.3), (sx * fw * 0.6, fh), (0, fh * 0.8)], True, cw=(sx > 0)) +
                f'<Stroke thickness="0.6" name="Edge">{solid("AA3A2512")}</Stroke>'
                f'<Fill name="Fill">{solid("FFC9A66C")}</Fill></Shape>'
                for sx, fy, fw, fh in ((-1, -6, 4.5, 3.5), (1, 9, 5, 3), (1, -12, 3, 2.5)))
            + f'<Shape name="Worn Ends" id="{nid()}"><Rectangle width="378" height="{f(2 * RU)}" name="Path"/>'
              f'<Fill name="Fill">{lin_grad(-189, 0, 189, 0, [(0, "B04A2E14"), (0.07, "404A2E14"), (0.16, "004A2E14"), (0.84, "004A2E14"), (0.93, "404A2E14"), (1, "B04A2E14")])}</Fill></Shape>'
            + f'<Shape y="-8.5" name="Sheen" id="{nid()}"><Rectangle width="340" height="1.6" cornerRadiusTL="0.8" name="Path"/>'
              f'<Fill name="Fill">{lin_grad(-170, 0, 170, 0, [(0, "00FFF6DC"), (0.3, "70FFF6DC"), (0.7, "70FFF6DC"), (1, "00FFF6DC")])}</Fill></Shape>'
            + "".join(bands)
            + f'<Shape name="Roll Paper" id="{nid()}">{poly_xml(body_pts, True)}'
              f'<Stroke thickness="0.9" name="Edge">{solid("CC3A2512")}</Stroke>'
              f'<Fill name="Fill">{grad}</Fill></Shape>'
            + f'<Shape y="{f(RU * 0.55)}" name="Contact Shadow" id="{nid()}"><Rectangle width="388" height="{f(RU * 1.2)}" originY="0" cornerRadiusTL="4" name="Path"/>'
              f'<Fill name="Fill">{lin_grad(0, 0, 0, RU * 1.2, [(0, "B0000000"), (0.4, "70000000"), (1, "00000000")])}</Fill></Shape>'
            + '</Node>')
        # rod and knobs (fixed size)
        wood = [(0, "FF1E120A"), (0.3, "FF6E4626"), (0.5, "FF8A5C34"), (0.75, "FF3E2614"), (1, "FF150C06")]
        bronze = [(0, "FF2A1A0C"), (0.25, "FF9C7840"), (0.4, "FFE0C07A"), (0.6, "FF7A5A2A"), (1, "FF20140A")]
        knobs = []
        for sx in (-1, 1):
            knobs.append(
                f'<Node x="{f(sx * 236)}" name="Handle" id="{nid()}">'
                f'<Shape x="{f(sx * 12)}" y="-8" name="Glint" id="{nid()}"><Ellipse width="9" height="4" name="Path"/>'
                f'<Fill name="Fill">{solid("55FFF0D0")}</Fill></Shape>'
                f'<Shape x="{f(sx * 35)}" name="Finial" id="{nid()}"><Ellipse width="9" height="10" name="Path"/>'
                f'<Fill name="Fill">{lin_grad(0, -5, 0, 5, bronze)}</Fill></Shape>'
                f'<Shape x="{f(sx * 29)}" name="Neck" id="{nid()}"><Rectangle width="5" height="9" cornerRadiusTL="2" name="Path"/>'
                f'<Fill name="Fill">{lin_grad(0, -4.5, 0, 4.5, bronze)}</Fill></Shape>'
                f'<Shape x="{f(sx * 15)}" name="Knob" id="{nid()}"><Ellipse width="26" height="30" name="Path"/>'
                f'<Stroke thickness="0.8" name="Edge">{solid("AA120A04")}</Stroke>'
                f'<Fill name="Fill">{lin_grad(0, -15, 0, 15, bronze)}</Fill></Shape>'
                f'<Shape x="{f(sx * 1)}" name="Collar" id="{nid()}"><Rectangle width="8" height="24" cornerRadiusTL="2.5" name="Path"/>'
                f'<Stroke thickness="0.8" name="Edge">{solid("AA120A04")}</Stroke>'
                f'<Fill name="Fill">{lin_grad(0, -12, 0, 12, bronze)}</Fill></Shape>'
                f'</Node>')
        rod = (f'<Shape name="Rod" id="{nid()}"><Rectangle width="466" height="11" cornerRadiusTL="3" name="Path"/>'
               f'<Fill name="Fill">{lin_grad(0, -5.5, 0, 5.5, wood)}</Fill></Shape>')
        hit = (f'<Shape isTargetOpaque="true" name="Roll Tap Area" id="{self.hit}"><Rectangle width="480" height="{f(2 * R0)}" name="Path"/>'
               f'<Fill name="Fill">{solid("00000000")}</Fill></Shape>')
        return (f'<Node x="{CX}" y="{f(CY + self.sign * R0)}" name="{self.name}" id="{self.node}">'
                + hit + body + "".join(knobs) + rod + '</Node>')

# ----------------------------------------------------------------------------
# animation sampling
# ----------------------------------------------------------------------------
class Track:
    """a keyed property: list of (frame, value)."""
    def __init__(self, obj, prop, kind='double'):
        self.obj, self.prop, self.kind = obj, prop, kind
        self.keys = []
    def add(self, fr, v):
        self.keys.append((fr, v))

def simplify(keys, tol):
    if len(keys) <= 2:
        return keys
    out = [keys[0]]
    i = 0
    while i < len(keys) - 1:
        j = i + 2
        best = i + 1
        while j < len(keys):
            (f0, v0), (f1, v1) = keys[i], keys[j]
            ok = True
            for k in range(i + 1, j):
                fk, vk = keys[k]
                t = (fk - f0) / (f1 - f0)
                if abs(v0 + (v1 - v0) * t - vk) > tol:
                    ok = False
                    break
            if not ok:
                break
            best = j
            j += 1
        out.append(keys[best])
        i = best
    return out

def anim_xml(name, aid, duration, tracks, loop="oneShot"):
    by_obj = {}
    for t in tracks:
        by_obj.setdefault(t.obj, []).append(t)
    parts = []
    for obj, ts in by_obj.items():
        props = []
        for t in ts:
            if t.kind == 'color':
                ks = []
                prev = None
                for i, (fr, v) in enumerate(t.keys):
                    if v == prev and i != len(t.keys) - 1 and t.keys[i + 1][1] == v:
                        continue
                    ks.append(f'<KeyFrameColor value="{v}" frame="{fr}" interpolationType="linear"/>')
                    prev = v
                props.append(f'<KeyedProperty property="{t.prop}">{"".join(ks)}</KeyedProperty>')
            else:
                tol = {'rotation': 0.0006, 'opacity': 0.004, 'scaleY': 0.002}.get(t.prop, 0.05)
                ks = simplify(t.keys, tol)
                kx = "".join(f'<KeyFrameDouble value="{f(v) if t.prop not in ("rotation",) else f"{v:.5f}"}" frame="{fr}" interpolationType="linear"/>' for fr, v in ks)
                props.append(f'<KeyedProperty property="{t.prop}">{kx}</KeyedProperty>')
        parts.append(f'<KeyedObject objectId="{obj}">{"".join(props)}</KeyedObject>')
    return f'<LinearAnimation loopValue="{loop}" fps="60" duration="{duration}" name="{name}" id="{aid}">{"".join(parts)}</LinearAnimation>'

def bezier_ease(x1, y1, x2, y2):
    def bx(t): return 3 * (1 - t) ** 2 * t * x1 + 3 * (1 - t) * t * t * x2 + t ** 3
    def by(t): return 3 * (1 - t) ** 2 * t * y1 + 3 * (1 - t) * t * t * y2 + t ** 3
    def e(u):
        if u <= 0: return 0.0
        if u >= 1: return 1.0
        lo, hi = 0.0, 1.0
        for _ in range(40):
            m = (lo + hi) / 2
            if bx(m) < u: lo = m
            else: hi = m
        return by((lo + hi) / 2)
    return e

def spring_follow(target_fn, frames, omega, zeta, s0, clamp_lo=None):
    """critically-ish damped follower of target, integrated at 4 substeps/frame."""
    x, v = s0, 0.0
    out = []
    dt = 1 / 240
    for fr in range(frames + 1):
        out.append(x)
        for sub in range(4):
            tt = fr + sub / 4
            a = omega * omega * (target_fn(tt) - x) - 2 * zeta * omega * v
            v += a * dt
            x += v * dt
            if clamp_lo is not None and x < clamp_lo:
                x = clamp_lo
                v = abs(v) * 0.18   # soft bump when the rolls meet
    return out

def smoothstep(a, b, x):
    if b == a: return 1.0 if x >= b else 0.0
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)

# ============================================================================
# assemble
# ============================================================================
build_glyph_content()
ROLL_T = Roll("Top Roll", -1, 21)
ROLL_B = Roll("Bottom Roll", +1, 37)

ID_SM, ID_VM, ID_PROP, ID_INST = "0:7", "0:40", "0:41", "0:42"
ID_MASK, ID_MASK_RECT = nid(), nid()
ID_SHADOW, ID_SHADOW_RECT = nid(), nid()
ID_PAGE, ID_PAPERMASK = nid(), nid()
ID_CURL_T, ID_CURL_B = nid(), nid()
ID_SEAM, ID_SEAM_PULSE = nid(), nid()
ID_MOTES, ID_AURA, ID_PAGE_AURA = nid(), nid(), nid()
ID_PAGEHIT, ID_PAGEHIT_RECT = nid(), nid()
ID_RUNES, ID_DIAGRAM = nid(), nid()
ID_RUNEMASK, ID_RUNEMASK_RECT = nid(), nid()
ID_TEXTMASK, ID_TEXTMASK_RECT = nid(), nid()
ID_TEXT, ID_TXT_FILL, ID_TXT_GLOW = nid(), nid(), nid()
ID_SWEEP, ID_FLASH, ID_SPARKS = nid(), nid(), nid()
ID_RING = nid()
ID_PROP_TR, ID_PROP_TXT = "0:43", "0:44"
SWEEP_TOP, SWEEP_SPAN = -300.0, 600.0
TXT_INK, TXT_HOT = "FF3A2412", "FFE4FCFF"
DEFAULT_TEXT = ("The Ward of the Seventh Star\n\n"
    "Whosoever reads these words aloud beneath an open sky shall be shielded from the gaze of the night "
    "until the coming of the dawn.\n\n"
    "Let the reader stand within a circle of salt, face the north, and speak the seven names in turn. "
    "With each name a star shall kindle above; when all seven burn, the ward is sealed.\n\n"
    "Break the circle, and the ward breaks with it.")
sp = random.Random(31)
SPARKS = [dict(id=nid(), x=sp.uniform(-165, 165), y=sp.uniform(-262, 262), vx=sp.uniform(-22, 22),
               rise=sp.uniform(25, 70), life=sp.randint(26, 46), sz=sp.uniform(1.6, 3.2)) for _ in range(52)]

def xml_esc(t):
    return t.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "&#10;")

outline = paper_outline()

def page_xml():
    parts = []
    # hole worn through the vellum
    hole_pts = []
    hr = random.Random(4)
    for k in range(11):
        a = 2 * math.pi * k / 11
        r = 6.5 * hr.uniform(0.6, 1.15)
        hole_pts.append((r * 1.3 * math.cos(a), r * math.sin(a)))
    parts.append(f'<Shape x="146" y="-250" name="Worn Hole" id="{nid()}">{poly_xml(hole_pts, True)}'
                 f'<Stroke thickness="1.4" join="round" name="Burnt Rim">{solid("DD4A2C12")}</Stroke>'
                 f'<Fill name="Fill">{solid("FF151A22")}</Fill></Shape>')
    parts.append(f'' + blob_shape("Hole Scorch", nid(), 146, -250, 30, 24, "A0603A18"))
    # cracks running in from the tears
    for pts in ([(173, 205), (162, 201), (151, 206), (143, 203)],
                [(-176, -30), (-166, -27), (-158, -31)],
                [(181, -140), (172, -137)]):
        parts.append(f'<Shape name="Crack" id="{nid()}">{poly_xml(pts)}'
                     f'<Stroke thickness="0.9" cap="round" join="round" name="Line">{solid("995A3A1C")}</Stroke></Shape>')
    # --- translation layer: sparks, sweep of light, flash ------------------
    sparks = []
    for k in SPARKS:
        sparks.append(f'<Shape x="{f(k["x"])}" y="{f(k["y"])}" opacity="0" name="Spark" id="{k["id"]}">'
                      f'<Star width="{f(k["sz"] * 4.2)}" height="{f(k["sz"] * 4.2)}" points="4" innerRadius="0.18" name="Twinkle"/>'
                      f'<Stroke thickness="1.2" join="round" name="Bloom">{solid("C040D8FF")}<Feather strength="2.2" name="Soft"/></Stroke>'
                      f'<Fill name="Core">{solid("FFF4FFFF")}</Fill></Shape>')
    parts.append(f'<Node name="Sparks" id="{ID_SPARKS}">' + "".join(sparks) + '</Node>')
    parts.append(f'<Node y="{f(SWEEP_TOP)}" opacity="0" name="Translation Sweep" id="{ID_SWEEP}">'
                 f'<Shape name="Sweep Core" id="{nid()}">{poly_xml([(-178, 0), (178, 0)])}'
                 f'<Stroke thickness="1.6" cap="round" name="Core">{lin_grad(-178, 0, 178, 0, [(0, "00F2FEFF"), (0.12, "FFF2FEFF"), (0.88, "FFF2FEFF"), (1, "00F2FEFF")])}</Stroke></Shape>'
                 f'<Shape name="Sweep Bloom" id="{nid()}">{poly_xml([(-175, 0), (175, 0)])}'
                 f'<Stroke thickness="5" cap="round" name="Bloom">{lin_grad(-175, 0, 175, 0, [(0, "0040D8FF"), (0.15, "E040D8FF"), (0.85, "E040D8FF"), (1, "0040D8FF")])}<Feather strength="7" name="Soft"/></Stroke></Shape>'
                 + blob_shape("Sweep Haze", nid(), 0, 0, 470, 80, "6A36CFF5", hard=0.05) + '</Node>')
    parts.append(f'<Shape y="2" opacity="0" name="Shockwave" id="{ID_RING}"><Ellipse width="100" height="100" name="Path"/>'
                 f'<Stroke thickness="1.6" transformAffectsStroke="false" name="Core">{solid("FFF2FEFF")}</Stroke>'
                 f'<Stroke thickness="6" transformAffectsStroke="false" name="Bloom">{solid("C040D8FF")}<Feather strength="6" name="Soft"/></Stroke></Shape>')
    parts.append(blob_shape("Translation Flash", ID_FLASH, 0, 2, 300, 300, "E8E8FDFF", extra='opacity="0"', hard=0.04))
    # --- the runes and diagram (wiped away by the sweep) ---------------------
    runes = [f'<ClippingShape sourceId="{ID_RUNEMASK}" fillRule="evenOdd" name="Unswept"/>']
    for y, gap, dia in ((-229, 12, True), (256, 26, False)):  # divider flourishes
        runes.append(f'<Shape y="{y}" name="Divider" id="{nid()}">'
                     f'{poly_xml([(-120, 0), (-gap, 0)])}{poly_xml([(gap, 0), (120, 0)])}'
                     + (poly_xml([(0, -4), (4, 0), (0, 4), (-4, 0)], True) if dia else '') +
                     f'<Stroke thickness="1" cap="round" name="Ink">{solid(argb(INK, 0.5))}</Stroke></Shape>')
    for g in Glow.all:
        if g.group == 'rune':
            runes.append(g.xml())
    diag = [g.xml() for g in Glow.all if g.group == 'diagram']
    diag.append(f'<Shape opacity="0" blendModeValue="screen" name="Diagram Light" id="{ID_PAGE_AURA}"><Ellipse width="330" height="330" name="Path"/>'
                f'<Fill name="Fill">{rad_grad(0, 0, 165, [(0, "3A3EC8F0"), (0.5, "1A2EA0D0"), (1, "002A90C0")])}</Fill></Shape>')
    runes.append(f'<Node y="2" name="Diagram" id="{ID_DIAGRAM}">' + "".join(diag) + '</Node>')
    parts.append(f'<Node name="Runes" id="{ID_RUNES}">' + "".join(runes) + '</Node>')
    # --- the translated text (revealed behind the sweep) ---------------------
    parts.append(
        f'<Node name="Translation" id="{nid()}"><ClippingShape sourceId="{ID_TEXTMASK}" name="Swept"/>'
        f'<Text x="0" y="2" width="296" height="520" originX="0.5" originY="0.5" sizingValue="fixed" '
        f'overflowValue="fitFontSize" wrapValue="wrap" alignValue="center" verticalAlignValue="middle" paragraphSpacing="6" '
        f'name="Translated Text" id="{ID_TEXT}">'
        f'<TextStylePaint fontSize="21" fontAssetId="0:70" familyName="IM FELL English" styleName="Regular" name="Scribe Ink" id="0:71">'
        f'<Stroke thickness="1.1" join="round" name="Arcane Glow">{solid("0040D8FF", ID_TXT_GLOW)}<Feather strength="1.6" name="Soft"/></Stroke>'
        f'<Fill name="Ink">{solid(TXT_INK, ID_TXT_FILL)}</Fill></TextStylePaint>'
        f'<TextValueRun styleId="0:71" text="{xml_esc(DEFAULT_TEXT)}" name="Text" id="{nid()}">'
        f'<DataBindContext sourcePathIds="{ID_VM}-{ID_PROP_TXT}" propertyKey="268"/></TextValueRun>'
        f'</Text></Node>')
    # inked border, hand ruled
    br = random.Random(9)
    def ruled(hw, hh, jit):
        pts = []
        for (x0, y0, x1, y1) in [(-hw, -hh, hw, -hh), (hw, -hh, hw, hh), (hw, hh, -hw, hh), (-hw, hh, -hw, -hh)]:
            for k in range(8):
                t = k / 8
                pts.append((x0 + (x1 - x0) * t + br.uniform(-jit, jit), y0 + (y1 - y0) * t + br.uniform(-jit, jit)))
        return pts
    parts.append(f'<Shape name="Border Outer" id="{nid()}">{poly_xml(ruled(170, 288, 0.7), True)}'
                 f'<Stroke thickness="1.7" join="round" name="Ink">{solid(argb(INK, 0.6))}</Stroke></Shape>')
    parts.append(f'<Shape name="Border Inner" id="{nid()}">{poly_xml(ruled(164, 282, 0.5), True)}'
                 f'<Stroke thickness="0.8" join="round" name="Ink">{solid(argb(INK, 0.5))}</Stroke></Shape>')
    for sx in (-1, 1):
        for sy in (-1, 1):
            parts.append(f'<Shape x="{sx * 167}" y="{sy * 285}" name="Corner Knot" id="{nid()}">'
                         f'<Ellipse width="9" height="9" name="Path"/><Ellipse width="3" height="3" name="Path"/>'
                         f'<Stroke thickness="1" name="Ink">{solid(argb(INK, 0.6))}</Stroke>'
                         f'<Fill name="Fill">{solid("FFD6B57E")}</Fill></Shape>')
    # paper detail, clipped to the paper outline
    det = []
    det.append(f'<Shape x="0" y="{f(-OPEN_HALF + R1)}" name="Curl Shade Top" id="{ID_CURL_T}"><Rectangle width="420" height="30" originY="0" name="Path"/>'
               f'<Fill name="Fill">{lin_grad(0, 0, 0, 30, [(0, "8A2E1C0C"), (0.35, "3A2E1C0C"), (1, "002E1C0C")])}</Fill></Shape>')
    det.append(f'<Shape x="0" y="{f(OPEN_HALF - R1)}" name="Curl Shade Bottom" id="{ID_CURL_B}"><Rectangle width="420" height="30" originY="1" name="Path"/>'
               f'<Fill name="Fill">{lin_grad(0, 0, 0, -30, [(0, "8A2E1C0C"), (0.35, "3A2E1C0C"), (1, "002E1C0C")])}</Fill></Shape>')
    det.append(f'<Shape name="Edge Burn" id="{nid()}">{poly_xml(outline, True)}'
               f'<Stroke thickness="18" join="round" name="Burn">{solid("5C643C18")}<Feather strength="10" name="Soft"/></Stroke></Shape>')
    sr = random.Random(17)
    for k in range(10):
        cx, cy = sr.uniform(-160, 160), sr.uniform(-300, 300)
        r = sr.uniform(14, 46)
        pts = [((r * sr.uniform(0.7, 1.15)) * math.cos(2 * math.pi * j / 9),
                (r * sr.uniform(0.6, 1.0)) * math.sin(2 * math.pi * j / 9)) for j in range(9)]
        for j in range(3):   # each stain is a few overlapping soft lobes, so it is irregular
            det.append(blob_shape("Stain", nid(), cx + sr.uniform(-r, r) * 0.5, cy + sr.uniform(-r, r) * 0.4,
                                  r * sr.uniform(1.4, 2.4), r * sr.uniform(0.9, 1.4), argb("7A5028", sr.uniform(0.12, 0.24)),
                                  extra=f'rotation="{f(sr.uniform(-0.6, 0.6))}"', hard=0.1))
    # a cup ring and a few foxing spots
    det.append(f'<Shape x="-98" y="262" name="Ring Stain" id="{nid()}"><Ellipse width="58" height="50" name="Path"/>'
               f'<Stroke thickness="2.4" name="Ring">{solid("26704820")}<Feather strength="3" name="Soft"/></Stroke></Shape>')
    for k in range(26):
        cx, cy = sr.uniform(-180, 180), sr.uniform(-320, 320)
        r = sr.uniform(1.2, 3.6)
        det.append(f'<Shape x="{f(cx)}" y="{f(cy)}" name="Foxing" id="{nid()}"><Ellipse width="{f(r * 1.3)}" height="{f(r)}" name="Path"/>'
                   f'<Fill name="Fill">{solid(argb("6A4520", sr.uniform(0.25, 0.5)))}</Fill></Shape>')
    for fy in (-122, 118):
        nz = noise1d(int(fy) + 400)
        pts = [(x, fy + nz(x * 3) * 1.2) for x in range(-200, 201, 20)]
        det.append(f'<Shape name="Fold Light" id="{nid()}">{poly_xml([(x, y + 1.3) for x, y in pts])}'
                   f'<Stroke thickness="1.4" name="Line">{solid("50FFF4D8")}</Stroke></Shape>')
        det.append(f'<Shape name="Fold Dark" id="{nid()}">{poly_xml(pts)}'
                   f'<Stroke thickness="1.1" name="Line">{solid("387A5028")}</Stroke></Shape>')
    # long fibres in the vellum
    for k in range(18):
        x0, y0 = sr.uniform(-170, 120), sr.uniform(-320, 320)
        L = sr.uniform(30, 90)
        det.append(f'<Shape name="Fibre" id="{nid()}">{poly_xml([(x0, y0), (x0 + L * 0.5, y0 + sr.uniform(-2, 2)), (x0 + L, y0 + sr.uniform(-3, 3))])}'
                   f'<Stroke thickness="0.7" cap="round" name="Line">{solid(argb("8A6438", sr.uniform(0.15, 0.3)))}</Stroke></Shape>')
    parts.append(f'<Node name="Paper Detail" id="{nid()}"><ClippingShape sourceId="{ID_PAPERMASK}" name="Paper Clip"/>{"".join(det)}</Node>')
    # paper itself
    parts.append(f'<Shape name="Vellum" id="{nid()}">{poly_xml(outline, True)}'
                 f'<Stroke thickness="1.1" join="round" name="Torn Edge">{solid("C8553517")}</Stroke>'
                 f'<Fill name="Fill">{rad_grad(-20, -40, 430, [(0, "FFEBD6A6"), (0.45, "FFDDBE86"), (0.8, "FFC49E62"), (1, "FFA9804A")])}</Fill></Shape>')
    parts.append(f'<Shape name="Paper Mask" id="{ID_PAPERMASK}">{poly_xml(outline, True)}</Shape>')
    parts.append(f'<Shape name="Rune Mask" id="{ID_RUNEMASK}"><Rectangle width="700" height="900" name="Everything"/>'
                 f'<Rectangle y="{f(SWEEP_TOP)}" width="460" height="0" originY="0" name="Swept" id="{ID_RUNEMASK_RECT}"/></Shape>')
    parts.append(f'<Shape name="Text Mask" id="{ID_TEXTMASK}">'
                 f'<Rectangle y="{f(SWEEP_TOP)}" width="460" height="0" originY="0" name="Swept" id="{ID_TEXTMASK_RECT}"/></Shape>')
    parts.append(f'<Shape name="Page Tap Area" id="{ID_PAGEHIT}"><Rectangle width="380" height="0" name="Path" id="{ID_PAGEHIT_RECT}"/>'
                 f'<Fill name="Fill">{solid("00000000")}</Fill></Shape>')
    return (f'<Node x="{CX}" y="{CY}" name="Page" id="{ID_PAGE}">'
            f'<ClippingShape sourceId="{ID_MASK}" name="Reveal Clip"/>' + "".join(parts) + '</Node>')

MOTES = []
mr = random.Random(23)
for k in range(16):
    MOTES.append(dict(id=nid(), x=mr.choice([-1, 1]) * mr.uniform(120, 250), y0=mr.uniform(-260, 300),
                      rise=mr.uniform(50, 110), ph=mr.random(), r=mr.uniform(2.0, 3.6), sway=mr.uniform(4, 12), gid=nid()))

def motes_xml():
    out = []
    for m in MOTES:
        out.append(f'<Shape x="{f(m["x"])}" y="{f(m["y0"])}" opacity="0" name="Mote" id="{m["id"]}">'
                   f'<Ellipse width="{f(m["r"])}" height="{f(m["r"])}" name="Path"/>'
                   f'<Fill name="Core">{solid("FFE8FDFF")}</Fill></Shape>')
        out.append(blob_shape("Mote Glow", m["gid"], m["x"], m["y0"], m["r"] * 5, m["r"] * 5, "904FD6FF", extra='opacity="0"', hard=0.05))
    return f'<Node x="{CX}" y="{CY}" opacity="0" name="Motes" id="{ID_MOTES}">' + "".join(out) + '</Node>'

# ----------------------------------------------------------------------------
# pose -> tracks
# ----------------------------------------------------------------------------
def new_tracks():
    T = {}
    def tr(obj, prop, kind='double'):
        key = (obj, prop)
        if key not in T:
            T[key] = Track(obj, prop, kind)
        return T[key]
    return T, tr

def write_pose(tr, fr, sT, sB, rotT, rotB, glow, seam, motes):
    RT, RB = radius_at(sT), radius_at(sB)
    yT = CY - R0 - sT
    yB = CY + R0 + sB
    tr(ROLL_T.node, 'y').add(fr, yT)
    tr(ROLL_B.node, 'y').add(fr, yB)
    tr(ROLL_T.node, 'rotation').add(fr, rotT)
    tr(ROLL_B.node, 'rotation').add(fr, rotB)
    tr(ROLL_T.body, 'scaleY').add(fr, RT / RU)
    tr(ROLL_B.body, 'scaleY').add(fr, RB / RU)
    for roll, s, sgn in ((ROLL_T, sT, -1), (ROLL_B, sB, 1)):
        ph = phi_at(s) * sgn
        for b in roll.bands:
            th = b['th'] + ph
            c = math.cos(th)
            tr(b['id'], 'y').add(fr, RU * 0.97 * math.sin(th))
            tr(b['id'], 'scaleY').add(fr, max(0.08, c))
            tr(b['id'], 'opacity').add(fr, smoothstep(0.0, 0.45, c))
    mid, gap = (yT + yB) / 2, (yB - yT)
    tr(ID_MASK, 'y').add(fr, mid)
    tr(ID_MASK_RECT, 'height').add(fr, gap)
    tr(ID_PAGEHIT, 'y').add(fr, mid - CY)
    tr(ID_PAGEHIT_RECT, 'height').add(fr, gap)
    tr(ID_SHADOW, 'y').add(fr, mid + 14)
    tr(ID_SHADOW_RECT, 'height').add(fr, max(0.0, gap - 2 * R0))
    tr(ID_CURL_T, 'y').add(fr, yT - CY + RT * 0.7)
    tr(ID_CURL_B, 'y').add(fr, yB - CY - RB * 0.7)
    for g in Glow.all:
        v = glow(g)
        tr(g.core, 'opacity').add(fr, smoothstep(0.15, 1.0, v))
        tr(g.halo, 'opacity').add(fr, smoothstep(0.0, 0.8, v))
    dia = glow(Glow.all[3])
    tr(ID_PAGE_AURA, 'opacity').add(fr, dia)
    tr(ID_SEAM, 'opacity').add(fr, seam)
    tr(ID_MOTES, 'opacity').add(fr, motes)
    tr(ID_AURA, 'opacity').add(fr, motes)

def visible_frame(sT_list, sB_list, ey):
    for fr, (a, b) in enumerate(zip(sT_list, sB_list)):
        if ey <= 0:
            half = R0 + a - radius_at(a)
            if half > -ey + 6: return fr
        else:
            half = R0 + b - radius_at(b)
            if half > ey + 6: return fr
    return len(sT_list)

def wobble(fr, start, length, amp, cycles, phase=0.0):
    u = (fr - start) / length
    if u <= 0 or u >= 1: return 0.0
    return amp * math.sin(math.pi * u) ** 2 * math.sin(2 * math.pi * cycles * u + phase)

# -- unroll ------------------------------------------------------------------
UN_LEN = 170
easeT = bezier_ease(0.5, 0.0, 0.22, 1.0)
tgtT = lambda t: D * easeT((t - 6) / 64)
tgtB = lambda t: D * easeT((t - 10) / 66)
sT = spring_follow(tgtT, UN_LEN, 10.5, 0.62, 0.0)
sB = spring_follow(tgtB, UN_LEN, 10.0, 0.58, 0.0)
sT[-1] = sB[-1] = D
vis = {g: visible_frame(sT, sB, g.ey) for g in Glow.all}

def build_unroll():
    T, tr = new_tracks()
    for fr in list(range(0, UN_LEN + 1, 2)) + ([UN_LEN] if UN_LEN % 2 else []):
        def glow(g, fr=fr):
            st = vis[g] + 8
            return 1.0 if fr == UN_LEN else smoothstep(st, st + 34, fr)
        write_pose(tr, fr, sT[fr], sB[fr],
                   wobble(fr, 4, 96, 0.016, 1.5) if fr < UN_LEN else 0.0,
                   wobble(fr, 8, 100, -0.013, 1.3, 0.7) if fr < UN_LEN else 0.0,
                   glow, 1.0 - smoothstep(0, 16, fr), smoothstep(70, 130, fr) if fr < UN_LEN else 1.0)
    return anim_xml("Unroll", "0:61", UN_LEN, T.values())

# -- roll up -----------------------------------------------------------------
UP_LEN = 140
easeU = bezier_ease(0.45, 0.0, 0.35, 1.0)
tgtTu = lambda t: D * (1 - easeU((t - 18) / 62))
tgtBu = lambda t: D * (1 - easeU((t - 22) / 62))
uT = spring_follow(tgtTu, UP_LEN, 10.5, 0.75, D, clamp_lo=0.0)
uB = spring_follow(tgtBu, UP_LEN, 10.0, 0.75, D, clamp_lo=0.0)
uT[-1] = uB[-1] = 0.0

def build_rollup():
    T, tr = new_tracks()
    for fr in range(0, UP_LEN + 1, 2):
        def glow(g, fr=fr):
            st = (1 - min(1.0, abs(g.ey) / 260)) * 8   # outer lines fade first
            return 0.0 if fr == UP_LEN else 1.0 - smoothstep(st, st + 26, fr)
        write_pose(tr, fr, uT[fr], uB[fr],
                   wobble(fr, 14, 90, -0.012, 1.4) if fr < UP_LEN else 0.0,
                   wobble(fr, 18, 90, 0.011, 1.2, 1.1) if fr < UP_LEN else 0.0,
                   glow, smoothstep(96, 132, fr) if fr < UP_LEN else 1.0,
                   (1.0 - smoothstep(0, 24, fr)) if fr < UP_LEN else 0.0)
    return anim_xml("Roll Up", "0:62", UP_LEN, T.values())

def build_static(name, aid, s, glowv, seam, motes):
    T, tr = new_tracks()
    write_pose(tr, 0, s, s, 0.0, 0.0, lambda g: glowv, seam, motes)
    return anim_xml(name, aid, 1, T.values())

# -- ambient ---------------------------------------------------------------
PULSE_LEN = 240
def build_pulse():
    T, tr = new_tracks()
    pr = random.Random(5)
    for g in Glow.all:
        ph = pr.uniform(0, 2 * math.pi)
        t = tr(g.halo_col, 'colorValue', 'color')
        for fr in range(0, PULSE_LEN + 1, 12):
            a = 0.26 + 0.14 * math.sin(2 * math.pi * 2 * fr / PULSE_LEN + ph)
            t.add(fr, argb(GLOW_HALO, a))
    for fr in range(0, PULSE_LEN + 1, 8):
        tr(ID_SEAM_PULSE, 'opacity').add(fr, 0.65 + 0.35 * math.sin(2 * math.pi * 2 * fr / PULSE_LEN))
    for m in MOTES:
        for fr in range(0, PULSE_LEN + 1, 6):
            u = (fr / PULSE_LEN + m['ph']) % 1.0
            for oid in (m['id'], m['gid']):
                tr(oid, 'y').add(fr, m['y0'] - m['rise'] * u)
                tr(oid, 'x').add(fr, m['x'] + m['sway'] * math.sin(2 * math.pi * (u * 1.5 + m['ph'])))
                tr(oid, 'opacity').add(fr, math.sin(math.pi * u) ** 2)
    return anim_xml("Arcane Pulse", "0:63", PULSE_LEN, T.values(), loop="loop")

SPIN_LEN = 2400
def build_spin():
    T, tr = new_tracks()
    spins = {"Outer Ring": 2 * math.pi, "Heptagram": -2 * math.pi, "Inner Seal": 2 * math.pi / 3}
    for g in Glow.all:
        if g.name in spins:
            tr(g.node, 'rotation').add(0, 0.0)
            tr(g.node, 'rotation').add(SPIN_LEN, spins[g.name])
    return anim_xml("Diagram Spin", "0:64", SPIN_LEN, T.values(), loop="loop")

# -- translation -------------------------------------------------------------
def lerp_col(c0, c1, t):
    t = max(0.0, min(1.0, t))
    a = [int(c0[i:i + 2], 16) for i in range(0, 8, 2)]
    b = [int(c1[i:i + 2], 16) for i in range(0, 8, 2)]
    return "".join(f"{int(round(x + (y - x) * t)):02X}" for x, y in zip(a, b))

def write_tpose(tr, fr, h, sweep, flash, flash_s, rot, dscale, shake, hot, glow_a, spark_fn, ring=(0.0, 0.3)):
    tr(ID_RUNEMASK_RECT, 'height').add(fr, h)
    tr(ID_TEXTMASK_RECT, 'height').add(fr, h)
    tr(ID_SWEEP, 'y').add(fr, SWEEP_TOP + h)
    tr(ID_SWEEP, 'opacity').add(fr, sweep)
    tr(ID_FLASH, 'opacity').add(fr, flash)
    tr(ID_FLASH, 'scaleX').add(fr, flash_s)
    tr(ID_FLASH, 'scaleY').add(fr, flash_s)
    tr(ID_DIAGRAM, 'rotation').add(fr, rot)
    tr(ID_RING, 'opacity').add(fr, ring[0])
    tr(ID_RING, 'scaleX').add(fr, ring[1])
    tr(ID_RING, 'scaleY').add(fr, ring[1])
    tr(ID_DIAGRAM, 'scaleX').add(fr, dscale)
    tr(ID_DIAGRAM, 'scaleY').add(fr, dscale)
    tr(ID_RUNES, 'x').add(fr, shake[0])
    tr(ID_RUNES, 'y').add(fr, shake[1])
    tr(ID_TXT_FILL, 'colorValue', 'color').add(fr, lerp_col(TXT_INK, TXT_HOT, hot))
    tr(ID_TXT_GLOW, 'colorValue', 'color').add(fr, argb("40D8FF", glow_a))
    for k in SPARKS:
        x, y, o, sc = spark_fn(k, fr)
        tr(k['id'], 'x').add(fr, x)
        tr(k['id'], 'y').add(fr, y)
        tr(k['id'], 'opacity').add(fr, o)
        tr(k['id'], 'scaleX').add(fr, sc)
        tr(k['id'], 'scaleY').add(fr, sc)
        tr(k['id'], 'rotation').add(fr, (fr - 0) * 0.06 * (1 if k['vx'] > 0 else -1))

def spark_path(k, fr, t0):
    """a spark born on the sweep line at frame t0, drifting up and burning out."""
    if t0 is None or fr < t0:
        return k['x'], k['y'], 0.0, 1.0
    u = (fr - t0) / k['life']
    if u >= 1:
        return k['x'] + k['vx'], k['y'] - k['rise'], 0.0, 0.3
    o = (u / 0.08) if u < 0.08 else (1 - (u - 0.08) / 0.92) ** 1.4
    return (k['x'] + k['vx'] * u, k['y'] - k['rise'] * (1 - (1 - u) ** 2), o, 1.5 - 1.1 * u)

def sweep_times(hs, downward):
    """frame at which the sweep line passes each spark's y."""
    out = {}
    for k in SPARKS:
        out[k['id']] = None
        for fr, h in enumerate(hs):
            y = SWEEP_TOP + h
            if (downward and y >= k['y'] and h > 0) or (not downward and y <= k['y'] and h < SWEEP_SPAN):
                out[k['id']] = fr
                break
    return out

def shake_at(fr, a, b, amp):
    e = smoothstep(a, a + 8, fr) * (1 - smoothstep(b - 8, b, fr))
    return (amp * e * math.sin(fr * 1.9) * math.cos(fr * 0.7), amp * 0.7 * e * math.sin(fr * 2.6 + 1))

def ring_at(fr, a, b):
    u = (fr - a) / (b - a)
    if u <= 0 or u >= 1: return (0.0, 0.3)
    return (min(1.0, u / 0.06) * (1 - u) ** 1.5, 0.3 + 3.6 * (1 - (1 - u) ** 3))

TR_LEN = 170
ease_sw = bezier_ease(0.45, 0.0, 0.4, 1.0)
ease_in = bezier_ease(0.55, 0.0, 0.9, 0.4)
TURNS = 4 * math.pi

def build_translate():
    T, tr = new_tracks()
    hs = [SWEEP_SPAN * ease_sw((fr - 34) / 80) for fr in range(TR_LEN + 1)]
    t0 = sweep_times(hs, True)
    for fr in range(0, TR_LEN + 1, 2):
        end = fr == TR_LEN
        flash = smoothstep(16, 34, fr) * (1 - smoothstep(36, 84, fr))
        write_tpose(tr, fr, SWEEP_SPAN if end else hs[fr],
                    0.0 if end else smoothstep(28, 36, fr) * (1 - smoothstep(110, 122, fr)),
                    0.0 if end else flash, 0.35 + 1.5 * smoothstep(12, 84, fr),
                    TURNS if end else TURNS * (0.25 * ease_in(fr / 40) if fr < 40 else 0.25 + 0.75 * ease_sw((fr - 40) / 80)),
                    1.0 + 0.14 * smoothstep(0, 36, fr),
                    (0, 0) if end else shake_at(fr, 0, 38, 1.8),
                    0.0 if end else 1.0 - smoothstep(118, 160, fr),
                    0.0 if end else 0.9 * (1 - smoothstep(118, 165, fr)),
                    lambda k, fr: (k['x'], k['y'], 0.0, 1.0) if end else spark_path(k, fr, t0[k['id']]),
                    ring_at(fr, 28, 74) if not end else (0.0, 0.3))
    return anim_xml("Translate", "0:67", TR_LEN, T.values())

UT_LEN = 170
def build_untranslate():
    T, tr = new_tracks()
    hs = [SWEEP_SPAN * (1 - ease_sw((fr - 20) / 80)) for fr in range(UT_LEN + 1)]
    t0 = sweep_times(hs, False)
    for fr in range(0, UT_LEN + 1, 2):
        end = fr == UT_LEN
        flash = smoothstep(92, 112, fr) * (1 - smoothstep(114, 160, fr))
        write_tpose(tr, fr, 0.0 if end else hs[fr],
                    0.0 if end else smoothstep(14, 22, fr) * (1 - smoothstep(96, 108, fr)),
                    0.0 if end else flash, 0.35 + 1.5 * smoothstep(90, 160, fr),
                    0.0 if end else TURNS * (1 - bezier_ease(0.2, 0.6, 0.35, 1.0)((fr - 20) / 120)),
                    1.0 + 0.14 * (1 - smoothstep(100, 150, fr)),
                    (0, 0) if end else shake_at(fr, 100, 134, 1.4),
                    0.0 if end else smoothstep(0, 20, fr),
                    0.0 if end else 0.9 * smoothstep(0, 18, fr),
                    lambda k, fr: (k['x'], k['y'], 0.0, 1.0) if end else spark_path(k, fr, t0[k['id']]),
                    ring_at(fr, 108, 154) if not end else (0.0, 0.3))
    return anim_xml("Untranslate", "0:68", UT_LEN, T.values())

def build_tstatic(name, aid, translated):
    T, tr = new_tracks()
    write_tpose(tr, 0, SWEEP_SPAN if translated else 0.0, 0.0, 0.0, 1.0,
                TURNS if translated else 0.0, 1.14 if translated else 1.0, (0, 0), 0.0, 0.0,
                lambda k, fr: (k['x'], k['y'], 0.0, 1.0))
    return anim_xml(name, aid, 1, T.values())

# ----------------------------------------------------------------------------
# state machine
# ----------------------------------------------------------------------------
def cond(val, prop=ID_PROP):
    return (f'<TransitionViewModelCondition opValue="equal"><TransitionPropertyViewModelComparator>'
            f'<BindablePropertyBoolean><DataBindContext sourcePathIds="{ID_VM}-{prop}" propertyKey="634"/></BindablePropertyBoolean>'
            f'</TransitionPropertyViewModelComparator><TransitionValueBooleanComparator value="{val}"/></TransitionViewModelCondition>')

def toggle(name, target, prop, lid, rid):
    return (f'<StateMachineListenerSingle targetId="{target}" listenerTypeValue="click" name="{name}" id="{lid}">'
            f'<ListenerViewModelChange fromViewModelProperty="true" fromDataBindId="{rid}"><BindablePropertyBoolean>'
            f'<DataBindContext sourcePathIds="{ID_VM}-{prop}" propertyKey="634" id="{rid}" converterId="0:90"/>'
            f'<DataBindContext sourcePathIds="{ID_VM}-{prop}" propertyKey="634" direction="true"/>'
            f'</BindablePropertyBoolean></ListenerViewModelChange></StateMachineListenerSingle>')

SM = f'''
<StateMachine name="Scroll Machine" id="{ID_SM}">
{toggle("Tap Top Roll", ROLL_T.hit, ID_PROP, "0:80", "0:81")}
{toggle("Tap Bottom Roll", ROLL_B.hit, ID_PROP, "0:83", "0:84")}
{toggle("Tap Page", ID_PAGEHIT, ID_PROP_TR, "0:86", "0:87")}
  <StateMachineLayer name="Scroll" id="0:8">
    <AnyState x="520" y="-160"/>
    <ExitState x="680" y="-160"/>
    <EntryState x="0" y="0">
      <StateTransition stateToId="0:11">{cond("true")}</StateTransition>
      <StateTransition stateToId="0:10"/>
    </EntryState>
    <AnimationState x="200" y="0" animationId="0:60" id="0:10">
      <StateTransition stateToId="0:12">{cond("true")}</StateTransition>
    </AnimationState>
    <AnimationState x="200" y="160" animationId="0:65" id="0:11">
      <StateTransition stateToId="0:13">{cond("false")}</StateTransition>
    </AnimationState>
    <AnimationState x="440" y="0" animationId="0:61" id="0:12">
      <StateTransition stateToId="0:13" enableExitTime="true" exitTimeIsPercetange="true" exitTime="100">{cond("false")}</StateTransition>
    </AnimationState>
    <AnimationState x="440" y="160" animationId="0:62" id="0:13">
      <StateTransition stateToId="0:12" enableExitTime="true" exitTimeIsPercetange="true" exitTime="100">{cond("true")}</StateTransition>
    </AnimationState>
  </StateMachineLayer>
  <StateMachineLayer name="Translation" id="0:24">
    <AnyState x="520" y="-160"/>
    <ExitState x="680" y="-160"/>
    <EntryState x="0" y="0">
      <StateTransition stateToId="0:31">{cond("true", ID_PROP_TR)}</StateTransition>
      <StateTransition stateToId="0:30"/>
    </EntryState>
    <AnimationState x="200" y="0" animationId="0:66" id="0:30">
      <StateTransition stateToId="0:32">{cond("true", ID_PROP_TR)}</StateTransition>
    </AnimationState>
    <AnimationState x="200" y="160" animationId="0:69" id="0:31">
      <StateTransition stateToId="0:33">{cond("false", ID_PROP_TR)}</StateTransition>
    </AnimationState>
    <AnimationState x="440" y="0" animationId="0:67" id="0:32">
      <StateTransition stateToId="0:33" enableExitTime="true" exitTimeIsPercetange="true" exitTime="100">{cond("false", ID_PROP_TR)}</StateTransition>
    </AnimationState>
    <AnimationState x="440" y="160" animationId="0:68" id="0:33">
      <StateTransition stateToId="0:32" enableExitTime="true" exitTimeIsPercetange="true" exitTime="100">{cond("true", ID_PROP_TR)}</StateTransition>
    </AnimationState>
  </StateMachineLayer>
  <StateMachineLayer name="Arcane Pulse" id="0:20">
    <AnyState x="360" y="0"/>
    <ExitState x="520" y="0"/>
    <EntryState x="0" y="0"><StateTransition stateToId="0:21"/></EntryState>
    <AnimationState x="180" y="0" animationId="0:63" id="0:21"/>
  </StateMachineLayer>
  <StateMachineLayer name="Diagram Spin" id="0:22">
    <AnyState x="360" y="0"/>
    <ExitState x="520" y="0"/>
    <EntryState x="0" y="0"><StateTransition stateToId="0:23"/></EntryState>
    <AnimationState x="180" y="0" animationId="0:64" id="0:23"/>
  </StateMachineLayer>
</StateMachine>'''

def scene():
    seam = (f'<Node x="{CX}" y="{CY}" name="Seam Glow" id="{ID_SEAM}"><Node name="Seam Pulse" id="{ID_SEAM_PULSE}">'
            f'<Shape name="Seam Light" id="{nid()}">{poly_xml([(-150, 0), (150, 0)])}'
            f'<Stroke thickness="1.4" cap="round" name="Bloom">{lin_grad(-150, 0, 150, 0, [(0, "0040D8FF"), (0.3, "7840D8FF"), (0.7, "7840D8FF"), (1, "0040D8FF")])}<Feather strength="3" name="Soft"/></Stroke>'
            f'<Stroke thickness="0.7" cap="round" name="Core">{lin_grad(-150, 0, 150, 0, [(0, "00E8FDFF"), (0.35, "DDE8FDFF"), (0.65, "DDE8FDFF"), (1, "00E8FDFF")])}</Stroke>'
            f'</Shape></Node></Node>')
    mask = (f'<Shape x="{CX}" y="{CY}" name="Reveal Mask" id="{ID_MASK}">'
            f'<Rectangle width="470" height="{f(2 * R0)}" name="Path" id="{ID_MASK_RECT}"/></Shape>')
    shadow = (f'<Shape x="{CX + 8}" y="{CY + 14}" name="Page Shadow" id="{ID_SHADOW}">'
              f'<Rectangle width="430" height="0" name="Path" id="{ID_SHADOW_RECT}"/>'
              f'<Fill name="Fill">{lin_grad(-215, 0, 215, 0, [(0, "00000000"), (0.12, "70000000"), (0.88, "70000000"), (1, "00000000")])}</Fill></Shape>')
    aura = (f'<Shape x="{CX}" y="{CY}" opacity="0" blendModeValue="screen" name="Arcane Aura" id="{ID_AURA}"><Ellipse width="760" height="860" name="Path"/>'
            f'<Fill name="Fill">{rad_grad(0, 0, 400, [(0, "4031A8D8"), (0.5, "18206890"), (1, "00102040")])}</Fill></Shape>')
    vignette = (f'<Shape x="{CX}" y="{CY}" name="Vignette" id="{nid()}"><Rectangle width="{W}" height="{H}" name="Path"/>'
                f'<Fill name="Fill">{rad_grad(0, -20, 560, [(0, "00000000"), (0.6, "30000000"), (1, "C0000000")])}</Fill></Shape>')
    anims = [build_static("Rolled", "0:60", 0.0, 0.0, 1.0, 0.0),
             build_unroll(), build_rollup(),
             build_pulse(), build_spin(),
             build_static("Open", "0:65", D, 1.0, 0.0, 1.0),
             build_tstatic("Runes Shown", "0:66", False), build_translate(), build_untranslate(),
             build_tstatic("Text Shown", "0:69", True)]
    art = (f'<Artboard isComponent="true" x="700" y="0" defaultStateMachineId="{ID_SM}" viewModelId="{ID_VM}" viewModelInstanceId="{ID_INST}" '
           f'styleId="0:5" width="{W}" height="{H}" name="Scroll" id="0:2">'
           f'<LayoutComponentStyle name="Artboard Style" id="0:5"/>'
           + seam + motes_xml() + ROLL_T.xml() + ROLL_B.xml() + page_xml() + shadow + aura + mask
           + SM + "".join(anims) + '</Artboard>')
    # backdrop: the night-sky background, scaled to cover whatever the viewport is
    backdrop = (f'<Artboard isComponent="true" x="1400" y="0" defaultStateMachineId="0:97" styleId="0:96" width="{W}" height="{H}" name="Backdrop" id="0:95">'
                f'<LayoutComponentStyle name="Backdrop Style" id="0:96"/>' + vignette
                + f'<Fill name="Background">{rad_grad(CX, CY - 40, 620, [(0, "FF2A3546"), (0.55, "FF151B26"), (1, "FF07090E")])}</Fill>'
                f'<StateMachine name="Backdrop Machine" id="0:97"><StateMachineLayer name="Idle" id="0:98">'
                f'<AnyState x="200" y="0"/><ExitState x="360" y="0"/><EntryState x="0" y="0"/></StateMachineLayer></StateMachine>'
                '</Artboard>')
    def slot(name, leaf_id, art_id, fit, nested_sm=None):
        sid = nid()

        nsm = f'<NestedStateMachine animationId="{nested_sm}" name="Scroll Machine" id="{nid()}"/>' if nested_sm else ''
        return (f'<LayoutComponent styleId="{sid}" name="{name}" id="{nid()}">'
                f'<LayoutComponentStyle layoutWidthScaleType="fill" layoutHeightScaleType="fill" name="{name} Style" id="{sid}"/>'
                f'<NestedArtboardLeaf artboardId="{art_id}" fit="{fit}" alignmentX="0" alignmentY="0" name="{name} Art" id="{leaf_id}">{nsm}</NestedArtboardLeaf>'
                '</LayoutComponent>')
    root_style = nid()
    stage = (f'<Artboard x="0" y="0" defaultStateMachineId="0:93" viewModelId="{ID_VM}" viewModelInstanceId="{ID_INST}" '
             f'styleId="0:92" width="{W}" height="{H}" name="Scroll Stage" id="0:91">'
             f'<LayoutComponentStyle layoutWidthScaleType="fill" layoutHeightScaleType="fill" name="Stage Style" id="0:92"/>'
             f'<LayoutComponent styleId="{root_style}" name="Viewport" id="{nid()}">'
             f'<LayoutComponentStyle layoutTypeValue="stack" layoutWidthScaleType="fill" layoutHeightScaleType="fill" name="Viewport Style" id="{root_style}"/>'
             + slot("Scroll Slot", nid(), "0:2", "contain", ID_SM)
             + slot("Backdrop Slot", nid(), "0:95", "cover")
             + '</LayoutComponent>'
             f'<Fill name="Letterbox">{solid("FF07090E")}</Fill>'
             f'<StateMachine name="Stage Machine" id="0:93"><StateMachineLayer name="Idle" id="0:94">'
             f'<AnyState x="200" y="0"/><ExitState x="360" y="0"/><EntryState x="0" y="0"/></StateMachineLayer></StateMachine>'
             '</Artboard>')
    art = stage + art + backdrop + '<ComponentAsset artboardId="0:2" name="Scroll"/><ComponentAsset artboardId="0:95" name="Backdrop"/>'
    vm = (f'<ViewModel defaultInstanceId="{ID_INST}" name="Scroll" id="{ID_VM}">'
          f'<ViewModelPropertyBoolean name="isOpen" id="{ID_PROP}"/>'
          f'<ViewModelPropertyBoolean name="isTranslated" id="{ID_PROP_TR}"/>'
          f'<ViewModelPropertyString name="translatedText" id="{ID_PROP_TXT}"/>'
          f'<ViewModelInstance exports="true" name="Default" id="{ID_INST}">'
          f'<ViewModelInstanceBoolean propertyValue="false" viewModelPropertyId="{ID_PROP}"/>'
          f'<ViewModelInstanceBoolean propertyValue="false" viewModelPropertyId="{ID_PROP_TR}"/>'
          f'<ViewModelInstanceString propertyValue="{xml_esc(DEFAULT_TEXT)}" viewModelPropertyId="{ID_PROP_TXT}"/>'
          f'</ViewModelInstance></ViewModel>'
          f'<FontAsset file="fonts/IMFellEnglish-Regular.ttf" name="IM Fell English" id="0:70"/>')
    conv = '<DataConverterBooleanNegate name="Not" id="0:90"/>'
    return f'<Rive version="1" kind="fragment">{art}{vm}{conv}</Rive>\n'

if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "scene.rml"
    open(out, "w").write(scene())
    print("wrote", out, "glows", len(Glow.all))
