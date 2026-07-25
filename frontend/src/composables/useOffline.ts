/**
 * Offline detection + automatic sync trigger.
 *
 * Listens to navigator.onLine events + periodic health checks.
 * Auto-triggers sync when back online; provides reactive state to UI.
 */

import { ref, onMounted, onUnmounted } from 'vue'
import { syncPendingOperations, getQueueLength } from '../db/sync'
import { refreshAllCaches } from '../db/cache'

export type NetworkStatus = 'online' | 'offline' | 'syncing' | 'sync_failed'

export function useOffline() {
  const status = ref<NetworkStatus>(navigator.onLine ? 'online' : 'offline')
  const pendingCount = ref(0)

  let healthTimer: ReturnType<typeof setInterval> | null = null
  let cacheInitialized = false

  /** Execute sync. */
  async function doSync() {
    if (status.value === 'syncing') return
    status.value = 'syncing'

    try {
      const result = await syncPendingOperations()
      if (result.fail > 0 && result.success === 0) {
        status.value = 'sync_failed'
      } else {
        status.value = 'online'
      }
      pendingCount.value = await getQueueLength()
    } catch {
      status.value = 'sync_failed'
    }
  }

  /** Initialize cache (pull full data on first online attempt). */
  async function initCache() {
    if (cacheInitialized) return
    if (!navigator.onLine) return

    try {
      // Check if server is reachable first
      const res = await fetch('/api/v1/health')
      if (!res.ok) return

      await refreshAllCaches()
      cacheInitialized = true
    } catch {
      // Server unreachable, skip
    }
  }

  /** Online event handler. */
  async function handleOnline() {
    await initCache()
    await doSync()
  }

  /** Offline event handler. */
  function handleOffline() {
    status.value = 'offline'
    pendingCount.value = 0
    getQueueLength().then((n) => (pendingCount.value = n))
  }

  onMounted(() => {
    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)

    // Initialize cache
    initCache()

    // Periodic health check (every 30s) to detect silent disconnection
    healthTimer = setInterval(async () => {
      if (!navigator.onLine) {
        status.value = 'offline'
        return
      }
      try {
        const res = await fetch('/api/v1/health')
        if (res.ok && status.value !== 'online') {
          status.value = 'online'
          await doSync()
        }
      } catch {
        if (status.value === 'online') {
          status.value = 'offline'
        }
      }
    }, 30000)
  })

  onUnmounted(() => {
    window.removeEventListener('online', handleOnline)
    window.removeEventListener('offline', handleOffline)
    if (healthTimer) clearInterval(healthTimer)
  })

  return { status, pendingCount, doSync, initCache }
}
