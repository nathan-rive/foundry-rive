"""Generates scene.rml for the Mechanisms sample: a pressure plate, a floor lever
and a portcullis, for wiring one tile to another with Monk's Active Tile Triggers.

    py -I tools/gen_scene.py        (from the project folder)

- Plate (100x100): a stone slab set in the floor, seen straight down. It sinks
  while `pressed` is true, puffing dust, and its rune glows in `color`.
- Lever (100x100): a floor lever on a stone block, seen from above at an angle.
  The arm swings from left to right while `pulled` is true. Clicking it toggles
  `pulled` where the runtime passes clicks on (journal pages).
- Gate (300x150): a portcullis in a wall, seen from above at an angle: the
  wall's top, its foreshortened face, and the portcullis in the gateway. It
  rises behind the lintel while `open` is true; `rattle` shakes it.

Each artboard has its own view model (Plate, Lever, Gate). No scripts.
"""

import math
import random
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "scene.rml"

VM_PLATE, P_PRESSED, P_COLOR, I_PLATE = "0:40", "0:41", "0:42", "0:43"
VM_LEVER, P_PULLED, I_LEVER = "0:50", "0:51", "0:52"
VM_GATE, P_OPEN, P_RATTLE, I_GATE = "0:55", "0:56", "0:57", "0:58"
C_NOT = "0:60"
KEY_X, KEY_Y, KEY_ROT, KEY_SX, KEY_SY, KEY_OPACITY = 13, 14, 15, 16, 17, 18
KEY_COLOR, KEY_BOOL, KEY_TRIGGER = 37, 634, 686
TAU = math.tau

STONE_TOP, STONE_FACE, STONE_EDGE = "FF8C857A", "FF5E5850", "FF3A3631"
IRON, IRON_LIGHT, IRON_DARK = "FF34312D", "FF5C5852", "FF181614"
RUNE = "FF6FD3FF"


class Ids:
    def __init__(self, start=100):
        self.n = start

    def __call__(self):
        self.n += 1
        return f"0:{self.n}"


ids = Ids()


def bind(vm, prop, key, converter=None, write=False):
    conv = f' converterId="{converter}"' if converter else ""
    direction = ' direction="true"' if write else ""
    return f'<DataBindContext sourcePathIds="{vm}-{prop}" propertyKey="{key}"{conv}{direction}/>'


def solid(color, bound=None):
    inner = bind(*bound, KEY_COLOR) if bound else ""
    return f'<SolidColor colorValue="{color}" name="Color">{inner}</SolidColor>'


def linear(start, end, stops):
    s = "".join(f'<GradientStop colorValue="{c}" position="{p}"/>' for p, c in stops)
    return f'<LinearGradient startX="{start[0]}" startY="{start[1]}" endX="{end[0]}" endY="{end[1]}" name="Gradient">{s}</LinearGradient>'


def rect(x, y, w, h, fill, stroke=None, radius=0, name="Box", sid=None, thickness=2, extra=""):
    sid = f' id="{sid}"' if sid else ""
    stroke_xml = f'<Stroke thickness="{thickness}" name="Edge">{solid(stroke)}</Stroke>' if stroke else ""
    fill_xml = "" if fill is None else f'<Fill name="Fill">{fill if fill.startswith("<") else solid(fill)}</Fill>'
    return (f'<Shape x="{x}" y="{y}" name="{name}"{sid}{extra}><Rectangle width="{w}" height="{h}" cornerRadiusTL="{radius}" name="Path"/>'
            f'{stroke_xml}{fill_xml}</Shape>')


def ellipse(x, y, w, h, fill, name="Dot", sid=None, extra=""):
    sid = f' id="{sid}"' if sid else ""
    return f'<Shape x="{x}" y="{y}" name="{name}"{sid}{extra}><Ellipse width="{w}" height="{h}" name="Path"/><Fill name="Fill">{fill}</Fill></Shape>'


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


def settle(t, start=0.75, amount=0.12):
    """Eases to 1 by `start`, then a damped wobble about 1 (an overshoot that settles)."""
    if t < start:
        return ease(t / start)
    u = (t - start) / (1 - start)
    return 1 + amount * math.sin(math.pi * u * 2) * (1 - u)


# --- state machines --------------------------------------------------------

def is_bool(vm, prop, value):
    return f'''<TransitionViewModelCondition opValue="equal">
    <TransitionPropertyViewModelComparator>
        <BindablePropertyBoolean>{bind(vm, prop, KEY_BOOL)}</BindablePropertyBoolean>
    </TransitionPropertyViewModelComparator>
    <TransitionValueBooleanComparator value="{str(value).lower()}"/>
</TransitionViewModelCondition>'''


def two_state_layer(name, vm, prop, rest, going, on, coming):
    """Rest <-> on through one-shot transitions, entering straight into the saved value."""
    s = {k: ids() for k in ("rest", "going", "on", "coming")}

    def st(key, anim, x, *trans, reset=False):
        r = ' reset="true"' if reset else ""
        return f'<AnimationState x="{x}" y="0" animationId="{anim.id}"{r} id="{s[key]}">' + "".join(trans) + "</AnimationState>"

    def go(to, cond=""):
        return f'<StateTransition stateToId="{s[to]}">{cond}</StateTransition>'

    exit_ = lambda to: f'<StateTransition stateToId="{s[to]}" enableExitTime="true" exitTimeIsPercetange="true" exitTime="100"/>'
    return f'''<StateMachineLayer name="{name}">
    <EntryState x="-200" y="0">{go("on", is_bool(vm, prop, True))}{go("rest")}</EntryState>
    {st("rest", rest, 0, go("going", is_bool(vm, prop, True)))}
    {st("going", going, 200, exit_("on"), reset=True)}
    {st("on", on, 400, go("coming", is_bool(vm, prop, False)))}
    {st("coming", coming, 600, exit_("rest"), reset=True)}
</StateMachineLayer>'''


def trigger_layer(name, vm, prop, idle, play):
    s_idle, s_play = ids(), ids()
    return f'''<StateMachineLayer name="{name}">
    <AnyState x="0" y="-120">
        <StateTransition stateToId="{s_play}">
            <TransitionViewModelCondition>
                <TransitionPropertyViewModelComparator>
                    <BindablePropertyTrigger>{bind(vm, prop, KEY_TRIGGER)}</BindablePropertyTrigger>
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


def toggle_listener(target, vm, prop):
    """A click on `target` sets prop to not(prop)."""
    rid = ids()
    return (f'<StateMachineListenerSingle targetId="{target}" listenerTypeValue="click" name="Toggle">'
            f'<ListenerViewModelChange fromViewModelProperty="true" fromDataBindId="{rid}"><BindablePropertyBoolean>'
            f'<DataBindContext sourcePathIds="{vm}-{prop}" propertyKey="{KEY_BOOL}" converterId="{C_NOT}" id="{rid}"/>'
            f'{bind(vm, prop, KEY_BOOL, write=True)}'
            f'</BindablePropertyBoolean></ListenerViewModelChange></StateMachineListenerSingle>')


# --- Plate -----------------------------------------------------------------

def plate():
    """A slab in the floor, straight down: it sinks and its rune lights."""
    up, pressing, down, releasing = Anim("Up", 1), Anim("Pressing", 30), Anim("Down", 1), Anim("Releasing", 24)
    slab, shade, glow, dust = ids(), ids(), ids(), ids()

    def slab_keys(anim, fn):
        if anim.duration == 1:
            v = fn(0)
            anim.hold(slab, KEY_SX, 1 - 0.06 * v)
            anim.hold(slab, KEY_SY, 1 - 0.06 * v)
            anim.hold(slab, KEY_Y, 50 + 1.5 * v)
            anim.hold(shade, KEY_OPACITY, 0.3 * v)
            anim.hold(glow, KEY_OPACITY, v)
        else:
            anim.curve(slab, KEY_SX, lambda t: 1 - 0.06 * fn(t))
            anim.curve(slab, KEY_SY, lambda t: 1 - 0.06 * fn(t))
            anim.curve(slab, KEY_Y, lambda t: 50 + 1.5 * fn(t))
            anim.curve(shade, KEY_OPACITY, lambda t: 0.3 * fn(t))
            anim.curve(glow, KEY_OPACITY, lambda t: max(0, min(1, fn(t))) ** 2)

    slab_keys(up, lambda t: 0)
    slab_keys(pressing, lambda t: settle(t, 0.35, 0.1))
    slab_keys(down, lambda t: 1)
    slab_keys(releasing, lambda t: 1 - ease(t))
    for anim in (up, down, releasing):
        anim.hold(dust, KEY_OPACITY, 0)

    # Dust puffs out of the gap on each side as the slab drops.
    rng = random.Random(5)
    puffs = []
    pressing.key(dust, KEY_OPACITY, [(0, 1), (30, 1)])
    for i in range(10):
        pid = ids()
        side = i % 4
        along = rng.uniform(-30, 30)
        x0, y0, dx, dy = {0: (along, -40, 0, -1), 1: (40, along, 1, 0), 2: (along, 40, 0, 1), 3: (-40, along, -1, 0)}[side]
        reach = rng.uniform(8, 14)
        size = rng.uniform(5, 9)
        puffs.append(ellipse(round(50 + x0, 1), round(50 + y0, 1), round(size, 1), round(size, 1), solid("90B8AE9C"), "Puff", pid, ' opacity="0"'))
        pressing.key(pid, KEY_X, [(0, 50 + x0), (4, 50 + x0), (26, 50 + x0 + dx * reach)])
        pressing.key(pid, KEY_Y, [(0, 50 + y0), (4, 50 + y0), (26, 50 + y0 + dy * reach)])
        pressing.key(pid, KEY_OPACITY, [(0, 0), (4, 0), (8, 0.9), (26, 0)])
        pressing.key(pid, KEY_SX, [(0, 0.4), (4, 0.4), (26, 1.6)])
        pressing.key(pid, KEY_SY, [(0, 0.4), (4, 0.4), (26, 1.6)])

    rune_path = '<Star points="6" innerRadius="0.5" width="26" height="26" name="Path"/>'
    cracks = "\n".join(rect(x, y, w, 1.5, "40000000", name="Crack", extra=f' rotation="{r}"')
                       for x, y, w, r in [(-24, -22, 14, 0.5), (22, 26, 12, -0.4), (26, -20, 9, 1.1), (-22, 24, 10, -1.2)])
    content = f"""<Node name="Dust" id="{dust}">
{indent(chr(10).join(puffs), 4)}
</Node>
<Node x="50" y="50" name="Slab" id="{slab}">
    {rect(0, 0, 76, 76, "FF000000", radius=5, name="Shade", sid=shade, extra=' opacity="0"')}
    <Node name="Glow" opacity="0" id="{glow}">
        <Shape name="Rune Light"><Ellipse width="40" height="40" name="Path"/>{rune_path}<Stroke thickness="3" name="Line" blendModeValue="screen">{solid(RUNE, (VM_PLATE, P_COLOR))}</Stroke></Shape>
        {ellipse(0, 0, 56, 56, f'<RadialGradient startX="0" startY="0" endX="28" endY="0" name="Gradient"><GradientStop colorValue="{RUNE}" position="0">{bind(VM_PLATE, P_COLOR, 38)}</GradientStop><GradientStop colorValue="00000000" position="1"/></RadialGradient>', "Halo", extra=' opacity="0.5"').replace('<Fill name="Fill">', '<Fill name="Fill" blendModeValue="screen">')}
    </Node>
    <Shape name="Rune"><Ellipse width="40" height="40" name="Path"/>{rune_path}<Stroke thickness="3" name="Groove">{solid("70201D1A")}</Stroke></Shape>
{indent(cracks, 4)}
    {rect(0, 0, 76, 76, linear((-38, -38), (38, 38), [(0, "FF9A948A"), (1, "FF6A645B")]), STONE_EDGE, 5, "Top", thickness=2)}
</Node>
{rect(50, 50, 86, 86, "C0141110", radius=7, name="Gap")}
{rect(50, 50, 92, 92, "50000000", radius=9, name="Gap Shadow")}"""
    layers = two_state_layer("Plate", VM_PLATE, P_PRESSED, up, pressing, down, releasing)
    return content, [layers], [up, pressing, down, releasing], ""


# --- Lever -----------------------------------------------------------------

def lever():
    """A floor lever on a block, seen from above at an angle: the arm stands up
    out of a slot, foreshortened, and swings from left to right."""
    up, pulling, pulled, returning = Anim("Up", 1), Anim("Pulling", 26), Anim("Pulled", 1), Anim("Returning", 26)
    arm, arm_shadow, hit = ids(), ids(), ids()
    left, right = -0.5, 0.5

    def arm_keys(anim, fn):
        for obj in (arm, arm_shadow):
            if anim.duration == 1:
                anim.hold(obj, KEY_ROT, fn(0))
            else:
                anim.curve(obj, KEY_ROT, fn)

    arm_keys(up, lambda t: left)
    arm_keys(pulling, lambda t: left + (right - left) * settle(t, 0.6, 0.08))
    arm_keys(pulled, lambda t: right)
    arm_keys(returning, lambda t: right + (left - right) * settle(t, 0.6, 0.08))

    def arm_drawing(shadow):
        if shadow:
            return f'''{ellipse(0, -46, 15, 15, solid("48000000"), "Knob")}
{rect(0, -22, 6, 46, "48000000", radius=3, name="Shaft")}'''
        return f'''{ellipse(-2, -48, 5, 4, solid("90FFFFFF"), "Shine")}
<Shape y="-46" name="Knob"><Ellipse width="15" height="15" name="Path"/><Stroke thickness="1.5" name="Edge">{solid("FF4A1A12")}</Stroke><Fill name="Fill">{solid("FFA2382A")}</Fill></Shape>
{rect(-1, -22, 2, 44, IRON_LIGHT, name="Highlight")}
{rect(0, -22, 6, 46, IRON, IRON_DARK, 3, "Shaft", thickness=1)}'''

    content = f"""{rect(50, 50, 100, 100, "01000000", name="Hit Area", sid=hit)}
<Node x="50" y="56" scaleY="0.62" name="Tilt">
    <Node name="Arm" rotation="{left}" id="{arm}">
{indent(arm_drawing(False), 8)}
    </Node>
</Node>
{rect(50, 56, 40, 6, "FF141210", radius=3, name="Slot")}
{rect(37, 56, 6, 10, IRON, name="Bracket")}
{rect(63, 56, 6, 10, IRON, name="Bracket")}
{rect(50, 56, 56, 30, linear((0, -15), (0, 15), [(0, "FF9A948A"), (1, "FF7E786E")]), STONE_EDGE, 4, "Block Top")}
{rect(50, 77, 56, 14, STONE_FACE, STONE_EDGE, 3, "Block Face")}
<Node x="58" y="64" scaleY="0.38" name="Arm Shadow Tilt">
    <Node name="Arm Shadow" rotation="{left}" id="{arm_shadow}">
{indent(arm_drawing(True), 8)}
    </Node>
</Node>
{rect(56, 66, 62, 44, "40000000", radius=8, name="Block Shadow")}"""
    layers = two_state_layer("Lever", VM_LEVER, P_PULLED, up, pulling, pulled, returning)
    return content, [layers], [up, pulling, pulled, returning], toggle_listener(hit, VM_LEVER, P_PULLED)


# --- Gate ------------------------------------------------------------------

GATE_L, GATE_R = 105, 195       # the gateway's sides
TOP_Y, FACE_Y, GROUND_Y = 22, 58, 118   # wall top, face top (the lintel's front edge), the ground


def gate():
    """A wall with a gateway, seen from above at an angle: the wall's top, its
    foreshortened face, and a portcullis in the gateway that rises behind the lintel."""
    closed, opening, open_, closing = Anim("Closed", 1), Anim("Opening", 90), Anim("Open", 1), Anim("Closing", 30)
    still, rattle = Anim("Still", 1), Anim("Rattle", 40)
    grid, grid_shake, bar_shadows, clip = ids(), ids(), ids(), ids()
    rise = 50

    def grid_keys(anim, fn, step=2):
        if anim.duration == 1:
            anim.hold(grid, KEY_Y, -rise * fn(0))
            anim.hold(bar_shadows, KEY_OPACITY, 1 - fn(0))
        else:
            anim.curve(grid, KEY_Y, lambda t: -rise * fn(t), step)
            anim.curve(bar_shadows, KEY_OPACITY, lambda t: 1 - min(1, max(0, fn(t))))

    def winch(t):
        """Hauled up in jerks of the chain, then a small drop as it catches."""
        base = ease(t / 0.9) if t < 0.9 else 1
        jerk = 0.02 * math.sin(TAU * t * 7) * (1 - t)
        catch = -0.03 * math.sin(math.pi * (t - 0.9) / 0.1) if t > 0.9 else 0
        return base + jerk + catch

    def drop(t):
        if t < 0.55:
            return 1 - (t / 0.55) ** 2
        u = (t - 0.55) / 0.45
        return 0.06 * math.sin(math.pi * u) * (1 - u)

    grid_keys(closed, lambda t: 0)
    grid_keys(opening, winch)
    grid_keys(open_, lambda t: 1)
    grid_keys(closing, drop, 1)
    still.hold(grid_shake, KEY_X, 0)
    rattle.curve(grid_shake, KEY_X, lambda t: 2.5 * math.sin(TAU * t * 6) * (1 - t), 1)
    rattle.curve(grid_shake, KEY_Y, lambda t: -1.2 * abs(math.sin(TAU * t * 3)) * (1 - t), 1)

    width = GATE_R - GATE_L
    face_h = GROUND_Y - FACE_Y
    bars = []
    for i in range(7):
        x = GATE_L + 7 + i * (width - 14) / 6
        bars.append(f'''<Shape x="{x:.1f}" y="{GROUND_Y - 4}" name="Spike"><Polygon points="3" width="8" height="9" rotation="3.1416" name="Path"/><Fill name="Fill">{solid(IRON)}</Fill></Shape>''')
        bars.append(rect(round(x - 1, 1), (FACE_Y + GROUND_Y) / 2 - 8, 1.5, face_h, IRON_LIGHT, name="Bar Shine"))
        bars.append(rect(round(x, 1), (FACE_Y + GROUND_Y) / 2 - 8, 5, face_h, IRON, IRON_DARK, 1, "Bar", thickness=1))
    rails = [rect((GATE_L + GATE_R) / 2, y, width - 6, 4, IRON, IRON_DARK, 1, "Rail", thickness=1) for y in (FACE_Y + 8, FACE_Y + 26, FACE_Y + 44)]

    # The wall's stones: courses of blocks on the top and on the face, with
    # the gateway left open in the face.
    def courses(y0, y1, rows, color, skip_gate):
        out = []
        h = (y1 - y0) / rows
        for r in range(rows):
            y = y0 + h * r
            out.append(rect(150, round(y + h, 1), 300, 1.5, "50000000", name="Course"))
            x = -20 if r % 2 else 0
            while x < 300:
                if not (skip_gate and GATE_L - 4 < x < GATE_R + 4):
                    out.append(rect(round(x, 1), round(y + h / 2, 1), 1.5, round(h, 1), "50000000", name="Joint"))
                x += 40
        return "\n".join(out)

    shadow_stripes = "\n".join(
        f'<Shape x="{GATE_L + 7 + i * (width - 14) / 6 + 6:.1f}" y="{GROUND_Y + 9}" rotation="-0.35" name="Bar Shadow">'
        f'<Rectangle width="4" height="18" name="Path"/><Fill name="Fill">{solid("38000000")}</Fill></Shape>' for i in range(7))

    content = f"""<Node name="Wall Top">
{indent(courses(TOP_Y, FACE_Y, 2, None, False), 4)}
    {rect(150, (TOP_Y + FACE_Y) / 2, 300, FACE_Y - TOP_Y, linear((0, -18), (0, 18), [(0, "FF9C958A"), (1, "FF847D72")]), STONE_EDGE, 0, "Top", thickness=2)}
</Node>
<Node name="Gateway">
    {rect((GATE_L + GATE_R) / 2, FACE_Y + 3, width + 8, 6, "FF6E675D", STONE_EDGE, 0, "Lintel")}
    <Node name="Portcullis">
        <Node name="Shake" id="{grid_shake}">
            <Node name="Grid" id="{grid}">
{indent(chr(10).join(rails + bars), 16)}
            </Node>
        </Node>
        <ClippingShape sourceId="{clip}" name="Gateway Clip"/>
    </Node>
    <Shape x="{(GATE_L + GATE_R) / 2}" y="{(FACE_Y + GROUND_Y) / 2}" name="Gateway Mask" id="{clip}"><Rectangle width="{width + 2}" height="{face_h}" name="Path"/></Shape>
    {rect((GATE_L + GATE_R) / 2, (FACE_Y + GROUND_Y) / 2, width, face_h, linear((0, -face_h / 2), (0, face_h / 2), [(0, "FF0E0C0B"), (0.6, "FF241F1B"), (1, "FF4A4238")]), name="Passage")}
</Node>
<Node name="Wall Face">
{indent(courses(FACE_Y, GROUND_Y, 3, None, True), 4)}
    {rect(GATE_L / 2, (FACE_Y + GROUND_Y) / 2, GATE_L, face_h, linear((0, -30), (0, 30), [(0, "FF5E5850"), (1, "FF433E38")]), STONE_EDGE, 0, "Face Left", thickness=2)}
    {rect((300 + GATE_R) / 2, (FACE_Y + GROUND_Y) / 2, 300 - GATE_R, face_h, linear((0, -30), (0, 30), [(0, "FF5E5850"), (1, "FF433E38")]), STONE_EDGE, 0, "Face Right", thickness=2)}
</Node>
<Node name="Bar Shadows" id="{bar_shadows}">
{indent(shadow_stripes, 4)}
</Node>
{rect(160, GROUND_Y + 9, 300, 18, "40000000", name="Wall Shadow")}"""
    layers = [two_state_layer("Gate", VM_GATE, P_OPEN, closed, opening, open_, closing),
              trigger_layer("Rattle", VM_GATE, P_RATTLE, still, rattle)]
    return content, layers, [closed, opening, open_, closing, still, rattle], ""


def artboard(name, vm, inst, width, height, at, build):
    content, layers, anims, listeners = build()
    style, sm = ids(), ids()
    machine = f'<StateMachine name="{name}" id="{sm}">\n' + "\n".join(layers) + listeners + "\n</StateMachine>"
    return f'''<Artboard viewModelId="{vm}" viewModelInstanceId="{inst}" defaultStateMachineId="{sm}" styleId="{style}"
          x="{at[0]}" y="{at[1]}" width="{width}" height="{height}" name="{name}" id="{ids()}">
<LayoutComponentStyle name="Artboard Style" id="{style}"/>
{content}
{machine}
{chr(10).join(a.xml() for a in anims)}
</Artboard>'''


def main():
    body = "\n\n".join([
        artboard("Plate", VM_PLATE, I_PLATE, 100, 100, (0, 0), plate),
        artboard("Lever", VM_LEVER, I_LEVER, 100, 100, (160, 0), lever),
        artboard("Gate", VM_GATE, I_GATE, 300, 150, (320, 0), gate),
        f'<DataConverterBooleanNegate name="Not" id="{C_NOT}"/>',
        f'''<ViewModel defaultInstanceId="{I_PLATE}" name="Plate" id="{VM_PLATE}">
    <ViewModelPropertyBoolean name="pressed" id="{P_PRESSED}"/>
    <ViewModelPropertyColor name="color" id="{P_COLOR}"/>
    <ViewModelInstance exports="true" name="Default" id="{I_PLATE}">
        <ViewModelInstanceBoolean propertyValue="false" viewModelPropertyId="{P_PRESSED}"/>
        <ViewModelInstanceColor propertyValue="{RUNE}" viewModelPropertyId="{P_COLOR}"/>
    </ViewModelInstance>
</ViewModel>
<ViewModel defaultInstanceId="{I_LEVER}" name="Lever" id="{VM_LEVER}">
    <ViewModelPropertyBoolean name="pulled" id="{P_PULLED}"/>
    <ViewModelInstance exports="true" name="Default" id="{I_LEVER}">
        <ViewModelInstanceBoolean propertyValue="false" viewModelPropertyId="{P_PULLED}"/>
    </ViewModelInstance>
</ViewModel>
<ViewModel defaultInstanceId="{I_GATE}" name="Gate" id="{VM_GATE}">
    <ViewModelPropertyBoolean name="open" id="{P_OPEN}"/>
    <ViewModelPropertyTrigger name="rattle" id="{P_RATTLE}"/>
    <ViewModelInstance exports="true" name="Default" id="{I_GATE}">
        <ViewModelInstanceBoolean propertyValue="false" viewModelPropertyId="{P_OPEN}"/>
        <ViewModelInstanceTrigger viewModelPropertyId="{P_RATTLE}"/>
    </ViewModelInstance>
</ViewModel>''',
    ])
    header = "<!-- Generated by tools/gen_scene.py; edit that, not this. -->\n"
    OUT.write_text(f'<Rive version="1" kind="fragment">\n{header}{body}\n</Rive>\n', encoding="utf-8", newline="\n")
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
