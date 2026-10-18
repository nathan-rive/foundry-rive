# Sign (a hanging signboard and a banner)

Text bound to data, in two artboards that share one view model. Built with the Rive CLI, **no scripts**, so a local build (`rive . --once`) runs on web runtimes without signing. `scene.rml` is generated: edit `tools/gen_scene.py` and run `py -I tools/gen_scene.py`.

![States](preview/sign_states.png)

*Top: the default sign; blue edge with gold lettering; the two banners. Bottom: the sign laid out at 700×160, and at 360×240 with a long name.*

| Artboard | Size | Use |
|---|---|---|
| `Sign` | 480×200 | A wooden signboard hanging from two rings, built from flex boxes for the **Layout** fit: a wider or deeper tile gives a bigger board (the rings stay near the ends), and the lettering shrinks to fit whatever text it gets. It sways gently, and swings when bumped. |
| `Banner` | 220×380 | A swallowtail cloth banner on a crossbar, rippling in the wind, with a star emblem and the same text. Contain fit. |

## Data (view model `Sign`)

| Property | Type | Default | Does |
|---|---|---|---|
| `text` | string | `The Gilded Flagon` | The sign's lettering and the banner's title, one line, shrunk to fit. |
| `color` | color | `#8E2B23` | The banner's cloth and the sign's painted edge. |
| `textColor` | color | `#F0DDB0` | The lettering, and the banner's emblem. |
| `swing` | trigger | | The sign swings and settles (as when someone bumps it). |

## How it's built

- **Sign:** a column of a row of hanger rings (`spaceBetween`, padded in from the ends) and the board. The board is a `stack` layout: three planks (a flex column), the lettering's shadow (offset 3 px) and the lettering, overlapping. The lettering is a `Text` with a `fill` participant and `fitFontSize`, so it centres and shrinks to the board. The board pivots at its top centre (`ComponentOrigin`), so the sway and the swing rotate it about the rings. The swing layer is after the sway layer, so it overrides the sway while it plays.
- **Banner:** the cloth is a `PointsPath` whose side vertices and tails ripple, more the further down they are; a second copy of the path carries a band of shadow folds, a linear gradient that drifts with the wave. The emblem and title follow the ripple.
- **Font:** IM Fell English (SIL Open Font License, `fonts/OFL.txt`).

Checked with CLI screenshots (each state above) and in the 2.44.2 web runtime the module uses: both artboards load, the sign lays out with `Fit.Layout`, and `text`, `color` and `swing` changed live behave as in the CLI.
