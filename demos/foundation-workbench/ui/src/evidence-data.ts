/** Original comparison branches and the five continuous mock snapshots. */
export const previousSnapshot:Record<string,string>={quality_hold:'morning',received:'morning',partial_receipt:'contended',quality_release:'partial_receipt',group_replenished:'quality_release',lift_blocked:'group_replenished'};
export type Selection={snapshot_id:string;order_id?:string;order_ids?:string[]};
/** Match the recorded data and orders; viewing a saved record never submits a model run. */
export function sameSelection(a:Selection,b:Selection):boolean{return a.snapshot_id===b.snapshot_id&&JSON.stringify(a.order_ids?[...a.order_ids].sort():[a.order_id])===JSON.stringify(b.order_ids?[...b.order_ids].sort():[b.order_id]);}
/** Narrow a persisted tool value without adding calculated or synthetic result fields. */
export function returnedRows(value:unknown):Record<string,unknown>[] {if(!value||typeof value!=='object')return [];const v=value as Record<string,unknown>;return Array.isArray(v.materials)?v.materials.filter((r):r is Record<string,unknown>=>!!r&&typeof r==='object'&&typeof r.material_id==='string'):typeof v.material_id==='string'?[v]:[];}
/** Prefer the material changed by each demonstration; the unchanged first material can obscure it. */
export function preferredMaterial(snapshot:string,ids:string[]):string {const preferred=['contended','partial_receipt','quality_release','group_replenished','lift_blocked'].includes(snapshot)?'MAT-002':'MAT-003';return ids.includes(preferred)?preferred:ids[0]??'';}
