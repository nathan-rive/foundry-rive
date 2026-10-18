"""Tiny helper library for emitting Rive RML from Python.

Containers (Artboard, Node, Solo) take children BACK-TO-FRONT here (the order a
painter would lay them down) and are emitted reversed, because in RML the first
sibling draws on top. Everything inside a Shape is emitted in authored order.
"""
import math
from xml.sax.saxutils import quoteattr

_next = [100]


def nid():
    _next[0] += 1
    return f"0:{_next[0]}"


DRAW_CONTAINERS = {"Artboard", "Node", "Solo"}


class E:
    def __init__(self, tag, kids=None, **attrs):
        self.tag = tag
        self.attrs = {}
        for k, v in attrs.items():
            k = k.rstrip("_")
            if v is None:
                continue
            self.attrs[k] = v
        self.kids = list(kids or [])
        self.tail = []  # non-drawable children emitted after drawables (state machines etc.)

    @property
    def id(self):
        if "id" not in self.attrs:
            self.attrs["id"] = nid()
        return self.attrs["id"]

    def add(self, *ks):
        for k in ks:
            if k is None:
                continue
            if isinstance(k, (list, tuple)):
                self.add(*k)
            else:
                self.kids.append(k)
        return self

    def render(self, ind=0):
        pad = "  " * ind
        a = "".join(f" {k}={quoteattr(fmt(v))}" for k, v in self.attrs.items())
        kids = self.kids
        if self.tag in DRAW_CONTAINERS:
            draw = [k for k in kids if k.tag in DRAWABLES]
            other = [k for k in kids if k.tag not in DRAWABLES]
            kids = other + list(reversed(draw))
        kids = kids + self.tail
        if not kids:
            return f"{pad}<{self.tag}{a}/>"
        inner = "\n".join(k.render(ind + 1) for k in kids)
        return f"{pad}<{self.tag}{a}>\n{inner}\n{pad}</{self.tag}>"


DRAWABLES = {"Shape", "Node", "Solo", "Text", "Image", "NestedArtboard"}


def fmt(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float):
        s = f"{v:.4f}".rstrip("0").rstrip(".")
        return s if s not in ("-0", "") else "0"
    return str(v)


# ---------------------------------------------------------------- geometry

def smooth(points, closed=True, tension=1.0, name="Path", **kw):
    """Catmull-Rom style path. Each point is (x, y) or (x, y, 's') for a corner,
    or (x, y, 's', r) for a rounded corner."""
    n = len(points)
    verts = []
    for i, p in enumerate(points):
        x, y = p[0], p[1]
        sharp = len(p) > 2 and p[2] == "s"
        if sharp:
            r = p[3] if len(p) > 3 else 0
            verts.append(E("StraightVertex", x=float(x), y=float(y), radius=float(r) if r else None))
            continue
        if closed:
            pp = points[(i - 1) % n]
            pn = points[(i + 1) % n]
        else:
            pp = points[i - 1] if i > 0 else p
            pn = points[i + 1] if i < n - 1 else p
        tx, ty = (pn[0] - pp[0]) / 2.0, (pn[1] - pp[1]) / 2.0
        ang = math.atan2(ty, tx)
        dout = math.hypot(pn[0] - x, pn[1] - y) / 3.0 * tension
        din = math.hypot(x - pp[0], y - pp[1]) / 3.0 * tension
        if (not closed) and (i == 0 or i == n - 1):
            if i == 0:
                din = 0
            else:
                dout = 0
        verts.append(E("CubicDetachedVertex", x=float(x), y=float(y),
                       inRotation=ang + math.pi, inDistance=din,
                       outRotation=ang, outDistance=dout))
    return E("PointsPath", verts, isClosed=closed, name=name, **kw)


def poly(points, closed=False, name="Path", **kw):
    return E("PointsPath", [E("StraightVertex", x=float(p[0]), y=float(p[1])) for p in points],
             isClosed=closed, name=name, **kw)


def ellipse(w, h, x=None, y=None, name="Path"):
    return E("Ellipse", width=float(w), height=float(h), x=x, y=y, name=name)


def rect(w, h, r=0, x=None, y=None, name="Path"):
    return E("Rectangle", width=float(w), height=float(h), cornerRadiusTL=float(r) if r else None,
             x=x, y=y, name=name)


def mirror(points, cx=256):
    """Mirror a point list across x=cx, reversing order to keep winding."""
    out = []
    for p in reversed(points):
        out.append((2 * cx - p[0], p[1]) + tuple(p[2:]))
    return out


def mirror_open(points, cx=256):
    return [(2 * cx - p[0], p[1]) + tuple(p[2:]) for p in points]


def heart(cx, cy, s):
    """Heart path centred at cx,cy, roughly s wide."""
    k = s / 40.0
    pts = [(0, 18, "s"), (-16, 4), (-20, -8), (-14, -17), (-5, -16), (0, -9, "s"),
           (5, -16), (14, -17), (20, -8), (16, 4)]
    return smooth([(cx + x * k, cy + y * k) + tuple(r) for (x, y, *r) in pts])


# ---------------------------------------------------------------- paint

def solid(color, bind=None, name="Color", keyid=None):
    sc = E("SolidColor", colorValue=color, name=name)
    if keyid:
        sc.attrs["id"] = keyid
    if bind:
        sc.add(bind)
    return sc


def fill(color, bind=None, name="Fill", rule=None):
    return E("Fill", [solid(color, bind)], name=name, fillRule=rule)


def stroke(th, color, bind=None, cap="round", join="round", name="Stroke", extra=None):
    s = E("Stroke", [solid(color, bind)], thickness=float(th), cap=cap, join=join, name=name)
    if extra:
        s.add(extra)
    return s


def shape(name, geo, paints, x=None, y=None, opacity=None, binds=None, rotation=None, **kw):
    s = E("Shape", name=name, x=x, y=y, opacity=opacity, rotation=rotation, **kw)
    s.add(geo)
    s.add(paints)
    if binds:
        s.add(binds)
    return s


def node(name, kids=None, **kw):
    return E("Node", kids, name=name, **kw)
