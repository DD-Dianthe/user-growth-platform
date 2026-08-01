/** 用户画像分群面板 — KMeans 聚类可视化 */
import React, { useEffect, useState } from 'react';
import ReactECharts from 'echarts-for-react';
import { Card, Spin, Row, Col, Table, Tag, Button, Space, message } from 'antd';
import {
  PieChartOutlined, RadarChartOutlined, ReloadOutlined, ClusterOutlined,
} from '@ant-design/icons';
import {
  fetchSegmentsOverview, runSegmentation,
  type SegmentOverview, type SegmentsResponse,
} from '../api/dashboard';

const SEGMENT_COLORS: Record<string, string> = {
  '高价值用户': '#f5222d',
  '潜力用户': '#fa8c16',
  '普通用户': '#1677ff',
  '流失用户': '#8c8c8c',
};

const SEGMENT_ICONS: Record<string, string> = {
  '高价值用户': '👑',
  '潜力用户': '🚀',
  '普通用户': '👤',
  '流失用户': '💤',
};

const UserSegmentsPanel: React.FC = () => {
  const [data, setData] = useState<SegmentsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);

  const fetchData = () => {
    setLoading(true);
    fetchSegmentsOverview()
      .then(setData)
      .catch(() => message.error('获取分群数据失败'))
      .finally(() => setLoading(false));
  };

  const handleRun = () => {
    setRunning(true);
    runSegmentation()
      .then((res) => {
        message.success(`聚类完成: ${res.total_users} 用户 → ${res.clusters} 分群`);
        fetchData();
      })
      .catch((e) => message.error(`运行失败: ${e.message}`))
      .finally(() => setRunning(false));
  };

  useEffect(() => { fetchData(); }, []);

  if (!data) return <Spin spinning={loading} />;

  // ── 饼图：分群占比 ──
  const pieOption = {
    tooltip: { trigger: 'item', formatter: '{b}: {c}人 ({d}%)' },
    legend: { bottom: 0, textStyle: { fontSize: 12 } },
    series: [{
      type: 'pie',
      radius: ['45%', '70%'],
      center: ['50%', '45%'],
      avoidLabelOverlap: false,
      padAngle: 2,
      itemStyle: { borderRadius: 6 },
      label: { show: false },
      emphasis: { scale: true, scaleSize: 10 },
      data: data.segments.map((s) => ({
        name: s.segment,
        value: s.user_count,
        itemStyle: { color: SEGMENT_COLORS[s.segment] },
      })),
    }],
  };

  // ── 雷达图：分群特征对比 ──
  const radarOption = {
    tooltip: {},
    legend: { bottom: 0, textStyle: { fontSize: 11 } },
    radar: {
      indicator: [
        { name: '登录次数', max: 100 },
        { name: '浏览行为', max: 100 },
        { name: '购买次数', max: 100 },
        { name: '消费金额', max: 100 },
        { name: '活跃度(反)', max: 100 },
      ],
      center: ['50%', '47%'],
      radius: '65%',
    },
    series: [{
      type: 'radar',
      data: data.segments.map((s) => {
        const maxValues = {
          login_count: Math.max(...data.segments.map((x) => x.avg_login), 1),
          view_count: Math.max(...data.segments.map((x) => x.avg_view), 1),
          purchase_count: Math.max(...data.segments.map((x) => x.avg_purchase), 1),
          avg_amount: Math.max(...data.segments.map((x) => x.avg_amount), 1),
          days_inactive: Math.max(...data.segments.map((x) => x.avg_days_inactive), 1),
        };
        return {
          name: s.segment,
          value: [
            +(s.avg_login / maxValues.login_count * 100).toFixed(1),
            +(s.avg_view / maxValues.view_count * 100).toFixed(1),
            +(s.avg_purchase / maxValues.purchase_count * 100).toFixed(1),
            +(s.avg_amount / maxValues.avg_amount * 100).toFixed(1),
            +(Math.max(0, 100 - s.avg_days_inactive / maxValues.days_inactive * 100)).toFixed(1),
          ],
          itemStyle: { color: SEGMENT_COLORS[s.segment] },
          lineStyle: { color: SEGMENT_COLORS[s.segment] },
          areaStyle: {
            color: SEGMENT_COLORS[s.segment],
            opacity: 0.1,
          },
        };
      }),
    }],
  };

  // ── 表格列 ──
  const columns = [
    {
      title: '用户类别', dataIndex: 'segment', key: 'segment', width: 120,
      render: (v: string) => (
        <Space>
          <span>{SEGMENT_ICONS[v]}</span>
          <Tag color={v === '高价值用户' ? 'red' : v === '潜力用户' ? 'orange' : v === '普通用户' ? 'blue' : 'default'}>
            {v}
          </Tag>
        </Space>
      ),
    },
    { title: '人数', dataIndex: 'user_count', key: 'count', width: 80, render: (v: number) => v.toLocaleString() },
    { title: '人均登录', dataIndex: 'avg_login', key: 'login', width: 80 },
    { title: '人均浏览', dataIndex: 'avg_view', key: 'view', width: 80 },
    { title: '人均购买', dataIndex: 'avg_purchase', key: 'purchase', width: 80 },
    {
      title: '人均消费', dataIndex: 'avg_amount', key: 'amount', width: 100,
      render: (v: number) => `¥${v.toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`,
    },
    {
      title: '不活跃(天)', dataIndex: 'avg_days_inactive', key: 'inactive', width: 90,
    },
    {
      title: '贡献GMV', dataIndex: 'total_amount', key: 'gmv', width: 120,
      render: (v: number) => `¥${v.toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`,
    },
  ];

  return (
    <Card
      title={
        <Space>
          <ClusterOutlined style={{ color: '#722ed1' }} />
          用户画像分群
          <Tag color="purple">KMeans</Tag>
          <span style={{ fontSize: 12, color: '#999', fontWeight: 400 }}>
            {data.total_users.toLocaleString()} 位用户
          </span>
        </Space>
      }
      extra={
        <Space>
          <Button size="small" icon={<ReloadOutlined />} onClick={fetchData} loading={loading}>刷新</Button>
          <Button type="primary" size="small" icon={<PieChartOutlined />} onClick={handleRun} loading={running}>
            重新聚类
          </Button>
        </Space>
      }
      className="chart-card"
    >
      <Spin spinning={loading}>
        {/* ── 上方：饼图 + 雷达图 ── */}
        <Row gutter={[16, 16]}>
          <Col xs={24} lg={10}>
            <div style={{ textAlign: 'center', fontWeight: 600, fontSize: 14, marginBottom: 4, color: '#555' }}>
              分群占比分布
            </div>
            <ReactECharts option={pieOption} style={{ height: 300 }} />
          </Col>
          <Col xs={24} lg={14}>
            <div style={{ textAlign: 'center', fontWeight: 600, fontSize: 14, marginBottom: 4, color: '#555' }}>
              分群特征雷达图
            </div>
            <ReactECharts option={radarOption} style={{ height: 300 }} />
          </Col>
        </Row>

        {/* ── 下方：数据表 ── */}
        <Table
          dataSource={data.segments}
          columns={columns}
          rowKey="segment"
          size="small"
          pagination={false}
          style={{ marginTop: 16 }}
        />
      </Spin>
    </Card>
  );
};

export default UserSegmentsPanel;
