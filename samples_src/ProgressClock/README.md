# Progress Clock

A Blades-in-the-Dark-style progress clock: a pie split into segments that fills one segment at a time. A 400×460 artboard (`Clock`) with a transparent background, for a journal page the GM drives live or a scene tile. Built with the Rive CLI from `scene.rml`, with **no scripts**, so a local build (`rive . --once`) runs on web runtimes without signing.

## Data (view model `ProgressClock`)

| Property | Type | Default | Does |
|---|---|---|---|
| `segments` | number | 6 | How many segments. Any whole number works; 4, 6 and 8 are the usual. |
| `filled` | number | 2 | How many are filled. The fill sweeps to the new value, and the clock pops. |
| `color` | color | `#C8452D` | The fill colour. |
| `label` | string | `Clock` | The name under the clock; long names shrink to fit. |
| `tick` | trigger | | Pops the clock without changing it (for "the clock ticks" moments). |

## How it's built

- **Fill:** one ellipse drawn as a stroke as thick as the clock's radius, so a stroke reads as a pie. A `TrimPath` ends at `filled / segments` (a formula converter, clamped to 0–1), eased by an interpolator converter.
- **Dividers:** the same thick ellipse with a `DashPath`: a thin dash, then a gap of `1 / segments` of the path (percentage dashes). One shape draws any number of dividers.
- **Pop:** the state machine's any-state goes to a one-shot `Pop` (a scale bump and a flash ring) when `tick` fires, or when `filled` changes (a `DataConverterTrigger` on `filled`). It doesn't pop when the file loads.
- **Font:** IM Fell English (SIL Open Font License, `fonts/OFL.txt`), as in AnimatedScroll.

Checked with CLI screenshots (4, 6 and 8 segments, the label, colour, `tick`, and a `filled` change mid-run), and in the 2.44.2 web runtime the module uses, with the values set live.
