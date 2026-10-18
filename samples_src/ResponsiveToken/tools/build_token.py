#!/usr/bin/env python3
"""Generates scene.rml for the responsive D&D character token.

Run from the project root:   python3 tools/build_token.py
Then:                        rive . --verify

All coordinates are on a 512x512 artboard, centre (256,256).
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from rml import E, nid, smooth, poly, ellipse, rect, mirror, mirror_open, heart, solid, fill, stroke, shape, node, fmt  # noqa
import formula as F  # noqa

OUT = os.path.join(os.path.dirname(HERE), "scene.rml")

OL = "FF1C120E"      # outline ink
OLW = 7.0            # main outline weight
WHITE = "FFF8F4EC"

# ============================================================== view model
VM = nid()
VMI = nid()
P = {}
VM_PROPS = []          # (element, instance-value element)
ROOTS = []             # root elements (converters, enums)
ENUMS = {}


def path(name):
    return f"{VM}-{P[name]}"


def enum(name, values):
    eid = nid()
    vals = {}
    kids = []
    for key, label in values:
        vid = nid()
        vals[key] = (vid, len(vals))
        kids.append(E("DataEnumValue", key=key, value=label, id=vid))
    ROOTS.append(E("DataEnumCustom", kids, name=name, id=eid))
    ENUMS[name] = (eid, vals)
    return eid


def vprop(kind, name, default, enum_name=None):
    pid = nid()
    P[name] = pid
    if kind == "number":
        VM_PROPS.append((E("ViewModelPropertyNumber", name=name, id=pid),
                         E("ViewModelInstanceNumber", propertyValue=float(default), viewModelPropertyId=pid)))
    elif kind == "bool":
        VM_PROPS.append((E("ViewModelPropertyBoolean", name=name, id=pid),
                         E("ViewModelInstanceBoolean", propertyValue=bool(default), viewModelPropertyId=pid)))
    elif kind == "color":
        VM_PROPS.append((E("ViewModelPropertyColor", name=name, id=pid),
                         E("ViewModelInstanceColor", propertyValue=default, viewModelPropertyId=pid)))
    elif kind == "trigger":
        VM_PROPS.append((E("ViewModelPropertyTrigger", name=name, id=pid),
                         E("ViewModelInstanceTrigger", viewModelPropertyId=pid)))
    elif kind == "enum":
        eid, vals = ENUMS[enum_name]
        VM_PROPS.append((E("ViewModelPropertyEnumCustom", enumId=eid, name=name, id=pid),
                         E("ViewModelInstanceEnum", propertyValue=vals[default][0], viewModelPropertyId=pid)))
    return pid


enum("HairStyle", [("short", "Short"), ("long", "Long"), ("topknot", "Topknot"), ("bald", "Bald"), ("hood", "Hood")])
enum("BeardStyle", [("none", "None"), ("stubble", "Stubble"), ("mustache", "Mustache"), ("full", "Full Beard")])
enum("EarStyle", [("round", "Round"), ("pointed", "Pointed")])

# --- health
vprop("number", "hp", 30)
vprop("number", "maxHp", 30)
vprop("number", "tempHp", 0)
vprop("bool", "showHpRing", True)
# --- appearance
vprop("color", "skinColor", "FFE3AE88")
vprop("color", "hairColor", "FF6B3A1E")
vprop("color", "eyeColor", "FF3C78B4")
vprop("color", "outfitColor", "FF8C2E2E")
vprop("color", "cloakColor", "FF2F4D3C")
vprop("color", "hornColor", "FF3B3036")
vprop("color", "backgroundColor", "FF34506B")
vprop("color", "frameColor", "FFCFA54C")
vprop("enum", "hairStyle", "short", "HairStyle")
vprop("enum", "beardStyle", "none", "BeardStyle")
vprop("enum", "earStyle", "round", "EarStyle")
vprop("bool", "horns", False)
vprop("bool", "tusks", False)
# --- conditions
CONDITIONS = ["blinded", "charmed", "deafened", "frightened", "grappled", "incapacitated",
              "invisible", "paralyzed", "petrified", "poisoned", "prone", "restrained",
              "stunned", "unconscious", "concentrating", "dead"]
for c in CONDITIONS:
    vprop("bool", c, False)
vprop("number", "exhaustion", 0)
# --- one-shot feedback
vprop("trigger", "hit", None)
vprop("trigger", "heal", None)

# ============================================================== converters
_conv_cache = {}


def conv(name, tokens):
    if name in _conv_cache:
        return _conv_cache[name]
    cid = nid()
    ROOTS.append(E("DataConverterFormula", tokens, name=name, id=cid))
    _conv_cache[name] = cid
    return cid


def H():
    """hp / max(1, maxHp) -- the health fraction. Use as the bind source 'hp'."""
    return F.par(F.inp() + F.op("/") + F.fn("max", F.val(1), F.prop(path("maxHp"), 30)))


def hp_le(t):
    return conv(f"health <= {t}", F.step_le(H(), t))


def hp_gt(t):
    return conv(f"health > {t}", F.val(1) + F.op("-") + F.step_le(H(), t))


def hp_band(hi, lo):
    """lo < health <= hi"""
    return conv(f"{lo} < health <= {hi}", F.step_le(H(), hi) + F.op("-") + F.step_le(H(), lo))


def num_ge(t, label="value"):
    return conv(f"{label} >= {t}", F.step_ge(F.inp(), t))


_tonum = [None]


def enum_is(enum_name, key):
    name = f"{enum_name} is {key}"
    if name in _conv_cache:
        return _conv_cache[name]
    if _tonum[0] is None:
        _tonum[0] = nid()
        ROOTS.append(E("DataConverterToNumber", name="Enum to index", id=_tonum[0]))
    k = ENUMS[enum_name][1][key][1]
    eq = conv(f"index == {k}", F.val(1) + F.op("-") +
              F.fn("min", F.val(1), F.fn("pow", F.inp() + F.op("-") + F.val(k), F.val(2))))
    gid = nid()
    ROOTS.append(E("DataConverterGroup", [E("DataConverterGroupItem", converterId=_tonum[0]),
                                          E("DataConverterGroupItem", converterId=eq)], name=name, id=gid))
    _conv_cache[name] = gid
    return gid


def b_color(prop):
    return E("DataBindContext", sourcePathIds=path(prop), propertyKey=37)


def b_opacity(prop, conv_id):
    return E("DataBindContext", sourcePathIds=path(prop), propertyKey=18, converterId=conv_id)


def b_enum(prop, enum_name, key):
    return b_opacity(prop, enum_is(enum_name, key))


def b_hp(conv_id, key=18):
    return E("DataBindContext", sourcePathIds=path("hp"), propertyKey=key, converterId=conv_id)


# ============================================================== paint stacks
TINTS = {}   # tint name -> list of SolidColor ids to key (alpha on/off)
TINT_COLORS = {
    "poisoned": ("0050B83C", "8050B83C"),
    "frightened": ("00A8C4F0", "70A8C4F0"),
    "paralyzed": ("008C5CF0", "708C5CF0"),
    "dead": ("00A0A8A4", "C0A0A8A4"),
    "incapacitated": ("00505060", "50505060"),
}
TINT_COLORS["critical"] = ("009CB0A0", "589CB0A0")   # HP pallor, driven by the Health layer
TINT_COLORS["down"] = ("00A4AEB4", "8CA4AEB4")
TINT_COLORS["petrified"] = ("008F8C86", "EC8F8C86")    # stone: also applied to hair, clothes, eyes


def stone_fill():
    sid = nid()
    TINTS.setdefault("petrified", []).append(sid)
    return E("Fill", [E("SolidColor", colorValue=TINT_COLORS["petrified"][0], name="petrified tint", id=sid)],
             name="Tint petrified")


def stone_stroke(th):
    sid = nid()
    TINTS.setdefault("petrified", []).append(sid)
    return E("Stroke", [E("SolidColor", colorValue=TINT_COLORS["petrified"][0], name="petrified tint", id=sid)],
             thickness=float(th), cap="round", join="round", name="Tint petrified")


def skin_paints(outline=True, olw=OLW):
    """Skin fill bound to skinColor, plus every tint layered on top as extra fills."""
    ps = [fill("FFE3AE88", b_color("skinColor"), name="Skin")]
    for tname, (off, on) in TINT_COLORS.items():
        sid = nid()
        TINTS.setdefault(tname, []).append(sid)
        ps.append(E("Fill", [E("SolidColor", colorValue=off, name=f"{tname} tint", id=sid)],
                    name=f"Tint {tname}"))
    if outline:
        ps.append(stroke(olw, OL, name="Outline"))
    return ps


def bound_paints(prop, default, outline=True, olw=OLW):
    ps = [fill(default, b_color(prop)), stone_fill()]
    if outline:
        ps.append(stroke(olw, OL, name="Outline"))
    return ps


def ink(th=5, alpha="FF"):
    return stroke(th, alpha + OL[2:])


# ============================================================== geometry data
HEAD = [(256, 102), (318, 110), (358, 150), (372, 214), (366, 278), (344, 328), (304, 362), (256, 375),
        (208, 362), (168, 328), (146, 278), (140, 214), (154, 150), (194, 110)]
TORSO = [(18, 560, "s"), (28, 462), (80, 414), (170, 390), (256, 386), (342, 390), (432, 414), (484, 462),
         (494, 560, "s")]
MANTLE_L = [(16, 560, "s"), (28, 464), (72, 420), (150, 394), (204, 383), (224, 398), (214, 452), (194, 560, "s")]
MANTLE_R = mirror(MANTLE_L)
VNECK = [(222, 388, "s"), (256, 440, "s"), (290, 388, "s")]
EAR_PT_L = [(166, 214), (130, 192), (98, 150, "s", 3), (110, 206), (128, 252), (162, 278)]
EAR_PT_R = mirror(EAR_PT_L)
HAIR_SHORT = [(146, 254, "s"), (134, 196), (144, 140), (186, 102), (256, 84), (326, 102), (368, 140), (378, 196),
              (366, 254, "s"), (356, 252, "s"), (350, 208),
              (346, 190, "s", 3), (328, 150, "s", 3), (308, 184, "s", 3), (284, 148, "s", 3), (260, 182, "s", 3),
              (236, 148, "s", 3), (212, 184, "s", 3), (190, 150, "s", 3), (168, 190, "s", 3), (162, 208),
              (156, 252, "s")]
HAIR_LONG_L = [(160, 160), (128, 210), (110, 300), (104, 400), (120, 470, "s", 4), (148, 450), (178, 470, "s", 4),
               (182, 380), (170, 300), (164, 230)]
HAIR_LONG_R = mirror(HAIR_LONG_L)
HAIR_TOP = [(146, 252, "s"), (136, 194), (150, 138), (194, 104), (256, 92), (318, 104), (362, 138), (376, 194),
            (366, 252, "s"), (354, 236), (348, 190), (330, 150), (296, 128), (256, 122), (216, 128), (182, 150),
            (164, 190), (158, 236)]
HOOD_BACK = [(86, 560, "s"), (92, 420), (104, 300), (122, 196), (166, 114), (256, 68), (346, 114), (390, 196),
             (408, 300), (420, 420), (426, 560, "s")]
HOOD_RIM = [(136, 336), (138, 216), (164, 136), (256, 98), (348, 136), (374, 216), (376, 336)]
BEARD = [(144, 252), (148, 306), (170, 354), (210, 392), (256, 406), (302, 392), (342, 354), (364, 306),
         (368, 252), (352, 264), (340, 302), (308, 318, "s", 6), (256, 310), (204, 318, "s", 6), (172, 302),
         (160, 264)]
MUSTACHE = [(256, 300), (228, 294), (204, 304), (190, 326, "s", 4), (220, 318), (256, 314), (292, 318),
            (322, 326, "s", 4), (308, 304), (284, 294)]
HORN_L = [(200, 134), (180, 100), (164, 64), (150, 34, "s", 2), (184, 54), (208, 88), (226, 118)]
HORN_R = mirror(HORN_L)
EYE_L = (212, 242)
EYE_R = (300, 242)


def clip_to(src_id):
    return E("ClippingShape", sourceId=src_id, name="Clip")


# ============================================================== build: background & frame
def build_frame():
    back = []
    bg = shape("Background", ellipse(470, 470), [
        fill("FF34506B", b_color("backgroundColor")),
        E("Fill", [E("RadialGradient", [E("GradientStop", colorValue="00000000", position=0.0),
                                        E("GradientStop", colorValue="00000000", position=0.55),
                                        E("GradientStop", colorValue="99000000", position=1.0)],
                     startX=0.0, startY=-30.0, endX=0.0, endY=235.0, name="Vignette")], name="Vignette"),
    ], x=256, y=256)
    back.append(bg)
    return back


def build_frame_front():
    out = []
    # thick iron ring, inner + outer gilt lines (frameColor)
    out.append(shape("Frame Iron", ellipse(484, 484), [
        stroke(30, "FF221C19"),
        stroke(2, "40FFFFFF"),
    ], x=256, y=256))
    out.append(shape("Frame Inner Trim", ellipse(466, 466), [stroke(5, "FFCFA54C", b_color("frameColor"))],
                     x=256, y=256))
    out.append(shape("Frame Outer Trim", ellipse(500, 500), [stroke(4, "FFCFA54C", b_color("frameColor"))],
                     x=256, y=256))
    # rivets
    rivets = []
    for i in range(8):
        a = i * math.pi / 4 + math.pi / 8
        rivets.append(shape("Rivet", ellipse(10, 10), [fill("FFCFA54C", b_color("frameColor")), ink(2)],
                            x=256 + 242 * math.cos(a), y=256 + 242 * math.sin(a)))
    out.append(node("Rivets", rivets))
    return out


# ============================================================== build: character
def build_body():
    """Shoulders, neck, ears and hair-behind-head. Back to front."""
    out = []
    # hood (back drape)
    hood = shape("Hood Back", smooth(HOOD_BACK), bound_paints("cloakColor", "FF2F4D3C"),
                 binds=b_enum("hairStyle", "HairStyle", "hood"))
    out.append(hood)
    torso = shape("Tunic", smooth(TORSO), bound_paints("outfitColor", "FF8C2E2E"))
    out.append(torso)
    out.append(shape("V Neck", poly(VNECK, closed=True), skin_paints(olw=5)))
    neck = shape("Neck", rect(84, 120, r=12), skin_paints(), x=256, y=342)
    out.append(neck)
    out.append(shape("Neck Shadow", ellipse(120, 54), [fill("48000000")], x=256, y=330,
                     ).add(clip_to(neck.id)))
    for nm, pts in (("Mantle L", MANTLE_L), ("Mantle R", MANTLE_R)):
        out.append(shape(nm, smooth(pts), bound_paints("cloakColor", "FF2F4D3C")))
    # mantle folds
    out.append(shape("Mantle Folds", [smooth([(70, 470), (96, 440), (130, 424)], closed=False),
                                      smooth([(442, 470), (416, 440), (382, 424)], closed=False)],
                     [stroke(4, "60000000")]))
    # clasps + chain
    out.append(shape("Clasp Chain", smooth([(214, 420), (256, 444), (298, 420)], closed=False),
                     [stroke(7, OL), stroke(4, "FFCFA54C", b_color("frameColor"))]))
    for x in (214, 298):
        out.append(shape("Clasp", ellipse(26, 26), [fill("FFCFA54C", b_color("frameColor")), ink(4)], x=x, y=420))
        out.append(shape("Clasp Gem", ellipse(10, 10), [fill("FF9E2236"), ], x=x, y=420))
    # long hair behind head
    long_back = node("Long Hair Back", [
        shape("Lock L", smooth(HAIR_LONG_L), bound_paints("hairColor", "FF6B3A1E")),
        shape("Lock R", smooth(HAIR_LONG_R), bound_paints("hairColor", "FF6B3A1E")),
    ])
    long_back.add(b_enum("hairStyle", "HairStyle", "long"))
    out.append(long_back)
    # ears
    round_ears = node("Ears Round", [
        shape("Ear L", ellipse(42, 64), skin_paints(), x=146, y=246),
        shape("Ear R", ellipse(42, 64), skin_paints(), x=366, y=246),
        shape("Ear Inner", [smooth([(152, 226), (140, 246), (152, 266)], closed=False),
                            smooth([(360, 226), (372, 246), (360, 266)], closed=False)], [ink(4, "90")]),
    ])
    round_ears.add(b_enum("earStyle", "EarStyle", "round"))
    pointed = node("Ears Pointed", [
        shape("Ear L", smooth(EAR_PT_L), skin_paints()),
        shape("Ear R", smooth(EAR_PT_R), skin_paints()),
        shape("Ear Inner", [smooth([(150, 228), (122, 190), (138, 250)], closed=False),
                            smooth(mirror_open([(150, 228), (122, 190), (138, 250)]), closed=False)],
              [ink(4, "90")]),
    ])
    pointed.add(b_enum("earStyle", "EarStyle", "pointed"))
    out.append(round_ears)
    out.append(pointed)
    return out, neck


def eye(cx, cy, side):
    s = 1 if side == "R" else -1
    kids = [
        shape("White", ellipse(60, 42), [fill(WHITE), stone_fill(), ink(3.5)], x=cx, y=cy),
        shape("Iris", ellipse(30, 32), [fill("FF3C78B4", b_color("eyeColor")), stone_fill(), ink(2.5)], x=cx, y=cy + 1),
        shape("Pupil", ellipse(13, 13), [fill("FF0E0A08")], x=cx, y=cy + 1),
        shape("Glint", ellipse(8, 8), [fill("FFFFFFFF")], x=cx + 5, y=cy - 6),
        shape("Lid", smooth([(cx - 32, cy + 2), (cx - 17, cy - 18), (cx + 4, cy - 22), (cx + 23, cy - 15),
                             (cx + 33, cy)], closed=False), [ink(6.5)]),
    ]
    return node(f"Eye {side}", kids)


def brow(side, pts, name="Brow"):
    if side == "R":
        pts = mirror_open(pts)
    return shape(f"{name} {side}", smooth(pts, closed=False),
                 [stroke(17, OL), stroke(10, "FF6B3A1E", b_color("hairColor")), stone_stroke(10)])


BROW_NEUTRAL = [(182, 214), (206, 200), (240, 206)]
BROW_PAIN = [(182, 210), (208, 206), (240, 194)]
BROW_DOWN = [(184, 216), (210, 212), (238, 216)]


def build_face(head):
    """Face features, back to front, all in absolute coords."""
    out = []
    out.append(shape("Head Shade", ellipse(150, 340), [E("Fill", [solid("26000000"), E("Feather", strength=26.0)],
                                                         fillRule="clockwise", name="Shade")],
                     x=392, y=250).add(clip_to(head.id)))
    out.append(shape("Cheeks", [ellipse(40, 22, x=-66.0, y=0.0), ellipse(40, 22, x=66.0, y=0.0)],
                     [fill("2EE0405A")], x=256, y=292))
    # beards
    out.append(shape("Stubble", smooth(BEARD), [fill("FF6B3A1E", b_color("hairColor"))], opacity=0.2)
               .add(b_enum("beardStyle", "BeardStyle", "stubble")))
    out.append(shape("Full Beard", smooth(BEARD), bound_paints("hairColor", "FF6B3A1E"))
               .add(b_enum("beardStyle", "BeardStyle", "full")))
    # mouths by health
    out.append(build_mouths())
    mus = node("Mustache", [shape("Mustache", smooth(MUSTACHE), bound_paints("hairColor", "FF6B3A1E", olw=5))])
    mus.add(E("DataBindContext", sourcePathIds=path("beardStyle"), propertyKey=18, converterId=mustache_conv()))
    out.append(mus)
    tusks = node("Tusks", [shape("Tusk L", poly([(226, 340), (231, 306), (244, 338)], closed=True),
                                 [fill("FFF4EEDC"), ink(3.5)]),
                           shape("Tusk R", poly(mirror([(226, 340), (231, 306), (244, 338)]), closed=True),
                                 [fill("FFF4EEDC"), ink(3.5)])], opacity=0.0)
    out.append(tusks)
    # nose
    out.append(shape("Nose", [smooth([(240, 290), (256, 300), (272, 290)], closed=False)], [ink(5.5)]))
    out.append(shape("Nose Bridge", smooth([(264, 248), (270, 270), (268, 284)], closed=False), [ink(4, "70")]))
    return out, tusks


def mustache_conv():
    # opacity 1 when beardStyle index is 2 (mustache) or 3 (full):  clamp((idx - 1.5) * 1000)
    name = "beard has mustache"
    if name in _conv_cache:
        return _conv_cache[name]
    if _tonum[0] is None:
        _tonum[0] = nid()
        ROOTS.append(E("DataConverterToNumber", name="Enum to index", id=_tonum[0]))
    f = conv("index >= 2", F.step_ge(F.inp(), 1.5))
    gid = nid()
    ROOTS.append(E("DataConverterGroup", [E("DataConverterGroupItem", converterId=_tonum[0]),
                                          E("DataConverterGroupItem", converterId=f)], name=name, id=gid))
    _conv_cache[name] = gid
    return gid


def build_mouths():
    m = node("Mouth")
    smile = shape("Smile", smooth([(226, 318), (256, 333), (286, 318)], closed=False), [ink(6.5)])
    flat = shape("Flat", smooth([(232, 326), (256, 324), (280, 327)], closed=False), [ink(6.5)])
    grim = shape("Grimace", smooth([(224, 334), (240, 322), (256, 326), (272, 321), (288, 334)], closed=False),
                 [ink(6.5)])
    grit = node("Gritted", [
        shape("Teeth", rect(70, 26, r=9), [fill(WHITE), ink(5)], x=256, y=328),
        shape("Teeth Lines", [poly([(222, 328), (290, 328)]), poly([(240, 316), (240, 340)]),
                              poly([(256, 316), (256, 340)]), poly([(272, 316), (272, 340)])], [ink(3)]),
    ])
    gasp = node("Gasp", [
        shape("Open", ellipse(38, 32), [fill("FF3A1212"), ink(5)], x=256, y=330),
        shape("Tongue", ellipse(22, 10), [fill("FFC0505A")], x=256, y=340),
    ])
    slack = shape("Slack", ellipse(26, 12), [fill("FF3A1212"), ink(4)], x=256, y=330)
    smile.add(b_hp(hp_gt(0.75)))
    flat.add(b_hp(hp_band(0.75, 0.5)))
    grim.add(b_hp(hp_band(0.5, 0.3)))
    grit.add(b_hp(hp_band(0.3, 0.1)))
    gasp.add(b_hp(hp_band(0.1, 0.0)))
    slack.add(b_hp(hp_le(0.0)))
    m.add(smile, flat, grim, grit, gasp, slack)
    return m


def build_eyes():
    out = []
    # damage under the eyes: black eye ring (stage 3+)
    out.append(shape("Black Eye", ellipse(78, 60), [fill("806A2A6E"), ], x=EYE_R[0] + 2, y=EYE_R[1] + 6)
               .add(b_hp(hp_le(0.3))))
    eyes = node("Eyes", [eye(*EYE_L, "L"), eye(*EYE_R, "R")])
    out.append(eyes)
    # brows by health
    b = node("Brows")
    neutral = node("Brows Neutral", [brow("L", BROW_NEUTRAL), brow("R", BROW_NEUTRAL)])
    pain = node("Brows Pained", [brow("L", BROW_PAIN), brow("R", BROW_PAIN)])
    down = node("Brows Down", [brow("L", BROW_DOWN), brow("R", BROW_DOWN)])
    neutral.add(b_hp(hp_gt(0.5)))
    pain.add(b_hp(hp_band(0.5, 0.0)))
    down.add(b_hp(hp_le(0.0)))
    b.add(neutral, pain, down)
    out.append(b)
    return out


def eye_patch(cx, cy, w=70, h=52, name="Patch"):
    return shape(name, ellipse(w, h), skin_paints(outline=False), x=cx, y=cy)


def closed_eye(cx, cy, side, name="Closed"):
    return node(f"{name} {side}", [
        eye_patch(cx, cy),
        shape("Line", smooth([(cx - 26, cy - 2), (cx, cy + 8), (cx + 26, cy - 2)], closed=False), [ink(6)]),
    ])


def build_eye_damage():
    out = []
    # stage 3: right eye puffy, half shut
    puffy = shape("Puffy Lid", smooth([(268, 244), (272, 222), (300, 212), (328, 222), (332, 244), (300, 238)]),
                  skin_paints(olw=5) + [fill("707A2C78")])
    puffy.add(b_hp(hp_band(0.3, 0.1)))
    out.append(puffy)
    shut = node("Swollen Shut", [
        shape("Swelling", ellipse(72, 54), skin_paints(olw=5) + [fill("A07A2C78")], x=EYE_R[0], y=EYE_R[1]),
        shape("Slit", smooth([(276, 246), (300, 250), (324, 244)], closed=False), [ink(5)]),
    ])
    shut.add(b_hp(hp_band(0.1, 0.0)))
    out.append(shut)
    down = node("Eyes Closed (Down)", [closed_eye(*EYE_L, "L"), closed_eye(*EYE_R, "R")])
    down.add(b_hp(hp_le(0.0)))
    out.append(down)
    return out


def blood(pts, th=None, name="Blood"):
    if th:
        return shape(name, smooth(pts, closed=False), [stroke(th + 3, "FF5A0A10"), stroke(th, "FFC8172B")])
    return shape(name, smooth(pts), [fill("FFC8172B"), stroke(2.5, "FF5A0A10")])


def drip(x, y0, y1, w, name="Drip"):
    """Tapered blood run ending in a droplet."""
    m = y0 + (y1 - y0) * 0.55
    pts = [(x - w * 0.5, y0, "s", 2), (x + w * 0.5, y0, "s", 2), (x + w * 0.3, m), (x + w * 0.62, y1 - w * 0.6),
           (x, y1), (x - w * 0.62, y1 - w * 0.6), (x - w * 0.3, m)]
    return shape(name, smooth(pts), [fill("FFC8172B"), stroke(2.5, "FF5A0A10"),
                                    ])


def cut(x0, y0, x1, y1, name="Cut", th=7):
    return shape(name, poly([(x0, y0), (x1, y1)]), [stroke(th + 3, "FF5A0A10"), stroke(th - 3, "FFD8283C")])


def build_wounds():
    """Accumulating damage art, one Node per stage."""
    out = []
    s1 = node("Stage 1 Scuffed", [
        shape("Scratches", [poly([(174, 278), (194, 262)]), poly([(180, 290), (202, 272)]),
                            poly([(190, 300), (208, 286)])], [stroke(5, "FF9A1A24")]),
        shape("Bruise", ellipse(42, 24), [fill("50703070")], x=326, y=282),
        shape("Dirt", ellipse(50, 18), [fill("40402A18")], x=226, y=192, rotation=-0.25),
    ])
    s1.add(b_hp(hp_le(0.75)))
    s2 = node("Stage 2 Bloodied", [
        drip(244, 294, 322, 9, name="Nose Drip L"),
        drip(267, 294, 312, 7, name="Nose Drip R"),
        cut(306, 186, 342, 198, name="Brow Gash"),
        drip(344, 198, 248, 9, name="Temple Drip"),
    ])
    s2.add(b_hp(hp_le(0.5)))
    s3 = node("Stage 3 Battered", [
        drip(168, 170, 238, 9, name="Left Temple Drip"),
        shape("Split Lip", ellipse(10, 9), [fill("FFC8172B"), stroke(2, "FF5A0A10")], x=276, y=334),
        drip(278, 336, 356, 6, name="Lip Drip"),
        shape("Sweat", smooth([(362, 150, "s"), (370, 168), (362, 177), (354, 168)]), [fill("E0D8F0FF"), ink(2.5)]),
        blood([(290, 428), (306, 424), (310, 436), (298, 442), (286, 438)], name="Tunic Spatter"),
        blood([(318, 448), (326, 446), (326, 454), (318, 455)], name="Tunic Spatter 2"),
    ])
    s3.add(b_hp(hp_le(0.3)))
    s4 = node("Stage 4 Critical", [
        cut(244, 264, 272, 256, name="Bridge Cut", th=6),
        cut(300, 300, 334, 290, name="Cheek Gash", th=8),
        drip(318, 298, 344, 10, name="Cheek Drip"),
        drip(200, 262, 300, 8, name="Under-eye Drip"),
        drip(256, 368, 396, 10, name="Chin Drip"),
        blood([(140, 430), (166, 420), (180, 440), (160, 456), (140, 450)], name="Shoulder Blood"),
        blood([(372, 470), (392, 462), (400, 480), (380, 488)], name="Mantle Blood"),
    ])
    s4.add(b_hp(hp_le(0.1)))
    out += [s1, s2, s3, s4]
    return out


def build_hair_front():
    out = []
    short = node("Hair Short", [
        shape("Hair", smooth(HAIR_SHORT, tension=0.9), bound_paints("hairColor", "FF6B3A1E")),
        shape("Shine", smooth([(186, 130), (222, 108), (262, 102)], closed=False), [stroke(7, "40FFFFFF")]),
    ])
    short.add(b_enum("hairStyle", "HairStyle", "short"))
    long_ = node("Hair Long Top", [
        shape("Hair", smooth(HAIR_SHORT, tension=0.9), bound_paints("hairColor", "FF6B3A1E")),
        shape("Shine", smooth([(186, 130), (222, 108), (262, 102)], closed=False), [stroke(7, "40FFFFFF")]),
    ])
    long_.add(b_enum("hairStyle", "HairStyle", "long"))
    top = node("Hair Topknot", [
        shape("Bun", ellipse(78, 62), bound_paints("hairColor", "FF6B3A1E"), x=256, y=80),
        shape("Hair", smooth(HAIR_TOP), bound_paints("hairColor", "FF6B3A1E")),
        shape("Tie", rect(44, 14, r=5), [fill("FF5A3A22"), ink(4)], x=256, y=106),
        shape("Comb Lines", [smooth([(200, 120), (230, 104)], closed=False),
                             smooth([(312, 120), (282, 104)], closed=False)], [stroke(4, "50000000")]),
    ])
    top.add(b_enum("hairStyle", "HairStyle", "topknot"))
    bald = shape("Scalp Shine", ellipse(56, 22), [fill("3CFFFFFF")], x=220, y=138, rotation=-0.35)
    bald.add(b_enum("hairStyle", "HairStyle", "bald"))
    hood_rim = node("Hood Rim", [shape("Rim", smooth(HOOD_RIM, closed=False),
                                       [stroke(42, OL, cap="butt"),
                                        stroke(30, "FF2F4D3C", b_color("cloakColor"), cap="butt"),
                                        stroke(30, "26000000", cap="butt")])])
    hood_rim.add(b_enum("hairStyle", "HairStyle", "hood"))
    out += [short, long_, top, bald, hood_rim]
    return out


def build_horns():
    h = node("Horns", [
        shape("Horn L", smooth(HORN_L), bound_paints("hornColor", "FF3B3036", olw=5)),
        shape("Horn R", smooth(HORN_R), bound_paints("hornColor", "FF3B3036", olw=5)),
        shape("Ridges", [poly([(188, 112), (210, 102)]), poly([(176, 88), (196, 78)]),
                         poly(mirror_open([(188, 112), (210, 102)])), poly(mirror_open([(176, 88), (196, 78)]))],
              [stroke(3.5, "70000000")]),
    ], opacity=0.0)
    return h


# ============================================================== conditions
exec(compile(open(os.path.join(HERE, "conditions.py")).read(), "conditions.py", "exec"))


# ============================================================== main assembly
def build():
    style_id = nid()
    art = E("Artboard", [E("LayoutComponentStyle", name="Artboard Style", id=style_id)], name="Token", width=512,
            height=512, viewModelId=VM, viewModelInstanceId=VMI, styleId=style_id)
    sm_id = nid()
    art.attrs["defaultStateMachineId"] = sm_id

    clip_shape = shape("Disc Clip", ellipse(462, 462), [], x=256, y=256)

    body, neck = build_body()
    head = shape("Head", smooth(HEAD), skin_paints())
    face, tusks = build_face(head)
    horns = build_horns()

    build_conditions()
    head_inner = node("Head Offset", x=-256.0, y=-350.0)
    head_inner.add(head, face, build_eyes(), build_eye_damage(), build_wounds(), SLOTS["face"],
                   build_hair_front(), horns, SLOTS["head_top"])
    head_pivot = node("Head Pivot", [head_inner], x=256.0, y=350.0)
    head_pivot.add(b_hp(conv("down tilt", F.step_le(H(), 0.0) + F.op("*") + F.val(0.16)), key=15))

    char = node("Character", SLOTS["back"] + body + [head_pivot] + SLOTS["body_front"])
    breath = node("Breath", [char])
    visibility = node("Visibility", [breath])
    hit_shake = node("Hit Shake", [visibility])
    fright_shake = node("Fright Shake", [hit_shake])
    pose_inner = node("Pose Offset", [fright_shake], x=-256.0, y=-330.0)
    pose = node("Pose", [pose_inner], x=256.0, y=330.0)
    hit, heal, motes = build_feedback()
    prone_shadow = shape("Prone Ground", ellipse(420, 50), [fill("50000000")], x=290, y=396, opacity=0.0)
    char_clip = node("Character Clip", [prone_shadow, pose] + SLOTS["overlay"] + [heal, hit])
    char_clip.add(clip_to(clip_shape.id))
    hp_ring, temp_hp = build_health_ring()

    art.add(build_frame(), clip_shape, char_clip, build_frame_front(), hp_ring, SLOTS["frame"], temp_hp)

    STATE["art"] = art
    STATE["sm_id"] = sm_id
    STATE["nodes"] = dict(breath=breath, pose=pose, char=char, horns=horns, tusks=tusks, head_pivot=head_pivot,
                          visibility=visibility, hit_shake=hit_shake, fright_shake=fright_shake, hit=hit,
                          heal=heal, motes=motes, hp_ring=hp_ring, prone_shadow=prone_shadow)
    return art


STATE = {}


def build_state_machine():
    art = STATE["art"]
    n = STATE["nodes"]
    anims = []
    layers = []

    def anim(name, keys, duration=1, loop=False):
        a = E("LinearAnimation", name=name, duration=duration, loopValue="loop" if loop else None, id=nid())
        for obj, prop_name, frames, kind in keys:
            kp = E("KeyedProperty", property=prop_name)
            for fr, v in frames:
                if kind == "d":
                    kp.add(E("KeyFrameDouble", value=float(v), frame=fr, interpolationType="linear"))
                elif kind == "c":
                    kp.add(E("KeyFrameColor", value=v, frame=fr, interpolationType="linear"))
            a.add(E("KeyedObject", [kp], objectId=obj))
        anims.append(a)
        return a

    def bool_cond(prop, value):
        return E("TransitionViewModelCondition", [
            E("TransitionPropertyViewModelComparator", [E("BindablePropertyBoolean", [
                E("DataBindContext", sourcePathIds=path(prop), propertyKey=634)])]),
            E("TransitionValueBooleanComparator", value=value)], opValue="equal")

    def toggle_layer(name, prop, off_keys, on_keys, on_duration=1, on_loop=False, ms=250):
        a_off = anim(f"{name} Off", off_keys)
        a_on = anim(f"{name} On", on_keys, duration=on_duration, loop=on_loop)
        s_off, s_on = nid(), nid()
        layer = E("StateMachineLayer", [
            E("AnyState", x=160.0, y=-120.0), E("ExitState", x=400.0, y=-120.0),
            E("EntryState", [E("StateTransition", stateToId=s_off)], x=0.0, y=0.0),
            E("AnimationState", [E("StateTransition", [bool_cond(prop, True)], stateToId=s_on, duration=ms)],
              animationId=a_off.id, id=s_off, x=200.0, y=0.0),
            E("AnimationState", [E("StateTransition", [bool_cond(prop, False)], stateToId=s_off, duration=ms)],
              animationId=a_on.id, id=s_on, x=420.0, y=100.0),
        ], name=name, id=nid())
        layers.append(layer)

    # idle breathing
    breath_keys = [(fr, -2.5 * (1 - math.cos(2 * math.pi * fr / 240)) / 2) for fr in range(0, 241, 30)]
    idle = anim("Idle Breath", [(n["breath"].id, "y", breath_keys, "d")], duration=240, loop=True)
    s_idle = nid()
    layers.append(E("StateMachineLayer", [
        E("AnyState", x=160.0, y=-120.0), E("ExitState", x=400.0, y=-120.0),
        E("EntryState", [E("StateTransition", stateToId=s_idle)], x=0.0, y=0.0),
        E("AnimationState", animationId=idle.id, id=s_idle, x=200.0, y=0.0)], name="Idle", id=nid()))

    toggle_layer("Horns", "horns", [(n["horns"].id, "opacity", [(0, 0)], "d")],
                 [(n["horns"].id, "opacity", [(0, 1)], "d")], ms=0)
    toggle_layer("Tusks", "tusks", [(n["tusks"].id, "opacity", [(0, 0)], "d")],
                 [(n["tusks"].id, "opacity", [(0, 1)], "d")], ms=0)

    # ---- health pallor (state machine reads the computed health fraction)
    frac = conv("health fraction", F.clamp01(H()))

    def hp_cond(opv, v):
        return E("TransitionViewModelCondition", [
            E("TransitionPropertyViewModelComparator", [E("BindablePropertyNumber", [
                E("DataBindContext", sourcePathIds=path("hp"), propertyKey=636, converterId=frac)])]),
            E("TransitionValueNumberComparator", value=float(v))], opValue=opv)

    def keys_for(on_tints):
        ks = []
        for t in ("critical", "down"):
            off, on = TINT_COLORS[t]
            for sid in TINTS[t]:
                ks.append((sid, "colorValue", [(0, on if t in on_tints else off)], "c"))
        return ks

    a_n, a_c, a_d = anim("Health Normal", keys_for(())), anim("Health Critical", keys_for(("critical",))), \
        anim("Health Down", keys_for(("down",)))
    sn, sc, sd = nid(), nid(), nid()
    T = lambda to, *conds: E("StateTransition", list(conds), stateToId=to, duration=400)
    layers.append(E("StateMachineLayer", [
        E("AnyState", x=160.0, y=-120.0), E("ExitState", x=400.0, y=-120.0),
        E("EntryState", [E("StateTransition", stateToId=sn)], x=0.0, y=0.0),
        E("AnimationState", [T(sd, hp_cond("lessThanOrEqual", 0)), T(sc, hp_cond("lessThanOrEqual", 0.1))],
          animationId=a_n.id, id=sn, x=200.0, y=0.0),
        E("AnimationState", [T(sd, hp_cond("lessThanOrEqual", 0)), T(sn, hp_cond("greaterThan", 0.1))],
          animationId=a_c.id, id=sc, x=420.0, y=120.0),
        E("AnimationState", [T(sn, hp_cond("greaterThan", 0.1)), T(sc, hp_cond("greaterThan", 0))],
          animationId=a_d.id, id=sd, x=640.0, y=0.0),
    ], name="Health Pallor", id=nid()))

    STATE["keys_for_tint"] = lambda t, on: [(sid, "colorValue", [(0, TINT_COLORS[t][1 if on else 0])], "c")
                                            for sid in TINTS[t]]

    # ---- conditions: one two-state layer each
    def op_keys(ids, v):
        return [(i, "opacity", [(0, v)], "d") for i in ids]

    EXTRA = {
        "invisible": ([(n["visibility"].id, "opacity", [(0, 1.0)], "d")],
                      [(n["visibility"].id, "opacity", [(0, 0.28)], "d")]),
        "prone": ([(n["pose"].id, "rotation", [(0, 0.0)], "d"), (n["pose"].id, "x", [(0, 256.0)], "d"),
                   (n["pose"].id, "y", [(0, 330.0)], "d"), (n["prone_shadow"].id, "opacity", [(0, 0.0)], "d")],
                  [(n["pose"].id, "rotation", [(0, -1.45)], "d"), (n["pose"].id, "x", [(0, 360.0)], "d"),
                   (n["pose"].id, "y", [(0, 300.0)], "d"), (n["prone_shadow"].id, "opacity", [(0, 1.0)], "d")]),
        "frightened": ([(n["fright_shake"].id, "x", [(0, 0.0)], "d")],
                       [(n["fright_shake"].id, "x", [(f, (2.5 if (f // 2) % 2 else -2.5) * (1 if f % 60 < 40 else 0.3))
                                                     for f in range(0, 61, 2)], "d")]),
    }
    for c in CONDITIONS:
        info = COND.get(c, {"groups": [], "loops": [], "dur": 1})
        gids = [g.id for g in info["groups"]]
        off = op_keys(gids, 0.0)
        on = op_keys(gids, 1.0)
        if c in TINTS:
            off += STATE["keys_for_tint"](c, False)
            on += STATE["keys_for_tint"](c, True)
        if c in EXTRA:
            off += EXTRA[c][0]
            on += EXTRA[c][1]
        on += info["loops"]
        dur = max(info["dur"], 60 if c == "frightened" else 1)
        toggle_layer(c[0].upper() + c[1:], c, off, on, on_duration=dur, on_loop=dur > 1,
                     ms=450 if c in ("prone", "invisible", "petrified") else 250)

    toggle_layer("HP Ring", "showHpRing", [(n["hp_ring"].id, "opacity", [(0, 0.0)], "d")],
                 [(n["hp_ring"].id, "opacity", [(0, 1.0)], "d")], ms=0)

    # ---- hit / heal one-shots
    def trig_cond(prop):
        return E("TransitionViewModelCondition", [
            E("TransitionPropertyViewModelComparator", [E("BindablePropertyTrigger", [
                E("DataBindContext", sourcePathIds=path(prop), propertyKey=686)])]),
            E("TransitionValueTriggerComparator")])

    mote_keys_idle = [(m.id, "y", [(0, 420.0)], "d") for m, _ in n["motes"]]
    a_idle = anim("Feedback Idle", [(n["hit"].id, "opacity", [(0, 0.0)], "d"),
                                    (n["hit_shake"].id, "x", [(0, 0.0)], "d"),
                                    (n["heal"].id, "opacity", [(0, 0.0)], "d")] + mote_keys_idle)
    a_hit = anim("Hit", [(n["hit"].id, "opacity", [(0, 0.0), (3, 0.55), (36, 0.0)], "d"),
                         (n["hit_shake"].id, "x", [(0, 0), (3, -12), (6, 10), (9, -8), (12, 6), (15, -3), (18, 0)],
                          "d")], duration=36)
    a_heal = anim("Heal", [(n["heal"].id, "opacity", [(0, 0.0), (8, 1.0), (40, 0.8), (60, 0.0)], "d")] +
                  [(m.id, "y", [(0, 420.0), (6 * i, 420.0), (6 * i + 40, 200.0), (60, 180.0)], "d")
                   for m, i in n["motes"]], duration=60)
    si, sh, sl = nid(), nid(), nid()
    done = dict(enableExitTime=True, exitTimeIsPercetange=True, exitTime=100.0)
    layers.append(E("StateMachineLayer", [
        E("AnyState", x=160.0, y=-120.0), E("ExitState", x=400.0, y=-120.0),
        E("EntryState", [E("StateTransition", stateToId=si)], x=0.0, y=0.0),
        E("AnimationState", [E("StateTransition", [trig_cond("hit")], stateToId=sh),
                             E("StateTransition", [trig_cond("heal")], stateToId=sl)],
          animationId=a_idle.id, id=si, x=200.0, y=0.0),
        E("AnimationState", [E("StateTransition", stateToId=si, **done),
                             E("StateTransition", [trig_cond("heal")], stateToId=sl)],
          animationId=a_hit.id, id=sh, reset=True, x=420.0, y=-100.0),
        E("AnimationState", [E("StateTransition", stateToId=si, **done),
                             E("StateTransition", [trig_cond("hit")], stateToId=sh)],
          animationId=a_heal.id, id=sl, reset=True, x=420.0, y=120.0),
    ], name="Hit and Heal", id=nid()))

    STATE["anim"] = anim
    STATE["toggle_layer"] = toggle_layer
    STATE["bool_cond"] = bool_cond
    STATE["layers"] = layers
    STATE["anims"] = anims


def finish():
    art = STATE["art"]
    sm = E("StateMachine", STATE["layers"], name="Token Machine", id=STATE["sm_id"])
    art.tail = [sm] + STATE["anims"]
    vm = E("ViewModel", [p for p, _ in VM_PROPS] +
           [E("ViewModelInstance", [v for _, v in VM_PROPS], exports=True, name="Default", id=VMI)]
           + PRESETS, name="CharacterToken", defaultInstanceId=VMI, id=VM)
    doc = E("Rive", [art] + ROOTS + [vm], version="1", kind="fragment")
    with open(OUT, "w") as f:
        f.write("<!-- GENERATED by tools/build_token.py; edit the generator, not this file. -->\n")
        f.write(doc.render() + "\n")


PRESET_DEFS = {
    "Human Fighter": {},
    "Elf Wizard": dict(skinColor="FFF2D2B6", hairColor="FFE8D9A0", eyeColor="FF3FA36A", outfitColor="FF3A4C9A",
                       cloakColor="FF4B2F6E", earStyle="pointed", hairStyle="long", backgroundColor="FF2A2F55"),
    "Dwarf Cleric": dict(skinColor="FFD49A76", hairColor="FFB4472A", eyeColor="FF6A4A2A", outfitColor="FF8E8E9A",
                         cloakColor="FFB08A2E", hairStyle="bald", beardStyle="full", backgroundColor="FF5A3A2A"),
    "Half-Orc Barbarian": dict(skinColor="FF8FA866", hairColor="FF1E1A1A", eyeColor="FFC8A020", outfitColor="FF6A4A30",
                               cloakColor="FF5A5A5A", hairStyle="topknot", tusks=True, beardStyle="stubble",
                               backgroundColor="FF4A2222"),
    "Tiefling Warlock": dict(skinColor="FFC0505A", hairColor="FF2A1A3A", eyeColor="FFFFD040", outfitColor="FF2A2A3A",
                             cloakColor="FF6A1A2E", hairStyle="long", horns=True, hornColor="FF2A2228",
                             backgroundColor="FF2A1A30"),
    "Halfling Rogue": dict(skinColor="FFE8B894", hairColor="FF4A2E1A", eyeColor="FF5A8A3A", outfitColor="FF5A4A3A",
                           cloakColor="FF2E3A2A", hairStyle="hood", earStyle="pointed", backgroundColor="FF1E2A24"),
    "Dragonborn Paladin": dict(skinColor="FF4C7AB0", hairColor="FF2C3E58", eyeColor="FFF0C030", outfitColor="FFB8B8C8",
                               cloakColor="FF2A4A8A", hairStyle="bald", horns=True, hornColor="FFE8DCC0",
                               backgroundColor="FF2A3A4A"),
}
PRESETS = []


def build_presets():
    for pname, over in PRESET_DEFS.items():
        if not over:
            continue
        vals = []
        for (pel, iel) in VM_PROPS:
            name = pel.attrs["name"]
            v = E(iel.tag, **{k: iel.attrs[k] for k in iel.attrs})
            if name in over:
                if iel.tag == "ViewModelInstanceEnum":
                    ename = {"hairStyle": "HairStyle", "beardStyle": "BeardStyle", "earStyle": "EarStyle"}[name]
                    v.attrs["propertyValue"] = ENUMS[ename][1][over[name]][0]
                else:
                    v.attrs["propertyValue"] = over[name]
            vals.append(v)
        PRESETS.append(E("ViewModelInstance", vals, exports=True, name=pname, id=nid()))

if __name__ == "__main__":
    build()
    build_state_machine()
    build_presets()
    finish()
    print("wrote", OUT)
