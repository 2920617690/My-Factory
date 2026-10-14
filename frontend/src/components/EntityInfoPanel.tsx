import { Bot, Box, Cpu, Factory, MapPin, Package } from 'lucide-react'

import type { FactoryEntity, FactoryState } from '../types'

interface EntityInfoPanelProps {
  entity: FactoryEntity
  state: FactoryState | null
}

const iconByKind = {
  factory: Factory,
  equipment: Cpu,
  warehouse: Package,
  node: MapPin,
  workstation: Box,
  agv: Bot,
}

const statusLabels: Record<string, string> = {
  idle: '待机',
  available: '可用',
  standby: '待命',
  mock: '模拟模式',
}

export function EntityInfoPanel({ entity, state }: EntityInfoPanelProps) {
  const Icon = iconByKind[entity.kind]
  const inventory = entity.materialId && state?.inventory?.[entity.materialId] !== undefined
    ? state.inventory[entity.materialId]
    : entity.inventory
  const rawStatus = state?.status ?? entity.status
  const status = statusLabels[rawStatus] ?? rawStatus

  return (
    <aside className="panel entity-panel">
      <div className="panel-title">
        <Icon size={18} aria-hidden="true" />
        <h2>上下文</h2>
      </div>
      <dl className="kv">
        <div>
          <dt>编号</dt>
          <dd>{entity.id}</dd>
        </div>
        <div>
          <dt>类型</dt>
          <dd>{entity.kind}</dd>
        </div>
        <div>
          <dt>楼层</dt>
          <dd>{entity.floor}</dd>
        </div>
        <div>
          <dt>区域</dt>
          <dd>{entity.zone}</dd>
        </div>
        <div>
          <dt>状态</dt>
          <dd>{status}</dd>
        </div>
        {entity.materialId && (
          <div>
            <dt>物料</dt>
            <dd>{entity.materialId}</dd>
          </div>
        )}
        {inventory !== undefined && (
          <div>
            <dt>当前库存</dt>
            <dd>{inventory}</dd>
          </div>
        )}
        {state?.currentTaskId && (
          <div>
            <dt>当前任务</dt>
            <dd>{state.currentTaskId}</dd>
          </div>
        )}
        {entity.task && (
          <div>
            <dt>说明</dt>
            <dd>{entity.task}</dd>
          </div>
        )}
      </dl>
    </aside>
  )
}
