"""Generates scene.rml for the Sign sample: a hanging signboard and a banner.

    py -I tools/gen_scene.py        (from the project folder)

- Sign (480x200): a wooden signboard hanging from two rings, built from flex
  boxes for the Layout fit: a wider or taller tile gives a bigger board, and the
  lettering shrinks to fit whatever text it is given. It sways gently, and
  swings when `swing` fires.
- Banner (220x380): a swallowtail cloth banner on a crossbar, rippling in the
  wind, with an emblem and the same text.

Both share the view model Sign: text (string), color (the banner's cloth and
the board's painted edge), textColor (the lettering), swing (trigger). No scripts.
"""

import math
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "scene.rml"

VM, P_TEXT, P_COLOR, P_TEXT_COLOR, P_SWING, VM_INST = "0:40", "0:41", "0:42", "0:43", "0:44", "0:45"
FONT = "0:30"
KEY_ROT, KEY_OPACITY, KEY_X, KEY_Y = 15, 18, 13, 14
KEY_VX, KEY_VY = 24, 25
KEY_GRAD_START_X, KEY_GRAD_END_X = 42, 34
TAU = math.tau


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
    inner = bind(prop, 37) if prop else ""
    return f'<SolidColor colorValue="{color}" name="Color">{inner}</SolidColor>'


class Anim:
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


def sampled(duration, fn, step=6):
    """Keyframes of fn(t) every `step` frames, t from 0 to 1, always ending on the last frame."""
    frames = list(range(0, duration, step)) + [duration]
    return [(f, fn(f / duration)) for f in frames]


def units(**kw):
    """Layout style attributes with their units: units(paddingLeft=10) -> both attributes."""
    return "".join(f' {k}="{v}" {k}UnitsValue="points"' for k, v in kw.items())


def text_box(name, offset, color, prop):
    """A box filling the board (a stack, so it overlaps the planks), holding the lettering."""
    style, run_style = ids(), ids()
    dx, dy = offset
    return f'''<LayoutComponent clip="false" x="{dx}" y="{dy}" width="440" height="120" styleId="{style}" name="{name}" id="{ids()}">
    <LayoutComponentStyle layoutAlignmentType="center" layoutWidthScaleType="fill" layoutHeightScaleType="fill"{units(paddingLeft=22, paddingRight=22, paddingTop=8, paddingBottom=8)} name="{name} Style" id="{style}"/>
    <Text sizingValue="fixed" width="396" height="104" alignValue="center" verticalAlignValue="middle"
          overflowValue="fitFontSize" wrapValue="noWrap" name="{name} Text">
        <LayoutParticipant layoutWidthScaleType="fill" layoutHeightScaleType="fill" name="Fill"/>
        <TextStylePaint fontSize="76" fontAssetId="{FONT}" name="{name} Paint" id="{run_style}">
            <Fill name="Fill">{solid(color, prop)}</Fill>
        </TextStylePaint>
        <TextValueRun styleId="{run_style}" text="The Gilded Flagon" name="Run">{bind(P_TEXT, 268)}</TextValueRun>
    </Text>
</LayoutComponent>'''


def sign():
    sway, swing, idle = Anim("Sway", 300), Anim("Swing", 170, loop=False), Anim("Still", 1, loop=False)
    root_style, hang_style, board_style, planks_style = ids(), ids(), ids(), ids()
    board, hangers = ids(), ids()

    rings = "\n".join(f'''        <Shape name="Ring">
            <LayoutParticipant layoutWidthScaleType="hug" layoutHeightScaleType="hug" name="Hug"/>
            <Ellipse width="22" height="22" name="Path"/>
            <Stroke thickness="5" name="Iron">{solid("FF2B2724")}</Stroke>
        </Shape>''' for _ in range(2))

    plank_colors = ["FF6E4829", "FF65411F", "FF6A4526"]
    planks = []
    for c in plank_colors:
        s = ids()
        planks.append(f'''                <LayoutComponent clip="false" width="420" height="40" styleId="{s}" name="Plank" id="{ids()}">
                    <LayoutComponentStyle layoutWidthScaleType="fill" layoutHeightScaleType="fill" cornerRadiusTL="4" name="Plank Style" id="{s}"/>
                    <Fill name="Wood">{solid(c)}</Fill>
                    <Stroke thickness="1.5" name="Seam">{solid("FF3B2614")}</Stroke>
                </LayoutComponent>''')

    # Gentle sway, and a damped swing when bumped. The swing layer comes later,
    # so while it plays it overrides the sway.
    sway.key(board, KEY_ROT, sampled(sway.duration, lambda t: 0.018 * math.sin(TAU * t), step=10))
    swing.key(board, KEY_ROT, sampled(swing.duration, lambda t: 0.16 * math.exp(-t * 4.2) * math.sin(TAU * t * 3.4), step=4))
    idle.key(hangers, KEY_OPACITY, [(0, 1)])

    content = f'''<LayoutComponent clip="false" width="480" height="200" styleId="{root_style}" name="Root" id="{ids()}">
    <LayoutComponentStyle layoutWidthScaleType="fill" layoutHeightScaleType="fill" flexDirectionValue="column"{units(paddingLeft=10, paddingRight=10, paddingTop=4, paddingBottom=10)} name="Root Style" id="{root_style}"/>
    <LayoutComponent clip="false" width="460" height="26" styleId="{hang_style}" name="Hangers" id="{hangers}">
        <LayoutComponentStyle layoutWidthScaleType="fill" layoutHeightScaleType="fixed" flexDirectionValue="row"
                              layoutAlignmentType="spaceBetweenEnd"{units(paddingLeft=56, paddingRight=56)} name="Hangers Style" id="{hang_style}"/>
{rings}
    </LayoutComponent>
    <LayoutComponent clip="false" width="460" height="160" styleId="{board_style}" name="Board" id="{board}">
        <LayoutComponentStyle layoutTypeValue="stack" layoutWidthScaleType="fill" layoutHeightScaleType="fill"{units(paddingLeft=10, paddingRight=10, paddingTop=10, paddingBottom=10)} cornerRadiusTL="12" name="Board Style" id="{board_style}"/>
        <ComponentOrigin originX="0.5" originY="0" name="Hang Point"/>
        <Fill name="Backing">{solid("FF3E2816")}</Fill>
        <Stroke thickness="7" name="Painted Edge">{solid("FF8E2B23", P_COLOR)}</Stroke>
{text_box("Lettering", (0, 0), "FFF0DDB0", P_TEXT_COLOR)}
{text_box("Lettering Shadow", (3, 3), "AA1E120A", None)}
            <LayoutComponent clip="false" width="440" height="140" styleId="{planks_style}" name="Planks" id="{ids()}">
                <LayoutComponentStyle layoutWidthScaleType="fill" layoutHeightScaleType="fill" flexDirectionValue="column"{units(gapVertical=4)} name="Planks Style" id="{planks_style}"/>
{chr(10).join(planks)}
            </LayoutComponent>
    </LayoutComponent>
</LayoutComponent>'''
    return content, [sway], (idle, swing)


def banner():
    wave = Anim("Wave", 180)
    cloth, folds, grad, emblem, label = ids(), ids(), ids(), ids(), ids()

    # The cloth outline: (x, y, kind). Sides are smooth curves; the top hangs
    # from the bar and stays put; the further down, the more it ripples.
    outline = [
        (-75, 0, "s"), (75, 0, "s"),
        (75, 110, "c"), (75, 220, "c"),
        (75, 320, "s"), (0, 266, "s"), (-75, 320, "s"),
        (-75, 220, "c"), (-75, 110, "c"),
    ]

    def ripple(y, t):
        depth = y / 320
        return 8 * depth * math.sin(TAU * t - depth * 2.6)

    def path(prefix):
        verts, vids = [], []
        for x, y, kind in outline:
            vid = ids()
            vids.append((vid, x, y))
            if kind == "s":
                verts.append(f'<StraightVertex x="{x}" y="{y}" name="V" id="{vid}"/>')
            else:
                # Smooth, with vertical handles (pointing down the left side, up the right).
                rot = math.pi / 2 if x > 0 else -math.pi / 2
                verts.append(f'<CubicMirroredVertex x="{x}" y="{y}" rotation="{rot:.4f}" distance="38" name="V" id="{vid}"/>')
        for vid, x, y in vids:
            if y > 0:
                wave.key(vid, KEY_VX, sampled(wave.duration, lambda t, x=x, y=y: x + ripple(y, t)))
        return f'<PointsPath isClosed="true" isClockwise="true" name="{prefix} Path">' + "".join(verts) + "</PointsPath>"

    # Folds: a band of shadows across the cloth that drifts with the wave.
    wave.key(grad, KEY_GRAD_START_X, sampled(wave.duration, lambda t: -90 + 14 * math.sin(TAU * t)))
    wave.key(grad, KEY_GRAD_END_X, sampled(wave.duration, lambda t: 90 + 14 * math.sin(TAU * t)))
    wave.key(emblem, KEY_X, sampled(wave.duration, lambda t: 110 + ripple(150, t) * 0.6))
    wave.key(label, KEY_X, sampled(wave.duration, lambda t: 110 + ripple(64, t) * 0.6))

    stops = [(0, "30000000"), (0.22, "00000000"), (0.45, "26000000"), (0.62, "00000000"), (0.85, "22000000"), (1, "38000000")]
    stop_xml = "".join(f'<GradientStop colorValue="{c}" position="{p}"/>' for p, c in stops)
    label_style = ids()

    content = f'''<Node x="110" y="24" name="Pole">
    <Shape x="-104" name="Knob"><Ellipse width="18" height="18" name="Path"/><Fill name="Fill">{solid("FFC9A44A")}</Fill></Shape>
    <Shape x="104" name="Knob"><Ellipse width="18" height="18" name="Path"/><Fill name="Fill">{solid("FFC9A44A")}</Fill></Shape>
    <Shape name="Bar"><Rectangle width="204" height="12" cornerRadiusTL="6" name="Path"/><Fill name="Fill">{solid("FF4A2E1A")}</Fill></Shape>
</Node>
<Text x="110" y="64" sizingValue="fixed" width="128" height="34" originX="0.5" originY="0.5" alignValue="center"
      verticalAlignValue="middle" overflowValue="fitFontSize" wrapValue="noWrap" name="Label" id="{label}">
    <TextStylePaint fontSize="26" fontAssetId="{FONT}" name="Label Paint" id="{label_style}">
        <Fill name="Fill">{solid("FFF0DDB0", P_TEXT_COLOR)}</Fill>
    </TextStylePaint>
    <TextValueRun styleId="{label_style}" text="The Gilded Flagon" name="Run">{bind(P_TEXT, 268)}</TextValueRun>
</Text>
<Node x="110" y="170" name="Emblem" id="{emblem}">
    <Shape name="Star">
        <Star points="5" innerRadius="0.45" width="58" height="58" name="Path"/>
        <Fill name="Fill">{solid("FFF0DDB0", P_TEXT_COLOR)}</Fill>
    </Shape>
    <Shape name="Ring">
        <Ellipse width="86" height="86" name="Path"/>
        <Stroke thickness="5" name="Stroke">{solid("FFF0DDB0", P_TEXT_COLOR)}</Stroke>
    </Shape>
</Node>
<Shape x="110" y="30" name="Folds" id="{folds}">
    {path("Folds")}
    <Fill name="Fill"><LinearGradient startX="-90" startY="0" endX="90" endY="0" name="Folds" id="{grad}">{stop_xml}</LinearGradient></Fill>
</Shape>
<Shape x="110" y="30" name="Cloth" id="{cloth}">
    {path("Cloth")}
    <Stroke thickness="5" name="Trim">{solid("FFC9A44A")}</Stroke>
    <Fill name="Fill">{solid("FF8E2B23", P_COLOR)}</Fill>
</Shape>'''
    return content, [wave], None


def artboard(name, width, height, at, build):
    content, loops, swing = build()
    style, sm = ids(), ids()
    layers = []
    for anim in loops:
        st = ids()
        layers.append(f'''    <StateMachineLayer name="{anim.name}" id="{ids()}">
        <EntryState x="-200" y="0"><StateTransition stateToId="{st}"/></EntryState>
        <AnimationState x="0" y="0" animationId="{anim.id}" id="{st}"/>
    </StateMachineLayer>''')
    anims = list(loops)
    if swing:
        idle, swing_anim = swing
        anims += [idle, swing_anim]
        s_idle, s_swing = ids(), ids()
        layers.append(f'''    <StateMachineLayer name="Swing" id="{ids()}">
        <AnyState x="0" y="-120">
            <StateTransition stateToId="{s_swing}">
                <TransitionViewModelCondition>
                    <TransitionPropertyViewModelComparator>
                        <BindablePropertyTrigger>{bind(P_SWING, 686)}</BindablePropertyTrigger>
                    </TransitionPropertyViewModelComparator>
                    <TransitionValueTriggerComparator/>
                </TransitionViewModelCondition>
            </StateTransition>
        </AnyState>
        <EntryState x="-200" y="0"><StateTransition stateToId="{s_idle}"/></EntryState>
        <AnimationState x="0" y="0" animationId="{idle.id}" id="{s_idle}"/>
        <AnimationState x="200" y="0" animationId="{swing_anim.id}" reset="true" id="{s_swing}">
            <StateTransition stateToId="{s_idle}" enableExitTime="true" exitTimeIsPercetange="true" exitTime="100"/>
        </AnimationState>
    </StateMachineLayer>''')
    machine = f'<StateMachine name="Sign" id="{sm}">\n' + "\n".join(layers) + "\n</StateMachine>"
    return f'''<Artboard viewModelId="{VM}" viewModelInstanceId="{VM_INST}" defaultStateMachineId="{sm}" styleId="{style}"
          x="{at[0]}" y="{at[1]}" width="{width}" height="{height}" name="{name}" id="{ids()}">
<LayoutComponentStyle name="Artboard Style" id="{style}"/>
{content}
{machine}
{chr(10).join(a.xml() for a in anims)}
</Artboard>'''


def main():
    body = "\n\n".join([
        artboard("Sign", 480, 200, (0, 0), sign),
        artboard("Banner", 220, 380, (560, 0), banner),
        f'<FontAsset file="fonts/IMFellEnglish-Regular.ttf" name="IM Fell English" id="{FONT}"/>',
        f'''<ViewModel defaultInstanceId="{VM_INST}" name="Sign" id="{VM}">
    <ViewModelPropertyString name="text" id="{P_TEXT}"/>
    <ViewModelPropertyColor name="color" id="{P_COLOR}"/>
    <ViewModelPropertyColor name="textColor" id="{P_TEXT_COLOR}"/>
    <ViewModelPropertyTrigger name="swing" id="{P_SWING}"/>
    <ViewModelInstance exports="true" name="Default" id="{VM_INST}">
        <ViewModelInstanceString propertyValue="The Gilded Flagon" viewModelPropertyId="{P_TEXT}"/>
        <ViewModelInstanceColor propertyValue="FF8E2B23" viewModelPropertyId="{P_COLOR}"/>
        <ViewModelInstanceColor propertyValue="FFF0DDB0" viewModelPropertyId="{P_TEXT_COLOR}"/>
        <ViewModelInstanceTrigger viewModelPropertyId="{P_SWING}"/>
    </ViewModelInstance>
</ViewModel>''',
    ])
    header = "<!-- Generated by tools/gen_scene.py; edit that, not this. -->\n"
    OUT.write_text(f'<Rive version="1" kind="fragment">\n{header}{body}\n</Rive>\n', encoding="utf-8", newline="\n")
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
