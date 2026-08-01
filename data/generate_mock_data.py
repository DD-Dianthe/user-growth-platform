"""
互联网电商APP模拟数据生成器 v2（完整字段版）

数据规模:
  - 用户表: 100,000 条 (7 字段)
  - 行为事件表: 1,000,000 条 (7 字段)
  - 订单表: 300,000 条 (7 字段)

新增字段:
  users:    gender, device_type
  events:   session_id, page_url, duration_ms, device_info
  orders:   product_category, order_status, is_first_order
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import os
import time
import json
import uuid

# ============ 配置 ============
N_USERS = 100_000
N_EVENTS = 1_000_000
N_ORDERS = 300_000
SEED = 42

np.random.seed(SEED)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "mock")
os.makedirs(OUTPUT_DIR, exist_ok=True)

END_DATE = np.datetime64("2026-07-31")
START_DATE = END_DATE - np.timedelta64(730, "D")

# 页面与事件映射
PAGE_EVENT_MAP = {
    "login":          ["/login", "/splash"],
    "view_product":   ["/home", "/products/detail", "/search", "/recommend", "/category/electronics",
                       "/category/clothing", "/category/food", "/category/home", "/category/beauty"],
    "add_cart":       ["/products/detail", "/cart"],
    "pay":            ["/cart", "/checkout", "/payment", "/order/confirm"],
}

# 商品品类
PRODUCT_CATEGORIES = ["电子产品", "服装鞋帽", "食品生鲜", "家居日用", "美妆个护",
                      "母婴用品", "运动户外", "图书音像", "医疗健康", "其他"]

# 订单状态 & 权重
ORDER_STATUSES = ["已支付", "已支付", "已支付", "已支付", "已支付",
                  "已取消", "已取消",
                  "退款中", "已退款"]
STATUS_WEIGHTS = [0.50, 0.15, 0.10, 0.05, 0.05, 0.04, 0.03, 0.04, 0.04]

t0 = time.time()
print("=" * 60)
print("互联网电商APP模拟数据生成器 v2 (完整字段)")
print(f"用户: {N_USERS:,} | 行为: {N_EVENTS:,} | 订单: {N_ORDERS:,}")
print("=" * 60)

# ============================================================
# 第一步: 用户表
# ============================================================
print("\n[1/3] 生成用户表...")

user_ids = np.arange(1, N_USERS + 1, dtype=np.int32)

# 年龄
ages = np.clip(np.random.normal(28, 8, N_USERS), 15, 65).astype(np.int16)

# 城市
cities_all = np.array([
    "北京","上海","广州","深圳",
    "杭州","成都","武汉","南京","重庆","西安","长沙","苏州","郑州","天津",
    "合肥","福州","厦门","济南","青岛","昆明","贵阳","南宁","南昌","太原",
    "石家庄","哈尔滨","长春","沈阳","海口","银川","拉萨",
])
city_w = np.array([
    0.06,0.06,0.06,0.06,
    0.03,0.03,0.03,0.03,0.03,0.03,0.03,0.03,0.03,0.03,
    0.03,0.03,0.03,0.03,0.03,0.03,0.03,0.03,0.03,0.03,
    0.023,0.023,0.023,0.023,0.023,0.023,0.022,
])
city_w /= city_w.sum()
cities = np.random.choice(cities_all, N_USERS, p=city_w)

# 注册时间 (向近期倾斜)
reg_days = (1 - np.sqrt(np.random.random(N_USERS))) * 730
reg_times = END_DATE - np.timedelta64(1, "D") * reg_days.astype(int)

# 渠道
ch_pool = np.array(["organic", "paid_search", "social_media", "referral", "email"])
ch_w = np.array([0.35, 0.25, 0.20, 0.15, 0.05])
channels = np.random.choice(ch_pool, N_USERS, p=ch_w)

# --- 新增字段 ---
# 性别: 男 52% / 女 48%
genders = np.random.choice(["男", "女"], N_USERS, p=[0.52, 0.48])

# 设备: iOS 35% / Android 65%
devices = np.random.choice(["iOS", "Android"], N_USERS, p=[0.35, 0.65])


# 帕累托活跃度分
activity_raw = np.random.pareto(2.0, N_USERS)
activity_score = activity_raw / activity_raw.sum()

# 组装用户 DF
df_users = pd.DataFrame({
    "user_id": user_ids,
    "age": ages,
    "gender": genders,
    "city": cities,
    "device_type": devices,
    "registration_time": pd.to_datetime(reg_times).strftime("%Y-%m-%d %H:%M:%S"),
    "channel": channels,
})

print(f"  生成 {N_USERS:,} 条用户 (7 字段) | 耗时 {time.time() - t0:.1f}s")
print(f"  性别: 男 {genders.tolist().count('男'):,} / 女 {genders.tolist().count('女'):,}")
print(f"  设备: iOS {(devices == 'iOS').sum():,} / Android {(devices == 'Android').sum():,}")

# ============================================================
# 第二步: 行为事件
# ============================================================
print(f"\n[2/3] 生成行为事件表 ({N_EVENTS:,} 条)...")
t1 = time.time()

# 每用户事件数
ev_counts = np.maximum(1, (activity_score * N_EVENTS).astype(np.int32))
diff = N_EVENTS - ev_counts.sum()
if diff > 0:
    idx = np.random.choice(N_USERS, diff, replace=True)
    np.add.at(ev_counts, idx, 1)
elif diff < 0:
    idx = np.random.choice(np.where(ev_counts > 1)[0], abs(diff), replace=True)
    np.add.at(ev_counts, idx, -1)

total_ev = ev_counts.sum()
user_id_arr = np.repeat(user_ids, ev_counts)

# 事件类型
EVENT_TYPES = ["login", "view_product", "add_cart", "pay"]
EV_PROBS = [0.25, 0.40, 0.20, 0.15]
ev_idx = np.random.choice(4, total_ev, p=EV_PROBS)
ev_type_arr = np.array(EVENT_TYPES)[ev_idx]

# 事件时间
end_ts_i64 = END_DATE.astype("datetime64[s]").astype("int64")
reg_ts_i64 = reg_times.astype("datetime64[s]").astype("int64")
intervals = np.maximum(1, end_ts_i64 - reg_ts_i64)
proportions = np.random.beta(2, 1, total_ev)
cum_ev = np.concatenate([[0], np.cumsum(ev_counts)])
ev_ts_i64 = np.empty(total_ev, dtype=np.int64)
for i in range(N_USERS):
    lo, hi = cum_ev[i], cum_ev[i + 1]
    if hi > lo:
        ev_ts_i64[lo:hi] = reg_ts_i64[i] + (proportions[lo:hi] * intervals[i]).astype(np.int64)
ev_times = ev_ts_i64.astype("datetime64[s]")

# --- 新增字段: session_id ---
# 策略: 同一用户在 30 分钟窗口内的事件归为同一 session
# 先按 user_id + event_time 排序，相邻事件间隔 > 1800s 则开始新 session
sort_order = np.lexsort((ev_ts_i64, user_id_arr))
user_id_sorted = user_id_arr[sort_order]
ev_ts_sorted = ev_ts_i64[sort_order]

session_ids = np.empty(total_ev, dtype=object)
current_sid = ""
for i in range(total_ev):
    if i == 0 or user_id_sorted[i] != user_id_sorted[i - 1]:
        # 新用户 → 新 session
        current_sid = f"sess_{uuid.uuid4().hex[:12]}"
    else:
        gap = ev_ts_sorted[i] - ev_ts_sorted[i - 1]
        if gap > 1800:  # >30分钟 → 新 session
            current_sid = f"sess_{uuid.uuid4().hex[:12]}"
    session_ids[i] = current_sid

# 恢复原始排序
session_ids_unsorted = np.empty(total_ev, dtype=object)
session_ids_unsorted[sort_order] = session_ids
session_ids = session_ids_unsorted

n_sessions = len(set(session_ids))
print(f"  会话数: {n_sessions:,}")

# --- 新增字段: page_url ---
# 根据事件类型分配对应页面
page_urls = np.empty(total_ev, dtype=object)
for i in range(total_ev):
    pages = PAGE_EVENT_MAP[ev_type_arr[i]]
    page_urls[i] = np.random.choice(pages)

# --- 新增字段: duration_ms ---
# 浏览商品页面停留较长(3-120s)，登录/支付较短(2-30s)
durations = np.empty(total_ev, dtype=np.int32)
is_view = ev_type_arr == "view_product"
is_login = ev_type_arr == "login"
is_cart = ev_type_arr == "add_cart"
is_pay = ev_type_arr == "pay"

# view_product: lognormal(mean ~20s)
durations[is_view] = np.exp(np.random.normal(np.log(20000), 0.8, is_view.sum())).astype(np.int32)
# login: ~5s median
durations[is_login] = np.exp(np.random.normal(np.log(5000), 0.6, is_login.sum())).astype(np.int32)
# add_cart: ~8s
durations[is_cart] = np.exp(np.random.normal(np.log(8000), 0.7, is_cart.sum())).astype(np.int32)
# pay: ~12s
durations[is_pay] = np.exp(np.random.normal(np.log(12000), 0.5, is_pay.sum())).astype(np.int32)
durations = np.clip(durations, 100, 300000)  # 100ms ~ 5min

# --- 新增字段: device_info (JSON) ---
# 根据用户设备生成，包含 os_version, app_version, network
device_types = np.array(devices)[user_id_arr - 1]  # user_id → device_type
os_versions = np.where(device_types == "iOS",
                       np.random.choice(["16.0", "16.1", "17.0", "17.2", "18.0"], total_ev),
                       np.random.choice(["12.0", "13.0", "14.0", "14.1"], total_ev))
app_versions = np.random.choice(["3.2.0", "3.2.1", "3.3.0", "3.4.0", "4.0.0"], total_ev,
                                p=[0.10, 0.15, 0.30, 0.25, 0.20])
networks = np.random.choice(["WiFi", "4G", "5G"], total_ev, p=[0.60, 0.25, 0.15])

device_infos = np.empty(total_ev, dtype=object)
for i in range(total_ev):
    device_infos[i] = json.dumps({
        "os": device_types[i],
        "os_version": os_versions[i],
        "app_version": app_versions[i],
        "network": networks[i],
    }, ensure_ascii=False)

# 组装事件 DF
df_events = pd.DataFrame({
    "user_id": user_id_arr,
    "event_type": ev_type_arr,
    "event_time": pd.to_datetime(ev_times).strftime("%Y-%m-%d %H:%M:%S"),
    "session_id": session_ids,
    "page_url": page_urls,
    "duration_ms": durations,
    "device_info": device_infos,
}).sort_values("event_time").reset_index(drop=True)

print(f"  生成 {len(df_events):,} 条事件 (7 字段) | 耗时 {time.time() - t1:.1f}s")
print(f"  唯一 session 数: {df_events['session_id'].nunique():,}")

# ============================================================
# 第三步: 订单
# ============================================================
print(f"\n[3/3] 生成订单表 ({N_ORDERS:,} 条)...")
t2 = time.time()

ord_counts = np.maximum(0, (activity_score * N_ORDERS).astype(np.int32))
# 70% 用户有订单
zmask = ord_counts == 0
n_zero = zmask.sum()
target = max(0, int(N_USERS * 0.7) - (ord_counts > 0).sum())
if target > 0:
    chosen = np.random.choice(np.where(zmask)[0], min(target, n_zero), replace=False)
    ord_counts[chosen] = 1

diff_o = N_ORDERS - ord_counts.sum()
if diff_o > 0:
    idx = np.random.choice(np.where(ord_counts > 0)[0], diff_o, replace=True)
    np.add.at(ord_counts, idx, 1)
elif diff_o < 0:
    idx = np.random.choice(np.where(ord_counts > 1)[0], abs(diff_o), replace=True)
    np.add.at(ord_counts, idx, -1)

total_ord = ord_counts.sum()
ord_uid = np.repeat(user_ids, ord_counts)

# 订单金额: 对数正态
log_amt = np.random.normal(4.2, 1.0, total_ord)
amounts = np.round(np.clip(np.exp(log_amt), 0.5, 5000), 2)

# 订单时间
ord_props = np.random.beta(2, 1, total_ord)
cum_ord = np.concatenate([[0], np.cumsum(ord_counts)])
ord_ts = np.empty(total_ord, dtype=np.int64)
for i in range(N_USERS):
    lo, hi = cum_ord[i], cum_ord[i + 1]
    if hi > lo:
        ord_ts[lo:hi] = reg_ts_i64[i] + (ord_props[lo:hi] * intervals[i]).astype(np.int64)
ord_times = ord_ts.astype("datetime64[s]")

# --- 新增字段: product_category ---
categories = np.random.choice(PRODUCT_CATEGORIES, total_ord,
                              p=[0.20,0.18,0.15,0.12,0.10,0.08,0.07,0.05,0.03,0.02])

# --- 新增字段: order_status ---
statuses = np.random.choice(ORDER_STATUSES, total_ord, p=STATUS_WEIGHTS)

# --- 新增字段: is_first_order ---
# 按用户分组，每用户第一单标记为 True
user_ord_positions = np.concatenate([[0], np.cumsum(ord_counts)])
is_first = np.zeros(total_ord, dtype=bool)
for i in range(N_USERS):
    lo, hi = user_ord_positions[i], user_ord_positions[i + 1]
    if hi > lo:
        is_first[lo] = True

# 组装订单 DF
df_orders = pd.DataFrame({
    "order_id": np.arange(1, total_ord + 1, dtype=np.int32),
    "user_id": ord_uid,
    "amount": amounts,
    "product_category": categories,
    "order_status": statuses,
    "is_first_order": is_first,
    "pay_time": pd.to_datetime(ord_times).strftime("%Y-%m-%d %H:%M:%S"),
})

print(f"  生成 {len(df_orders):,} 条订单 (7 字段) | 耗时 {time.time() - t2:.1f}s")
print(f"  品类 Top5: {df_orders['product_category'].value_counts().head(5).to_dict()}")
status_dist = df_orders['order_status'].value_counts()
for s, n in status_dist.items():
    print(f"  状态-{s}: {n:,} ({n/total_ord*100:.1f}%)")
print(f"  首单数: {is_first.sum():,}")

# ============================================================
# 第四步: 输出 CSV
# ============================================================
print(f"\n[输出] 写入 CSV...")
t3 = time.time()

def save_csv(df, name):
    p = os.path.join(OUTPUT_DIR, name)
    df.to_csv(p, index=False)
    return p, len(df), os.path.getsize(p) / 1024 / 1024

p1, n1, s1 = save_csv(df_users, "users.csv")
p2, n2, s2 = save_csv(df_events, "user_events.csv")
p3, n3, s3 = save_csv(df_orders, "orders.csv")

print(f"  users.csv          → {n1:>8,} 行 x {len(df_users.columns)} 字段 | {s1:.1f} MB")
print(f"  user_events.csv    → {n2:>8,} 行 x {len(df_events.columns)} 字段 | {s2:.1f} MB")
print(f"  orders.csv         → {n3:>8,} 行 x {len(df_orders.columns)} 字段 | {s3:.1f} MB")
print(f"  写入耗时 {time.time() - t3:.1f}s")

# ============================================================
# 验证
# ============================================================
print(f"\n{'=' * 60}")
print("快速验证")
print("=" * 60)
print(f"  用户: {n1:,} | 字段: {list(df_users.columns)}")
print(f"  事件: {n2:,} | 字段: {list(df_events.columns)}")
print(f"  订单: {n3:,} | 字段: {list(df_orders.columns)}")
print(f"  总字段: {len(df_users.columns) + len(df_events.columns) + len(df_orders.columns)}")

# 关联检查
ou = set(df_orders['user_id'].unique())
eu = set(df_events['user_id'].unique())
uu = set(df_users['user_id'].unique())
print(f"  孤立ID: 行为={len(eu - uu)} 订单={len(ou - uu)}")

print(f"\n  ✅ 全部完成！总耗时 {time.time() - t0:.1f}s")
print("=" * 60)
