# SpikeTrap

A Rive tile of a cobblestone trapdoor over a spiked pit, built with the Rive CLI
(RML + one Luau script).

- `scene.rml` — artboard, view model, state machine and timelines
- `trap.luau` — procedural cobbles, pit and spikes, and the stone-by-stone fall
- `build/SpikeTrap.riv` — the built file (`rive . --once` to rebuild)

## Integration contract

**Artboard** `SpikeTrap` · **State machine** `Trap` · **View model** `SpikeTrap`

| Property | Type | Default | Meaning |
|---|---|---|---|
| `state` | enum `TrapState`: `hidden` · `revealed` · `active` | `hidden` | The persistent trap state. Changing it plays the transition. |
| `stoneSize` | number (px) | 28 | Average cobble size. Sets cobble density. |
| `spikeSpacing` | number (px) | 22 | Average spike spacing. Sets spike density. |
| `seed` | number | 1 | Re-rolls the random layout. Use a per-tile value so neighbouring traps differ. |

**Size the tile with the runtime's Layout fit** (`Fit.Layout` / `fit: layout`), so
the artboard is *resized* to the tile instead of scaled. The script regenerates
everything for the new size at constant density, so a tile with twice the area
gets roughly twice the cobbles and spikes. The background is transparent.

## States and transitions

| From → To | What plays |
|---|---|
| on load | Jumps straight to the stored `state`, no animation |
| hidden → revealed | 0.7 s fade: outlines solidify into stones, the pit darkens in through the seams |
| revealed → hidden | the reverse fade |
| revealed → active | **Collapse** (2.5 s): stones break loose one by one from the centre outward, glow, and fall into the pit |
| hidden → active | fade and Collapse together |
| active → revealed | **Reform** (2.5 s): stones float back up out of the pit, edges first, and lock into a floor |
| active → hidden | Reform, then the fade to hidden |

If `state` changes mid-Collapse or mid-Reform, the running animation finishes
first and then heads for the new state, so the floor never jumps.

## Publishing for the web (Foundry)

Foundry uses the web runtime, and **web runtimes reject unsigned scripts**. A
local build (`rive . --once`) is unsigned, so ship a signed one:

```bash
rive login
rive push          # binds the project to a file in your Rive account
rive . --publish
```

Without a workspace on the Cadet plan or higher, `--publish` may add a watermark.

## Previewing

`rive .` opens the live previewer. The previewer has a `--data` flag for the
starting state, e.g. `rive . --data=state=active`.
