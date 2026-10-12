/** Process adapter over the unchanged B pure business library; no Agent loop. */
import { mkdtempSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { loadSnapshot, analyze } from './vendor/business.mjs';

let text = '';
for await (const part of process.stdin) {
  text += part;
  if (Buffer.byteLength(text) > 1048576) throw new Error('INPUT_TOO_LARGE');
}
let dir;
try {
  const request = JSON.parse(text);
  dir = mkdtempSync(join(tmpdir(), 'mf-inventory-'));
  const path = join(dir, 'snapshot.json');
  writeFileSync(path, JSON.stringify({ scenarios:[request.snapshot] }), { mode:0o600 });
  const snapshot = loadSnapshot(path, request.snapshot.snapshot_id);
  process.stdout.write(JSON.stringify({ ok:true, value:analyze(snapshot, request.arguments) }) + '\n');
} catch (error) {
  process.stdout.write(JSON.stringify({ ok:false, code:error instanceof Error ? error.message : 'PLUGIN_FAILED' }) + '\n');
  process.exitCode = 1;
} finally {
  if (dir) rmSync(dir, { recursive:true, force:true });
}
