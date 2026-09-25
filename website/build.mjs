import { copyFile, mkdir, readFile } from 'node:fs/promises';
import { validateBenchmark } from './data.js';

const source = new URL('../docs/data/jevbench-public-001.json', import.meta.url);
validateBenchmark(JSON.parse(await readFile(source, 'utf8')));
const output = new URL('./dist/', import.meta.url);
await mkdir(new URL('data/', output), { recursive: true });
// Explicit public assets only: never copy a repository directory into the site.
for (const file of ['index.html', 'style.css', 'app.js', 'data.js', 'favicon.svg']) {
  await copyFile(new URL(file, import.meta.url), new URL(file, output));
}
await copyFile(source, new URL('data/jevbench-public-001.json', output));
console.log('Built website/dist from public assets and the recorded benchmark.');
