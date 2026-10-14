export type FloorId = 'F1' | 'F2'
export type FloorFilter = FloorId | 'all'
export type EntityKind = 'factory' | 'equipment' | 'warehouse' | 'node' | 'workstation' | 'agv'
export type SimulationStrategy = string

export interface FactoryEntity {
  id: string
  kind: EntityKind
  floor: FloorId
  zone: string
  status: string
  inventory?: number
  materialId?: string
  task?: string
}

export interface SimulationSnapshot {
  simTime: number
  inventory: Record<string, number>
  equipment: Record<string, string>
}

export interface Metrics {
  finalOnHand: number
  totalReplenished: number
  totalConsumed: number
  shortageEvents: number
}

export interface SimulationEvent {
  event_id: string
  sim_time: number
  sequence: number
  kind: string
  entity_id: string
  payload: Record<string, unknown>
}

export interface SimulationRun {
  runId: string
  scenarioId: string
  strategy: SimulationStrategy
  dataMode: string
  timeUnit: string
  state: SimulationSnapshot
  events: SimulationEvent[]
  metrics: Metrics
}

export type TaskStatus = 'CREATED' | 'QUEUED' | 'RUNNING' | 'COMPLETED' | 'FAILED'
export type EventType =
  | 'task.created'
  | 'task.started'
  | 'task.completed'
  | 'task.failed'
  | 'plugin.started'
  | 'plugin.completed'
  | 'plugin.failed'
  | 'inventory.changed'
  | 'equipment.state.changed'

export interface EntityRef {
  entity_id: string
  entity_type: EntityKind
}

export interface FactoryState {
  entityId: string
  entityType: EntityKind
  status: string
  inventory?: Record<string, number>
  currentTaskId?: string
  updatedAt: string
}

export interface ActionIntent {
  capability: string
  target: EntityRef
  parameters?: Record<string, unknown>
}

export interface ExecutionTraceStep {
  execution_id: string
  task_id: string
  plugin_id: string
  capability: string
  status: TaskStatus
  started_at: string
  ended_at?: string
  summary: string
}

export interface FactoryTask {
  task_id: string
  execution_id: string
  target: EntityRef
  capability: string
  status: TaskStatus
  created_at: string
  updated_at: string
  result?: {
    title: string
    summary: string
    recommendations: string[]
    metrics: Record<string, number | string>
  }
  error?: {
    error_code: string
    message: string
  }
  trace: ExecutionTraceStep[]
}

export interface FactoryEvent {
  event_id: string
  event_type: EventType
  timestamp_utc: string
  source: string
  refs: {
    entity_id?: string
    task_id?: string
    execution_id?: string
  }
  payload: Record<string, unknown>
  schema_version: string
}
