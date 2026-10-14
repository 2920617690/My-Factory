import { http, HttpResponse } from 'msw'

import { factoryEntities, factoryStateById, seedEvents, seedTasks } from '../simulationData'
import type { ActionIntent, FactoryEvent, FactoryState, FactoryTask, TaskStatus } from '../types'

const tasks: FactoryTask[] = [...seedTasks]
const events: FactoryEvent[] = [...seedEvents]
const stateById: Record<string, FactoryState> = structuredClone(factoryStateById)
let taskCounter = 1
let eventCounter = 2

const now = () => new Date().toISOString()
const nextTaskId = () => `TASK-${String(taskCounter++).padStart(3, '0')}`
const nextExecutionId = (taskId: string) => `EXEC-${taskId.slice(-3)}`
const nextEventId = () => `EVT-${String(eventCounter++).padStart(3, '0')}`

function pushEvent(event_type: FactoryEvent['event_type'], refs: FactoryEvent['refs'], payload: Record<string, unknown>) {
  events.unshift({
    event_id: nextEventId(),
    event_type,
    timestamp_utc: now(),
    source: 'msw-platform-mock',
    refs,
    payload,
    schema_version: 'v1',
  })
}

function updateTask(task: FactoryTask, status: TaskStatus) {
  task.status = status
  task.updated_at = now()
  task.trace[0] = {
    ...task.trace[0],
    status,
    ended_at: status === 'COMPLETED' || status === 'FAILED' ? now() : task.trace[0].ended_at,
  }
}

function completeInventoryTask(task: FactoryTask) {
  if (task.status !== 'RUNNING') return

  task.result = {
    title: 'WH-001 库存分析完成',
    summary: 'MAT-001 当前库存 6 件，可覆盖 ORD-001 的首轮备料校验；建议等待 Platform 接入后再写入真实 Factory State。',
    recommendations: ['保持 WH-001 为可用状态', '补充 WMS 来源批次字段', '后续由 Platform 校验后触发 inventory.changed'],
    metrics: {
      material_count: 1,
      current_on_hand: 6,
      order_quantity: 10,
      risk_level: 'medium',
    },
  }
  updateTask(task, 'COMPLETED')
  pushEvent('plugin.completed', { entity_id: 'WH-001', task_id: task.task_id, execution_id: task.execution_id }, {
    plugin_id: 'mock-inventory-plugin',
    capability: task.capability,
  })
  pushEvent('task.completed', { entity_id: 'WH-001', task_id: task.task_id, execution_id: task.execution_id }, {
    status: task.status,
    result_title: task.result.title,
  })
}

export const handlers = [
  http.get('/api/v1/factory', () => HttpResponse.json({
    factory_id: 'FACTORY-001',
    name: 'SVS 双层装配演示厂',
    data_mode: 'mock',
  })),

  http.get('/api/v1/factory/entities', () => HttpResponse.json({ entities: factoryEntities })),

  http.get('/api/v1/factory/entities/:entityId/state', ({ params }) => {
    const entityId = String(params.entityId)
    const state = stateById[entityId]

    if (!state) {
      return HttpResponse.json({ error_code: 'NOT_FOUND', message: `未知实体 ${entityId}` }, { status: 404 })
    }

    return HttpResponse.json(state)
  }),

  http.post('/api/v1/actions', async ({ request }) => {
    const intent = await request.json() as ActionIntent

    if (intent.capability !== 'inventory.analyze' || intent.target.entity_id !== 'WH-001') {
      return HttpResponse.json(
        {
          error_code: 'VALIDATION',
          message: 'MVP 0.1 第一轮联调仅开放 WH-001 的 inventory.analyze。',
        },
        { status: 400 },
      )
    }

    const taskId = nextTaskId()
    const executionId = nextExecutionId(taskId)
    const createdAt = now()
    const task: FactoryTask = {
      task_id: taskId,
      execution_id: executionId,
      target: intent.target,
      capability: intent.capability,
      status: 'RUNNING',
      created_at: createdAt,
      updated_at: createdAt,
      trace: [
        {
          execution_id: executionId,
          task_id: taskId,
          plugin_id: 'mock-inventory-plugin',
          capability: intent.capability,
          status: 'RUNNING',
          started_at: createdAt,
          summary: 'Runtime Mock 已发现 inventory.analyze capability，并调用库存分析插件。',
        },
      ],
    }

    tasks.unshift(task)
    stateById['WH-001'] = {
      ...stateById['WH-001'],
      currentTaskId: taskId,
      updatedAt: createdAt,
    }

    pushEvent('task.created', { entity_id: 'WH-001', task_id: taskId, execution_id: executionId }, {
      capability: intent.capability,
    })
    pushEvent('task.started', { entity_id: 'WH-001', task_id: taskId, execution_id: executionId }, {
      status: task.status,
    })
    pushEvent('plugin.started', { entity_id: 'WH-001', task_id: taskId, execution_id: executionId }, {
      plugin_id: 'mock-inventory-plugin',
      capability: intent.capability,
    })

    globalThis.setTimeout(() => completeInventoryTask(task), 900)

    return HttpResponse.json({ task }, { status: 201 })
  }),

  http.get('/api/v1/tasks', () => HttpResponse.json({ tasks })),

  http.get('/api/v1/tasks/:taskId', ({ params }) => {
    const taskId = String(params.taskId)
    const task = tasks.find((item) => item.task_id === taskId)

    if (!task) {
      return HttpResponse.json({ error_code: 'NOT_FOUND', message: `未知任务 ${taskId}` }, { status: 404 })
    }

    return HttpResponse.json(task)
  }),

  http.get('/api/v1/events', () => HttpResponse.json({ events })),
]
