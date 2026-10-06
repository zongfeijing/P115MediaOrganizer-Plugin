// Module-federation templates contain blank lines with spaces. Normalize emitted
// text after building so git whitespace checks and cross-platform CI agree.
import { readdir, readFile, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
const root = fileURLToPath(new URL('../../plugins.v3/p115mediaorganizer/dist/', import.meta.url));
async function normalize(directory) {
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const filename = path.join(directory, entry.name);
    if (entry.isDirectory()) await normalize(filename);
    else if (/\.(js|css|html)$/.test(entry.name)) {
      const text = await readFile(filename, 'utf8');
      await writeFile(filename, text.replace(/[\t ]+$/gm, '').replace(/\r\n/g, '\n'));
    }
  }
}
await normalize(root);
