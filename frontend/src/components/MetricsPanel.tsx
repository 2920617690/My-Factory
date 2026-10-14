import { Gauge } from 'lucide-react'

import type { Metrics, SimulationSnapshot } from '../types'

interface MetricsPanelProps {
  metrics: Metrics
  snapshot: SimulationSnapshot
}

export function MetricsPanel({ metrics, snapshot }: MetricsPanelProps) {
  return (
    <section className="panel metrics-panel">
      <div className="panel-title">
        <Gauge size={18} aria-hidden="true" />
        <h2>运行指标</h2>
      </div>
      <div className="metric-grid">
        <Metric label="仿真时间" value={snapshot.simTime} />
        <Metric label="MAT-001" value={snapshot.inventory['MAT-001']} />
        <Metric label="最终库存" value={metrics.finalOnHand} />
        <Metric label="缺货事件" value={metrics.shortageEvents} />
      </div>
    </section>
  )
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  )
}


