# Plan: sample animations for the public release

Status: draft for review (branch `feature/samples`). Nothing is built yet.

## Goal

Ship a handful of Rive animations with the module so a new user can see what it does within a minute, in any game system, without uploading anything or importing actors that only work in one system.

## What ships where

Foundry has no document type for a Rive file, so the files and the things that use them ship separately.

| Piece | What it is | Works in every system? |
|---|---|---|
| **Sample files** | The `.riv` files in the module folder, `modules/foundry-rive/samples/`. Foundry serves module files directly, so tiles, tokens and pages can point at them, and the file picker can browse to them. Nothing is uploaded into anyone's world. | Yes |
| **"Rive Samples" journal compendium** (main entry point) | One Rive page per sample: the animation playing, a caption, and a short note on its inputs and properties and how to drive them. Plus a "Getting started" page. Readable straight from the compendium, no import needed. | Yes: journal entries aren't system data |
| **Demo scene** | A small scene with Rive tiles already set up: the spike trap, the ritual circle with its three sites, and later a door, a torch and a progress clock (see the wish list). The trap and sites come with Monk's Active Tile Triggers actions, which simply do nothing without MATT. **No tokens**: a placed token points at an actor, and actors are system data. | Yes, as long as it has no tokens |
| **Adventure: "Rive for Foundry demo"** (optional) | The demo scene plus the journal, imported in one click. Good for the announcement ("import the demo and walk onto the trap"). | Yes, if it contains no actors or items |
| **Macro compendium** | Macros such as "Give the selected token the Rive sample token": they set our flags on whatever token is selected, in any system, instead of us shipping actors. Plus "Open the Rive samples". | Yes: script macros are system-agnostic |
| **"Samples" button** (optional) | On the Rive tab and the page editor, next to Browse: opens the file picker at the samples folder. | Yes |

Compendium packs are only tied to a system when `module.json` gives the pack a `system` key, so none of ours will. An Adventure isn't tied to a system by type either; only the actors and items inside one are.

## Rules for system-neutral samples

- **Bind to what every system has:** token fields (`hidden`, `elevation`, `name`, `disposition`) and conditions (`status:<id>`), using core v12 ids (`dead`, `prone`, `blind`, `poison`, `invisible`, ...). Systems rename a few (dnd5e uses `blinded`, `poisoned`), so each sample page says which ones it uses.
- **System data paths go in the docs, not the samples:** `system.attributes.hp.value` and the like stay in the README's "Common bindings" table, with per-system examples.
- **No actors or items** in any pack.
- **Layout fit where it helps:** samples drawn for their artboard size (the spike trap) ship with the Layout fit, so a bigger tile shows more content instead of stretching.
- **Signed exports only:** every sample is exported or published signed from Rive, so its scripts run (the runtime refuses unsigned scripts).

## The current files

Inventory of the `.riv` files we have (artboard, state machine, view model):

| File | What it shows | Proposal |
|---|---|---|
| `spiketrap.riv` (448×428, `Trap`) | Scripted cobbles and spikes; `state` enum hidden/revealed/active, `stoneSize`, `spikeSpacing`, `seed`. Layout-fit friendly. | **Ship.** Trap tile in the demo scene, with MATT actions: walk on it → `active`. |
| `magicritualcircle.riv` (500×500, `Ritual`) | `site1Active`–`site3Active` booleans. | **Ship.** Demo scene: three site tiles light up the circle while someone stands on them (the flow already built for RitualSiteA). |
| `ratswarm.riv` (300×300) | Token art; `hp`, `maxHp`, `ratScale`. | **Ship** as a token sample, applied by macro. hp/maxHp bindings are system-specific, so they're documented rather than preset. |
| `responsivetoken.riv` (512×512, `Token Machine`) | 35 properties: hp/temp hp ring, colours, hair/beard/ears/horns, 18 condition booleans, exhaustion, `hit`/`heal` triggers. | **Ship** as the flagship token sample, applied by macro. Its condition names follow dnd5e; a page explains binding them to `status:<id>` per system. |
| `databinding_complete.riv` (3 artboards) | Every property type (enum, trigger, colour, boolean, string, number), test-styled. | **Rework or drop.** A good "every type" demo for the docs, but it looks like a test file. |
| `basic`, `text`, `statemachine-animation`, `databinding` | Development fixtures. | **Don't ship** (keep them in the repo for testing). |
| `vehicles.riv` (spike) | Rive community file. | **Don't ship**: licence unknown. |

## Sample sources: `samples_src/`

The existing samples were built with the Rive CLI (RML, plus Luau for the scripted ones), and their projects now live in `samples_src/`. Each has `scene.rml` (often generated by a script in `tools/`), a README with an **integration contract** (artboard, state machine, view model, property table, states), and an ignored `build/` folder. New samples follow the same layout. Release builds use `rive <dir> --publish` (signed); local checks use `--once`/`--verify`.

| Project | Use case | Contract (short) |
|---|---|---|
| `SpikeTrap` | Scene tile, layout fit, scripted | `state` hidden/revealed/active, `stoneSize`, `spikeSpacing`, `seed` |
| `MagicRitualCircle` | Scene tile driven by other tiles (6×6 squares at 100 px) | `site1Active`–`site3Active` |
| `RatSwarm` | Token, scripted | `hp`, `maxHp`, `ratScale` |
| `ResponsiveToken` | Token, data-bound portrait | hp ring, colours, features, 18 conditions, `hit`/`heal` |
| `AnimatedScroll` | **Journal set piece** to show players | `isOpen`, `isTranslated`, `translatedText` (string) |

## Coverage: one good example per use case

| Use case | Examples |
|---|---|
| Scene tile, reacting to the world (MATT) | SpikeTrap; **lever / pressure plate** driving another tile |
| Tile driven by other tiles | MagicRitualCircle |
| Ambient scene dressing | **torch / brazier** |
| Token | ResponsiveToken, RatSwarm |
| Journal set piece flashed to players | AnimatedScroll; **door** |
| GM-driven tracker (journal or tile) | **progress clock** |
| Text binding | **sign / banner**; AnimatedScroll |
| Reward beat | **treasure chest** |

## New samples to build

Chosen (2026-10-17), in build order:

1. **Progress clock** (Blades-style). **Source done** (`samples_src/ProgressClock`, 2026-10-17): `segments:number` (any count), `filled:number` (the fill sweeps, the clock pops), `color:color`, `label:string`, `tick` trigger. No scripts, so the local build runs unsigned; checked in the 2.44.2 runtime. Still to do: ship the `.riv` in `samples/` and try it on the server as a journal page and a tile.
2. **Torch / brazier.** **Source done** (`samples_src/Brazier`, 2026-10-17): three top-down artboards (`Brazier`, a wall `Torch`, and a `Trough` for the Layout fit) sharing `lit:boolean` (eased fade, embers stay), `intensity:number` (0–1.5), `color:color` and a `flare` trigger. No scripts; checked in the 2.44.2 runtime. Still to do: ship the `.riv` and try it on the server.
   - *2026-10-17:* the user finds the shape-based fire weak. A shader fire (WGSL, `spike/gpu-fire`) looks far better but needs the `@rive-app/webgl2` runtime with GPU Canvas, which the module doesn't ship. Kept as a spike for a possible "GPU effects" feature later; the samples continue without shaders. Revisit the fire's look before release.
3. **Sign / banner.** **Source done** (`samples_src/Sign`, 2026-10-17): a hanging `Sign` (flex boxes for the Layout fit; the lettering centres and shrinks to fit; sways, and a `swing` trigger) and a rippling `Banner`, sharing `text:string`, `color:color` and `textColor:color`. No scripts; checked in the 2.44.2 runtime. Still to do: ship the `.riv` and try it on the server.
4. **Treasure chest.** `state:enum` (closed/open/empty), `open` trigger with sparkle; MATT reward beat.
5. **Lever / pressure plate + target.** Same arrangement as the ritual circle: the plate (`pressed:boolean`) animates under the token, and its MATT actions drive a second tile, e.g. a portcullis or gate that reads well top-down (`open:boolean`), or the chest. A wall lever (`pulled:boolean`, click trigger) is the click variant.
6. **Door, as a journal set piece** rather than a scene tile, since doors are hard to show top-down. `state:enum` (closed/open/locked), `knock`/`rattle` triggers; the GM shows the page to players, like the scroll.

Not now:
- **Condition ring and other token overlays:** out of scope for the module for now (decided 2026-10-17 after the overlay spike). The spike works, but both ways of drawing over an image token reach into Foundry's token rendering in ways with real risks. Findings and risks: `spikes/token-overlay-findings.md` on the `spike/token-overlay` branch, kept for reference and not to be merged.
- **Spell aura:** attaching one to a token would need either active effects (system-specific) or the token overlays above.

## Build steps

1. **Samples folder:** add `samples/` to the module with the chosen `.riv` files (signed builds of the `samples_src/` projects), and add `samples` to the release zip.
   - Verified during the overlay spike: the server serves `.riv` from module folders (status 200), so the samples ship as plain `.riv` files.
2. **Pack sources and build:**
   - Keep pack contents as JSON in the repo (`packs-src/<pack>/*.json`), so they're reviewable and diffable.
   - Compile them to v12 LevelDB folders in the release workflow with Foundry's CLI (`@foundryvtt/foundryvtt-cli`, `fvtt package pack`), and add `packs/` to the zip.
   - Declare the packs in `module.json` with no `system` key.
3. **Journal compendium "Rive Samples":** a Getting started page, one Rive page per sample, and binding recipes.
4. **Macro compendium:** apply a sample to the selected tokens or tiles; open the samples journal. The macros write only `flags.foundry-rive` on the selected placeables, after a confirmation, so they pass the World-safety checklist.
5. **Demo scene with MATT actions,** then wrap scene and journal as an Adventure (optional).
6. **Samples button** next to Browse (optional).
7. **README:** a "Samples" section, plus a screenshot or GIF for the announcement.

## Safety and tests

- **No new world writes from module code,** except the macros, which only write our own flags. Importing from a compendium is the user's own action.
- **New unit tests** on the pack JSON sources:
  - every Rive page and tile points at a file in `samples/`;
  - no pack contains actors or items;
  - flags have only our keys;
  - every sample loads with no refused scripts. That one runs in the health check on the server, not in Node.
- **Health check:** run it on the imported demo scene for the release build.

## Decisions

Made (2026-10-17):
- Build the progress clock, torch/brazier, sign/banner and treasure chest; the lever/pressure plate with a target tile; the door as a journal set piece.
- Condition ring, token overlays and spell aura: not now (see above).
- `samples_src/` is committed (without `build/`), so the samples' sources are public. Not part of the module zip.

Still open:
1. Licence for the sample files (the scroll's font is OFL; note that in the samples' credits).
2. Adventure (one-click demo) or separate packs only. I'd do both.
3. Demo without MATT: just say "install MATT for the trap and plates", or also add a MATT-free path (GM buttons in the journal)?
4. Pack names ("Rive Samples", "Rive Macros", "Rive for Foundry demo").
