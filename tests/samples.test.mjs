import assert from "./assert.mjs";
import { readdir, readFile } from "node:fs/promises";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

/**
 * The sample animations in samples/ ship in the module zip: each must be a real
 * Rive file, and the release workflow must include the folder.
 */
const root = fileURLToPath(new URL("..", import.meta.url));

export const tests = [
  ["every file in samples/ is a .riv with the Rive header, or a text notice", async () => {
    const names = await readdir(join(root, "samples"));
    const rivs = names.filter(n => n.endsWith(".riv"));
    assert.ok(rivs.length > 0, "samples/ has no .riv files");
    for (const name of rivs) {
      const head = (await readFile(join(root, "samples", name))).subarray(0, 4).toString("latin1");
      assert.equal(head, "RIVE", `${name} doesn't start with the RIVE header`);
    }
    const other = names.filter(n => !n.endsWith(".riv") && !n.endsWith(".md") && !n.endsWith(".txt"));
    assert.deepEqual(other, [], "samples/ holds only .riv files and text notices");
  }],

  ["the release zip includes samples/", async () => {
    const workflow = await readFile(join(root, ".github", "workflows", "release.yml"), "utf8");
    const zip = workflow.split("\n").find(line => line.includes("zip -r module.zip"));
    assert.ok(zip, "no zip step in release.yml");
    assert.ok(/\ssamples\s/.test(zip), "the zip step leaves out samples/");
  }]
];
