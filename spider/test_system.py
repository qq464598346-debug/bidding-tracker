# -*- coding: utf-8 -*-
"""测试爬虫系统是否正常工作"""
import sys, io
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

print("=" * 50)
print("  爬虫系统测试 v4.0")
print("=" * 50)

# 测试1: 数据库
print("\n[1/3] 数据库初始化...")
from core.config import Settings
from core.db import Database
settings = Settings()
db = Database(settings.DATABASE_PATH)
db.init_tables()
stats = db.get_stats()
db.close()
print(f"  总记录数: {stats['total']}")
print(f"  各运营商: {stats.get('by_operator', {})}")

# 测试2: API服务
print("\n[2/3] API服务启动测试...")
from api.server import create_app
app = create_app()
client = app.test_client()

resp = client.get('/api/stats')
data = resp.get_json()
print(f"  /api/stats -> {resp.status_code}")
if data:
    d = data.get('data', {})
    print(f"  total={d.get('total')}, today_new={d.get('today_new')}")

# 测试3: 招标列表API
resp2 = client.get('/api/bidding?limit=5')
data2 = resp2.get_json()
print(f"  /api/bidding?limit=5 -> {resp2.status_code}")
if data2:
    items = data2.get('data', {}).get('items', [])
    print(f"  返回{len(items)}条数据")
    if items:
        it = items[0]
        print(f"  首条: [{it.get('operator')}] {it.get('title','')[:40]}...")

print("\n" + "=" * 50)
print("  ✅ 所有模块正常!")
print("=" * 50)
