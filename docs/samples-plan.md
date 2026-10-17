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

## Wish list: new files that would make better examples

You said you could make some. These would round out the samples, ordered by how much they show off. Each is system-neutral, and all fit 100–200 px grids.

1. **Progress clock** (Blades-style segmented circle). `segments:number` (4/6/8), `filled:number`, `color:color`, `label:string`, and a `tick` trigger with a little pop. Works in any genre: GM live controls on a journal page or a tile. Probably the single most useful sample.
2. **Door or portcullis.** `state:enum` (closed/open/locked) plus a `rattle` trigger for locked. Demo: a MATT click opens it; or bind it to a Foundry door's state later.
3. **Torch, brazier or campfire.** `lit:boolean`, `intensity:number` and a flicker loop. Pairs naturally with scene lighting; Layout fit for long braziers.
4. **Generic condition ring for tokens.** A frame drawn around the token image, with one small icon per core condition (`dead`, `prone`, `blind`, `deaf`, `poison`, `stun`, `restrain`, `sleep`, `invisible`, `burning`, ...) as booleans, plus `hp`/`maxHp` for an optional ring. It binds out of the box to `@actor` `status:<id>` in every system, which `responsivetoken` can't because of its dnd5e names. Strong announcement material.
5. **Lever or pressure plate.** `pulled:boolean` and a `clunk` trigger. Lets the demo show chained MATT actions (pull the lever → the door opens).
6. **Banner, sign or handout plaque.** `text:string`, `color:color`, Layout fit. Shows text binding, e.g. a tavern sign bound to the scene's or a token's name.
7. **Treasure chest.** `state:enum` (closed/open/empty) and an `open` trigger with sparkle. A classic MATT reward beat.
8. **Spell or area effect.** A looping aura plus a `cast` trigger. A tile you can drop on any template area.

Notes for making them:
- **Names:** use camelCase property names with no system-specific vocabulary. One view model per file, bound to the default instance.
- **Sizing:** draw at roughly 100 px per grid square, and test them with the Layout fit if they should scale by size.
- **Export:** export signed. Keep files small: embed only the fonts and images you need.
- **Licence:** say what licence the samples ship under (MIT like the code, or CC BY 4.0).

## Build steps

1. **Samples folder:** add `samples/` to the module with the chosen `.riv` files, and add `samples` to the release zip.
   - Verify the server serves `.riv` from module folders. Uploads of `.riv` were refused earlier, but serving should be fine; if it isn't, ship `.riv.json` wrappers instead.
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

## Decisions for you

1. **Which files to ship:** the four "Ship" files above, rework or drop `databinding_complete`, and which wish-list files you'll make.
2. **Licence** for the sample files.
3. **Adventure (one-click demo) or separate packs only.** I'd do both: separate packs for browsing, and the Adventure for the announcement.
4. **Monk's Active Tile Triggers in the demo:** the actions sit inert without MATT. Should the demo journal say "install MATT to make the trap and circle react", or should the demo also include a MATT-free path, such as a GM button in the journal?
5. **Naming:** pack names ("Rive Samples", "Rive Macros", "Rive for Foundry demo").
