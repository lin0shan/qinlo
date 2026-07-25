import urllib.request, json

# 检查 inventory_log 的实际 change_type 值
resp = urllib.request.urlopen('http://localhost:8000/api/v1/reports/inbound?period=daily')
data = json.loads(resp.read().decode())
print('=== 入库报表(已过滤) ===')
print(json.dumps(data, ensure_ascii=False, indent=2))

# 检查入库API直接原始数据
print()
import sqlite3
conn = sqlite3.connect('D:\\Agent development\\个人商业助手\\data\\business_helper.db')
c = conn.cursor()

# 检查所有 inventory_log 的 change_type
c.execute("SELECT DISTINCT change_type, COUNT(*) FROM inventory_logs GROUP BY change_type")
print('=== inventory_log change_type 分布 ===')
for r in c.fetchall():
    print(f"  {r[0]}: {r[1]} 条")

print()
c.execute("SELECT id, product_id, change_type, change_quantity, created_at FROM inventory_logs ORDER BY id")
print('=== inventory_log 全部记录 ===')
for r in c.fetchall():
    print(f"  id={r[0]} pid={r[1]} type={r[2]} qty={r[3]} created={r[4]}")

# 检查 sale_orders 状态
print()
c.execute("SELECT DISTINCT status, COUNT(*) FROM sale_orders GROUP BY status")
print('=== sale_orders status 分布 ===')
for r in c.fetchall():
    print(f"  {r[0]}: {r[1]} 条")

# 检查 sale_order_items
print()
c.execute("SELECT soi.id, soi.sale_order_id, soi.product_id, soi.quantity, soi.unit_price FROM sale_order_items soi ORDER BY soi.id")
print('=== sale_order_items 全部记录 ===')
for r in c.fetchall():
    print(f"  id={r[0]} order={r[1]} pid={r[2]} qty={r[3]} price={r[4]}")

conn.close()
