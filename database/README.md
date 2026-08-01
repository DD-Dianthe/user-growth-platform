# 数据库设计文档

## 数据仓库架构

互联网用户增长分析平台采用 **星型模型 + 预聚合层** 的轻量数据仓库设计：

```
        ┌─────────────────────┐
        │   users (DIM 维度)   │
        └──────┬──────┬───────┘
               │      │
    ┌──────────▼┐  ┌──▼───────────┐
    │user_events│  │  orders (FACT)│
    │(行为事实)  │  │  (交易事实)    │
    └───────────┘  └───────────────┘
               │      │
        ┌──────▼──────▼───────┐
        │  daily_metrics       │
        │  (预聚合加速层)       │
        └──────────────────────┘
```

## 表结构

| 表名 | 类型 | 行数 | 说明 |
|------|------|------|------|
| `users` | DIM 维度表 | 100K | 用户主数据，含人口统计和渠道归因 |
| `user_events` | FACT 事实表 | 1M | 用户行为事件流水，OLAP 查询主表 |
| `orders` | FACT 事实表 | 300K | 交易订单，含品类/状态/首单标记 |
| `daily_metrics` | AGG 聚合表 | 按天生成 | 预计算日指标，看板直查不扫全表 |

## 切换 MySQL 步骤

```bash
# 1. 修改 backend/.env
DB_TYPE=mysql
MYSQL_HOST=127.0.0.1
MYSQL_PASSWORD=your_real_password

# 2. 执行建表 DDL（或在导入脚本中自动执行）
mysql -u root -p < database/migrations/001_init_tables.sql

# 3. 导入数据
python database/scripts/import_to_mysql.py

# 4. 重启后端服务
```
