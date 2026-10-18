# Magic Ritual Circle (Rive tile)

A 600x600 artboard = **6x6 grid squares at 100px**. Transparent except for the
carved lines and the light, so it sits over any stone floor texture.

## Layout (grid cells, col,row from top-left)

| Ritual site | Cell  | Bound boolean  |
|-------------|-------|----------------|
| Site 1      | (4,4) | `site1Active`  |
| Site 2      | (0,3) | `site2Active`  |
| Site 3      | (3,0) | `site3Active`  |

The central circle sits at the sites' centroid (283,283), so the three
conduits are the same length. Each site fills exactly one grid square.

## Data binding

View model `RitualCircle`, default instance `Default` (all three `true`).
The `Ritual` state machine must be running (it is the artboard's default).

| Active sites | Center                                                               |
|--------------|----------------------------------------------------------------------|
| 0            | Dormant: dull engravings, a barely-there ember breathing in the core |
| 1            | Stirring: outer band rings glow dimly                               |
| 2            | Awakened: band bright, hexagram sigil + core lit, slow outer halo    |
| 3            | Full ritual: inner ring, bloom, flashing rays, orbiting sparks, shockwave pulses |

Independently, each active site lights its own circle, its conduit (energy
flows toward the center) and the third of the outer rune band facing it.
Power-ups blend in over 0.7s; power-downs fade out over 1.1s.

## Editing

`scene.rml` is generated. Change `tools/gen_scene.py` (palette, radii, rune
set, timings) and run `python3 tools/gen_scene.py`, then `rive . --verify`.
Preview combinations with e.g. `rive . --data=site2Active=false`.
