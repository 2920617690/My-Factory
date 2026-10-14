import type { FactoryEntity, FactoryEvent, FactoryState, FactoryTask } from './types'

export const initialSnapshot = {
  simTime: 0,
  inventory: { 'MAT-001': 6 },
  equipment: { 'EQ-001': 'idle', 'EQ-002': 'idle' },
}

export const factoryEntities: FactoryEntity[] = [
  {
    id: 'EQ-001',
    kind: 'equipment',
    floor: 'F1',
    zone: '机加工区',
    status: 'idle',
    task: '等待任务分配',
  },
  {
    id: 'EQ-002',
    kind: 'equipment',
    floor: 'F1',
    zone: '检测区',
    status: 'idle',
    task: '预留设备状态联动',
  },
  {
    id: 'WH-001',
    kind: 'warehouse',
    floor: 'F1',
    zone: '仓储区',
    status: 'available',
    materialId: 'MAT-001',
    inventory: initialSnapshot.inventory['MAT-001'],
    task: '可执行库存分析',
  },
  {
    id: 'NODE-001',
    kind: 'node',
    floor: 'F1',
    zone: '仓储物流点',
    status: 'standby',
    task: '模拟物流节点',
  },
  {
    id: 'AGV-001',
    kind: 'agv',
    floor: 'F1',
    zone: '一层搬运通道',
    status: 'standby',
    task: '等待调度',
  },
  {
    id: 'WS-001',
    kind: 'workstation',
    floor: 'F2',
    zone: '预装区',
    status: 'idle',
    task: '预留装配前工位',
  },
  {
    id: 'WS-002',
    kind: 'workstation',
    floor: 'F2',
    zone: '装配区',
    status: 'idle',
    task: '订单 ORD-001 目标工位',
  },
  {
    id: 'AGV-002',
    kind: 'agv',
    floor: 'F2',
    zone: '二层转运通道',
    status: 'standby',
    task: '等待跨层任务',
  },
]

export const factoryStateById: Record<string, FactoryState> = {
  'FACTORY-001': {
    entityId: 'FACTORY-001',
    entityType: 'factory',
    status: 'mock',
    updatedAt: '2026-10-12T00:00:00.000Z',
  },
  'EQ-001': {
    entityId: 'EQ-001',
    entityType: 'equipment',
    status: 'idle',
    updatedAt: '2026-10-12T00:00:00.000Z',
  },
  'EQ-002': {
    entityId: 'EQ-002',
    entityType: 'equipment',
    status: 'idle',
    updatedAt: '2026-10-12T00:00:00.000Z',
  },
  'WH-001': {
    entityId: 'WH-001',
    entityType: 'warehouse',
    status: 'available',
    inventory: { 'MAT-001': 6 },
    updatedAt: '2026-10-12T00:00:00.000Z',
  },
  'NODE-001': {
    entityId: 'NODE-001',
    entityType: 'node',
    status: 'standby',
    updatedAt: '2026-10-12T00:00:00.000Z',
  },
  'AGV-001': {
    entityId: 'AGV-001',
    entityType: 'agv',
    status: 'standby',
    updatedAt: '2026-10-12T00:00:00.000Z',
  },
  'AGV-002': {
    entityId: 'AGV-002',
    entityType: 'agv',
    status: 'standby',
    updatedAt: '2026-10-12T00:00:00.000Z',
  },
  'WS-001': {
    entityId: 'WS-001',
    entityType: 'workstation',
    status: 'idle',
    updatedAt: '2026-10-12T00:00:00.000Z',
  },
  'WS-002': {
    entityId: 'WS-002',
    entityType: 'workstation',
    status: 'idle',
    updatedAt: '2026-10-12T00:00:00.000Z',
  },
}

export const seedEvents: FactoryEvent[] = [
  {
    event_id: 'EVT-SEED-001',
    event_type: 'inventory.changed',
    timestamp_utc: '2026-10-12T00:00:00.000Z',
    source: 'msw-platform-mock',
    refs: { entity_id: 'WH-001' },
    payload: { material_id: 'MAT-001', on_hand: 6, reason: 'mock.initial_state' },
    schema_version: 'v1',
  },
]

export const seedTasks: FactoryTask[] = []

export const timelineMarks = [0, 5, 10, 12]
