/**
 * IndexedDB connection manager.
 *
 * Opens/upgrades the database and provides access to every object store.
 * Low-level entry point for all offline data operations.
 */

const DB_NAME = 'business_helper_offline'
const DB_VERSION = 1

export interface ProductCache {
  id: number
  name: string
  barcode: string
  spec: string
  category: string
  unit: string
  retail_price: number
  cost_price: number
  safety_stock: number
  current_stock: number
  image_url: string
  status: string
  updated_at: string
}

export interface MemberCache {
  id: number
  name: string
  phone: string
  gender: string
  skin_type: string
  tags: string
  total_spent: number
  points: number
  updated_at: string
}

export interface PendingOperation {
  id?: number
  action: string
  payload: Record<string, unknown>
  client_id: string
  timestamp: number
}

export interface SyncMeta {
  key: string
  last_sync_at: number
  version: string
}

let dbPromise: Promise<IDBDatabase> | null = null

function openDB(): Promise<IDBDatabase> {
  if (dbPromise) return dbPromise

  dbPromise = new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION)

    req.onupgradeneeded = () => {
      const db = req.result

      // Product cache
      if (!db.objectStoreNames.contains('cache_products')) {
        db.createObjectStore('cache_products', { keyPath: 'id' })
      }

      // Member cache
      if (!db.objectStoreNames.contains('cache_members')) {
        db.createObjectStore('cache_members', { keyPath: 'id' })
      }

      // Pending sync operation queue
      if (!db.objectStoreNames.contains('pending_operations')) {
        const store = db.createObjectStore('pending_operations', {
          keyPath: 'id',
          autoIncrement: true,
        })
        store.createIndex('timestamp', 'timestamp', { unique: false })
      }

      // Sync metadata
      if (!db.objectStoreNames.contains('sync_meta')) {
        db.createObjectStore('sync_meta', { keyPath: 'key' })
      }
    }

    req.onsuccess = () => resolve(req.result)
    req.onerror = () => {
      dbPromise = null
      reject(req.error)
    }
  })

  return dbPromise
}

/** Generic putAll: batch-write an array into a given object store. */
export async function putAll<T>(storeName: string, items: T[]): Promise<void> {
  const db = await openDB()
  const tx = db.transaction(storeName, 'readwrite')
  const store = tx.objectStore(storeName)
  for (const item of items) {
    store.put(item)
  }
  return new Promise((resolve, reject) => {
    tx.oncomplete = () => resolve()
    tx.onerror = () => reject(tx.error)
  })
}

/** Generic getAll: read all records from a given object store. */
export async function getAll<T>(storeName: string): Promise<T[]> {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(storeName, 'readonly')
    const store = tx.objectStore(storeName)
    const req = store.getAll()
    req.onsuccess = () => resolve(req.result as T[])
    req.onerror = () => reject(req.error)
  })
}

/** Search products (local fuzzy match). */
export async function searchProducts(keyword: string): Promise<ProductCache[]> {
  const all = await getAll<ProductCache>('cache_products')
  if (!keyword) return all
  const kw = keyword.toLowerCase()
  return all.filter(
    (p) =>
      p.name.toLowerCase().includes(kw) ||
      (p.barcode && p.barcode.toLowerCase().includes(kw))
  )
}

/** Search members (local fuzzy match). */
export async function searchMembers(keyword: string): Promise<MemberCache[]> {
  const all = await getAll<MemberCache>('cache_members')
  if (!keyword) return all
  const kw = keyword.toLowerCase()
  return all.filter(
    (m) =>
      m.name.toLowerCase().includes(kw) ||
      m.phone.includes(kw)
  )
}

/** Enqueue a sync operation. */
export async function enqueueOperation(op: PendingOperation): Promise<void> {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction('pending_operations', 'readwrite')
    const store = tx.objectStore('pending_operations')
    store.add(op)
    tx.oncomplete = () => resolve()
    tx.onerror = () => reject(tx.error)
  })
}

/** Get all pending sync operations (sorted by timestamp). */
export async function getPendingOperations(): Promise<PendingOperation[]> {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction('pending_operations', 'readonly')
    const store = tx.objectStore('pending_operations')
    const index = store.index('timestamp')
    const req = index.getAll()
    req.onsuccess = () => resolve(req.result as PendingOperation[])
    req.onerror = () => reject(req.error)
  })
}

/** Remove completed operations. */
export async function clearOperations(ids: number[]): Promise<void> {
  const db = await openDB()
  const tx = db.transaction('pending_operations', 'readwrite')
  const store = tx.objectStore('pending_operations')
  for (const id of ids) {
    store.delete(id)
  }
  return new Promise((resolve, reject) => {
    tx.oncomplete = () => resolve()
    tx.onerror = () => reject(tx.error)
  })
}

/** Read sync metadata. */
export async function getSyncMeta(key: string): Promise<SyncMeta | undefined> {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction('sync_meta', 'readonly')
    const store = tx.objectStore('sync_meta')
    const req = store.get(key)
    req.onsuccess = () => resolve(req.result as SyncMeta | undefined)
    req.onerror = () => reject(req.error)
  })
}

/** Write sync metadata. */
export async function putSyncMeta(meta: SyncMeta): Promise<void> {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction('sync_meta', 'readwrite')
    const store = tx.objectStore('sync_meta')
    store.put(meta)
    tx.oncomplete = () => resolve()
    tx.onerror = () => reject(tx.error)
  })
}

export { openDB }
