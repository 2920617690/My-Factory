/** Two official Cordis tools; source stays read only and shell tools are disabled. */
import { appendFileSync, writeFileSync } from 'node:fs';
import { isAbsolute } from 'node:path';
import { defineTool } from '@deepseek-ai/dsh-tools';
import { loadSnapshot, inventory, analyze } from './business.mjs';

export const name = 'my-factory-realistic-demo';
export const inject = ['tools'];

export function apply(ctx, config) {
  for (const key of ['fixturePath', 'auditPath', 'registryPath']) if (!isAbsolute(config?.[key] ?? '')) throw new Error(`INVALID_CONFIG_${key}`);
  const snapshot = loadSnapshot(config.fixturePath, config.snapshotId);
  const names = ['factory_inventory_query', 'factory_shortage_analyze'];
  const register = (toolName, parameters, description, execute) => ctx.effect(() => ctx.tools.register(defineTool({
    name: toolName, parameters, description,
    output: { schema: { type: 'object', additionalProperties: true }, render: (_args, value) => [{ type: 'text', text: JSON.stringify(value) }] },
    async execute(args, exec) { if (exec.signal.aborted) throw new Error('ABORTED'); return execute(args); },
  })));
  register(names[0], { material_id: { type: 'string', required: true, description: 'Material ID. Use * to query the complete read-only inventory snapshot.' } },
    'Read synthetic ERP/WMS inventory by batch, quality, reserved quantity and floor. No stock changes. * returns all material facts.',
    args => inventory(snapshot, args.material_id));
  register(names[1], {
    order_id: { type: 'string', description: 'Use alone to check a complete order BOM with exact quantities from the fixture.' },
    order_ids: { type: 'array', items: { type: 'string' }, description: 'Use alone with 2 to 5 unique order IDs to compare combined BOM demand against shared stock once. No allocation or optimization.' },
    material_id: { type: 'string', description: 'For a single material, use with demand; do not combine with order_id.' },
    demand: { type: 'integer', description: 'Nonnegative integer demand, required with material_id.' },
    target_floor: { type: 'integer', description: '1 or 2 for single-material analysis; defaults to 2.' },
  }, 'Check one order or an order group, BOM shortages, partial receipts, quality release and cross-floor constraints. Excludes holds, reservations and unreceived quantities. Read only, without allocating stock. order_id and order_ids are mutually exclusive.',
  args => analyze(snapshot, args));
  ctx.effect(() => ctx.tools.guard(exec => names.includes(exec.name) ? undefined : 'MF_READONLY_POLICY: write/execute tool is not allowed'));
  ctx.on('tools/result', (exec, result) => appendFileSync(config.auditPath,
    JSON.stringify({ at: new Date().toISOString(), call_id: exec.callId, name: exec.name,
      arguments: exec.arguments, result, snapshot_id: snapshot.snapshot_id }) + '\n', { mode: 0o600 }));
  const schemas = ctx.tools.schemas();
  if (schemas.length !== 2 || schemas.some(row => !names.includes(row.name))) throw new Error('UNEXPECTED_TOOLS');
  writeFileSync(config.registryPath, JSON.stringify({ schemas, snapshot_id: snapshot.snapshot_id }, null, 2) + '\n', { mode: 0o600 });
}
