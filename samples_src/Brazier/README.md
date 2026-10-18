# Brazier (fire, seen from above)

Top-down fire for scene tiles, in three artboards that share one view model. Built with the Rive CLI, **no scripts**, so a local build (`rive . --once`) runs on web runtimes without signing. `scene.rml` is generated: edit `tools/gen_scene.py` and run `py -I tools/gen_scene.py`.

![States](preview/fire_states.png)

*Top: out, intensity 0.3, the default, green at 1.5, mid-flare. Bottom: the torch, and the trough at 400×100 and laid out at 700×100.*

| Artboard | Size | Use |
|---|---|---|
| `Brazier` | 300×300 | A round iron bowl of coals with its fire and glow. A 3×3 tile at 100 px squares. Contain fit. |
| `Torch` | 160×160 | A wall torch seen from above; the wall runs along the bottom edge, so rotate the tile to face the wall. |
| `Trough` | 400×100 | A long fire trough built from flex boxes, for the **Layout** fit: a longer or deeper tile gets a longer or deeper trough, with its five fires spread along it, instead of a stretched one. Made for 3:1 and longer. |

## Data (view model `Fire`)

| Property | Type | Default | Does |
|---|---|---|---|
| `lit` | boolean | true | Lights or puts out the fire; it fades over 0.6 s and the embers keep a faint glow. |
| `intensity` | number | 1 | 0 to 1.5: the fire's size and the glow's strength (eased). |
| `color` | color | `#FF7A1A` | The flame and glow colour, for magic fire. The white-hot core and the coals stay as they are. |
| `flare` | trigger | | A burst: the fire leaps up and settles. |

## How it's built

- Each fire is a cluster: flame tongues (ellipses radiating from the core, screen-blended), a white-to-flame-colour core, sparks that rise outwards and fade, and a radial-gradient glow under it. Every cluster has its own seeded random flicker, spread over three looping layers of different lengths (47, 61 and 73 frames) so the pattern doesn't visibly repeat, plus a slow pulse and a sparks loop.
- `lit` and `intensity` drive the fire through converter groups: boolean to number, `lit × clamp(intensity, 0, 1.5)`, a 0.6 s interpolator, then one formula per use (fire opacity, fire scale, glow opacity, coal heat). Each group has its own interpolator.
- `flare` is a one-shot on its own state machine layer, from the any-state.

Checked with CLI screenshots (each state above, the trough at 300, 400 and 700 wide and 300×200) and in the 2.44.2 web runtime the module uses: all three artboards load and play, and `lit`, `color` and `flare` changed live behave as in the CLI.
