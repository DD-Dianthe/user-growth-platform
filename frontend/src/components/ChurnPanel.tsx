import { useState, useEffect, useCallback } from 'react';
import {
  Card, Row, Col, Statistic, Table, Tag, Button,
  Progress, message, Spin, Empty, Space, Typography,
} from 'antd';
import {
  WarningOutlined, ReloadOutlined, SafetyOutlined,
  RiseOutlined, FallOutlined,
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';

import {
  fetchChurnOverview, fetchChurnHighRisk,
  runChurnPrediction,
  type ChurnOverviewResponse, type ChurnHighRiskItem, type ChurnRunResponse,
} from '../api/dashboard';

const { Text, Title: T } = Typography;

const SEGMENT_COLORS: Record<string, string> = {
  '高价值用户': '#f5222d',
  '潜力用户': '#fa8c16',
  '普通用户': '#1890ff',
  '流失用户': '#8c8c8c',
};

export default function ChurnPanel() {
  const [loading, setLoading] = useState(true);
  const [predicting, setPredicting] = useState(false);
  const [overview, setOverview] = useState<ChurnOverviewResponse | null>(null);
  const [highRiskUsers, setHighRiskUsers] = useState<ChurnHighRiskItem[]>([]);
  const [highRiskTotal, setHighRiskTotal] = useState(0);
  const [modelMetrics, setModelMetrics] = useState<ChurnRunResponse['model_metrics'] | null>(null);
  const [page, setPage] = useState(1);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [ov, hr] = await Promise.all([
        fetchChurnOverview(),
        fetchChurnHighRisk(50, 0, 'probability'),
      ]);
      setOverview(ov);
      setHighRiskUsers(hr.items);
      setHighRiskTotal(hr.total);
    } catch {
      message.error('加载流失预测数据失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const handleRunPrediction = async () => {
    setPredicting(true);
    try {
      const result = await runChurnPrediction();
      setModelMetrics(result.model_metrics);
      message.success(result.message);
      await loadData();
    } catch {
      message.error('流失预测运行失败');
    } finally {
      setPredicting(false);
    }
  };

  const handlePageChange = async (p: number) => {
    setPage(p);
    try {
      const hr = await fetchChurnHighRisk(50, (p - 1) * 50, 'probability');
      setHighRiskUsers(hr.items);
    } catch {
      // ignore
    }
  };

  if (loading) {
    return (
      <Card title="⚠️ 用户流失预测">
        <Spin description="加载流失数据...">
          <div style={{ height: 200 }} />
        </Spin>
      </Card>
    );
  }

  if (!overview) {
    return (
      <Card title="⚠️ 用户流失预测">
        <Empty description="暂无流失预测数据，请先运行预测模型">
          <Button type="primary" icon={<ReloadOutlined />} loading={predicting} onClick={handleRunPrediction}>
            运行流失预测
          </Button>
        </Empty>
      </Card>
    );
  }

  const { overview: ov, distribution: dist, profile } = overview;
  const churnRate = ov.total_users > 0 ? (ov.high_risk / ov.total_users * 100) : 0;

  // ── 风险分布柱状图 ──
  const distOption = {
    tooltip: { trigger: 'axis' as const },
    grid: { left: 50, right: 20, top: 10, bottom: 40 },
    xAxis: {
      type: 'category' as const,
      data: dist.map((d: { probability_bucket: string }) => d.probability_bucket),
      axisLabel: { fontSize: 11, rotate: 30 },
    },
    yAxis: { type: 'value' as const, name: '用户数', axisLabel: { formatter: (v: number) => v >= 1000 ? `${(v / 1000).toFixed(0)}k` : v } },
    series: [{
      type: 'bar',
      data: dist.map((d: { user_count: number; avg_prob: number }, i: number) => ({
        value: d.user_count,
        itemStyle: {
          color: i === 0 ? '#ff7a45' : '#95de64',
          borderRadius: [4, 4, 0, 0],
        },
      })),
      barWidth: '50%',
    }],
  };

  // ── 用户画像对比 ──
  const profileOption = {
    tooltip: { trigger: 'axis' as const },
    legend: { data: ['高风险用户', '正常用户'], bottom: 0 },
    grid: { left: 80, right: 30, top: 10, bottom: 40 },
    xAxis: { type: 'category' as const, data: ['登录次数', '浏览次数', '购买次数', '消费金额', '不活跃天数'] },
    yAxis: { type: 'value' as const },
    series: [
      {
        name: '高风险用户',
        type: 'bar',
        data: profile.filter((p: { is_high_risk: number }) => p.is_high_risk === 1).map((p: { avg_login: number; avg_view: number; avg_purchase: number; avg_amount: number; avg_days_inactive: number }) => [
          p.avg_login, p.avg_view, p.avg_purchase, p.avg_amount, p.avg_days_inactive,
        ])[0] || [],
        itemStyle: { color: '#f5222d', borderRadius: [4, 4, 0, 0] },
      },
      {
        name: '正常用户',
        type: 'bar',
        data: profile.filter((p: { is_high_risk: number }) => p.is_high_risk === 0).map((p: { avg_login: number; avg_view: number; avg_purchase: number; avg_amount: number; avg_days_inactive: number }) => [
          p.avg_login, p.avg_view, p.avg_purchase, p.avg_amount, p.avg_days_inactive,
        ])[0] || [],
        itemStyle: { color: '#52c41a', borderRadius: [4, 4, 0, 0] },
      },
    ],
  };

  // ── 模型评估指标 ──
  const hasModelMetrics = modelMetrics && modelMetrics.auc > 0;

  const columns = [
    { title: '用户ID', dataIndex: 'user_id', key: 'user_id', width: 90 },
    {
      title: '流失概率',
      dataIndex: 'churn_probability',
      key: 'churn_probability',
      width: 120,
      render: (v: number) => (
        <span style={{ color: v > 0.9 ? '#f5222d' : v > 0.8 ? '#fa8c16' : '#1890ff', fontWeight: 600 }}>
          {(v * 100).toFixed(1)}%
        </span>
      ),
      sorter: (a: ChurnHighRiskItem, b: ChurnHighRiskItem) => a.churn_probability - b.churn_probability,
    },
    { title: '不活跃(天)', dataIndex: 'days_inactive', key: 'days_inactive', width: 110 },
    { title: '登录', dataIndex: 'login_count', key: 'login_count', width: 70 },
    { title: '浏览', dataIndex: 'view_count', key: 'view_count', width: 70 },
    { title: '购买', dataIndex: 'purchase_count', key: 'purchase_count', width: 70 },
    {
      title: '消费金额',
      dataIndex: 'total_amount',
      key: 'total_amount',
      width: 110,
      render: (v: number) => `¥${v.toFixed(0)}`,
    },
    {
      title: '分群',
      dataIndex: 'segment',
      key: 'segment',
      width: 100,
      render: (v: string) => <Tag color={SEGMENT_COLORS[v] || '#d9d9d9'}>{v}</Tag>,
    },
  ];

  return (
    <Card
      title={
        <Space>
          <WarningOutlined style={{ color: '#f5222d' }} />
          <span>⚠️ 用户流失预测</span>
        </Space>
      }
      extra={
        <Button
          type="primary"
          danger
          icon={<ReloadOutlined />}
          loading={predicting}
          onClick={handleRunPrediction}
          size="small"
        >
          重新预测
        </Button>
      }
    >
      {/* ── KPI 卡片行 ── */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} md={6}>
          <Card size="small" style={{ background: '#fff7e6', border: '1px solid #ffd591' }}>
            <Statistic
              title="高风险用户"
              value={ov.high_risk}
              suffix={<Text type="secondary" style={{ fontSize: 14 }}>人</Text>}
              styles={{ content: { color: '#f5222d', fontSize: 28 } }}
              prefix={<FallOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card size="small" style={{ background: '#f6ffed', border: '1px solid #b7eb8f' }}>
            <Statistic
              title="安全用户"
              value={ov.total_users - ov.high_risk}
              suffix={<Text type="secondary" style={{ fontSize: 14 }}>人</Text>}
              styles={{ content: { color: '#52c41a', fontSize: 28 } }}
              prefix={<SafetyOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card size="small">
            <Statistic
              title="平均流失概率"
              value={(ov.avg_probability * 100).toFixed(1)}
              suffix="%"
              styles={{ content: { color: '#fa8c16', fontSize: 28 } }}
              prefix={<RiseOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card size="small">
            <div style={{ textAlign: 'center' }}>
              <div style={{ color: '#666', marginBottom: 8, fontSize: 13 }}>流失率</div>
              <Progress
                type="circle"
                percent={parseFloat(churnRate.toFixed(1))}
                size={72}
                strokeColor={{ '0%': '#52c41a', '100%': '#f5222d' }}
                format={(p) => `${p}%`}
              />
            </div>
          </Card>
        </Col>
      </Row>

      {/* ── 图表行 ── */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} lg={12}>
          <Card size="small" title="风险概率分布">
            <ReactECharts
              option={distOption}
              style={{ height: 240 }}
              notMerge
            />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card size="small" title="用户画像对比 (高风险 vs 正常)">
            <ReactECharts
              option={profileOption}
              style={{ height: 240 }}
              notMerge
            />
          </Card>
        </Col>
      </Row>

      {/* ── 模型评估指标 ── */}
      {hasModelMetrics && (
        <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
          <Col xs={24}>
            <Card size="small" title="模型评估 (XGBoost)">
              <Row gutter={[16, 16]}>
                <Col xs={12} sm={6}>
                  <Statistic title="Accuracy" value={modelMetrics.accuracy} precision={4} styles={{ content: { color: '#1890ff' } }} />
                </Col>
                <Col xs={12} sm={6}>
                  <Statistic title="Precision" value={modelMetrics.precision} precision={4} styles={{ content: { color: '#52c41a' } }} />
                </Col>
                <Col xs={12} sm={6}>
                  <Statistic title="Recall" value={modelMetrics.recall} precision={4} styles={{ content: { color: '#fa8c16' } }} />
                </Col>
                <Col xs={12} sm={6}>
                  <Statistic title="AUC" value={modelMetrics.auc} precision={4} styles={{ content: { color: '#722ed1' } }} />
                </Col>
              </Row>
              <div style={{ marginTop: 12, fontSize: 12, color: '#999' }}>
                CV AUC: {modelMetrics.cv_auc_mean} ± {modelMetrics.cv_auc_std}
                &nbsp;|&nbsp; TP={modelMetrics.confusion_matrix.tp}
                &nbsp; FP={modelMetrics.confusion_matrix.fp}
                &nbsp; FN={modelMetrics.confusion_matrix.fn}
                &nbsp; TN={modelMetrics.confusion_matrix.tn}
              </div>
              {modelMetrics.top_features && (
                <div style={{ marginTop: 8 }}>
                  <Text type="secondary" style={{ fontSize: 12 }}>Top 特征: </Text>
                  {modelMetrics.top_features.slice(0, 5).map((f: { feature: string; importance: number }) => (
                    <Tag key={f.feature} style={{ fontSize: 11 }}>{f.feature} ({f.importance})</Tag>
                  ))}
                </div>
              )}
            </Card>
          </Col>
        </Row>
      )}

      {/* ── 高风险用户表 ── */}
      <Card
        size="small"
        title={`🔴 高风险用户列表 (共 ${highRiskTotal.toLocaleString()} 人)`}
        style={{ marginTop: hasModelMetrics ? 0 : 0 }}
      >
        <Table
          dataSource={highRiskUsers}
          columns={columns}
          rowKey={(r) => `${r.user_id}`}
          size="small"
          pagination={{
            current: page,
            pageSize: 50,
            total: highRiskTotal,
            onChange: handlePageChange,
            showSizeChanger: false,
            showTotal: (t: number) => `共 ${t.toLocaleString()} 人`,
          }}
          scroll={{ x: 800 }}
        />
      </Card>
    </Card>
  );
}
