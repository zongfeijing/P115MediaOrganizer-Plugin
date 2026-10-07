// Fail the build if a remote component bundles a second UI application or
// framework/global CSS instead of inheriting MoviePilot's registered controls.
import { readdir, readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";
const root = fileURLToPath(
  new URL("../../plugins.v3/p115mediaorganizer/dist/", import.meta.url),
);
async function check(directory) {
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const filename = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      await check(filename);
      continue;
    }
    const text = await readFile(filename, "utf8");
    if (entry.name.endsWith(".css")) {
      const selectors = /(?:^|})\s*([^{}]+)\{/g;
      for (const [, selector] of text.matchAll(selectors)) {
        if (selector.startsWith("@")) continue;
        if (!selector.includes("[data-v-"))
          throw new Error(`Unscoped CSS in ${filename}: ${selector}`);
      }
    }
    if (
      entry.name.endsWith(".js") &&
      /\bcreateVuetify\b|__federation_shared_vuetify/.test(text)
    ) {
      throw new Error(`Bundled UI runtime in ${filename}`);
    }
  }
}
await check(root);
console.log(
  "Native UI assets verified: scoped layout CSS only; no Vuetify runtime bundled.",
);
