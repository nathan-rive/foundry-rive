"""Generates scene.rml for the Brazier sample: top-down fire in three artboards.

    py -I tools/gen_scene.py        (from the project folder)

- Brazier (300x300): a round iron bowl of coals with a fire and its glow.
- Torch (160x160): a wall torch seen from above, the wall along the bottom edge.
- Trough (400x100): a long fire trough laid out with flex boxes, for the Layout
  fit: a wider or taller tile shows a longer trough instead of a stretched one.

All three share the view model Fire: lit (boolean), intensity (number, 0-1.5),
color (the flame colour), flare (trigger). No scripts.

Each fire is a cluster of shapes: flame tongues around a hot core, sparks, and a
glow. Every cluster gets its own random flicker (seeded, so the output is stable).
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
C_FIRE_SCALE = "0:54"
C_GLOW_OPACITY = "0:55"
C_COAL_HEAT = "0:56"
# One group (and one interpolator) per kind of bind.
GROUPS = {
    "opacity": ("0:60", "0:70", C_FIRE_OPACITY),
    "scale": ("0:61", "0:71", C_FIRE_SCALE),
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
        self.flicker = [Anim("Flicker A", 47), Anim("Flicker B", 61), Anim("Flicker C", 73)]
        self.pulse = Anim("Pulse", 89)
        self.sparks = Anim("Sparks", 100)
        self.idle = Anim("Idle", 1, loop=False)
        self.flare = Anim("Flare", 42, loop=False)

    def anims(self):
        return [*self.flicker, self.pulse, self.sparks, self.idle, self.flare]

    def state_machine(self):
        sm_id = ids()
        layers = []
        for anim in [*self.flicker, self.pulse, self.sparks]:
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


def cluster(ab, rng, x, y, scale, glow=300):
    """One fire, centred on (x, y), drawn at `scale` (1 = a fire about 140px across)."""
    fire, flare = ids(), ids()
    parts = []

    # Sparks: drawn on top, rising outwards and fading, at staggered times.
    for i in range(5):
        spark = ids()
        angle = rng.uniform(0, TAU)
        start = rng.randint(0, 99)
        rise = rng.randint(36, 52)
        dist = rng.uniform(55, 85)
        parts.append(f'''<Node rotation="{angle:.4f}" name="Spark Path">
    <Shape name="Spark" id="{spark}" opacity="0">
        <Ellipse width="{rng.uniform(4, 7):.1f}" height="{rng.uniform(4, 7):.1f}" name="Path"/>
        <Fill blendModeValue="screen" name="Fill"><SolidColor colorValue="FFFFE2A0" name="Color"/></Fill>
    </Shape>
</Node>''')
        # Keyframes over a 100-frame loop, wrapping around the end.
        ys, ops = [], []
        for f in range(0, 101, 4):
            t = ((f - start) % 100) / rise
            if t <= 1:
                ys.append((f, -dist * t))
                ops.append((f, math.sin(math.pi * t) * 0.95))
            else:
                ys.append((f, 0.0))
                ops.append((f, 0.0))
        ab.sparks.key(spark, KEY_Y, ys)
        ab.sparks.key(spark, KEY_OPACITY, ops)

    # The hot core: white, warm white, then the flame colour.
    core = ids()
    parts.append(f'''<Shape name="Core White">
    <Ellipse width="20" height="20" name="Path"/>
    <Fill blendModeValue="screen" name="Fill"><SolidColor colorValue="FFFFF8E8" name="Color"/></Fill>
</Shape>
<Shape name="Core Warm" opacity="0.9">
    <Ellipse width="40" height="40" name="Path"/>
    <Fill blendModeValue="screen" name="Fill"><SolidColor colorValue="FFFFE2A0" name="Color"/></Fill>
</Shape>
<Shape name="Core" id="{core}">
    <Ellipse width="66" height="66" name="Path"/>
    <Fill blendModeValue="screen" name="Fill">{color_paint("FFFF7A1A")}</Fill>
</Shape>''')
    ab.pulse.key(core, KEY_SX, jitter_loop(rng, ab.pulse.duration, 0.9, 1.1, (8, 14)))
    ab.pulse.key(core, KEY_SY, jitter_loop(rng, ab.pulse.duration, 0.9, 1.1, (8, 14)))

    # Flame tongues, radiating from the core; each one flickers on one of three loops.
    count = 7
    for i in range(count):
        tongue = ids()
        base = i * TAU / count + rng.uniform(-0.25, 0.25)
        length = rng.uniform(56, 74)
        width = rng.uniform(22, 30)
        parts.append(f'''<Node rotation="{base:.4f}" name="Tongue" id="{tongue}">
    <Shape y="{-length * 0.38:.1f}" name="Flame" opacity="0.85">
        <Ellipse width="{width:.1f}" height="{length:.1f}" name="Path"/>
        <Fill blendModeValue="screen" name="Fill">{color_paint("FFFF7A1A")}</Fill>
    </Shape>
</Node>''')
        anim = ab.flicker[i % 3]
        anim.key(tongue, KEY_SY, jitter_loop(rng, anim.duration, 0.65, 1.3))
        anim.key(tongue, KEY_SX, jitter_loop(rng, anim.duration, 0.8, 1.15))
        anim.key(tongue, KEY_ROT, [(f, base + v) for f, v in jitter_loop(rng, anim.duration, -0.14, 0.14)])

    ab.idle.key(flare, KEY_SX, [(0, 1)])
    ab.idle.key(flare, KEY_SY, [(0, 1)])
    for k in (KEY_SX, KEY_SY):
        ab.flare.key(flare, k, [(0, 1), (7, 1.6), (16, 1.45), (42, 1)])

    # The glow on the floor around the fire: under the fire, its own opacity bind.
    glow_id = ids()
    ab.pulse.key(glow_id, KEY_SX, jitter_loop(rng, ab.pulse.duration, 0.94, 1.04, (6, 12)))
    ab.pulse.key(glow_id, KEY_SY, [(f, v) for f, v in ab.pulse.keys[glow_id][KEY_SX]])
    g_opacity, g_scale = GROUPS["opacity"][0], GROUPS["scale"][0]
    inner = "\n".join("            " + line for p in parts for line in p.splitlines())
    return f'''<Node x="{x}" y="{y}" scaleX="{scale}" scaleY="{scale}" name="Fire Cluster">
    <Node name="Fire" id="{fire}">
        {bind(P_LIT, KEY_OPACITY, g_opacity)}
        {bind(P_LIT, KEY_SX, g_scale)}
        {bind(P_LIT, KEY_SY, g_scale)}
        <Node name="Flare" id="{flare}">
{inner}
        </Node>
    </Node>
    <Shape name="Glow" id="{glow_id}">
        {bind(P_LIT, KEY_OPACITY, GROUPS["glow"][0])}
        <Ellipse width="{glow}" height="{glow}" name="Path"/>
        <Fill blendModeValue="screen" name="Fill">
            <RadialGradient startX="0" startY="0" endX="{glow / 2}" endY="0" name="Gradient">
                <GradientStop colorValue="FFFF7A1A" position="0">{bind(P_COLOR, KEY_STOP_COLOR)}</GradientStop>
                <GradientStop colorValue="00000000" position="1"/>
            </RadialGradient>
        </Fill>
    </Shape>
</Node>'''


def coals(rng, x, y, radius, count, size=(13, 24)):
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
    return f'<Node x="{x}" y="{y}" name="Coal Bed">\n{hot}\n{dark}\n</Node>'


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
    rng = random.Random(11)
    return "\n".join([
        cluster(ab, rng, 150, 150, 1.0, glow=300),
        '''<Node x="150" y="150" name="Bowl">
    <Shape name="Rim Highlight">
        <Ellipse width="160" height="160" name="Path"/>
        <Stroke thickness="2" name="Stroke"><SolidColor colorValue="FF75665A" name="Color"/></Stroke>
    </Shape>
    <Shape name="Rim">
        <Ellipse width="150" height="150" name="Path"/>
        <Stroke thickness="14" name="Stroke"><SolidColor colorValue="FF2F2925" name="Color"/></Stroke>
    </Shape>
</Node>''',
        coals(rng, 150, 150, 52, 22),
        '''<Node x="150" y="150" name="Bowl Base">
    <Shape name="Inside">
        <Ellipse width="146" height="146" name="Path"/>
        <Fill name="Fill"><SolidColor colorValue="FF151210" name="Color"/></Fill>
    </Shape>
    <Shape name="Shadow">
        <Ellipse width="184" height="184" name="Path"/>
        <Fill name="Fill"><SolidColor colorValue="55000000" name="Color"/></Fill>
    </Shape>
</Node>''',
    ])


def torch(ab):
    """A torch in a wall bracket, seen from above: the wall is the bottom edge."""
    rng = random.Random(23)
    return "\n".join([
        cluster(ab, rng, 80, 70, 0.42, glow=330),
        '''<Node x="80" y="70" name="Torch Head">
    <Shape name="Cup Rim">
        <Ellipse width="40" height="40" name="Path"/>
        <Stroke thickness="5" name="Stroke"><SolidColor colorValue="FF3A322C" name="Color"/></Stroke>
    </Shape>
    <Shape name="Pitch">
        <Ellipse width="34" height="34" name="Path"/>
        <Fill name="Fill"><SolidColor colorValue="FF1A1411" name="Color"/></Fill>
    </Shape>
</Node>''',
        '''<Shape x="80" y="117" name="Arm">
    <Rectangle width="10" height="62" name="Path"/>
    <Fill name="Fill"><SolidColor colorValue="FF2F2925" name="Color"/></Fill>
</Shape>
<Shape x="80" y="152" name="Wall Plate">
    <Rectangle width="54" height="14" cornerRadiusTL="3" cornerRadiusTR="3" cornerRadiusBL="0" cornerRadiusBR="0" name="Path"/>
    <Fill name="Fill"><SolidColor colorValue="FF3A322C" name="Color"/></Fill>
    <Stroke thickness="2" name="Stroke"><SolidColor colorValue="FF1A1512" name="Color"/></Stroke>
</Shape>''',
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
{indent(cluster(ab, rng, 27, 32, 0.42, glow=330), 20)}
{indent(coals(rng, 27, 32, 24, 9, size=(10, 18)), 20)}
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
        return f'''<DataConverterInterpolator interpolationType="linear" duration="0.6" name="Ease" id="{interp}"/>
<DataConverterGroup name="Lit and intensity" id="{gid}">
    <DataConverterGroupItem converterId="{C_LIT_NUM}"/>
    <DataConverterGroupItem converterId="{C_LEVEL}"/>
    <DataConverterGroupItem converterId="{interp}"/>
    <DataConverterGroupItem converterId="{final}"/>
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
<!-- 0.35 + (0.65 * input) -->
<DataConverterFormula name="Fire scale" id="{C_FIRE_SCALE}">
    <FormulaTokenValue operationValue="0.35"/>
    <FormulaTokenOperation operationType="0"/>
    <FormulaTokenParenthesisOpen/>
    <FormulaTokenValue operationValue="0.65"/>
    <FormulaTokenOperation operationType="2"/>
    <FormulaTokenInput/>
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
    body = "\n\n".join([*artboards, converters(), vm])
    header = "<!-- Generated by tools/gen_scene.py; edit that, not this. -->\n"
    OUT.write_text(f'<Rive version="1" kind="fragment">\n{header}{body}\n</Rive>\n', encoding="utf-8", newline="\n")
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
