import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: '/inventory',
  },
  {
    path: '/inventory',
    name: 'Inventory',
    component: () => import('../views/InventoryView.vue'),
    meta: { title: '库存', icon: 'inventory' },
  },
  {
    path: '/sale',
    name: 'Sale',
    component: () => import('../views/SaleView.vue'),
    meta: { title: '销售', icon: 'sale' },
  },
  {
    path: '/products',
    name: 'Products',
    component: () => import('../views/ProductsView.vue'),
    meta: { title: '商品', icon: 'products' },
  },
  {
    path: '/import-products',
    name: 'ImportProducts',
    component: () => import('../views/ImportProductsView.vue'),
    meta: { title: '导入商品', icon: 'orders-o' },
  },
  {
    path: '/members',
    name: 'Members',
    component: () => import('../views/MembersView.vue'),
    meta: { title: '会员', icon: 'members' },
  },
  {
    path: '/shipments',
    name: 'Shipments',
    component: () => import('../views/ShipmentsView.vue'),
    meta: { title: '发货', icon: 'shipments' },
  },
  {
    path: '/reports',
    name: 'Reports',
    component: () => import('../views/ReportsView.vue'),
    meta: { title: '报表', icon: 'reports' },
  },
  {
    path: '/coupons',
    name: 'Coupons',
    component: () => import('../views/CouponsView.vue'),
    meta: { title: '兑换券', icon: 'coupon-o' },
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('../views/SettingsView.vue'),
    meta: { title: '设置', icon: 'settings' },
  },
]

export default routes
