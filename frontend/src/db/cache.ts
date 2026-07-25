/**
 * Offline cache manager.
 *
 * When online: pull data from API and write to IndexedDB.
 * When offline: read cached data from IndexedDB.
 */

import { putAll, getAll, searchProducts, searchMembers, getSyncMeta, putSyncMeta } from './db'
import type { ProductCache, MemberCache } from './db'

const API = '/api/v1'

/** Pull all products from API (paginated) and write to IndexedDB. */
export async function refreshProductCache(): Promise<void> {
  const all: ProductCache[] = []
  let page = 1

  while (true) {
    const res = await fetch(`${API}/products?page=${page}&page_size=100`)
    const data = await res.json()
    for (const p of data.items) {
      all.push({
        id: p.id,
        name: p.name,
        barcode: p.barcode || '',
        spec: p.spec || '',
        category: p.category,
        unit: p.unit,
        retail_price: p.retail_price,
        cost_price: p.cost_price,
        safety_stock: p.safety_stock || 0,
        current_stock: p.current_stock || 0,
        image_url: p.image_url || '',
        status: p.status,
        updated_at: p.updated_at || new Date().toISOString(),
      })
    }
    if (data.items.length < 100) break
    page++
  }

  await putAll('cache_products', all)
}

/** Pull all members from API (paginated) and write to IndexedDB. */
export async function refreshMemberCache(): Promise<void> {
  const all: MemberCache[] = []
  let page = 1

  while (true) {
    const res = await fetch(`${API}/members?page=${page}&page_size=100`)
    const data = await res.json()
    for (const m of data.items) {
      all.push({
        id: m.id,
        name: m.name,
        phone: m.phone,
        gender: m.gender || '',
        skin_type: m.skin_type || '',
        tags: m.tags || '',
        total_spent: m.total_spent || 0,
        points: m.points || 0,
        updated_at: m.created_at || new Date().toISOString(),
      })
    }
    if (data.items.length < 100) break
    page++
  }

  await putAll('cache_members', all)
}

/** Refresh all caches when online. */
export async function refreshAllCaches(): Promise<void> {
  try {
    await Promise.all([refreshProductCache(), refreshMemberCache()])
    await putSyncMeta({
      key: 'last_sync',
      last_sync_at: Date.now(),
      version: String(Date.now()),
    })
  } catch {
    // Silently fail when network is unavailable
  }
}

/** Search products offline (local fuzzy match). */
export async function findProductOffline(keyword: string): Promise<ProductCache[]> {
  return searchProducts(keyword)
}

/** Search members offline (local fuzzy match). */
export async function findMemberOffline(keyword: string): Promise<MemberCache[]> {
  return searchMembers(keyword)
}

/** Check if cached data exists. */
export async function hasCachedData(): Promise<boolean> {
  const products = await getAll<ProductCache>('cache_products')
  return products.length > 0
}

/** Get last sync timestamp. */
export async function getLastSyncTime(): Promise<number | null> {
  const meta = await getSyncMeta('last_sync')
  return meta?.last_sync_at ?? null
}
