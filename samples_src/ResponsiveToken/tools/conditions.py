# Condition overlays. Executed inside build_token.py's namespace (see the exec there),
# so it shares the helpers, the view model and the TINTS registry.
#
# Each condition gets one or more groups (opacity 0 at rest) placed into a depth SLOT, plus
# optional looping keys. build_condition_layers() then gives every condition a two-state layer.

COND = {}
SLOTS = {k: [] for k in ("back", "face", "head_top", "body_front", "overlay", "frame")}


def cond_group(cname, slot, kids, **kw):
    g = node(f"{cname.title()} FX", kids, opacity=0.0, **kw)
    COND.setdefault(cname, {"groups": [], "loops": [], "dur": 1})["groups"].append(g)
    SLOTS[slot].append(g)
    return g


def loop_keys(cname, keys, dur):
    c = COND.setdefault(cname, {"groups": [], "loops": [], "dur": 1})
    c["loops"] += keys
    c["dur"] = max(c["dur"], dur)


def osc(amp, period, dur, phase=0.0, base=0.0, step=None):
    step = step or max(1, period // 8)
    return [(f, base + amp * math.sin(2 * math.pi * (f / period + phase))) for f in range(0, dur + 1, step)]


def mouth_patch():
    return shape("Mouth Patch", ellipse(84, 40), skin_paints(outline=False), x=256, y=328)


def brow_patch(side):
    cx = 211 if side == "L" else 301
    return shape(f"Brow Patch {side}", ellipse(74, 34), skin_paints(outline=False), x=cx, y=206)


def wide_eye(cx, cy, pupil=8, w=64, h=52):
    return node("Wide Eye", [eye_patch(cx, cy, 76, 60),
                             shape("White", ellipse(w, h), [fill(WHITE), stone_fill(), ink(4)], x=cx, y=cy),
                             shape("Pupil", ellipse(pupil, pupil), [fill("FF0E0A08")], x=cx, y=cy)])


def zig(x, y, s):
    return poly([(x, y), (x + s, y), (x, y + s), (x + s, y + s)])


def lid_shape(cx, cy, low):
    return smooth([(cx - 34, cy + low, "s"), (cx - 18, cy - 20), (cx + 4, cy - 24), (cx + 24, cy - 17),
                   (cx + 35, cy + low, "s")])


def build_conditions():
    L, R = EYE_L, EYE_R

    # ---------------------------------------------------------------- blinded
    band = shape("Blindfold", smooth([(134, 216), (256, 204), (378, 216), (380, 268, "s", 6), (256, 260),
                                      (132, 268, "s", 6)]), [fill("FF2E2B3A"), ink(OLW)])
    folds = shape("Folds", [smooth([(150, 236), (256, 228), (362, 236)], closed=False),
                            smooth([(150, 250), (256, 244), (362, 250)], closed=False)], [stroke(3, "50FFFFFF")])
    knot = shape("Knot", ellipse(28, 26), [fill("FF2E2B3A"), ink(5)], x=382, y=240)
    tails = shape("Tails", [smooth([(386, 248), (404, 280), (400, 314, "s", 3), (390, 284), (378, 256)]),
                            smooth([(392, 244), (424, 266), (434, 298, "s", 3), (414, 272), (384, 252)])],
                  [fill("FF2E2B3A"), ink(5)])
    cond_group("blinded", "head_top", [tails, band, folds, knot])

    # ---------------------------------------------------------------- charmed
    eyes = []
    for (cx, cy) in (L, R):
        eyes += [eye_patch(cx, cy),
                 shape("Heart Eye", heart(cx, cy + 2, 58), [fill("FFFF4F8B"), ink(4.5)]),
                 shape("Glint", ellipse(9, 9), [fill("FFFFFFFF")], x=cx - 10, y=cy - 6)]
    blush = shape("Blush", [ellipse(50, 26, x=-66.0, y=0.0), ellipse(50, 26, x=66.0, y=0.0)],
                  [fill("A0FF6A9A")], x=256, y=292)
    cond_group("charmed", "face", [blush] + eyes)
    hearts = []
    for i, (hx, hy, sz) in enumerate(((180, 104, 30), (256, 70, 40), (330, 98, 28))):
        hn = node("Float Heart", [shape("Heart", heart(0, 0, sz), [fill("FFFF4F8B"), ink(4)])],
                  x=float(hx), y=float(hy))
        hearts.append(hn)
        loop_keys("charmed", [(hn.id, "y", osc(7, 60, 120, i / 3.0, base=hy, step=10), "d")], 120)
    cond_group("charmed", "head_top", hearts)

    # ---------------------------------------------------------------- deafened
    wrap = shape("Head Wrap", smooth([(146, 266), (142, 170), (190, 112), (256, 96), (322, 112), (370, 170),
                                      (366, 266)], closed=False),
                 [stroke(34, OL, cap="butt"), stroke(26, "FFE6D8B8", cap="butt"),
                  E("Stroke", [solid("50806040"), E("DashPath", [E("Dash", length=3.0), E("Dash", length=14.0)])],
                    thickness=26.0, cap="butt", name="Wrap Lines")])
    pads = []
    for x in (144, 368):
        pads.append(shape("Ear Pad", rect(52, 74, r=18), [fill("FFE6D8B8"), ink(OLW)], x=x, y=248))
        pads.append(shape("Pad Lines", [poly([(x - 18, 228), (x + 18, 252)]), poly([(x - 18, 252), (x + 18, 228)]),
                                        poly([(x - 18, 254), (x + 18, 274)])], [stroke(3, "70806040")]))
    cond_group("deafened", "head_top", [wrap] + pads)

    # ---------------------------------------------------------------- frightened
    fr = [brow_patch("L"), brow_patch("R"), wide_eye(*L), wide_eye(*R),
          brow("L", [(180, 192), (206, 184), (238, 172)], name="Scared Brow"),
          brow("R", [(180, 192), (206, 184), (238, 172)], name="Scared Brow"),
          mouth_patch(),
          shape("Wobble Mouth", smooth([(226, 332), (236, 322), (246, 332), (256, 322), (266, 332), (276, 322),
                                        (286, 330)], closed=False), [ink(5.5)]),
          shape("Sweat L", smooth([(170, 186, "s"), (178, 204), (170, 213), (162, 204)]), [fill("E8D8F0FF"), ink(3)]),
          shape("Sweat R", smooth([(350, 176, "s"), (359, 196), (350, 206), (341, 196)]), [fill("E8D8F0FF"), ink(3)])]
    cond_group("frightened", "face", fr)

    # ---------------------------------------------------------------- grappled
    hands = []
    for side in ("L", "R"):
        def m(pts):
            return pts if side == "L" else mirror_open(pts)
        fingers = [m([(52, 470), (70, 412), (100, 372)]), m([(74, 468), (110, 404), (142, 362)]),
                   m([(100, 474), (148, 414), (180, 380)]), m([(124, 484), (180, 440), (206, 412)])]
        thumb = m([(60, 500), (40, 452), (52, 420)])
        hand = [shape("Palm", smooth(m([(30, 560), (24, 500), (56, 452), (130, 450), (158, 500), (140, 560)])),
                      [fill("FF6E8A4C"), ink(OLW)])]
        hand.append(shape("Fingers", [smooth(f, closed=False) for f in fingers + [thumb]],
                          [stroke(40, OL), stroke(28, "FF6E8A4C")]))
        hand.append(shape("Claws", [smooth([(f[-1][0] - 7, f[-1][1] + 2), (f[-1][0] + (6 if side == "L" else -6),
                                              f[-1][1] - 14, "s"), (f[-1][0] + 7, f[-1][1] + 4)])
                                    for f in fingers],
                          [fill("FFEDE6D0"), ink(3)]))
        hand.append(shape("Knuckles", [ellipse(9, 9, x=float(f[1][0]), y=float(f[1][1])) for f in fingers],
                          [fill("60000000")]))
        hands.append(node(f"Hand {side}", hand))
    cond_group("grappled", "body_front", hands)

    # ---------------------------------------------------------------- incapacitated
    inc = [shape("Heavy Lid", lid_shape(cx, cy, 4), skin_paints(outline=False) + [ink(6.5)]) for (cx, cy) in (L, R)]
    inc += [mouth_patch(), shape("Dull Mouth", poly([(234, 328), (278, 326)]), [ink(6)])]
    cond_group("incapacitated", "face", inc)
    dots = [shape("Bubble", smooth([(330, 92), (360, 70), (400, 72), (424, 92), (410, 116), (364, 120)]),
                  [fill("F0E8E4DC"), ink(5)]),
            shape("Bubble Tail", ellipse(14, 14), [fill("F0E8E4DC"), ink(4)], x=338, y=134),
            shape("Dots", [ellipse(10, 10, x=-22.0, y=0.0), ellipse(10, 10, x=0.0, y=0.0),
                           ellipse(10, 10, x=22.0, y=0.0)], [fill("FF4A4450")], x=376, y=96)]
    cond_group("incapacitated", "head_top", dots)

    # ---------------------------------------------------------------- invisible (sparkles; fade is keyed later)
    sp = []
    for i, (x, y, s) in enumerate(((150, 170, 34), (370, 150, 28), (340, 330, 30), (176, 360, 26), (256, 80, 30))):
        st = node("Sparkle", [shape("Star", E("Star", width=float(s), height=float(s), points=4, innerRadius=0.25,
                                               name="Path"), [fill("FFE8F8FF"), ink(2.5)])], x=float(x), y=float(y))
        sp.append(st)
        ks = [(f, 0.4 + 0.6 * abs(math.sin(math.pi * (f / 60.0 + i / 5.0)))) for f in range(0, 121, 10)]
        loop_keys("invisible", [(st.id, "scaleX", ks, "d"), (st.id, "scaleY", ks, "d")], 120)
    cond_group("invisible", "overlay", sp)

    # ---------------------------------------------------------------- paralyzed
    par = [wide_eye(*L, pupil=7, w=60, h=44), wide_eye(*R, pupil=7, w=60, h=44),
           mouth_patch(), shape("Locked Mouth", rect(46, 8, r=3), [fill("FF3A1212"), ink(3)], x=256, y=328)]
    cond_group("paralyzed", "face", par)
    bolts = []
    for i, pts in enumerate(([(118, 120), (140, 160), (122, 176), (146, 220)],
                             [(394, 120), (372, 160), (390, 176), (366, 220)],
                             [(104, 290), (128, 310), (110, 330), (132, 360)],
                             [(408, 290), (384, 310), (402, 330), (380, 360)])):
        b = shape("Bolt", poly(pts), [E("Stroke", [solid("FFB48CFF"), E("Feather", strength=8.0)], thickness=14.0,
                                        cap="round", join="round", name="Glow"),
                                      stroke(5, "FFF4ECFF", join="miter")])
        bolts.append(b)
        loop_keys("paralyzed", [(b.id, "opacity", [(0, 1), (5 + i * 3, 0.15), (10 + i * 3, 1), (40, 0.3),
                                                   (48, 1), (60, 1)], "d")], 60)
    cond_group("paralyzed", "head_top", bolts)

    # ---------------------------------------------------------------- petrified (the stone tint does most of it)
    crack_paint = [stroke(4.5, "D0383430", join="miter")]
    cond_group("petrified", "head_top", [shape("Cracks", [
        poly([(232, 112), (222, 140), (236, 160), (226, 190)]), poly([(334, 250), (352, 272), (344, 300)]),
        poly([(176, 300), (194, 320), (186, 344)]), poly([(300, 152), (312, 176), (304, 196)])], crack_paint)])
    cond_group("petrified", "body_front", [shape("Body Cracks", [
        poly([(110, 430), (130, 460), (118, 490)]), poly([(400, 440), (380, 470), (396, 500)])], crack_paint)])

    # ---------------------------------------------------------------- poisoned
    po = [shape("Sick Bags", [smooth([(186, 266), (212, 278), (238, 266)], closed=False),
                              smooth([(274, 266), (300, 278), (326, 266)], closed=False)], [stroke(7, "B0508A30")]),
          mouth_patch(),
          shape("Queasy Mouth", smooth([(226, 330), (242, 320), (258, 330), (272, 322), (286, 328)], closed=False),
                [stroke(9, "FF2E5A18"), stroke(4.5, "FF7CC23C")]),
          shape("Drool", smooth([(278, 328, "s", 2), (288, 326, "s", 2), (288, 346), (292, 360), (283, 368),
                                 (276, 358), (280, 344)]), [fill("FF8ED24A"), ink(3)])]
    cond_group("poisoned", "face", po)
    bub = []
    for i, (x, s) in enumerate(((334, 24), (366, 18), (350, 14))):
        bn = node("Bubble", [shape("B", ellipse(s, s), [fill("8090E050"), stroke(3.5, "FF3E7A20")])],
                  x=float(x), y=330.0)
        bub.append(bn)
        off = i * 30
        loop_keys("poisoned", [
            (bn.id, "y", [(f, 340 - ((f + off) % 90) * 2.2) for f in range(0, 91, 5)], "d"),
            (bn.id, "opacity", [(f, 1.0 - ((f + off) % 90) / 90.0) for f in range(0, 91, 5)], "d")], 90)
    cond_group("poisoned", "head_top", bub)

    # ---------------------------------------------------------------- restrained
    ropes = shape("Ropes", [smooth([(20, 436), (130, 418), (256, 428), (382, 418), (492, 436)], closed=False),
                            smooth([(20, 482), (140, 466), (256, 476), (372, 466), (492, 482)], closed=False),
                            smooth([(70, 406), (170, 444), (256, 500)], closed=False),
                            smooth([(442, 406), (342, 444), (256, 500)], closed=False)],
                  [stroke(26, OL), stroke(18, "FFD8AE6E"),
                   E("Stroke", [solid("FF7A5230"), E("DashPath", [E("Dash", length=4.0), E("Dash", length=9.0)])],
                     thickness=18.0, cap="butt", name="Twist")])
    cond_group("restrained", "body_front", [ropes, shape("Rope Knot", ellipse(34, 28), [fill("FFD8AE6E"), ink(5)],
                                                         x=256, y=486)])

    # ---------------------------------------------------------------- stunned
    st = []
    for (cx, cy) in (L, R):
        pts = []
        for k in range(40):
            t = k / 39.0
            a = t * 2.6 * 2 * math.pi
            r = 2 + 20 * t
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a) * 0.8))
        st += [eye_patch(cx, cy, 76, 58), shape("Swirl White", ellipse(60, 46), [fill(WHITE), ink(4)], x=cx, y=cy),
               shape("Spiral", smooth(pts, closed=False), [ink(4.5)])]
    st += [mouth_patch(), shape("Dazed Mouth", smooth([(232, 326), (248, 332), (264, 324), (280, 330)],
                                                       closed=False), [ink(5.5)])]
    cond_group("stunned", "face", st)
    stars = []
    for i in range(3):
        sn = node("Orbit Star", [shape("Star", E("Star", width=50.0, height=50.0, points=5, innerRadius=0.48,
                                                  cornerRadius=3.0, name="Path"), [fill("FFFFD84A"), ink(5)])])
        stars.append(sn)
        xs, ys, ss = [], [], []
        for f in range(0, 91, 6):
            a = 2 * math.pi * (f / 90.0 + i / 3.0)
            xs.append((f, 256 + 128 * math.cos(a)))
            ys.append((f, 92 + 24 * math.sin(a)))
            ss.append((f, 0.85 + 0.25 * math.sin(a)))
        loop_keys("stunned", [(sn.id, "x", xs, "d"), (sn.id, "y", ys, "d"), (sn.id, "scaleX", ss, "d"),
                              (sn.id, "scaleY", ss, "d")], 90)
    cond_group("stunned", "head_top", stars)

    # ---------------------------------------------------------------- unconscious
    un = [closed_eye(*L, "L", name="Asleep"), closed_eye(*R, "R", name="Asleep"),
          mouth_patch(), shape("Snore", ellipse(16, 13), [fill("FF3A1212"), ink(3.5)], x=262, y=330)]
    cond_group("unconscious", "face", un)
    zs = []
    for i, s in enumerate((26, 36, 48)):
        zn = node("Z", [shape("Z", zig(-s / 2, -s / 2, s), [stroke(s * 0.3 + 7, OL, join="miter"),
                                                            stroke(s * 0.3, "FFE8F0FF", join="miter")])])
        zs.append(zn)
        off = i * 40
        frames = range(0, 121, 6)
        loop_keys("unconscious", [
            (zn.id, "x", [(f, 330 + ((f + off) % 120) * 0.7) for f in frames], "d"),
            (zn.id, "y", [(f, 160 - ((f + off) % 120) * 0.9) for f in frames], "d"),
            (zn.id, "opacity", [(f, min(1.0, 3 * (1 - ((f + off) % 120) / 120.0))) for f in frames], "d")], 120)
    cond_group("unconscious", "head_top", zs)

    # ---------------------------------------------------------------- concentrating (behind the head)
    halo = node("Halo", x=256.0, y=214.0)
    halo.add(shape("Glow", ellipse(330, 330), [E("Stroke", [solid("905CE0FF"), E("Feather", strength=12.0)],
                                                  thickness=12.0, name="Glow")]))
    ring = node("Rune Ring")
    ring.add(shape("Ring", ellipse(330, 330), [stroke(10, OL), stroke(5, "FFA8F2FF")]))
    ring.add(shape("Runes", ellipse(300, 300), [E("Stroke", [solid("FF5CE0FF"), E("DashPath", [
        E("Dash", length=14.0), E("Dash", length=10.0), E("Dash", length=4.0), E("Dash", length=10.0)])],
        thickness=10.0, cap="butt", name="Runes")]))
    for k in range(6):
        a = k * math.pi / 3
        ring.add(shape("Gem", E("Polygon", width=18.0, height=28.0, points=4, name="Path"),
                       [fill("FFE8FDFF"), ink(3)], rotation=a + math.pi / 2, x=165 * math.cos(a), y=165 * math.sin(a)))
    halo.add(ring)
    loop_keys("concentrating", [(ring.id, "rotation", [(0, 0.0), (600, 2 * math.pi)], "d")], 600)
    cond_group("concentrating", "back", [halo])

    # ---------------------------------------------------------------- dead
    dd = []
    for (cx, cy) in (L, R):
        dd += [eye_patch(cx, cy), shape("X", [poly([(cx - 16, cy - 14), (cx + 16, cy + 14)]),
                                             poly([(cx - 16, cy + 14), (cx + 16, cy - 14)])], [ink(8)])]
    dd += [mouth_patch(), shape("Dead Mouth", smooth([(230, 330), (246, 326), (262, 332), (282, 326)], closed=False),
                                [ink(5)]),
           shape("Tongue", smooth([(262, 330), (276, 330), (276, 344), (269, 350), (262, 344)]),
                 [fill("FFD06A78"), ink(3)])]
    cond_group("dead", "face", dd)
    shroud = shape("Shroud", ellipse(470, 470), [E("Fill", [E("RadialGradient", [
        E("GradientStop", colorValue="00101418", position=0.0), E("GradientStop", colorValue="30101418", position=0.5),
        E("GradientStop", colorValue="C0101418", position=1.0)], startX=0.0, startY=-40.0, endX=0.0, endY=235.0,
        name="G")], name="Shroud")], x=256, y=256)
    cond_group("dead", "overlay", [shroud])

    # ---------------------------------------------------------------- exhaustion (number driven, no layer)
    def exb(conv_id):
        return E("DataBindContext", sourcePathIds=path("exhaustion"), propertyKey=18, converterId=conv_id)
    ex = node("Exhaustion")
    bags = shape("Eye Bags", [smooth([(186, 266), (212, 278), (238, 266)], closed=False),
                              smooth([(274, 266), (300, 278), (326, 266)], closed=False)], [stroke(8, "B04A2850")])
    bags.add(exb(conv("exhaustion / 3", F.clamp01(F.inp() + F.op("/") + F.val(3)))))
    lids = node("Droop Lids", [shape("Droop", lid_shape(cx, cy, -2), skin_paints(outline=False) + [ink(6)])
                               for (cx, cy) in (L, R)])
    lids.add(exb(num_ge(2.5, "exhaustion")))
    sweat = shape("Tired Sweat", smooth([(356, 170, "s"), (365, 190), (356, 200), (347, 190)]),
                  [fill("E8D8F0FF"), ink(3)])
    sweat.add(exb(num_ge(1.5, "exhaustion")))
    ex.add(bags, lids, sweat)
    SLOTS["face"].append(ex)
    pips = node("Exhaustion Pips")
    pips.add(exb(num_ge(0.5, "exhaustion")))
    for i in range(6):
        a = math.pi / 2 + (2.5 - i) * 0.15
        x, y = 256 + 242 * math.cos(a), 256 + 242 * math.sin(a)
        pips.add(shape("Pip Socket", ellipse(22, 22), [fill("FF0E0B0A"),
                                                       stroke(3, "FFCFA54C", b_color("frameColor"))], x=x, y=y))
        lit = shape("Pip Lit", ellipse(14, 14), [fill("FFFF8A2A")], x=x, y=y)
        lit.add(exb(num_ge(i + 0.5, "exhaustion")))
        pips.add(lit)
    SLOTS["frame"].append(pips)


def build_health_ring():
    frac = conv("health fraction", F.clamp01(H()))
    out = [shape("HP Track", ellipse(484, 484), [stroke(14, "FF0E0B0A")], x=256, y=256)]
    for name, color, cid in (("HP Green", "FF58D05A", hp_gt(0.5)), ("HP Amber", "FFF2B53A", hp_band(0.5, 0.3)),
                             ("HP Red", "FFE8343A", hp_le(0.3))):
        tr = E("TrimPath", [E("DataBindContext", sourcePathIds=path("hp"), propertyKey=115, converterId=frac)],
               start=0.0, end=1.0, offset=0.0, modeValue="sequential", name="Trim")
        s = shape(name, ellipse(484, 484), [E("Stroke", [solid(color), tr], thickness=9.0, cap="round",
                                                name="Arc")], x=256, y=256)
        s.add(b_hp(cid))
        out.append(s)
    ring = node("HP Ring", out)
    th = node("Temp HP", [
        shape("Shield Glow", ellipse(500, 500), [E("Stroke", [solid("FF6FD2FF"), E("Feather", strength=10.0)],
                                                   thickness=12.0, name="Glow"), stroke(4, "FFBFEFFF")], x=256, y=256),
        shape("Shield Badge", smooth([(410, 62, "s", 3), (452, 62, "s", 3), (452, 96), (431, 126), (410, 96)]),
              [fill("FF2F8FD8"), ink(5)]),
        shape("Badge Plus", [poly([(431, 76), (431, 106)]), poly([(417, 91), (445, 91)])],
              [stroke(6, "FFFFFFFF", cap="round")]),
    ])
    th.add(E("DataBindContext", sourcePathIds=path("tempHp"), propertyKey=18, converterId=num_ge(0.5, "tempHp")))
    return ring, th


def build_feedback():
    """Hit / heal one-shot overlays (inside the disc, above the character)."""
    hit = shape("Hit Flash", ellipse(470, 470), [fill("FFE0202A")], x=256, y=256, opacity=0.0)
    heal = node("Heal Glow", opacity=0.0)
    heal.add(shape("Heal Wash", ellipse(470, 470), [E("Fill", [E("RadialGradient", [
        E("GradientStop", colorValue="0080FF9A", position=0.0), E("GradientStop", colorValue="2080FF9A", position=0.6),
        E("GradientStop", colorValue="C060F090", position=1.0)], startX=0.0, startY=0.0, endX=0.0, endY=235.0,
        name="G")], name="F")], x=256, y=256))
    motes = []
    for i, x in enumerate((150, 210, 290, 360, 250)):
        mn = node("Mote", [shape("Plus", [poly([(0, -9), (0, 9)]), poly([(-9, 0), (9, 0)])],
                                 [stroke(9, "FF1E6A2E"), stroke(5, "FFD8FFD8")])], x=float(x), y=400.0)
        heal.add(mn)
        motes.append((mn, i))
    return hit, heal, motes
