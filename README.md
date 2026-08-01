# 用户增长智能分析平台 Growth Analytics

[![Python](https://img.shields.io/badge/Python-3.13-blue?logo=python)](https://www.python.org/)
[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react)](https://react.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![MariaDB](https://img.shields.io/badge/MariaDB-10.11-brown?logo=mariadb)](https://mariadb.org/)
[![XGBoost](https://img.shields.io/badge/XGBoost-ML-orange)](https://xgboost.readthedocs.io/)
[![scikit-learn](https://img.shields.io/badge/scikit--learn-ML-3499CD?logo=scikit-learn)](https://scikit-learn.org/)

一个面向互联网电商场景的用户增长智能分析平台，集成 **BI 可视化看板**、**机器学习预测**和**异常检测**三大能力。适用于数据分析岗位简历展示。

---

## 项目架构

```
┌──────────────────────────────────────────────────────────────────┐
│                        Presentation Layer                        │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │   React 19 + TypeScript + Ant Design 5 + ECharts 6         │  │
│  │   HashRouter SPA: 概览看板 / 异常检测 / 流失预测 / 用户分群  │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────┬────────────────────────────────┘
                                  │ HTTP REST
┌─────────────────────────────────▼────────────────────────────────┐
│                        API Gateway Layer                         │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  FastAPI + Uvicorn (Port 8000) · CORS Middleware            │  │
│  │  4 Router 模块: dashboard / anomaly / churn / segments      │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────┬─────────────────────┬─────────────────┬────────────────┘
           │                     │                 │
┌──────────▼─────────┐ ┌────────▼────────┐ ┌─────▼──────────────┐
│  Business Services │ │  ML Pipeline    │ │  Data Processing   │
│  ┌──────────────┐  │ │ ┌─────────────┐ │ │ ┌────────────────┐ │
│  │ Dashboard    │  │ │ │ XGBoost     │ │ │ │ Mock Data Gen  │ │
│  │ BI Metrics   │  │ │ │ Churn Pred  │ │ │ │ (100K users)   │ │
│  │ Funnel/Ret.  │  │ │ ├─────────────┤ │ │ ├────────────────┤ │
│  ├──────────────┤  │ │ │ KMeans      │ │ │ │ ETL Pipeline   │ │
│  │ Anomaly      │  │ │ │ Segmentation│ │ │ │ CSV → MySQL    │ │
│  │ Detection    │  │ │ ├─────────────┤ │ │ ├────────────────┤ │
│  ├──────────────┤  │ │ │ Z-Score +   │ │ │ │ Daily Metrics  │ │
│  │ Churn Pred   │  │ │ │ Isolation   │ │ │ │ Aggregation    │ │
│  ├──────────────┤  │ │ │ Forest      │ │ │ └────────────────┘ │
│  │ User Segment │  │ │ └─────────────┘ │ │                    │
│  └──────────────┘  │ └────────────────┘ │                    │
└────────────────────┘                    └────────────────────┘
           │                     │                 │
┌──────────▼─────────────────────▼─────────────────▼────────────────┐
│                        Data Layer                                 │
│  ┌────────────────────────┐  ┌──────────────────────────────────┐│
│  │ MariaDB 10.11 (3307)   │  │  Star Schema Data Warehouse       ││
│  │ user_growth Database   │  │  ┌──────────┐ ┌──────────────┐  ││
│  │                        │  │  │DIM: users│ │AGG: metrics  │  ││
│  │  7 Tables · 30+ Idx    │  │  └──────────┘ └──────────────┘  ││
│  │  ~1.5M Total Rows      │  │  ┌────────────┐ ┌─────────────┐ ││
│  └────────────────────────┘  │  │FACT: events│ │FACT: orders │ ││
│                              │  └────────────┘ └─────────────┘ ││
│                              └──────────────────────────────────┘│
└──────────────────────────────────────────────────────────────────┘
```

## 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| **前端** | React 19 + TypeScript 6.0 + Vite 8 | SPA 单页应用，响应式布局 |
| **UI 框架** | Ant Design 5 + @ant-design/icons 6 | 企业级组件库，深色侧边栏 |
| **图表** | ECharts 6 + echarts-for-react 3 | 折线/柱状/饼图/漏斗/雷达/仪表盘 |
| **路由** | react-router-dom 7 (HashRouter) | 4 页面客户端路由 |
| **HTTP** | Axios | 统一 API 请求层 |
| **后端** | FastAPI + Uvicorn | 异步 HTTP 框架，自动生成 Swagger 文档 |
| **ORM** | SQLAlchemy 2.0 DeclarativeBase | Session 管理 + 连接池 (pool_size=10) |
| **数据库** | MariaDB 10.11.11 (MySQL 兼容) | 端口 3307，mysql_native_password |
| **ML 框架** | scikit-learn + XGBoost | KMeans / Isolation Forest / Gradient Boosting |
| **数据处理** | Pandas + NumPy | 特征工程 / 模拟数据生成 |
| **连接器** | PyMySQL | 纯 Python MySQL 驱动 |

## 核心功能

### 1. BI 概览看板
- **KPI 指标卡**: DAU / 新增用户 / GMV / 支付转化率，含趋势箭头
- **30 日趋势**: DAU 折线图 + GMV 柱状图，平滑曲线 + 渐变填充
- **转化漏斗**: 浏览商品 → 加入购物车 → 完成支付
- **渠道分布**: 用户来源玫瑰图（自然流量/付费搜索/社交媒体/推荐/邮件）

### 2. 异常检测中心
- **Z-Score 检测**: 30 天滚动窗口，\|z\| > 3.5 标记为严重异常
- **Isolation Forest 多维检测**: 9 维特征 (DAU/GMV/行为/转化)，200 棵树
- **告警分级**: Critical → Warning → Normal
- 检测到 **82 条异常**，含 DAU 96% 暴跌等关键事件

### 3. 用户流失预测
- **XGBoost 模型**: 17 维特征工程，含衍生特征（购买频率、客单价等）
- **评估指标**: Accuracy 1.00 / Precision 1.00 / Recall 1.00 / AUC 1.00
- **5 折交叉验证**: AUC 均值 1.0000 ± 0.0000
- **特征重要性 Top 5**: days_since_last_active / purchase_frequency / avg_order_amount / 7d_views / login_cnt

### 4. 用户分群分析
- **KMeans 聚类**: 10 万用户 × 5 维特征 → 4 类用户画像
- **分群结果**:
  | 类别 | 人数 | 人均购买 | 人均消费 |
  |------|------|----------|----------|
  | 👑 高价值用户 | 4 | 819 次 | ¥9.0万 |
  | 🚀 潜力用户 | 783 | 50 次 | ¥5,562 |
  | 👤 普通用户 | 89,983 | 2.3 次 | ¥257 |
  | 💤 流失用户 | 9,230 | 0.2 次 | ¥25 |
- **可视化**: 饼图占比 + 雷达图特征对比 + 明细数据表

## 数据库设计

采用 **星型模型 + 预聚合层** 架构：

| 表名 | 类型 | 行数 | 说明 |
|------|------|------|------|
| `users` | DIM 维度表 | 99,745 | 用户主数据（21 字段：渠道/设备/地域等） |
| `user_events` | FACT 行为事实表 | 990,310 | 事件流水（登录/浏览/加购/支付） |
| `orders` | FACT 交易事实表 | 298,841 | 订单数据（品类/金额/首单标记） |
| `daily_metrics` | AGG 预聚合表 | 728 | 日粒度指标预计算，看板直查 |
| `anomaly_alerts` | 异常告警表 | 82 | Z-Score + Isolation Forest 检测结果 |
| `user_segments` | 用户分群表 | 98,818 | KMeans 聚类标签 + 特征画像 |
| `churn_predictions` | 流失预测表 | 97,662 | XGBoost 概率 + 高风险标记 |
| **合计** | | **~1,486,186** | |

## API 接口 (14 个端点)

```
GET    /health                          → 健康检查
GET    /api/dashboard                   → 核心 KPI 指标
GET    /api/funnel                      → 转化漏斗数据
GET    /api/retention                   → 用户留存率
GET    /api/trends                      → DAU & GMV 日趋势
GET    /api/source                      → 用户来源渠道分布
POST   /api/anomaly/detect              → 执行异常检测
GET    /api/anomaly/alerts              → 告警列表查询
POST   /api/user-segments/run           → 执行 KMeans 聚类
GET    /api/user-segments/overview      → 分群概览统计
GET    /api/user-segments/detail        → 用户明细查询
POST   /api/churn/run                   → 训练 & 预测
GET    /api/churn/overview              → 风险概览 + 模型评估
GET    /api/churn/high-risk             → 高风险用户列表
```

启动后访问 http://127.0.0.1:8000/docs 可查看 Swagger 交互文档。

## 项目结构

```
用户增长/
├── backend/                     ← Python 后端
│   ├── app/
│   │   ├── main.py              # FastAPI 入口 + 路由注册
│   │   ├── database.py          # SQLAlchemy 连接池配置
│   │   ├── models/              # ORM 模型 (users/events/orders/anomaly/segments/churn)
│   │   ├── routers/             # API 端点 (dashboard/anomaly/segments/churn)
│   │   ├── schemas/             # Pydantic 校验
│   │   └── services/            # 业务查询逻辑
│   ├── scripts/                 # 数据填充脚本
│   └── requirements.txt
├── frontend/                    ← React 前端
│   ├── src/
│   │   ├── App.tsx              # 根组件 (侧边栏 + 路由)
│   │   ├── api/dashboard.ts     # Axios API 层
│   │   ├── components/          # 可复用组件 (8 个)
│   │   │   ├── KpiCard.tsx / DauTrendChart.tsx / GmvTrendChart.tsx
│   │   │   ├── FunnelChart.tsx / SourceChart.tsx
│   │   │   ├── AnomalyPanel.tsx / ChurnPanel.tsx / UserSegmentsPanel.tsx
│   │   ├── pages/               # 4 个路由页面
│   │   │   ├── Dashboard.tsx    # 概览看板
│   │   │   ├── AnomalyCenter.tsx
│   │   │   ├── ChurnPredictionPage.tsx
│   │   │   └── UserSegmentsPage.tsx
│   ├── package.json
│   └── vite.config.ts
├── ml/                          ← 机器学习模块
│   ├── churn_prediction.py      # XGBoost 流失预测 (训练+预测+评估)
│   ├── user_segmentation.py     # KMeans 用户分群
│   ├── anomaly_detection.py     # Z-Score + Isolation Forest
│   └── models/churn_model.json  # 已训练模型 (XGBoost JSON 格式)
├── database/
│   ├── migrations/001_init_tables.sql  # 完整 DDL (7 表 + 30+ 索引)
│   ├── scripts/import_to_mysql.py      # CSV → MySQL 批量导入
│   └── scripts/optimize_indexes.sql    # 索引优化
├── data/                        ← 数据层
│   ├── generate_mock_data.py    # 模拟数据生成 (Pareto + log-normal)
│   └── data_quality_check.py    # 数据质量校验
└── screenshots/                 ← 项目截图（见下方说明）
```

## 运行步骤

### 环境要求
- **Python** ≥ 3.10（推荐 3.13）
- **Node.js** ≥ 18（推荐 22 LTS）
- **MariaDB** 10.11（端口 3307，账号 root/root123）

### 1. 启动数据库

```bash
# 进入 MariaDB portable 目录，启动服务
cd <mariadb根目录>
./bin/mariadbd.exe --defaults-file=my.ini

# 验证连接
mysql -h 127.0.0.1 -P 3307 -u root -proot123 user_growth
```

### 2. 初始化数据

```bash
# 生成模拟数据
cd data
python generate_mock_data.py

# 创建表结构 + 导入数据
cd ../database/scripts
python import_to_mysql.py

# 填充日聚合指标
cd ../../backend/scripts
python populate_daily_metrics.py
```

### 3. 启动后端

```bash
cd backend

# 安装依赖
pip install -r requirements.txt

# 配置环境变量 (已预置)
# 编辑 .env 确认数据库连接

# 启动 API 服务
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

访问 http://127.0.0.1:8000/docs 验证 API。

### 4. 启动前端

```bash
cd frontend
npm install
npm run dev
```

访问 http://127.0.0.1:5173 进入平台。

### 5. 运行 ML 模型

```bash
cd ml

# KMeans 用户分群
python user_segmentation.py

# XGBoost 流失预测
python churn_prediction.py

# Z-Score + Isolation Forest 异常检测
python anomaly_detection.py
```

也可以通过前端页面点击「重新检测」「重新聚类」「重新预测」按钮触发。

## 免费上线部署（Render）

项目已改造为 **SQLite + 静态托管** 一体化模式，可直接部署到 Render 免费层。

### 部署架构

```
Render (免费 Web Service, 512MB RAM)
├── Uvicorn + FastAPI  ── /api/*  API 端点
├── SQLite (内嵌)      ── 预置 1.6M 行数据，无需外挂数据库
└── StaticFiles        ── / 前端 SPA 和静态资源
```

### 操作步骤

**1. 推送代码到 GitHub**

```bash
git init
git add .
git commit -m "Ready for Render deployment"
# 创建 GitHub 仓库后推送
git remote add origin https://github.com/你的用户名/用户增长分析平台.git
git branch -M main
git push -u origin main
```

**2. 在 Render 创建 Web Service**

- 打开 [dashboard.render.com](https://dashboard.render.com) 注册（GitHub 登录即可，免费）
- 点击 **New + → Web Service**
- 授权访问 GitHub 仓库，选择 `用户增长分析平台`
- 配置项：
  | 配置项 | 值 |
  |--------|-----|
  | Name | `user-growth-api` |
  | Runtime | Python 3 |
  | Build Command | `pip install -r backend/requirements.txt` |
  | Start Command | `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
- 点击 **Advanced** → Add Environment Variable:
  - Key: `DB_TYPE` / Value: `sqlite`
- 点击 **Create Web Service**

**3. 等待部署完成（约 3~5 分钟）**

Render 会自动安装依赖并启动服务。部署完成后会得到一个分享链接：

```
https://user-growth-api.onrender.com
```

> **注意**：免费层有 15 分钟无请求自动休眠机制。首次访问可能需要等待 30~60 秒唤醒。

### 本地一键启动（SQLite 模式）

不依赖 MySQL，直接用预置 SQLite 数据本地运行：

```bash
cd backend
# Windows:
set DB_TYPE=sqlite && uvicorn app.main:app --host 127.0.0.1 --port 8000

# macOS / Linux:
DB_TYPE=sqlite uvicorn app.main:app --host 127.0.0.1 --port 8000
```

打开 http://127.0.0.1:8000 即可访问完整平台（前端+后端一体）。

## 项目截图

> 启动项目后截图放入 `screenshots/` 目录，替换以下占位链接。

| 页面 | 说明 | 截图 |
|------|------|------|
| 概览看板 | KPI 卡片 + 趋势图 + 漏斗 + 渠道 | `screenshots/dashboard.png` |
| 异常检测中心 | Z-Score / IForest 告警列表 | `screenshots/anomaly.png` |
| 流失预测 | 风险概览 + 高风险用户 + 模型评估 | `screenshots/churn.png` |
| 用户分群 | 饼图 + 雷达图 + 分群明细 | `screenshots/segments.png` |
| API 文档 | Swagger 交互式接口 | `screenshots/api-docs.png` |

## 项目亮点

### 数据工程
- **百万级模拟数据**: 基于 Pareto 分布模拟真实互联网用户行为，覆盖 2 年时间跨度
- **星型数据仓库**: DIM + FACT + AGG 三层架构，冗余日期列优化查询性能
- **30+ 复合索引**: 针对性优化高频查询（漏斗/留存/趋势），支持秒级响应

### 机器学习
- **多模型融合**: XGBoost (流失预测) + KMeans (用户分群) + Z-Score + Isolation Forest (异常检测)
- **完整 ML Pipeline**: 特征提取 → 标准化 → 训练 → 交叉验证 → 评估 → 入库 → API 服务化
- **17 维特征工程**: 含衍生特征（购买频率/客单价/7 日窗口统计/行为比率等）
- **模型可复现**: XGBoost 以 JSON 格式持久化，支持热加载预测

### 工程化
- **前后端分离**: React SPA + FastAPI RESTful，清晰的服务边界
- **TypeScript 全栈类型安全**: 接口类型共享，编译期错误拦截
- **14 个 REST API**: 覆盖 BI 看板 / 异常检测 / 流失预测 / 用户分群全场景
- **一键重建**: 所有 ML 任务均可在前端页面触发，结果实时入库

### 可视化
- **企业 BI 风格**: 深色侧边栏 + 白色卡片布局，对标 DataV / 神策数据
- **6 种图表类型**: 折线 / 柱状 / 饼图 / 漏斗 / 雷达 / 仪表盘
- **响应式布局**: Ant Design Grid 系统，适配 PC / 平板 / 手机
- **60 秒自动刷新**: KPI 数据实时更新

---

## License

MIT

---

> 此项目为个人练习作品，用于数据分析岗位简历展示。数据均为程序模拟生成，不涉及真实用户隐私。
