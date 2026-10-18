"""Generates scene.rml for the TreasureChest sample: a chest seen from above.

    py -I tools/gen_scene.py        (from the project folder)

- Chest (320x320): a banded wooden chest, drawn as a camera looking down at an
  angle sees it: the lid's top faces the camera, the front is foreshortened and
  the chest's shadow lies on the ground. The lid swings up on its back hinge to
  show a heap of coins (or a bare floor), with a sparkle burst when it opens.

View model Chest: state (enum closed/open/empty), color (the treasure: coins,
glow and sparkles), locked (boolean: a padlock on the hasp), sparkle (trigger:
a glint over the chest). No scripts.
"""

import math
import random
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "scene.rml"

VM, P_STATE, P_COLOR, P_LOCKED, P_SPARKLE, VM_INST = "0:40", "0:41", "0:42", "0:43", "0:44", "0:45"
ENUM, E_CLOSED, E_OPEN, E_EMPTY = "0:50", "0:51", "0:52", "0:53"
C_LOCK_NUM, C_LOCK_EASE, C_LOCK = "0:60", "0:61", "0:62"
KEY_X, KEY_Y, KEY_ROT, KEY_SX, KEY_SY, KEY_OPACITY = 13, 14, 15, 16, 17, 18
KEY_COLOR, KEY_STOP_COLOR, KEY_ENUM, KEY_TRIGGER = 37, 38, 637, 686
TAU = math.tau

CX = 160          # the chest's centre line
HINGE = 118       # the back edge of the lid, where it is hinged
LID = 92          # the lid's depth as seen closed
FRONT = (HINGE + LID, 58)   # the front face: top y, height
OPEN = -0.78      # the lid's scaleY when open: flipped up behind the chest

WOOD_LIGHT, WOOD, WOOD_DARK, WOOD_EDGE = "FF946840", "FF6E4829", "FF3E2716", "FF2A1A0E"
IRON, RIVET, BRASS, BRASS_DARK = "FF34302C", "FF7A736A", "FFC9A44A", "FF6B5320"
GOLD = "FFE3B23C"


class Ids:
    def __init__(self, start=100):
        self.n = start

    def __call__(self):
        self.n += 1
        return f"0:{self.n}"


ids = Ids()


def bind(prop, key, converter=None):
    conv = f' converterId="{converter}"' if converter else ""
    return f'<DataBindContext sourcePathIds="{VM}-{prop}" propertyKey="{key}"{conv}/>'


def solid(color, prop=None):
    inner = bind(prop, KEY_COLOR) if prop else ""
    return f'<SolidColor colorValue="{color}" name="Color">{inner}</SolidColor>'


def gradient(kind, start, end, stops, gid=None):
    """A linear or radial gradient; a stop's colour may be bound: (position, colour, prop)."""
    out = []
    for stop in stops:
        pos, color, prop = (*stop, None)[:3]
        inner = bind(prop, KEY_STOP_COLOR) if prop else ""
        out.append(f'<GradientStop colorValue="{color}" position="{pos}">{inner}</GradientStop>')
    gid = f' id="{gid}"' if gid else ""
    tag = "LinearGradient" if kind == "linear" else "RadialGradient"
    return (f'<{tag} startX="{start[0]}" startY="{start[1]}" endX="{end[0]}" endY="{end[1]}" name="Gradient"{gid}>'
            + "".join(out) + f"</{tag}>")


def rect(x, y, w, h, fill, stroke=None, radius=0, name="Box", sid=None, thickness=2):
    sid = f' id="{sid}"' if sid else ""
    stroke_xml = f'<Stroke thickness="{thickness}" name="Edge">{solid(stroke)}</Stroke>' if stroke else ""
    fill_xml = fill if fill.startswith("<") else solid(fill)
    return (f'<Shape x="{x}" y="{y}" name="{name}"{sid}><Rectangle width="{w}" height="{h}" cornerRadiusTL="{radius}" name="Path"/>'
            f'{stroke_xml}<Fill name="Fill">{fill_xml}</Fill></Shape>')


def ellipse(x, y, w, h, fill, name="Dot", extra=""):
    return f'<Shape x="{x}" y="{y}" name="{name}"{extra}><Ellipse width="{w}" height="{h}" name="Path"/><Fill name="Fill">{fill}</Fill></Shape>'


class Anim:
    def __init__(self, name, duration, loop=True):
        self.name, self.duration, self.loop = name, duration, loop
        self.id = ids()
        self.keys = {}

    def key(self, obj, prop, frames):
        self.keys.setdefault(obj, {})[prop] = frames

    def hold(self, obj, prop, value):
        self.key(obj, prop, [(0, value)])

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


def sampled(duration, fn, step=2, start=0):
    """Keyframes of fn(t) every `step` frames from `start`, t from 0 to 1 over the whole animation."""
    frames = list(range(start, duration, step)) + [duration]
    return [(f, fn(f / duration)) for f in frames]


def ease_in_out(t):
    return 0.5 - 0.5 * math.cos(math.pi * min(1, max(0, t)))


def lid_open_fn(t):
    """The lid's scaleY while opening: a short lift, a swing up past upright, a settle."""
    if t < 0.12:
        return 1 - 0.06 * math.sin(math.pi * t / 0.12)
    u = (t - 0.12) / 0.88
    swing = ease_in_out(min(1, u / 0.7))
    settle = 0.07 * math.exp(-max(0, u - 0.7) * 9) * math.sin(math.pi * max(0, u - 0.7) / 0.3 * 1.5) if u > 0.7 else 0
    return 1 + (OPEN - 1) * swing - settle


def lid_close_fn(t):
    """Falling shut: accelerating, then a small bounce on the rim."""
    if t < 0.75:
        u = t / 0.75
        return OPEN + (1 - OPEN) * u * u
    u = (t - 0.75) / 0.25
    return 1 - 0.08 * math.sin(math.pi * u) * (1 - u)


# --- the drawing ----------------------------------------------------------

def coins():
    """A heap of coins on the chest's floor, with a few gems. Front coins draw on top."""
    rng = random.Random(7)
    pieces = []
    left, right, top, bottom = CX - 82, CX + 82, 134, 196
    for _ in range(150):
        x = rng.uniform(left, right)
        y = rng.uniform(top, bottom)
        r = ((x - CX) / 92) ** 2 + ((y - 168) / 40) ** 2
        lift = max(0, 16 * (1 - r))
        pieces.append((y, x, y - lift, rng.uniform(-0.45, 0.45), rng.random() < 0.035))
    pieces.sort(reverse=True)
    out = []
    gem_colors = ["FFB3203A", "FF2E6FD2", "FF2F9E5A", "FFB3203A"]
    gems = 0
    for _, x, y, rot, gem in pieces:
        if gem:
            c = gem_colors[gems % len(gem_colors)]
            gems += 1
            out.append(f'''<Node x="{x:.1f}" y="{y:.1f}" rotation="{rot:.3f}" name="Gem">
    {ellipse(-2.5, -1.5, 6, 3, solid("B0FFFFFF"), "Shine")}
    <Shape name="Stone"><Polygon points="6" width="17" height="11" name="Path"/><Stroke thickness="1.2" name="Edge">{solid("90000000")}</Stroke><Fill name="Fill">{solid(c)}</Fill></Shape>
</Node>''')
        else:
            out.append(f'''<Node x="{x:.1f}" y="{y:.1f}" rotation="{rot:.3f}" name="Coin">
    {ellipse(-2, -1.4, 6, 2.4, solid("A0FFFFFF"), "Shine")}
    <Shape name="Disc"><Ellipse width="15" height="8" name="Path"/><Stroke thickness="1.2" name="Edge">{solid("80301A00")}</Stroke><Fill name="Fill">{solid(GOLD, P_COLOR)}</Fill></Shape>
</Node>''')
    return "\n".join(out)


def star(x, y, size, color, sid, prop=None, opacity=1):
    return f'''<Node x="{x}" y="{y}" opacity="{opacity}" name="Sparkle" id="{sid}">
    <Shape name="Core"><Ellipse width="{size * 0.22:.1f}" height="{size * 0.22:.1f}" name="Path"/><Fill name="Fill">{solid("FFFFFFFF")}</Fill></Shape>
    <Shape name="Glint"><Star points="4" innerRadius="0.18" width="{size}" height="{size}" name="Path"/><Fill name="Fill" blendModeValue="screen">{solid(color, prop)}</Fill></Shape>
</Node>'''


def chest():
    closed, opening, open_, closing = Anim("Closed", 1, False), Anim("Opening", 66, False), Anim("Open", 240), Anim("Closing", 34, False)
    full, empty = Anim("Full", 1, False), Anim("Empty", 1, False)
    burst_idle, burst = Anim("Burst Idle", 1, False), Anim("Burst", 84, False)
    glint_idle, glint = Anim("Glint Idle", 1, False), Anim("Glint", 70, False)

    lid, outside, inside = ids(), ids(), ids()
    glow_lid, glow_contents, glow_shape = ids(), ids(), ids()
    treasure, floor_items = ids(), ids()
    burst_node, flash, glint_node = ids(), ids(), ids()

    # --- the lid layer: the lid's scaleY, which face shows, and the glow while open.
    def lid_keys(anim, fn, step=2):
        anim.key(lid, KEY_SY, sampled(anim.duration, fn, step) if anim.duration > 1 else [(0, fn(0))])
        side = lambda t: 1.0 if fn(t) > 0 else 0.0
        frames = sampled(anim.duration, fn, 1) if anim.duration > 1 else [(0, fn(0))]
        anim.key(outside, KEY_OPACITY, [(f, 1.0 if v > 0 else 0.0) for f, v in frames])
        anim.key(inside, KEY_OPACITY, [(f, 0.0 if v > 0 else 1.0) for f, v in frames])

    lid_keys(closed, lambda t: 1)
    closed.hold(glow_lid, KEY_OPACITY, 0)
    lid_keys(opening, lid_open_fn)
    opening.key(glow_lid, KEY_OPACITY, [(0, 0), (16, 0), (50, 1), (66, 1)])
    lid_keys(open_, lambda t: OPEN)
    open_.key(glow_lid, KEY_OPACITY, sampled(open_.duration, lambda t: 0.82 + 0.18 * math.cos(TAU * t), 10))
    lid_keys(closing, lid_close_fn)
    closing.key(glow_lid, KEY_OPACITY, [(0, 1), (18, 0), (34, 0)])

    # --- the contents layer: coins or a bare floor (the states cross-fade).
    for anim, v in ((full, 1), (empty, 0)):
        anim.hold(treasure, KEY_OPACITY, v)
        anim.hold(glow_contents, KEY_OPACITY, v)
        anim.hold(treasure, KEY_SY, 0.85 + 0.15 * v)

    # --- the burst: sparkles rising out of the chest as it opens.
    burst_idle.hold(burst_node, KEY_OPACITY, 0)
    burst.hold(burst_node, KEY_OPACITY, 1)
    burst.key(flash, KEY_OPACITY, [(0, 0), (12, 0), (24, 1), (64, 0)])
    burst.key(flash, KEY_SX, [(0, 0.4), (14, 0.4), (40, 1.1), (84, 1.2)])
    burst.key(flash, KEY_SY, [(0, 0.24), (14, 0.24), (40, 0.66), (84, 0.72)])
    rng = random.Random(3)
    sparkles = []
    for i in range(16):
        sid = ids()
        x0, y0 = CX + rng.uniform(-70, 70), rng.uniform(146, 186)
        dx, dy = rng.uniform(-30, 30), rng.uniform(55, 110)
        t0 = 14 + int(rng.uniform(0, 22))
        t1 = min(84, t0 + int(rng.uniform(34, 50)))
        size = rng.uniform(22, 40)
        color = ("FFFFF6D8", None) if i % 3 == 0 else (GOLD, P_COLOR)
        sparkles.append(star(round(x0, 1), round(y0, 1), round(size, 1), color[0], sid, color[1], opacity=0))
        burst.key(sid, KEY_OPACITY, [(0, 0), (t0, 0), (t0 + 6, 1), (int(t0 + (t1 - t0) * 0.6), 1), (t1, 0), (84, 0)])
        burst.key(sid, KEY_Y, [(0, y0), (t0, y0), (t1, y0 - dy), (84, y0 - dy)])
        burst.key(sid, KEY_X, [(0, x0), (t0, x0), (t1, x0 + dx), (84, x0 + dx)])
        burst.key(sid, KEY_ROT, [(0, 0), (t0, 0), (t1, rng.choice([-1, 1]) * rng.uniform(1.2, 2.4)), (84, 0)])
        pop = [(0, 0.2), (t0, 0.2), (t0 + 8, 1.15), (t1, 0.35), (84, 0.35)]
        burst.key(sid, KEY_SX, pop)
        burst.key(sid, KEY_SY, pop)

    # --- the glint (the sparkle trigger): three stars twinkle over the chest.
    glint_idle.hold(glint_node, KEY_OPACITY, 0)
    glint.hold(glint_node, KEY_OPACITY, 1)
    glints = []
    for i, (x, y, size) in enumerate([(CX + 54, 150, 52), (CX - 44, 178, 40), (CX + 4, 126, 46)]):
        sid = ids()
        glints.append(star(x, y, size, "FFFFF6D8", sid))
        t0 = 6 + i * 14
        tw = [(0, 0), (t0, 0), (t0 + 10, 1.2), (t0 + 26, 0), (70, 0)]
        glint.key(sid, KEY_SX, tw)
        glint.key(sid, KEY_SY, tw)
        glint.key(sid, KEY_ROT, [(0, 0), (t0, 0), (t0 + 26, 1.6), (70, 1.6)])

    # --- the pieces, front-most first.
    front_y, front_h = FRONT
    front_mid = front_y + front_h / 2
    rivets = lambda xs, ys: "\n".join(ellipse(x, y, 4, 3, solid(RIVET), "Rivet") for x in xs for y in ys)

    lid_outside = f"""<Node name="Outside" id="{outside}">
    {rivets([-66, 66], [12, 44, 76])}
    {rect(-66, LID / 2, 16, LID + 2, IRON, name="Band")}
    {rect(66, LID / 2, 16, LID + 2, IRON, name="Band")}
    {rect(0, LID - 5, 214, 12, WOOD_DARK, WOOD_EDGE, 4, "Front Lip")}
    {rect(0, 30, 204, 2, "50000000", name="Seam")}
    {rect(0, 60, 204, 2, "50000000", name="Seam")}
    {rect(0, LID / 2, 210, LID, gradient("linear", (0, 0), (0, LID), [(0, "FF5A391F"), (0.38, WOOD_LIGHT), (1, "FF5E3D22")]), WOOD_EDGE, 10, "Top", thickness=3)}
</Node>"""
    lid_inside = f"""<Node name="Inside" opacity="0" id="{inside}">
    {rect(0, LID - 4, 206, 8, "FF8A5F38", WOOD_EDGE, 3, "Rim")}
    {rect(0, 32, 196, 2, "60000000", name="Seam")}
    {rect(0, 62, 196, 2, "60000000", name="Seam")}
    {rect(0, LID / 2, 206, LID, gradient("linear", (0, 0), (0, LID), [(0, "FF24160B"), (1, "FF5A3B22")]), WOOD_EDGE, 8, "Face", thickness=3)}
</Node>"""

    padlock = f"""<Node x="{CX}" y="{front_y + 26}" name="Padlock">
    <DataBindContext sourcePathIds="{VM}-{P_LOCKED}" propertyKey="{KEY_OPACITY}" converterId="{C_LOCK}"/>
    {ellipse(0, 9, 5, 7, solid(BRASS), "Keyhole")}
    {rect(0, 10, 26, 20, gradient("linear", (0, -10), (0, 10), [(0, "FF6A655E"), (1, "FF2A2724")]), "FF121110", 5, "Body", thickness=1.5)}
    <Shape y="0" name="Shackle"><Ellipse width="15" height="17" name="Path"/><Stroke thickness="3.5" name="Steel">{solid("FF9A968E")}</Stroke></Shape>
</Node>"""

    lock_plate = f"""<Node x="{CX}" y="{front_y + 6}" name="Lock">
    {ellipse(0, 12, 5, 5, solid("FF140E0A"), "Keyhole")}
    {rect(0, 17, 4, 7, "FF140E0A", name="Keyhole Slot")}
    {rect(0, -4, 14, 14, BRASS, BRASS_DARK, 3, "Hasp", thickness=1.5)}
    {rect(0, 12, 30, 30, gradient("linear", (0, -15), (0, 15), [(0, "FFE0BE62"), (1, "FF9A7630")]), BRASS_DARK, 4, "Plate", thickness=1.5)}
</Node>"""

    hinges = "\n".join(rect(CX + dx, HINGE - 2, 20, 9, IRON, "FF1C1A18", 2, "Hinge", thickness=1) for dx in (-62, 62))

    front = f"""<Node name="Front">
    {rivets([CX - 66, CX + 66, CX - 94, CX + 94], [front_y + 12, front_y + front_h - 12])}
    {rect(CX - 94, front_mid, 18, front_h + 2, IRON, name="Corner")}
    {rect(CX + 94, front_mid, 18, front_h + 2, IRON, name="Corner")}
    {rect(CX - 66, front_mid, 16, front_h, IRON, name="Band")}
    {rect(CX + 66, front_mid, 16, front_h, IRON, name="Band")}
    {rect(CX, front_mid + 2, 198, 2, "60000000", name="Seam")}
    {rect(CX, front_mid, 206, front_h, gradient("linear", (0, -front_h / 2), (0, front_h / 2), [(0, "FF5C3B21"), (1, "FF34200F")]), WOOD_EDGE, 6, "Face", thickness=3)}
</Node>"""

    body_top = f"""<Node name="Body Top">
    {rect(CX, 136, 184, 22, gradient("linear", (0, -11), (0, 11), [(0, "FF22140A"), (1, "FF3A2515")]), name="Back Wall")}
    {rect(CX, 168, 184, 78, "FF2A1A0F", name="Floor")}
    {rect(CX, HINGE + LID / 2, 206, LID, "FF7A5432", WOOD_EDGE, 7, "Rim", thickness=3)}
</Node>"""

    floor = f"""<Node name="Floor Boards" id="{floor_items}">
    {rect(CX, 162, 180, 2, "50000000", name="Seam")}
    {rect(CX, 182, 180, 2, "50000000", name="Seam")}
</Node>"""

    content = f"""<Node name="Glint" opacity="0" id="{glint_node}">
{chr(10).join(glints)}
</Node>
<Node name="Burst" opacity="0" id="{burst_node}">
{chr(10).join(sparkles)}
    <Shape x="{CX}" y="160" opacity="0" scaleX="0.4" scaleY="0.24" name="Flash" id="{flash}">
        <Ellipse width="300" height="300" name="Path"/>
        <Fill name="Fill" blendModeValue="screen">{gradient("radial", (0, 0), (150, 0), [(0, GOLD, P_COLOR), (1, "00000000")])}</Fill>
    </Shape>
</Node>
<Node name="Glow Lid" opacity="0" id="{glow_lid}">
    <Node name="Glow Contents" id="{glow_contents}">
        <Shape x="{CX}" y="146" scaleY="0.62" opacity="0.6" name="Glow" id="{glow_shape}">
            <Ellipse width="250" height="250" name="Path"/>
            <Fill name="Fill" blendModeValue="screen">{gradient("radial", (0, 0), (125, 0), [(0, GOLD, P_COLOR), (1, "00000000")])}</Fill>
        </Shape>
    </Node>
</Node>
{padlock}
{lock_plate}
{hinges}
<Node x="{CX}" y="{HINGE}" name="Lid" id="{lid}">
{indent(lid_outside, 4)}
{indent(lid_inside, 4)}
</Node>
{front}
<Node y="200" name="Treasure" id="{treasure}">
    <Node y="-200" name="Heap">
{indent(coins(), 8)}
        {ellipse(CX, 166, 150, 40, solid("70000000"), "Heap Shade")}
        {ellipse(CX, 168, 168, 58, solid(GOLD, P_COLOR), "Heap Base")}
        {ellipse(CX, 172, 182, 68, solid("50000000"), "Heap Shadow")}
    </Node>
</Node>
{floor}
{body_top}
<Node name="Ground Shadow">
    {rect(CX + 14, 236, 226, 84, "48000000", radius=22, name="Shadow")}
    {rect(CX + 20, 244, 250, 100, "1E000000", radius=34, name="Penumbra")}
</Node>"""

    layers = {
        "lid": (closed, opening, open_, closing),
        "contents": (full, empty),
        "burst": (burst_idle, burst),
        "glint": (glint_idle, glint),
    }
    return content, layers


def indent(text, n):
    return "\n".join(" " * n + line for line in text.splitlines())


def is_state(value, op="equal"):
    return f'''<TransitionViewModelCondition opValue="{op}">
    <TransitionPropertyViewModelComparator>
        <BindablePropertyEnum>{bind(P_STATE, KEY_ENUM)}</BindablePropertyEnum>
    </TransitionPropertyViewModelComparator>
    <TransitionValueEnumComparator value="{value}"/>
</TransitionViewModelCondition>'''


def go(to, *conds, duration=None, exit_time=False):
    attrs = f' duration="{duration}"' if duration else ""
    if exit_time:
        attrs += ' enableExitTime="true" exitTimeIsPercetange="true" exitTime="100"'
    return f'<StateTransition stateToId="{to}"{attrs}>' + "".join(conds) + "</StateTransition>"


def machine(layers):
    closed, opening, open_, closing = layers["lid"]
    full, empty = layers["contents"]
    burst_idle, burst = layers["burst"]
    glint_idle, glint = layers["glint"]
    s = {k: ids() for k in ("closed", "opening", "open", "closing", "full", "empty", "b_idle", "b_play", "b_done", "g_idle", "g_play")}

    def state(key, anim, x, *transitions, reset=False):
        r = ' reset="true"' if reset else ""
        return f'<AnimationState x="{x}" y="0" animationId="{anim.id}"{r} id="{s[key]}">' + "".join(transitions) + "</AnimationState>"

    def layer(name, entry, *states, extra=""):
        return f'''<StateMachineLayer name="{name}">
    <EntryState x="-200" y="0">{entry}</EntryState>
    {extra}
    {chr(10).join(states)}
</StateMachineLayer>'''

    # Load straight into the persisted state: no animation on load.
    lid = layer("Lid",
                go(s["closed"], is_state(E_CLOSED)) + go(s["open"]),
                state("closed", closed, 0, go(s["opening"], is_state(E_CLOSED, "notEqual"))),
                state("opening", opening, 200, go(s["open"], exit_time=True), reset=True),
                state("open", open_, 400, go(s["closing"], is_state(E_CLOSED))),
                state("closing", closing, 600, go(s["closed"], exit_time=True), reset=True))
    # Emptied stays empty when closed; only setting it open again refills it.
    contents = layer("Contents",
                     go(s["empty"], is_state(E_EMPTY)) + go(s["full"]),
                     state("full", full, 0, go(s["empty"], is_state(E_EMPTY), duration=700)),
                     state("empty", empty, 200, go(s["full"], is_state(E_OPEN), duration=500)))
    # The burst plays each time the chest becomes open (not on load).
    burst_layer = layer("Burst",
                        go(s["b_done"], is_state(E_OPEN)) + go(s["b_idle"]),
                        state("b_idle", burst_idle, 0, go(s["b_play"], is_state(E_OPEN))),
                        state("b_play", burst, 200, go(s["b_done"], exit_time=True), reset=True),
                        state("b_done", burst_idle, 400, go(s["b_idle"], is_state(E_OPEN, "notEqual"))))
    glint_layer = layer("Glint",
                        go(s["g_idle"]),
                        state("g_idle", glint_idle, 0),
                        state("g_play", glint, 200, go(s["g_idle"], exit_time=True), reset=True),
                        extra=f'''<AnyState x="0" y="-120">
        <StateTransition stateToId="{s["g_play"]}">
            <TransitionViewModelCondition>
                <TransitionPropertyViewModelComparator>
                    <BindablePropertyTrigger>{bind(P_SPARKLE, KEY_TRIGGER)}</BindablePropertyTrigger>
                </TransitionPropertyViewModelComparator>
                <TransitionValueTriggerComparator/>
            </TransitionViewModelCondition>
        </StateTransition>
    </AnyState>''')
    anims = [*layers["lid"], *layers["contents"], *layers["burst"], *layers["glint"]]
    sm = ids()
    xml = f'<StateMachine name="Chest" id="{sm}">\n' + "\n".join([lid, contents, burst_layer, glint_layer]) + "\n</StateMachine>"
    return sm, xml, anims


def main():
    content, layers = chest()
    sm, sm_xml, anims = machine(layers)
    style = ids()
    art = f'''<Artboard viewModelId="{VM}" viewModelInstanceId="{VM_INST}" defaultStateMachineId="{sm}" styleId="{style}"
          x="0" y="0" width="320" height="320" name="Chest" id="{ids()}">
<LayoutComponentStyle name="Artboard Style" id="{style}"/>
{content}
{sm_xml}
{chr(10).join(a.xml() for a in anims)}
</Artboard>'''
    converters = f'''<DataConverterToNumber name="Locked as number" id="{C_LOCK_NUM}"/>
<DataConverterInterpolator interpolationType="linear" duration="0.25" name="Ease" id="{C_LOCK_EASE}"/>
<DataConverterGroup name="Padlock opacity" id="{C_LOCK}">
    <DataConverterGroupItem converterId="{C_LOCK_NUM}"/>
    <DataConverterGroupItem converterId="{C_LOCK_EASE}"/>
</DataConverterGroup>'''
    vm = f'''<DataEnumCustom name="ChestState" id="{ENUM}">
    <DataEnumValue key="closed" value="Closed" id="{E_CLOSED}"/>
    <DataEnumValue key="open" value="Open" id="{E_OPEN}"/>
    <DataEnumValue key="empty" value="Empty" id="{E_EMPTY}"/>
</DataEnumCustom>
<ViewModel defaultInstanceId="{VM_INST}" name="Chest" id="{VM}">
    <ViewModelPropertyEnumCustom enumId="{ENUM}" name="state" id="{P_STATE}"/>
    <ViewModelPropertyColor name="color" id="{P_COLOR}"/>
    <ViewModelPropertyBoolean name="locked" id="{P_LOCKED}"/>
    <ViewModelPropertyTrigger name="sparkle" id="{P_SPARKLE}"/>
    <ViewModelInstance exports="true" name="Default" id="{VM_INST}">
        <ViewModelInstanceEnum propertyValue="{E_CLOSED}" viewModelPropertyId="{P_STATE}"/>
        <ViewModelInstanceColor propertyValue="{GOLD}" viewModelPropertyId="{P_COLOR}"/>
        <ViewModelInstanceBoolean propertyValue="false" viewModelPropertyId="{P_LOCKED}"/>
        <ViewModelInstanceTrigger viewModelPropertyId="{P_SPARKLE}"/>
    </ViewModelInstance>
</ViewModel>'''
    header = "<!-- Generated by tools/gen_scene.py; edit that, not this. -->\n"
    body = "\n\n".join([art, converters, vm])
    OUT.write_text(f'<Rive version="1" kind="fragment">\n{header}{body}\n</Rive>\n', encoding="utf-8", newline="\n")
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
