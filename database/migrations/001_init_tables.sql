-- ============================================================
-- 互联网用户增长智能分析平台 — 初始化建表脚本
-- 数据库: MySQL 8.0+
-- 引擎: InnoDB | 字符集: utf8mb4 | 排序: utf8mb4_unicode_ci
-- ============================================================

CREATE DATABASE IF NOT EXISTS user_growth
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE user_growth;

-- ============================================================
-- 1. 用户主数据表 (DIM 维度表)
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
  user_id           INT           NOT NULL                    COMMENT '用户唯一ID',
  age               TINYINT       NOT NULL                    COMMENT '年龄',
  gender            VARCHAR(4)    NOT NULL                    COMMENT '性别(男/女)',
  city              VARCHAR(30)   NOT NULL                    COMMENT '所在城市',
  device_type       VARCHAR(10)   NOT NULL                    COMMENT '设备类型(iOS/Android)',
  registration_time DATETIME      NOT NULL                    COMMENT '注册时间',
  channel           VARCHAR(30)   NOT NULL                    COMMENT '注册渠道',
  created_at        DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
  updated_at        DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',

  PRIMARY KEY (user_id),
  INDEX idx_users_age (age),
  INDEX idx_users_gender (gender),
  INDEX idx_users_city (city),
  INDEX idx_users_device (device_type),
  INDEX idx_users_channel (channel),
  INDEX idx_users_reg_time (registration_time),
  INDEX idx_users_channel_reg (channel, registration_time)    -- 渠道按时间趋势分析
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='用户主数据维度表';


-- ============================================================
-- 2. 用户行为事件表 (FACT 事实表)
-- ============================================================
CREATE TABLE IF NOT EXISTS user_events (
  id           BIGINT        NOT NULL AUTO_INCREMENT          COMMENT '自增主键',
  user_id      INT           NOT NULL                         COMMENT '用户ID',
  event_type   VARCHAR(20)   NOT NULL                         COMMENT '事件类型: login/view_product/add_cart/pay',
  event_time   DATETIME      NOT NULL                         COMMENT '事件发生时间',
  event_date   DATE          NOT NULL                         COMMENT '事件日期(冗余,加速按日聚合)',
  session_id   VARCHAR(50)   NOT NULL DEFAULT ''              COMMENT '会话ID',
  page_url     VARCHAR(200)  NOT NULL DEFAULT ''              COMMENT '页面路径',
  duration_ms  INT           NOT NULL DEFAULT 0               COMMENT '页面停留时长(毫秒)',
  device_info  JSON          NULL                             COMMENT '设备信息(JSON)',

  PRIMARY KEY (id),
  INDEX idx_events_user_id (user_id),
  INDEX idx_events_event_type (event_type),
  INDEX idx_events_event_time (event_time),
  INDEX idx_events_event_date (event_date),
  INDEX idx_events_session (session_id),
  INDEX idx_events_page_url (page_url(100)),

  -- 复合索引：覆盖高频分析查询
  INDEX idx_events_user_time (user_id, event_time),           -- 用户行为时间线
  INDEX idx_events_type_time (event_type, event_date),        -- 事件类型日趋势
  INDEX idx_events_user_type (user_id, event_type),           -- 用户行为种类统计
  INDEX idx_events_type_page (event_type, page_url(50)),      -- 页面事件分析
  INDEX idx_events_session_time (session_id, event_time),     -- 会话内事件排序

  -- 外键关联
  CONSTRAINT fk_events_user FOREIGN KEY (user_id) REFERENCES users(user_id)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='用户行为事件事实表';


-- ============================================================
-- 3. 订单交易表 (FACT 事实表)
-- ============================================================
CREATE TABLE IF NOT EXISTS orders (
  order_id          INT           NOT NULL                    COMMENT '订单唯一ID',
  user_id           INT           NOT NULL                    COMMENT '用户ID',
  amount            DECIMAL(10,2) NOT NULL                    COMMENT '订单金额',
  product_category  VARCHAR(30)   NOT NULL                    COMMENT '商品品类',
  order_status      VARCHAR(10)   NOT NULL                    COMMENT '订单状态: 已支付/已取消/退款中/已退款',
  is_first_order    TINYINT(1)    NOT NULL DEFAULT 0          COMMENT '是否首单(0否/1是)',
  pay_time          DATETIME      NOT NULL                    COMMENT '支付时间',
  pay_date          DATE          NOT NULL                    COMMENT '支付日期(冗余,加速按日聚合)',
  created_at        DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',

  PRIMARY KEY (order_id),
  INDEX idx_orders_user_id (user_id),
  INDEX idx_orders_pay_time (pay_time),
  INDEX idx_orders_pay_date (pay_date),
  INDEX idx_orders_status (order_status),
  INDEX idx_orders_category (product_category),
  INDEX idx_orders_first (is_first_order),
  INDEX idx_orders_amount (amount),

  -- 复合索引：覆盖高频分析查询
  INDEX idx_orders_user_time (user_id, pay_time),             -- 用户订单时间线
  INDEX idx_orders_status_date (order_status, pay_date),      -- 订单状态日趋势
  INDEX idx_orders_category_date (product_category, pay_date),-- 品类日销售趋势
  INDEX idx_orders_user_status (user_id, order_status),       -- 用户订单状态分布

  -- 外键关联
  CONSTRAINT fk_orders_user FOREIGN KEY (user_id) REFERENCES users(user_id)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='订单交易事实表';


-- ============================================================
-- 4. 分析加速：物化视图替代 — 每日指标汇总表
--    互联网分析平台标配，避免每次看板请求都扫全表
-- ============================================================
CREATE TABLE IF NOT EXISTS daily_metrics (
  id             BIGINT        NOT NULL AUTO_INCREMENT        COMMENT '自增主键',
  stat_date      DATE          NOT NULL                       COMMENT '统计日期',
  dau            INT           NOT NULL DEFAULT 0             COMMENT '日活跃用户数',
  new_users      INT           NOT NULL DEFAULT 0             COMMENT '新增用户数',
  login_count    INT           NOT NULL DEFAULT 0             COMMENT '登录次数',
  view_count     INT           NOT NULL DEFAULT 0             COMMENT '浏览商品次数',
  cart_count     INT           NOT NULL DEFAULT 0             COMMENT '加购次数',
  pay_event_count INT          NOT NULL DEFAULT 0             COMMENT '支付事件次数',
  gmv            DECIMAL(14,2) NOT NULL DEFAULT 0.00          COMMENT '交易总额(GMV)',
  pay_users      INT           NOT NULL DEFAULT 0             COMMENT '支付用户数',
  order_count    INT           NOT NULL DEFAULT 0             COMMENT '订单总数',
  first_order_count INT        NOT NULL DEFAULT 0             COMMENT '首单数',
  avg_order_amount DECIMAL(10,2) NOT NULL DEFAULT 0.00        COMMENT '客单价',
  created_at     DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '计算时间',

  PRIMARY KEY (id),
  UNIQUE KEY uk_stat_date (stat_date),
  INDEX idx_metrics_date (stat_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='每日运营指标汇总表(预聚合加速层)';

-- ============================================================
-- 表: user_segments (KMeans 用户分群结果)
-- ============================================================
CREATE TABLE IF NOT EXISTS user_segments (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    user_id             INT NOT NULL,
    login_count         INT NOT NULL DEFAULT 0               COMMENT '登录次数',
    view_count          INT NOT NULL DEFAULT 0               COMMENT '浏览次数',
    purchase_count      INT NOT NULL DEFAULT 0               COMMENT '购买次数',
    total_amount        DECIMAL(12,2) NOT NULL DEFAULT 0.00  COMMENT '消费总额',
    days_since_last_active INT NOT NULL DEFAULT 0            COMMENT '距最后活跃天数',
    cluster_id          TINYINT NOT NULL                     COMMENT 'KMeans 聚类编号(0-3)',
    segment             VARCHAR(32) NOT NULL                 COMMENT '用户类别: 高价值用户/潜力用户/普通用户/流失用户',
    feature_json        TEXT                                 COMMENT '标准化特征 JSON',
    created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '计算时间',
    INDEX idx_us_user_id (user_id),
    INDEX idx_us_segment (segment),
    INDEX idx_us_cluster_id (cluster_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='KMeans 用户分群结果表';
