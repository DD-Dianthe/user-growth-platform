/** 首页 Dashboard 数据看板 */
import React, { useEffect, useState } from 'react';
import { Row, Col } from 'antd';
import {
  TeamOutlined, UserAddOutlined,
  DollarOutlined, PercentageOutlined,
} from '@ant-design/icons';
import KpiCard from '../components/KpiCard';
import DauTrendChart from '../components/DauTrendChart';
import GmvTrendChart from '../components/GmvTrendChart';
import FunnelChart from '../components/FunnelChart';
import SourceChart from '../components/SourceChart';
import { fetchDashboard, type DashboardOverview } from '../api/dashboard';
import './Dashboard.css';

const Dashboard: React.FC = () => {
  const [overview, setOverview] = useState<DashboardOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    fetchDashboard()
      .then((res) => setOverview(res.overview))
      .finally(() => setLoading(false));
  }, [refreshKey]);

  // 自动刷新 - 每 60 秒
  useEffect(() => {
    const t = setInterval(() => setRefreshKey((k) => k + 1), 60000);
    return () => clearInterval(t);
  }, []);

  const formatCNY = (v: number) => `¥${v.toLocaleString('zh-CN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;

  const formatPct = (v: number) => `${(v * 100).toFixed(2)}%`;

  return (
    <div className="dashboard-page">
      {/* ── KPI 指标卡 ── */}
      <Row gutter={[16, 16]} className="kpi-row">
        <Col xs={24} sm={12} lg={6}>
          <KpiCard
            title="日活跃用户 (DAU)"
            value={overview?.dau ?? 0}
            icon={<TeamOutlined />}
            iconColor="linear-gradient(135deg, #1677ff, #69b1ff)"
            trend="up"
            trendLabel="较昨日 +5.8%"
            loading={loading}
            formatter={(v) => v.toLocaleString()}
          />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <KpiCard
            title="新增用户"
            value={overview?.new_users ?? 0}
            icon={<UserAddOutlined />}
            iconColor="linear-gradient(135deg, #52c41a, #95de64)"
            trend="up"
            trendLabel="较昨日 +3.2%"
            loading={loading}
            formatter={(v) => v.toLocaleString()}
          />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <KpiCard
            title="GMV"
            value={overview?.gmv ?? 0}
            icon={<DollarOutlined />}
            iconColor="linear-gradient(135deg, #fa8c16, #ffc069)"
            trend="up"
            trendLabel="较昨日 +12.5%"
            loading={loading}
            formatter={formatCNY}
          />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <KpiCard
            title="支付转化率"
            value={overview?.conversion_rate ?? 0}
            icon={<PercentageOutlined />}
            iconColor="linear-gradient(135deg, #722ed1, #b37feb)"
            trend="up"
            trendLabel="较昨日 +1.8pp"
            loading={loading}
            formatter={formatPct}
          />
        </Col>
      </Row>

      {/* ── 趋势图 ── */}
      <Row gutter={[16, 16]} className="chart-row">
        <Col xs={24} lg={12}>
          <DauTrendChart />
        </Col>
        <Col xs={24} lg={12}>
          <GmvTrendChart />
        </Col>
      </Row>

      {/* ── 漏斗 & 来源 ── */}
      <Row gutter={[16, 16]} className="chart-row">
        <Col xs={24} lg={12}>
          <FunnelChart />
        </Col>
        <Col xs={24} lg={12}>
          <SourceChart />
        </Col>
      </Row>
    </div>
  );
};

export default Dashboard;
