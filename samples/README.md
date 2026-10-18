# Sample animations

Rive files that ship with Rive for Foundry, for tiles, tokens and journal pages. Foundry serves them from the module folder, so pick them with the file picker at `modules/foundry-rive/samples/` and nothing is uploaded into your world. Their sources (RML, scripts and a README with each file's properties) are in the repository's `samples_src/` folder.

| File | Artboards | Use | View model properties |
|---|---|---|---|
| `progress-clock.riv` | `Clock` | Journal page or tile: a Blades-style progress clock | `segments`, `filled`, `color`, `label`, `tick` |
| `brazier.riv` | `Brazier`, `Torch`, `Trough` | Scene tiles: fire seen from above (`Trough` is made for the Layout fit) | `lit`, `intensity`, `color`, `flare` |
| `sign.riv` | `Sign`, `Banner` | Scene tiles: a hanging sign and a banner seen from above (`Sign` is made for the Layout fit) | `text`, `color`, `textColor`, `swing` |
| `treasure-chest.riv` | `Chest` | Scene tile: a chest that opens on cue | `state` (closed/open/empty), `color`, `locked`, `sparkle` |
| `mechanisms.riv` | `Plate`, `Lever`, `Gate` | Scene tiles wired together with Monk's Active Tile Triggers | `pressed`, `color` / `pulled` / `open`, `rattle` |
| `door.riv` | `Door` | Journal page: a door in a stone archway | `state` (closed/open/locked), `color`, `knock`, `rattle` |

The fonts in `progress-clock.riv` and `sign.riv` are IM Fell English, under the SIL Open Font License (`OFL-IMFellEnglish.txt`).
