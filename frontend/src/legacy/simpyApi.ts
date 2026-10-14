import type { Metrics, SimulationRun, SimulationSnapshot, SimulationStrategy } from '../types'

const API_BASE_URL = import.meta.env.VITE_SIM_API_URL ?? 'http://127.0.0.1:8011'
const SCENARIO_ID = 'SIMPLE-INVENTORY-001'

interface ApiSnapshot {
  sim_time: number
  inventory: Record<string, number>
  equipment: Record<string, string>
}

interface ApiMetrics {
  final_on_hand: number
  total_replenished: number
  total_consumed: number
  shortage_events: number
}

interface ApiRun {
  run_id: string
  scenario_id: string
  strategy: SimulationStrategy
  data_mode: string
  time_unit: string
  state: ApiSnapshot
  events: SimulationRun['events']
  metrics: ApiMetrics
}

interface ApiStateResponse {
  run_id: string
  scenario_id: string
  strategy: SimulationStrategy
  state: ApiSnapshot
}

export async function createSimulationRun(strategy: SimulationStrategy, signal?: AbortSignal) {
  const response = await fetch(`${API_BASE_URL}/api/sim/runs`, {
    method: 'POST',
    signal,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ scenario_id: SCENARIO_ID, strategy }),
  })

  if (!response.ok) {
    throw new Error(`创建仿真运行失败 (${response.status})`)
  }

  return mapRun(await response.json() as ApiRun)
}

export async function getRunState(runId: string, simTime: number, signal?: AbortSignal) {
  const response = await fetch(`${API_BASE_URL}/api/sim/runs/${runId}/state?sim_time=${simTime}`, { signal })

  if (!response.ok) {
    throw new Error(`读取仿真状态失败 (${response.status})`)
  }

  const payload = await response.json() as ApiStateResponse
  return mapSnapshot(payload.state)
}

function mapRun(run: ApiRun): SimulationRun {
  return {
    runId: run.run_id,
    scenarioId: run.scenario_id,
    strategy: run.strategy,
    dataMode: run.data_mode,
    timeUnit: run.time_unit,
    state: mapSnapshot(run.state),
    events: run.events,
    metrics: mapMetrics(run.metrics),
  }
}

function mapSnapshot(snapshot: ApiSnapshot): SimulationSnapshot {
  return {
    simTime: snapshot.sim_time,
    inventory: snapshot.inventory,
    equipment: snapshot.equipment,
  }
}

function mapMetrics(metrics: ApiMetrics): Metrics {
  return {
    finalOnHand: metrics.final_on_hand,
    totalReplenished: metrics.total_replenished,
    totalConsumed: metrics.total_consumed,
    shortageEvents: metrics.shortage_events,
  }
}


