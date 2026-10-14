import { useEffect, useMemo, useState } from 'react'
import { Activity, Layers, LocateFixed, Play, RadioTower } from 'lucide-react'

import './App.css'
import { factoryClient } from './client/factoryClient'
import { EntityInfoPanel } from './components/EntityInfoPanel'
import { FactoryScene } from './components/FactoryScene'
import { factoryEntities } from './simulationData'
import type { FactoryEntity, FactoryEvent, FactoryState, FactoryTask, FloorFilter } from './types'

const factoryEntity: FactoryEntity = {
  id: 'FACTORY-001',
  kind: 'factory',
  floor: 'F1',
  zone: '双层模拟厂区',
  status: 'mock',
  task: 'Digital Factory Workspace',
}

function App() {
  const [visibleFloor, setVisibleFloor] = useState<FloorFilter>('all')
  const [entities, setEntities] = useState<FactoryEntity[]>(factoryEntities)
  const [selectedEntity, setSelectedEntity] = useState<FactoryEntity>(factoryEntities.find((entity) => entity.id === 'WH-001') ?? factoryEntities[0])
  const [selectedState, setSelectedState] = useState<FactoryState | null>(null)
  const [tasks, setTasks] = useState<FactoryTask[]>([])
  const [activeTask, setActiveTask] = useState<FactoryTask | null>(null)
  const [events, setEvents] = useState<FactoryEvent[]>([])
  const [sceneResetKey, setSceneResetKey] = useState(0)
  const [workspaceStatus, setWorkspaceStatus] = useState('正在连接 Platform Mock...')

  const sceneEntities = useMemo(() => [factoryEntity, ...entities], [entities])
  const floorLabels: Record<FloorFilter, string> = { all: '全部', F1: '一层', F2: '二层' }
  const canAnalyzeInventory = selectedEntity.id === 'WH-001'

  useEffect(() => {
    const controller = new AbortController()

    async function loadWorkspace() {
      try {
        const [nextEntities, nextEvents, nextTasks] = await Promise.all([
          factoryClient.listEntities(controller.signal),
          factoryClient.listEvents(controller.signal),
          factoryClient.listTasks(controller.signal),
        ])
        setEntities(nextEntities)
        setEvents(nextEvents)
        setTasks(nextTasks)
        setWorkspaceStatus('MSW Platform Mock 已连接')
      } catch (error) {
        if (!controller.signal.aborted) {
          setWorkspaceStatus(error instanceof Error ? error.message : 'Platform Mock 不可用')
        }
      }
    }

    void loadWorkspace()

    return () => controller.abort()
  }, [])

  useEffect(() => {
    const controller = new AbortController()

    async function loadEntityState() {
      try {
        const nextState = await factoryClient.getEntityState(selectedEntity.id, controller.signal)
        setSelectedState(nextState)
      } catch {
        if (!controller.signal.aborted) setSelectedState(null)
      }
    }

    void loadEntityState()

    return () => controller.abort()
  }, [selectedEntity.id])

  useEffect(() => {
    if (!activeTask || !['CREATED', 'QUEUED', 'RUNNING'].includes(activeTask.status)) return

    const timer = window.setInterval(async () => {
      const nextTask = await factoryClient.getTask(activeTask.task_id)
      const nextEvents = await factoryClient.listEvents()
      setActiveTask(nextTask)
      setTasks((current) => [nextTask, ...current.filter((task) => task.task_id !== nextTask.task_id)])
      setEvents(nextEvents)

      if (nextTask.status === 'COMPLETED' || nextTask.status === 'FAILED') {
        window.clearInterval(timer)
      }
    }, 700)

    return () => window.clearInterval(timer)
  }, [activeTask])

  async function runInventoryAnalysis() {
    if (!canAnalyzeInventory) return

    setWorkspaceStatus('正在创建库存分析任务...')
    const response = await factoryClient.submitAction({
      capability: 'inventory.analyze',
      target: {
        entity_id: selectedEntity.id,
        entity_type: selectedEntity.kind,
      },
      parameters: {
        material_id: selectedEntity.materialId ?? 'MAT-001',
        order_id: 'ORD-001',
      },
    })
    const nextEvents = await factoryClient.listEvents()
    setActiveTask(response.task)
    setTasks((current) => [response.task, ...current])
    setEvents(nextEvents)
    setWorkspaceStatus('任务已提交，等待 Runtime Mock 返回结果')
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">My Factory MVP 0.1 / Frontend Track</p>
          <h1>Digital Factory Workspace</h1>
          <p className={workspaceStatus.includes('已连接') ? 'api-status ok' : 'api-status'}>
            {workspaceStatus}
          </p>
        </div>
        <div className="topbar-actions">
          <div className="system-pill">
            <RadioTower size={17} aria-hidden="true" />
            Platform API / MSW
          </div>
          <button type="button" className="icon-button wide" onClick={() => setSceneResetKey((key) => key + 1)}>
            <LocateFixed size={18} aria-hidden="true" />
            重置视角
          </button>
        </div>
      </header>

      <section className="workspace">
        <div className="scene-region">
          <div className="scene-toolbar" aria-label="楼层显示">
            <Layers size={18} aria-hidden="true" />
            {(['all', 'F1', 'F2'] as const).map((floor) => (
              <button
                type="button"
                key={floor}
                className={visibleFloor === floor ? 'segmented active' : 'segmented'}
                onClick={() => setVisibleFloor(floor)}
              >
                {floorLabels[floor]}
              </button>
            ))}
          </div>
          <FactoryScene
            visibleFloor={visibleFloor}
            entities={sceneEntities}
            selectedEntityId={selectedEntity.id}
            onSelectEntity={setSelectedEntity}
            resetKey={sceneResetKey}
          />
        </div>

        <div className="side-region">
          <EntityInfoPanel entity={selectedEntity} state={selectedState} />
          <section className="panel action-panel">
            <div className="panel-title">
              <Play size={18} aria-hidden="true" />
              <h2>动作</h2>
            </div>
            <div className="panel-body">
              <button
                type="button"
                className="primary-action"
                disabled={!canAnalyzeInventory}
                onClick={() => void runInventoryAnalysis()}
              >
                库存分析
              </button>
              <p className="hint-text">
                {canAnalyzeInventory
                  ? '创建 inventory.analyze Action，经 Platform Mock 转为 Task 并返回执行结果。'
                  : 'MVP 0.1 第一轮联调仅开放 WH-001 的库存分析。'}
              </p>
            </div>
          </section>
          <TaskCenter tasks={tasks} activeTask={activeTask} />
        </div>
      </section>

      <section className="ops-region">
        <EventCenter events={events} />
        <TracePanel task={activeTask} />
        <section className="panel simulation-note">
          <div className="panel-title">
            <Activity size={18} aria-hidden="true" />
            <h2>仿真实验</h2>
          </div>
          <div className="panel-body compact-text">
            已完成的 SimPy baseline/replenish POC 作为后续 simulation.run capability 的基础保留；第二次会议的第一轮联调先以 inventory.analyze 任务闭环为主。
          </div>
        </section>
      </section>
    </main>
  )
}

function TaskCenter({ tasks, activeTask }: { tasks: FactoryTask[]; activeTask: FactoryTask | null }) {
  const visibleTasks = tasks.slice(0, 4)

  return (
    <section className="panel task-panel">
      <div className="panel-title">
        <Activity size={18} aria-hidden="true" />
        <h2>任务中心</h2>
      </div>
      <div className="list-panel">
        {visibleTasks.length === 0 ? (
          <p className="empty-text">尚未创建任务</p>
        ) : (
          visibleTasks.map((task) => (
            <div key={task.task_id} className={activeTask?.task_id === task.task_id ? 'list-item active' : 'list-item'}>
              <strong>{task.task_id}</strong>
              <span>{task.capability}</span>
              <em>{task.status}</em>
              {task.result && <p>{task.result.summary}</p>}
            </div>
          ))
        )}
      </div>
    </section>
  )
}

function EventCenter({ events }: { events: FactoryEvent[] }) {
  return (
    <section className="panel event-panel">
      <div className="panel-title">
        <RadioTower size={18} aria-hidden="true" />
        <h2>事件</h2>
      </div>
      <div className="list-panel horizontal-list">
        {events.slice(0, 5).map((event) => (
          <div key={event.event_id} className="list-item">
            <strong>{event.event_type}</strong>
            <span>{event.refs.task_id ?? event.refs.entity_id}</span>
            <em>{new Date(event.timestamp_utc).toLocaleTimeString()}</em>
          </div>
        ))}
      </div>
    </section>
  )
}

function TracePanel({ task }: { task: FactoryTask | null }) {
  return (
    <section className="panel trace-panel">
      <div className="panel-title">
        <Activity size={18} aria-hidden="true" />
        <h2>执行轨迹</h2>
      </div>
      <div className="list-panel horizontal-list">
        {!task ? (
          <p className="empty-text">选择 WH-001 并执行库存分析后显示 trace</p>
        ) : (
          task.trace.map((step) => (
            <div key={step.execution_id} className="list-item">
              <strong>{step.plugin_id}</strong>
              <span>{step.execution_id}</span>
              <em>{step.status}</em>
              <p>{step.summary}</p>
            </div>
          ))
        )}
      </div>
    </section>
  )
}

export default App
