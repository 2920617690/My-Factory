import type { ActionIntent, FactoryEntity, FactoryEvent, FactoryState, FactoryTask } from '../types'

const PLATFORM_BASE_URL = import.meta.env.VITE_PLATFORM_API_URL ?? ''

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${PLATFORM_BASE_URL}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...init?.headers,
    },
  })

  if (!response.ok) {
    throw new Error(`Platform API 请求失败 (${response.status})`)
  }

  return await response.json() as T
}

export const factoryClient = {
  async listEntities(signal?: AbortSignal) {
    const payload = await requestJson<{ entities: FactoryEntity[] }>('/api/v1/factory/entities', { signal })
    return payload.entities
  },

  async getEntityState(entityId: string, signal?: AbortSignal) {
    return await requestJson<FactoryState>(`/api/v1/factory/entities/${entityId}/state`, { signal })
  },

  async submitAction(intent: ActionIntent, signal?: AbortSignal) {
    return await requestJson<{ task: FactoryTask }>('/api/v1/actions', {
      method: 'POST',
      signal,
      body: JSON.stringify(intent),
    })
  },

  async getTask(taskId: string, signal?: AbortSignal) {
    return await requestJson<FactoryTask>(`/api/v1/tasks/${taskId}`, { signal })
  },

  async listTasks(signal?: AbortSignal) {
    const payload = await requestJson<{ tasks: FactoryTask[] }>('/api/v1/tasks', { signal })
    return payload.tasks
  },

  async listEvents(signal?: AbortSignal) {
    const payload = await requestJson<{ events: FactoryEvent[] }>('/api/v1/events', { signal })
    return payload.events
  },
}
