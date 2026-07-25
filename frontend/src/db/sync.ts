/**
 * Offline sync engine.
 *
 * When offline: enqueue operations to the pending_operations queue.
 * When online: batch POST to /api/v1/sync/batch, then clear synced items.
 */

import { enqueueOperation, getPendingOperations, clearOperations } from './db'
import type { PendingOperation } from './db'

const API = '/api/v1'

let syncInProgress = false

/** Enqueue an offline operation. */
export async function queueOperation(
  action: string,
  payload: Record<string, unknown>
): Promise<void> {
  const op: PendingOperation = {
    action,
    payload,
    client_id: crypto.randomUUID(),
    timestamp: Date.now(),
  }
  await enqueueOperation(op)
}

/** Get queue length. */
export async function getQueueLength(): Promise<number> {
  const ops = await getPendingOperations()
  return ops.length
}

/** Execute sync: batch-submit all pending operations. */
export async function syncPendingOperations(): Promise<{
  success: number
  fail: number
  errors: string[]
}> {
  if (syncInProgress) return { success: 0, fail: 0, errors: [] }
  syncInProgress = true

  try {
    const ops = await getPendingOperations()
    if (ops.length === 0) return { success: 0, fail: 0, errors: [] }

    const res = await fetch(`${API}/sync/batch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ operations: ops }),
    })

    if (!res.ok) {
      return { success: 0, fail: ops.length, errors: [`HTTP ${res.status}`] }
    }

    const data = await res.json()
    const results: Array<{ client_id?: string; success: boolean; message?: string }> =
      data.results

    // Remove successfully synced operations
    const successIds: number[] = []
    const errors: string[] = []
    for (let i = 0; i < ops.length; i++) {
      const result = results[i]
      if (result && result.success) {
        successIds.push(ops[i].id!)
      } else {
        const msg = result?.message || 'Sync failed'
        errors.push(msg)
        // Inventory conflict: mark as server-rejected
        if (msg.includes('库存') || msg.includes('已存在')) {
          successIds.push(ops[i].id!) // Also clear conflicted items (server already handled)
        }
      }
    }

    if (successIds.length > 0) {
      await clearOperations(successIds)
    }

    return { success: successIds.length, fail: ops.length - successIds.length, errors }
  } catch (e) {
    return { success: 0, fail: 0, errors: [String(e)] }
  } finally {
    syncInProgress = false
  }
}
