"""Generates scene.rml for the Brazier sample: fire seen from above, in three artboards.

    py -I tools/gen_scene.py        (from the project folder)

- Brazier (300x300): an iron bowl of coals on three legs, seen from above at an
  angle, with a fire standing up out of it and its glow on the floor.
- Torch (160x160): a wall torch seen from above, the wall along the bottom edge.
- Trough (400x100): a long fire trough laid out with flex boxes, for the Layout
  fit: a wider or taller tile shows a longer trough instead of a stretched one.

All three share the view model Fire: lit (boolean), intensity (number, 0-1.5),
color (the flame colour), flare (trigger).

The flames are drawn by a script, flame.luau (a ScriptedDrawable per fire):
layered contours whose edges are pushed about by noise scrolling upward. The
coals, the bowl and the glow are markup.
"""

import math
import random
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "scene.rml"

# Fixed ids: the view model, its properties and the converters.
VM, P_LIT, P_INTENSITY, P_COLOR, P_FLARE, VM_INST = "0:40", "0:41", "0:42", "0:43", "0:44", "0:45"

C_LIT_NUM = "0:50"     # boolean -> number
C_LEVEL = "0:51"       # lit * clamp(intensity, 0, 1.5)
C_FIRE_OPACITY = "0:53"
C_GLOW_OPACITY = "0:55"
C_COAL_HEAT = "0:56"
SCRIPT = "0:80"         # flame.luau
# One group (and one interpolator) per kind of bind.
GROUPS = {
    "level": ("0:64", "0:74", None),
    "opacity": ("0:60", "0:70", C_FIRE_OPACITY),
    "glow": ("0:62", "0:72", C_GLOW_OPACITY),
    "coals": ("0:63", "0:73", C_COAL_HEAT),
}

KEY_X, KEY_Y, KEY_ROT, KEY_SX, KEY_SY, KEY_OPACITY = 13, 14, 15, 16, 17, 18
KEY_COLOR, KEY_STOP_COLOR = 37, 38

TAU = math.tau


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


def color_paint(default, bound=True):
    inner = bind(P_COLOR, KEY_COLOR) if bound else ""
    return f'<SolidColor colorValue="{default}" name="Color">{inner}</SolidColor>'


class Anim:
    """Collects keyframes for one LinearAnimation: {object id: {property key: [(frame, value)]}}."""

    def __init__(self, name, duration, loop=True):
        self.name, self.duration, self.loop = name, duration, loop
        self.id = ids()
        self.keys = {}

    def key(self, obj, prop, frames):
        self.keys.setdefault(obj, {})[prop] = frames

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


def jitter_loop(rng, duration, lo, hi, step=(5, 9)):
    """Random values between lo and hi every few frames, ending where it started (seamless loop)."""
    first = rng.uniform(lo, hi)
    frames, f = [(0, first)], 0
    while True:
        f += rng.randint(*step)
        if f >= duration - 3:
            break
        frames.append((f, rng.uniform(lo, hi)))
    frames.append((duration, first))
    return frames


class Artboard:
    """The animations an artboard's fires add to, shared by every cluster in it."""

    def __init__(self):
        self.pulse = Anim("Pulse", 89)
        self.idle = Anim("Idle", 1, loop=False)
        self.flare = Anim("Flare", 42, loop=False)

    def anims(self):
        return [self.pulse, self.idle, self.flare]

    def state_machine(self):
        sm_id = ids()
        layers = []
        for anim in [self.pulse]:
            state = ids()
            layers.append(f'''        <StateMachineLayer name="{anim.name}" id="{ids()}">
            <EntryState x="-200" y="0"><StateTransition stateToId="{state}"/></EntryState>
            <AnimationState x="0" y="0" animationId="{anim.id}" id="{state}"/>
        </StateMachineLayer>''')
        idle, flare = ids(), ids()
        layers.append(f'''        <StateMachineLayer name="Flare" id="{ids()}">
            <AnyState x="0" y="-120">
                <StateTransition stateToId="{flare}">
                    <TransitionViewModelCondition>
                        <TransitionPropertyViewModelComparator>
                            <BindablePropertyTrigger>
                                {bind(P_FLARE, 686)}
                            </BindablePropertyTrigger>
                        </TransitionPropertyViewModelComparator>
                        <TransitionValueTriggerComparator/>
                    </TransitionViewModelCondition>
                </StateTransition>
            </AnyState>
            <EntryState x="-200" y="0"><StateTransition stateToId="{idle}"/></EntryState>
            <AnimationState x="0" y="0" animationId="{self.idle.id}" id="{idle}"/>
            <AnimationState x="200" y="0" animationId="{self.flare.id}" reset="true" id="{flare}">
                <StateTransition stateToId="{idle}" enableExitTime="true" exitTimeIsPercetange="true" exitTime="100"/>
            </AnimationState>
        </StateMachineLayer>''')
        return sm_id, f'<StateMachine name="Fire" id="{sm_id}">\n' + "\n".join(layers) + "\n</StateMachine>"


def cluster(ab, rng, x, y, size, glow=300, squash=0.6):
    """One fire with its base at (x, y): the scripted flame standing up from it,
    a hot spot on the coals and a glow on the floor (both squashed, as the floor
    is seen at an angle). `size` is the flame's width at intensity 1."""
    glow_id, flare = ids(), ids()
    seed = rng.uniform(0, 100)
    ab.pulse.key(glow_id, KEY_SX, jitter_loop(rng, ab.pulse.duration, 0.94, 1.04, (6, 12)))
    ab.pulse.key(glow_id, KEY_SY, [(f, v) for f, v in ab.pulse.keys[glow_id][KEY_SX]])
    ab.idle.key(flare, KEY_SX, [(0, 1)])
    ab.idle.key(flare, KEY_SY, [(0, 1)])
    for k in (KEY_SX, KEY_SY):
        ab.flare.key(flare, k, [(0, 1), (7, 1.35), (16, 1.25), (42, 1)])
    hot = size * 0.9

    def radial(name, width, group):
        return f'''<Shape name="{name}"{' id="' + glow_id + '"' if name == "Glow" else ""}>
                {bind(P_LIT, KEY_OPACITY, GROUPS[group][0])}
                <Ellipse width="{width:.1f}" height="{width:.1f}" name="Path"/>
                <Fill blendModeValue="screen" name="Fill">
                    <RadialGradient startX="0" startY="0" endX="{width / 2:.1f}" endY="0" name="Gradient">
                        <GradientStop colorValue="FFFF7A1A" position="0">{bind(P_COLOR, KEY_STOP_COLOR)}</GradientStop>
                        <GradientStop colorValue="00000000" position="1"/>
                    </RadialGradient>
                </Fill>
            </Shape>'''

    return f'''<Node x="{x}" y="{y}" name="Fire Cluster">
    <ScriptedDrawable scriptAssetId="{SCRIPT}" name="Flame">
        <ScriptInputNumber propertyValue="1" name="level">{bind(P_LIT, 243, GROUPS["level"][0])}</ScriptInputNumber>
        <ScriptInputColor propertyValue="FFFF7A1A" name="color">{bind(P_COLOR, 836)}</ScriptInputColor>
        <ScriptInputTrigger name="flare">{bind(P_FLARE, 870)}</ScriptInputTrigger>
        <ScriptInputNumber propertyValue="{size}" name="size"/>
        <ScriptInputNumber propertyValue="{seed:.2f}" name="seed"/>
    </ScriptedDrawable>
    <Node scaleY="{squash}" name="Floor Light">
        <Node name="Flare" id="{flare}">
            {radial("Hot Spot", hot, "opacity")}
            {radial("Glow", glow, "glow")}
        </Node>
    </Node>
</Node>'''


def arc(cx, cy, rx, ry, a0, a1, steps=24):
    """Points along an ellipse from angle a0 to a1 (radians, 0 = right, pi/2 = bottom)."""
    return [(cx + rx * math.cos(a0 + (a1 - a0) * i / steps), cy + ry * math.sin(a0 + (a1 - a0) * i / steps))
            for i in range(steps + 1)]


def points(pts, closed=False):
    verts = "".join(f'<StraightVertex x="{px:.2f}" y="{py:.2f}" name="V"/>' for px, py in pts)
    return f'<PointsPath isClosed="{str(closed).lower()}" isClockwise="true" name="Path">{verts}</PointsPath>'


def iron(color, width):
    return f'<Stroke thickness="{width}" cap="round" name="Iron"><SolidColor colorValue="{color}" name="Color"/></Stroke>'


def fill(color):
    return f'<Fill name="Fill"><SolidColor colorValue="{color}" name="Color"/></Fill>'


def coals(rng, x, y, radius, count, size=(13, 24), squash=1.0):
    """A bed of coals: dark lumps, with a hot copy on top whose opacity follows the fire."""
    lumps = []
    for _ in range(count):
        r = radius * math.sqrt(rng.random())
        a = rng.uniform(0, TAU)
        lumps.append((r * math.cos(a), r * math.sin(a), rng.uniform(*size), rng.uniform(*size), rng.uniform(0, TAU)))

    def layer(name, colors, extra=""):
        shapes = []
        for i, (lx, ly, w, h, rot) in enumerate(lumps):
            shapes.append(f'''        <Shape x="{lx:.1f}" y="{ly:.1f}" rotation="{rot:.3f}" name="Coal">
            <Ellipse width="{w:.1f}" height="{h:.1f}" name="Path"/>
            <Fill name="Fill"><SolidColor colorValue="{colors[i % len(colors)]}" name="Color"/></Fill>
        </Shape>''')
        return f'''    <Node name="{name}"{extra}>
''' + "\n".join(shapes) + "\n    </Node>"

    hot = layer("Hot Coals", ["FFC2491C", "FFE0702A", "FFA93514"])
    hot = hot.replace('<Node name="Hot Coals">', f'<Node name="Hot Coals">\n        {bind(P_LIT, KEY_OPACITY, GROUPS["coals"][0])}', 1)
    dark = layer("Coals", ["FF2E2420", "FF3A2C25", "FF241C19"])
    return f'<Node x="{x}" y="{y}" scaleY="{squash}" name="Coal Bed">\n{hot}\n{dark}\n</Node>'


def artboard_xml(name, width, height, content_fn, at=(0, 0), extra_style=""):
    ab = Artboard()
    style = ids()
    content = content_fn(ab)
    sm_id, sm = ab.state_machine()
    anims = "\n".join(a.xml() for a in ab.anims())
    return f'''<Artboard viewModelId="{VM}" viewModelInstanceId="{VM_INST}" defaultStateMachineId="{sm_id}" styleId="{style}"
          x="{at[0]}" y="{at[1]}" width="{width}" height="{height}" name="{name}" id="{ids()}">
<LayoutComponentStyle{extra_style} name="Artboard Style" id="{style}"/>
{content}
{sm}
{anims}
</Artboard>'''


def brazier(ab):
    """An iron bowl on three legs, seen from above at an angle: the rim is an
    ellipse, the bowl's side shows below it, and the fire stands up out of it.
    The rim's front edge is drawn over the fire's base, its back edge behind."""
    rng = random.Random(11)
    cx, cy, rx, ry = 150, 186, 92, 42
    legs = "\n".join(f'''<Shape name="Leg">{points([(x0, y0), (x1, y1)])}{iron("FF241F1B", 7)}</Shape>
<Shape x="{x1}" y="{y1 + 2}" name="Foot"><Ellipse width="14" height="6" name="Path"/>{fill("FF241F1B")}</Shape>'''
                      for x0, y0, x1, y1 in [(150, 250, 150, 284), (82, 226, 70, 266), (218, 226, 230, 266)])
    side = f'''<LinearGradient startX="0" startY="{cy}" endX="0" endY="{cy + 66}" name="Gradient"><GradientStop colorValue="FF3E352E" position="0"/><GradientStop colorValue="FF1C1815" position="1"/></LinearGradient>'''
    return "\n".join([
        f'<Shape name="Rim Front Shine">{points(arc(cx, cy + 3, rx - 4, ry - 1, 0.35, math.pi - 0.35))}{iron("FF6E5F52", 2)}</Shape>',
        f'<Shape name="Rim Front">{points(arc(cx, cy, rx, ry, -0.05, math.pi + 0.05))}{iron("FF2F2925", 12)}</Shape>',
        cluster(ab, rng, cx, cy - 4, 112, glow=330, squash=0.55),
        f'<Shape name="Rim Back">{points(arc(cx, cy, rx, ry, math.pi, 2 * math.pi))}{iron("FF3A322C", 12)}</Shape>',
        coals(rng, cx, cy, 72, 26, squash=0.46),
        f'<Shape x="{cx}" y="{cy}" name="Inside"><Ellipse width="{2 * rx}" height="{2 * ry}" name="Path"/>{fill("FF151210")}</Shape>',
        f'<Shape name="Bowl Side">{points(arc(cx, cy, rx, 66, 0, math.pi), True)}<Fill name="Fill">{side}</Fill></Shape>',
        legs,
        f'<Shape x="164" y="278" name="Shadow"><Ellipse width="220" height="56" name="Path"/>{fill("50000000")}</Shape>',
    ])


def torch(ab):
    """A torch in a wall bracket, seen from above at an angle: the wall is the
    bottom edge, the arm reaches out from it, and the flame stands up from the cup."""
    rng = random.Random(23)
    cx, cy = 80, 98
    return "\n".join([
        f'<Shape name="Cup Rim Front">{points(arc(cx, cy, 18, 7, 0, math.pi))}{iron("FF3A322C", 4)}</Shape>',
        cluster(ab, rng, cx, cy - 2, 40, glow=300, squash=0.6),
        f'<Shape name="Cup Rim Back">{points(arc(cx, cy, 18, 7, math.pi, 2 * math.pi))}{iron("FF4A4038", 4)}</Shape>',
        f'<Shape x="{cx}" y="{cy}" name="Pitch"><Ellipse width="34" height="13" name="Path"/>{fill("FF1A1411")}</Shape>',
        f'<Shape name="Cup">{points(arc(cx, cy, 18, 18, 0, math.pi), True)}{fill("FF2A241F")}</Shape>',
        f'<Shape x="{cx}" y="128" name="Arm"><Rectangle width="9" height="46" name="Path"/>{fill("FF2F2925")}</Shape>',
        f'''<Shape x="{cx}" y="152" name="Wall Plate">
    <Rectangle width="54" height="14" cornerRadiusTL="3" name="Path"/>
    {fill("FF3A322C")}
    <Stroke thickness="2" name="Stroke"><SolidColor colorValue="FF1A1512" name="Color"/></Stroke>
</Shape>''',
        f'<Shape x="{cx + 8}" y="136" name="Arm Shadow"><Rectangle width="10" height="30" name="Path"/>{fill("40000000")}</Shape>',
    ])


def trough(ab):
    """Flex boxes: the trough fills the artboard, five fire slots spread along it."""
    rng = random.Random(37)
    slots = []
    for i in range(5):
        slot_style = ids()
        slots.append(f'''            <LayoutComponent clip="false" width="54" height="64" styleId="{slot_style}" name="Fire Slot {i + 1}" id="{ids()}">
                <LayoutComponentStyle layoutWidthScaleType="fixed" layoutHeightScaleType="fixed" name="Slot Style" id="{slot_style}"/>
                <Node name="Slot Art">
{indent(cluster(ab, rng, 27, 46, 40, glow=220, squash=0.6), 20)}
{indent(coals(rng, 27, 46, 24, 9, size=(10, 18), squash=0.55), 20)}
                </Node>
            </LayoutComponent>''')
    root_style, bed_style, coal_style = ids(), ids(), ids()
    pad = lambda side, v: f' padding{side}="{v}" padding{side}UnitsValue="points"'
    all_pad = lambda v: "".join(pad(s, v) for s in ("Left", "Right", "Top", "Bottom"))
    corners = lambda v: f' cornerRadiusTL="{v}"'
    return f'''<LayoutComponent clip="false" width="400" height="100" styleId="{root_style}" name="Root" id="{ids()}">
    <LayoutComponentStyle layoutWidthScaleType="fill" layoutHeightScaleType="fill"{all_pad(6)} name="Root Style" id="{root_style}"/>
    <LayoutComponent clip="false" width="388" height="88" styleId="{bed_style}" name="Trough" id="{ids()}">
        <LayoutComponentStyle layoutWidthScaleType="fill" layoutHeightScaleType="fill"{all_pad(8)}{corners(20)} name="Trough Style" id="{bed_style}"/>
        <Fill name="Iron"><SolidColor colorValue="FF2F2925" name="Color"/></Fill>
        <Stroke thickness="3" name="Edge"><SolidColor colorValue="FF75665A" name="Color"/></Stroke>
        <LayoutComponent clip="false" width="372" height="72" styleId="{coal_style}" name="Coal Bed" id="{ids()}">
            <LayoutComponentStyle layoutWidthScaleType="fill" layoutHeightScaleType="fill" flexDirectionValue="row"
                                  layoutAlignmentType="spaceBetweenCenter"{corners(14)}{pad("Left", 6)}{pad("Right", 6)} name="Coal Bed Style" id="{coal_style}"/>
            <Fill name="Ash"><SolidColor colorValue="FF1C1613" name="Color"/></Fill>
{chr(10).join(slots)}
        </LayoutComponent>
    </LayoutComponent>
</LayoutComponent>'''


def indent(text, n):
    return "\n".join(" " * n + line for line in text.splitlines())


def converters():
    def group(gid, interp, final):
        last = f'\n    <DataConverterGroupItem converterId="{final}"/>' if final else ""
        return f'''<DataConverterInterpolator interpolationType="linear" duration="0.6" name="Ease" id="{interp}"/>
<DataConverterGroup name="Lit and intensity" id="{gid}">
    <DataConverterGroupItem converterId="{C_LIT_NUM}"/>
    <DataConverterGroupItem converterId="{C_LEVEL}"/>
    <DataConverterGroupItem converterId="{interp}"/>{last}
</DataConverterGroup>'''

    groups = "\n".join(group(*g) for g in GROUPS.values())
    return f'''<DataConverterToNumber name="Lit as number" id="{C_LIT_NUM}"/>
<!-- input * min(1.5, max(0, intensity)) -->
<DataConverterFormula name="Fire level" id="{C_LEVEL}">
    <FormulaTokenInput/>
    <FormulaTokenOperation operationType="2"/>
    <FormulaTokenFunction functionType="0"/>
    <FormulaTokenValue operationValue="1.5"/>
    <FormulaTokenArgumentSeparator/>
    <FormulaTokenFunction functionType="1"/>
    <FormulaTokenValue operationValue="0"/>
    <FormulaTokenArgumentSeparator/>
    <FormulaTokenValue>{bind(P_INTENSITY, 777)}</FormulaTokenValue>
    <FormulaTokenParenthesisClose/>
    <FormulaTokenParenthesisClose/>
</DataConverterFormula>
<!-- min(1, input * 4): the fire shows as soon as the level rises -->
<DataConverterFormula name="Fire opacity" id="{C_FIRE_OPACITY}">
    <FormulaTokenFunction functionType="0"/>
    <FormulaTokenValue operationValue="1"/>
    <FormulaTokenArgumentSeparator/>
    <FormulaTokenInput/>
    <FormulaTokenOperation operationType="2"/>
    <FormulaTokenValue operationValue="4"/>
    <FormulaTokenParenthesisClose/>
</DataConverterFormula>
<!-- min(1, input) * 0.5: the glow's gradient starts at full colour -->
<DataConverterFormula name="Glow opacity" id="{C_GLOW_OPACITY}">
    <FormulaTokenFunction functionType="0"/>
    <FormulaTokenValue operationValue="1"/>
    <FormulaTokenArgumentSeparator/>
    <FormulaTokenInput/>
    <FormulaTokenParenthesisClose/>
    <FormulaTokenOperation operationType="2"/>
    <FormulaTokenValue operationValue="0.5"/>
</DataConverterFormula>
<!-- 0.12 + (0.88 * min(1, input)): embers keep a faint glow when the fire is out -->
<DataConverterFormula name="Coal heat" id="{C_COAL_HEAT}">
    <FormulaTokenValue operationValue="0.12"/>
    <FormulaTokenOperation operationType="0"/>
    <FormulaTokenParenthesisOpen/>
    <FormulaTokenValue operationValue="0.88"/>
    <FormulaTokenOperation operationType="2"/>
    <FormulaTokenFunction functionType="0"/>
    <FormulaTokenValue operationValue="1"/>
    <FormulaTokenArgumentSeparator/>
    <FormulaTokenInput/>
    <FormulaTokenParenthesisClose/>
    <FormulaTokenParenthesisClose/>
</DataConverterFormula>
{groups}'''


def main():
    artboards = [
        artboard_xml("Brazier", 300, 300, brazier),
        artboard_xml("Torch", 160, 160, torch, at=(400, 0)),
        artboard_xml("Trough", 400, 100, trough, at=(0, 400)),
    ]
    vm = f'''<ViewModel defaultInstanceId="{VM_INST}" name="Fire" id="{VM}">
    <ViewModelPropertyBoolean name="lit" id="{P_LIT}"/>
    <ViewModelPropertyNumber name="intensity" id="{P_INTENSITY}"/>
    <ViewModelPropertyColor name="color" id="{P_COLOR}"/>
    <ViewModelPropertyTrigger name="flare" id="{P_FLARE}"/>
    <ViewModelInstance exports="true" name="Default" id="{VM_INST}">
        <ViewModelInstanceBoolean propertyValue="true" viewModelPropertyId="{P_LIT}"/>
        <ViewModelInstanceNumber propertyValue="1" viewModelPropertyId="{P_INTENSITY}"/>
        <ViewModelInstanceColor propertyValue="FFFF7A1A" viewModelPropertyId="{P_COLOR}"/>
        <ViewModelInstanceTrigger viewModelPropertyId="{P_FLARE}"/>
    </ViewModelInstance>
</ViewModel>'''
    body = "\n\n".join([*artboards, converters(), f'<ScriptAsset file="flame.luau" name="flame" id="{SCRIPT}"/>', vm])
    header = "<!-- Generated by tools/gen_scene.py; edit that, not this. -->\n"
    OUT.write_text(f'<Rive version="1" kind="fragment">\n{header}{body}\n</Rive>\n', encoding="utf-8", newline="\n")
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
