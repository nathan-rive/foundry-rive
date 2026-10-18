"""Generates scene.rml for the Door sample: a door in a stone archway, as a
journal set piece the GM shows to players.

    py -I tools/gen_scene.py        (from the project folder)

- Door (360x480): seen from the front. A plank door with iron straps and a
  ring knocker in an arched stone doorway. Opening, it swings inward on its
  left hinge, and the light beyond (`color`) spills onto the floor. Locked,
  a padlock hangs on the hasp; unlocked, it drops away.

View model Door: state (enum closed/open/locked), color (the light beyond),
knock (trigger: the knocker raps three times), rattle (trigger: the door
shakes in its frame). No scripts.
"""

import math
import random
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "scene.rml"

VM, P_STATE, P_COLOR, P_KNOCK, P_RATTLE, VM_INST = "0:40", "0:41", "0:42", "0:43", "0:44", "0:45"
ENUM, E_CLOSED, E_OPEN, E_LOCKED = "0:50", "0:51", "0:52", "0:53"
KEY_X, KEY_Y, KEY_ROT, KEY_SX, KEY_SY, KEY_OPACITY = 13, 14, 15, 16, 17, 18
KEY_COLOR, KEY_STOP_COLOR, KEY_ENUM, KEY_TRIGGER = 37, 38, 637, 686
TAU = math.tau

W, H = 360, 480
LEFT, RIGHT, SPRING, SILL = 70, 290, 200, 430     # the doorway: sides, where the arch springs, the floor
CXD = (LEFT + RIGHT) / 2
RADIUS = (RIGHT - LEFT) / 2
LIGHT = "FFFFB45A"
IRON, IRON_LIGHT, IRON_DARK = "FF2E2B28", "FF5A564F", "FF141210"
STONE, STONE_LIGHT, STONE_EDGE = "FF4A4540", "FF6E675D", "FF2A2724"


class Ids:
    def __init__(self, start=100):
        self.n = start

    def __call__(self):
        self.n += 1
        return f"0:{self.n}"


ids = Ids()


def bind(prop, key):
    return f'<DataBindContext sourcePathIds="{VM}-{prop}" propertyKey="{key}"/>'


def solid(color, prop=None):
    inner = bind(prop, KEY_COLOR) if prop else ""
    return f'<SolidColor colorValue="{color}" name="Color">{inner}</SolidColor>'


def gradient(kind, start, end, stops):
    out = []
    for stop in stops:
        pos, color, prop = (*stop, None)[:3]
        inner = bind(prop, KEY_STOP_COLOR) if prop else ""
        out.append(f'<GradientStop colorValue="{color}" position="{pos}">{inner}</GradientStop>')
    tag = "LinearGradient" if kind == "linear" else "RadialGradient"
    return f'<{tag} startX="{start[0]}" startY="{start[1]}" endX="{end[0]}" endY="{end[1]}" name="Gradient">' + "".join(out) + f"</{tag}>"


def rect(x, y, w, h, fill, stroke=None, radius=0, name="Box", sid=None, thickness=2, extra="", blend=""):
    sid = f' id="{sid}"' if sid else ""
    stroke_xml = f'<Stroke thickness="{thickness}" name="Edge">{solid(stroke)}</Stroke>' if stroke else ""
    blend = f' blendModeValue="{blend}"' if blend else ""
    fill_xml = "" if fill is None else f'<Fill name="Fill"{blend}>{fill if fill.startswith("<") else solid(fill)}</Fill>'
    return (f'<Shape x="{x}" y="{y}" name="{name}"{sid}{extra}><Rectangle width="{w}" height="{h}" cornerRadiusTL="{radius}" name="Path"/>'
            f'{stroke_xml}{fill_xml}</Shape>')


def ellipse(x, y, w, h, fill, name="Dot", sid=None, extra=""):
    sid = f' id="{sid}"' if sid else ""
    return f'<Shape x="{x}" y="{y}" name="{name}"{sid}{extra}><Ellipse width="{w}" height="{h}" name="Path"/><Fill name="Fill">{fill}</Fill></Shape>'


def points(pts, closed=True):
    verts = "".join(f'<StraightVertex x="{x:.2f}" y="{y:.2f}" name="V"/>' for x, y in pts)
    return f'<PointsPath isClosed="{str(closed).lower()}" isClockwise="true" name="Path">{verts}</PointsPath>'


def arch_outline(grow=0, steps=28):
    """The doorway's outline: up the left side, over the arch, down the right."""
    r = RADIUS + grow
    pts = [(LEFT - grow, SILL)]
    for i in range(steps + 1):
        a = math.pi - math.pi * i / steps
        pts.append((CXD + r * math.cos(a), SPRING - r * math.sin(a)))
    pts.append((RIGHT + grow, SILL))
    return pts


def indent(text, n):
    return "\n".join(" " * n + line for line in text.splitlines())


class Anim:
    def __init__(self, name, duration, loop=False):
        self.name, self.duration, self.loop = name, duration, loop
        self.id = ids()
        self.keys = {}

    def key(self, obj, prop, frames):
        self.keys.setdefault(obj, {})[prop] = frames

    def hold(self, obj, prop, value):
        self.key(obj, prop, [(0, value)])

    def curve(self, obj, prop, fn, step=2):
        frames = list(range(0, self.duration, step)) + [self.duration]
        self.key(obj, prop, [(f, fn(f / self.duration)) for f in frames])

    def xml(self):
        loop = "loop" if self.loop else "oneShot"
        out = [f'<LinearAnimation loopValue="{loop}" duration="{self.duration}" name="{self.name}" id="{self.id}">']
        for obj, props in self.keys.items():
            out.append(f'    <KeyedObject objectId="{obj}">')
            for prop, frames in props.items():
                out.append(f'        <KeyedProperty propertyKey="{prop}">')
                for frame, value in frames:
                    out.append(f'            <KeyFrameDouble value="{value:.4f}" frame="{frame}" interpolationType="linear"/>')
                out.append("        </KeyedProperty>")
            out.append("    </KeyedObject>")
        out.append("</LinearAnimation>")
        return "\n".join(out)


def ease(t):
    return 0.5 - 0.5 * math.cos(math.pi * min(1, max(0, t)))


# --- state machine helpers ------------------------------------------------

def is_state(value, op="equal"):
    return f'''<TransitionViewModelCondition opValue="{op}">
    <TransitionPropertyViewModelComparator>
        <BindablePropertyEnum>{bind(P_STATE, KEY_ENUM)}</BindablePropertyEnum>
    </TransitionPropertyViewModelComparator>
    <TransitionValueEnumComparator value="{value}"/>
</TransitionViewModelCondition>'''


def two_state_layer(name, value, rest, going, on, coming):
    """rest <-> on (while state == value), through one-shots; loads straight into the saved state."""
    s = {k: ids() for k in ("rest", "going", "on", "coming")}

    def st(key, anim, x, *trans, reset=False):
        r = ' reset="true"' if reset else ""
        return f'<AnimationState x="{x}" y="0" animationId="{anim.id}"{r} id="{s[key]}">' + "".join(trans) + "</AnimationState>"

    go = lambda to, cond="": f'<StateTransition stateToId="{s[to]}">{cond}</StateTransition>'
    exit_ = lambda to: f'<StateTransition stateToId="{s[to]}" enableExitTime="true" exitTimeIsPercetange="true" exitTime="100"/>'
    return f'''<StateMachineLayer name="{name}">
    <EntryState x="-200" y="0">{go("on", is_state(value))}{go("rest")}</EntryState>
    {st("rest", rest, 0, go("going", is_state(value)))}
    {st("going", going, 200, exit_("on"), reset=True)}
    {st("on", on, 400, go("coming", is_state(value, "notEqual")))}
    {st("coming", coming, 600, exit_("rest"), reset=True)}
</StateMachineLayer>'''


def trigger_layer(name, prop, idle, play):
    s_idle, s_play = ids(), ids()
    return f'''<StateMachineLayer name="{name}">
    <AnyState x="0" y="-120">
        <StateTransition stateToId="{s_play}">
            <TransitionViewModelCondition>
                <TransitionPropertyViewModelComparator>
                    <BindablePropertyTrigger>{bind(prop, KEY_TRIGGER)}</BindablePropertyTrigger>
                </TransitionPropertyViewModelComparator>
                <TransitionValueTriggerComparator/>
            </TransitionViewModelCondition>
        </StateTransition>
    </AnyState>
    <EntryState x="-200" y="0"><StateTransition stateToId="{s_idle}"/></EntryState>
    <AnimationState x="0" y="0" animationId="{idle.id}" id="{s_idle}"/>
    <AnimationState x="200" y="0" animationId="{play.id}" reset="true" id="{s_play}">
        <StateTransition stateToId="{s_idle}" enableExitTime="true" exitTimeIsPercetange="true" exitTime="100"/>
    </AnimationState>
</StateMachineLayer>'''


# --- the drawing ------------------------------------------------------------

def wall():
    """Courses of stone blocks behind everything, and a flagstone floor."""
    rng = random.Random(11)
    out = []
    y, row = 0, 0
    while y < SILL:
        h = 34
        x = -rng.uniform(0, 40) if row % 2 else -rng.uniform(30, 60)
        while x < W:
            w = rng.uniform(54, 78)
            shade = rng.choice(["FF4E4943", "FF48433D", "FF524C45", "FF45403A"])
            out.append(rect(round(x + w / 2, 1), y + h / 2, round(w - 3, 1), h - 3, shade, radius=3, name="Block"))
            x += w
        y += h
        row += 1
    floor = []
    for i, (y0, h) in enumerate([(SILL, 22), (SILL + 22, 28)]):
        x = -20 if i else -45
        while x < W:
            w = 70 + 10 * i
            floor.append(rect(x + w / 2, y0 + h / 2, w - 3, h - 3, "FF5E574E" if i else "FF544D45", radius=2, name="Flag"))
            x += w
    return "\n".join(floor) + "\n" + rect(W / 2, (SILL + H) / 2, W, H - SILL, "FF2A2622", name="Floor Joints") + "\n" + \
        "\n".join(out) + "\n" + rect(W / 2, SILL / 2, W, SILL, "FF24211E", name="Mortar")


def frame():
    """The stone surround: voussoirs round the arch and blocks up the jambs."""
    joints = []
    for i in range(1, 9):
        a = math.pi - math.pi * i / 9
        x0, y0 = CXD + RADIUS * math.cos(a), SPRING - RADIUS * math.sin(a)
        x1, y1 = CXD + (RADIUS + 30) * math.cos(a), SPRING - (RADIUS + 30) * math.sin(a)
        joints.append(f'<Shape name="Joint">{points([(x0, y0), (x1, y1)], False)}<Stroke thickness="2.5" name="Line">{solid(STONE_EDGE)}</Stroke></Shape>')
    for y in (SPRING + 58, SPRING + 132, SPRING + 200):
        for x0 in (LEFT - 30, RIGHT):
            joints.append(rect(x0 + 15, y, 30, 2.5, STONE_EDGE, name="Joint"))
    band = arch_outline(15)
    return f"""<Node name="Frame">
{indent(chr(10).join(joints), 4)}
    <Shape name="Inner Edge">{points(arch_outline(1), False)}<Stroke thickness="3" name="Line">{solid("FF1A1816")}</Stroke></Shape>
    <Shape name="Surround">{points(band, False)}<Stroke thickness="30" cap="butt" name="Stone">{gradient("linear", (0, 80), (0, SILL), [(0, "FF7A7368"), (1, "FF5E574E")])}</Stroke></Shape>
    <Shape name="Outer Edge">{points(arch_outline(31), False)}<Stroke thickness="4" name="Line">{solid("FF1E1C1A")}</Stroke></Shape>
</Node>"""


def door_face():
    """The door's front, in doorway coordinates: planks, straps, knocker plate, keyhole."""
    planks = []
    n = 5
    pw = (RIGHT - LEFT) / n
    for i in range(n):
        x = LEFT + pw * (i + 0.5)
        c = ["FF6A4527", "FF5F3D22", "FF684426", "FF5C3B20", "FF654225"][i]
        grain = "\n".join(rect(round(x + dx, 1), 260 + dy, 1.5, 120 + abs(dy), "26000000", name="Grain")
                          for dx, dy in ((-10, -60), (6, 30), (12, -110)))
        planks.append(grain)
        planks.append(rect(round(x, 1), (60 + SILL) / 2, round(pw - 2, 1), SILL - 60, c, "FF2A1A0E", 0, "Plank", thickness=2))

    def strap(y):
        rivets = "\n".join(ellipse(x, y, 5, 5, solid(IRON_LIGHT), "Rivet") for x in range(LEFT + 22, RIGHT - 10, 36))
        return f"""{rivets}
{rect((LEFT + RIGHT - 16) / 2 + 2, y, RIGHT - LEFT - 20, 16, IRON, IRON_DARK, 3, "Strap", thickness=1.5)}
{ellipse(RIGHT - 24, y, 22, 22, solid(IRON), "Strap End")}"""

    return f"""{strap(178)}
{strap(372)}
<Node x="{RIGHT - 34}" y="300" name="Lock Plate">
    {ellipse(0, -4, 6, 6, solid("FF0A0908"), "Keyhole")}
    {rect(0, 4, 3, 10, "FF0A0908", name="Keyhole Slot")}
    {rect(0, 0, 22, 44, gradient("linear", (0, -22), (0, 22), [(0, "FF4A4640"), (1, "FF26231F")]), IRON_DARK, 4, "Plate", thickness=1.5)}
</Node>
{chr(10).join(planks)}"""


def door():
    closed, opening, open_, closing = Anim("Shut", 1), Anim("Opening", 80), Anim("Open", 1), Anim("Closing", 40)
    unlocked, locking, locked, unlocking = Anim("Unlocked", 1), Anim("Locking", 40), Anim("Locked", 1), Anim("Unlocking", 48)
    still_k, knock = Anim("Knock Idle", 1), Anim("Knock", 96)
    still_r, rattle = Anim("Rattle Idle", 1), Anim("Rattle", 54)

    swing, shade, spill, glow = ids(), ids(), ids(), ids()
    knock_shake, rattle_shake = ids(), ids()
    ring_knock, ring_rattle = ids(), ids()
    padlock, padlock_swing = ids(), ids()
    dust = ids()

    # --- the door swinging inward on its left hinge: its width shrinks to the hinge.
    shut_w = 0.16

    def door_keys(anim, fn):
        if anim.duration == 1:
            v = fn(0)
            anim.hold(swing, KEY_SX, 1 - (1 - shut_w) * v)
            anim.hold(shade, KEY_OPACITY, 0.65 * v)
            anim.hold(spill, KEY_OPACITY, v)
            anim.hold(glow, KEY_OPACITY, 0.55 + 0.45 * v)
        else:
            anim.curve(swing, KEY_SX, lambda t: 1 - (1 - shut_w) * fn(t))
            anim.curve(shade, KEY_OPACITY, lambda t: 0.65 * min(1, max(0, fn(t))))
            anim.curve(spill, KEY_OPACITY, lambda t: min(1, max(0, fn(t))) ** 0.7)
            anim.curve(glow, KEY_OPACITY, lambda t: 0.55 + 0.45 * min(1, max(0, fn(t))))

    def creak_open(t):
        """A first small give, a pause, then the swing, slowing as it goes."""
        if t < 0.12:
            return 0.06 * ease(t / 0.12)
        if t < 0.24:
            return 0.06
        u = (t - 0.24) / 0.76
        return 0.06 + 0.94 * (1 - (1 - u) ** 2.4)

    def slam(t):
        if t < 0.7:
            return 1 - (t / 0.7) ** 2
        u = (t - 0.7) / 0.3
        return 0.05 * math.sin(math.pi * u) * (1 - u)

    door_keys(closed, lambda t: 0)
    door_keys(opening, creak_open)
    door_keys(open_, lambda t: 1)
    door_keys(closing, slam)

    # --- the padlock: swings onto the hasp, or drops to the floor.
    def lock_keys(anim, y, opacity, rot):
        anim.key(padlock, KEY_Y, y)
        anim.key(padlock, KEY_OPACITY, opacity)
        anim.key(padlock_swing, KEY_ROT, rot)

    lock_y = 300
    lock_keys(unlocked, [(0, lock_y)], [(0, 0)], [(0, 0)])
    lock_keys(locked, [(0, lock_y)], [(0, 1)], [(0, 0)])
    lock_keys(locking, [(0, lock_y - 14), (10, lock_y), (40, lock_y)], [(0, 0), (8, 1), (40, 1)],
              [(f, 0.5 * math.exp(-f / 12) * math.cos(f / 4.5)) for f in range(0, 41, 2)])
    fall = lambda f: lock_y + (0 if f < 8 else min(SILL + 26 - lock_y, 0.12 * (f - 8) ** 2))
    lock_keys(unlocking, [(f, fall(f)) for f in range(0, 49, 2)], [(0, 1), (30, 1), (48, 0)],
              [(0, 0), (8, -0.3), (48, -1.4)])

    # --- knock: the ring lifts and falls three times; the door jolts on each blow.
    still_k.hold(ring_knock, KEY_SY, 1)
    still_k.hold(ring_knock, KEY_Y, 0)
    still_k.hold(knock_shake, KEY_X, 0)
    still_k.hold(dust, KEY_OPACITY, 0)
    hits = [14, 44, 74]
    sy, y_, sx = [(0, 1)], [(0, 0)], [(0, 0)]
    for h in hits:
        sy += [(h - 10, 0.35), (h, 1)]
        y_ += [(h - 10, -14), (h, 0)]
        sx += [(h, 0), (h + 2, 1.6), (h + 5, -1.0), (h + 9, 0.4), (h + 13, 0)]
    sy.append((96, 1))
    y_.append((96, 0))
    sx.append((96, 0))
    knock.key(ring_knock, KEY_SY, sy)
    knock.key(ring_knock, KEY_Y, y_)
    knock.key(knock_shake, KEY_X, sx)
    knock.key(dust, KEY_OPACITY, [(0, 1), (96, 1)])
    rng = random.Random(4)
    motes = []
    for i in range(14):
        mid = ids()
        h = hits[i % 3]
        x0 = rng.uniform(LEFT + 20, RIGHT - 20)
        y0 = SPRING - math.sqrt(max(0, RADIUS ** 2 - (x0 - CXD) ** 2)) + 6
        fall_px = rng.uniform(40, 90)
        motes.append(ellipse(round(x0, 1), round(y0, 1), 3, 3, solid("C0C8BCA8"), "Mote", mid, ' opacity="0"'))
        knock.key(mid, KEY_OPACITY, [(0, 0), (h, 0), (h + 2, 0.9), (h + 30, 0)] + ([(96, 0)] if h + 30 < 96 else []))
        knock.key(mid, KEY_Y, [(0, y0), (h, y0), (min(96, h + 30), y0 + fall_px)] + ([(96, y0 + fall_px)] if h + 30 < 96 else []))
        knock.key(mid, KEY_X, [(0, x0), (h, x0), (min(96, h + 30), x0 + rng.uniform(-8, 8))])

    # --- rattle: the door shakes against its lock; the ring and the padlock swing.
    still_r.hold(rattle_shake, KEY_X, 0)
    still_r.hold(rattle_shake, KEY_Y, 0)
    still_r.hold(ring_rattle, KEY_ROT, 0)
    rattle.curve(rattle_shake, KEY_X, lambda t: 2.2 * math.sin(TAU * t * 9) * (1 - t) ** 0.6, 1)
    rattle.curve(rattle_shake, KEY_Y, lambda t: -0.8 * abs(math.sin(TAU * t * 4.5)) * (1 - t), 1)
    rattle.curve(ring_rattle, KEY_ROT, lambda t: 0.35 * math.sin(TAU * t * 3) * (1 - t), 1)

    ring = f"""<Node x="{CXD}" y="262" name="Knocker Rattle" id="{ring_rattle}">
    <Node name="Knocker Lift" id="{ring_knock}">
        <Shape y="28" name="Ring"><Ellipse width="44" height="48" name="Path"/><Stroke thickness="7" name="Iron">{solid(IRON)}</Stroke><Stroke thickness="9" name="Edge">{solid(IRON_DARK)}</Stroke></Shape>
    </Node>
</Node>
<Shape x="{CXD}" y="262" name="Knocker Plate"><Ellipse width="30" height="30" name="Path"/><Stroke thickness="2" name="Edge">{solid(IRON_DARK)}</Stroke><Fill name="Fill">{gradient("radial", (-4, -4), (16, 0), [(0, "FF6A655D"), (1, "FF2A2724")])}</Fill></Shape>"""

    padlock_xml = f"""<Node x="{RIGHT - 34}" y="{lock_y}" opacity="0" name="Padlock" id="{padlock}">
    <Node name="Swing" id="{padlock_swing}">
        {ellipse(0, 26, 6, 9, solid("FF0A0908"), "Keyhole")}
        {rect(0, 24, 34, 30, gradient("linear", (0, -15), (0, 15), [(0, "FF6E6860"), (1, "FF2E2A26")]), IRON_DARK, 6, "Body", thickness=2)}
        <Shape y="6" name="Shackle"><Ellipse width="22" height="26" name="Path"/><Stroke thickness="5" name="Steel">{solid("FF8E8A82")}</Stroke></Shape>
        {rect(0, -2, 10, 8, IRON, IRON_DARK, 2, "Hasp Loop", thickness=1)}
    </Node>
</Node>"""

    clip = ids()
    spill_pts = [(LEFT, SILL), (RIGHT, SILL), (RIGHT + 50, H), (LEFT - 50, H)]
    content = f"""<Shape x="{W / 2}" y="{H / 2}" name="Vignette"><Rectangle width="{W}" height="{H}" name="Path"/><Fill name="Fill">{gradient("radial", (0, -10), (330, 0), [(0.45, "00000000"), (1, "B0000000")])}</Fill></Shape>
<Node name="Dust" opacity="0" id="{dust}">
{indent(chr(10).join(motes), 4)}
</Node>
{padlock_xml}
{frame()}
<Node name="Doorway">
    <Node name="Rattle" id="{rattle_shake}">
        <Node name="Knock" id="{knock_shake}">
            <Node x="{LEFT}" name="Hinge" id="{swing}">
                <Node x="{-LEFT}" name="Door">
                    <Shape name="Shade" opacity="0" id="{shade}">{points(arch_outline(2))}<Fill name="Fill">{solid("FF000000")}</Fill></Shape>
{indent(ring, 20)}
{indent(door_face(), 20)}
                </Node>
            </Node>
        </Node>
    </Node>
    <ClippingShape sourceId="{clip}" name="Doorway Clip"/>
</Node>
<Shape name="Doorway Mask" id="{clip}">{points(arch_outline(0))}</Shape>
<Node name="Beyond">
    <Shape x="{CXD}" y="{SILL - 60}" scaleY="0.8" opacity="0.55" name="Light" id="{glow}"><Ellipse width="280" height="280" name="Path"/><Fill name="Fill" blendModeValue="screen">{gradient("radial", (0, 0), (140, 0), [(0, LIGHT, P_COLOR), (1, "00000000")])}</Fill></Shape>
    <Shape name="Passage">{points(arch_outline(0))}<Fill name="Fill">{gradient("linear", (0, 90), (0, SILL), [(0, "FF070605"), (0.7, "FF15110E"), (1, "FF2A221A")])}</Fill></Shape>
</Node>
<Shape name="Spill" opacity="0" id="{spill}">{points(spill_pts)}<Fill name="Fill" blendModeValue="screen">{gradient("linear", (0, SILL), (0, H), [(0, LIGHT, P_COLOR), (1, "00000000")])}</Fill></Shape>
{wall()}"""

    layers = [
        two_state_layer("Door", E_OPEN, closed, opening, open_, closing),
        two_state_layer("Lock", E_LOCKED, unlocked, locking, locked, unlocking),
        trigger_layer("Knock", P_KNOCK, still_k, knock),
        trigger_layer("Rattle", P_RATTLE, still_r, rattle),
    ]
    anims = [closed, opening, open_, closing, unlocked, locking, locked, unlocking, still_k, knock, still_r, rattle]
    return content, layers, anims


def main():
    content, layers, anims = door()
    style, sm = ids(), ids()
    machine = f'<StateMachine name="Door" id="{sm}">\n' + "\n".join(layers) + "\n</StateMachine>"
    art = f'''<Artboard viewModelId="{VM}" viewModelInstanceId="{VM_INST}" defaultStateMachineId="{sm}" styleId="{style}"
          x="0" y="0" width="{W}" height="{H}" name="Door" id="{ids()}">
<LayoutComponentStyle name="Artboard Style" id="{style}"/>
{content}
{machine}
{chr(10).join(a.xml() for a in anims)}
</Artboard>'''
    vm = f'''<DataEnumCustom name="DoorState" id="{ENUM}">
    <DataEnumValue key="closed" value="Closed" id="{E_CLOSED}"/>
    <DataEnumValue key="open" value="Open" id="{E_OPEN}"/>
    <DataEnumValue key="locked" value="Locked" id="{E_LOCKED}"/>
</DataEnumCustom>
<ViewModel defaultInstanceId="{VM_INST}" name="Door" id="{VM}">
    <ViewModelPropertyEnumCustom enumId="{ENUM}" name="state" id="{P_STATE}"/>
    <ViewModelPropertyColor name="color" id="{P_COLOR}"/>
    <ViewModelPropertyTrigger name="knock" id="{P_KNOCK}"/>
    <ViewModelPropertyTrigger name="rattle" id="{P_RATTLE}"/>
    <ViewModelInstance exports="true" name="Default" id="{VM_INST}">
        <ViewModelInstanceEnum propertyValue="{E_CLOSED}" viewModelPropertyId="{P_STATE}"/>
        <ViewModelInstanceColor propertyValue="{LIGHT}" viewModelPropertyId="{P_COLOR}"/>
        <ViewModelInstanceTrigger viewModelPropertyId="{P_KNOCK}"/>
        <ViewModelInstanceTrigger viewModelPropertyId="{P_RATTLE}"/>
    </ViewModelInstance>
</ViewModel>'''
    header = "<!-- Generated by tools/gen_scene.py; edit that, not this. -->\n"
    OUT.write_text(f'<Rive version="1" kind="fragment">\n{header}{art}\n\n{vm}\n</Rive>\n', encoding="utf-8", newline="\n")
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
