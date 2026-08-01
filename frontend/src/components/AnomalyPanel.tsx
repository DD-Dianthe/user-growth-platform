/** 异常检测告警面板 */
import React, { useEffect, useState } from 'react';
import { Card, Table, Tag, Button, message, Space, Spin } from 'antd';
import { AlertOutlined, ReloadOutlined } from '@ant-design/icons';
import axios from 'axios';

const API_BASE = 'http://127.0.0.1:8000/api';

interface AlertItem {
  alert_date: string;
  method: string;
  metric_name: string;
  metric_value: number;
  expected_value: number | null;
  z_score: number | null;
  anomaly_score: number | null;
  severity: string;
  details: Record<string, any>;
}

const AnomalyPanel: React.FC = () => {
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [detecting, setDetecting] = useState(false);

  const fetchAlerts = () => {
    setLoading(true);
    axios.get(`${API_BASE}/anomaly/alerts?limit=50`)
      .then((res) => setAlerts(res.data.items))
      .catch(() => message.error('获取告警数据失败'))
      .finally(() => setLoading(false));
  };

  const runDetection = () => {
    setDetecting(true);
    axios.post(`${API_BASE}/anomaly/detect`)
      .then((res) => {
        message.success(`检测完成: ${res.data.total_alerts} 条告警 (Critical ${res.data.critical}, Warning ${res.data.warning})`);
        fetchAlerts();
      })
      .catch(() => message.error('检测运行失败'))
      .finally(() => setDetecting(false));
  };

  useEffect(() => { fetchAlerts(); }, []);

  const columns = [
    {
      title: '日期',
      dataIndex: 'alert_date',
      key: 'date',
      width: 110,
      render: (v: string) => <span style={{ fontWeight: 500 }}>{v}</span>,
    },
    {
      title: '方法',
      dataIndex: 'method',
      key: 'method',
      width: 130,
      render: (v: string) => (
        <Tag color={v === 'zscore' ? 'blue' : 'purple'}>
          {v === 'zscore' ? 'Z-Score' : 'Isolation Forest'}
        </Tag>
      ),
    },
    {
      title: '指标值',
      dataIndex: 'metric_value',
      key: 'value',
      width: 120,
      render: (v: number) => v.toLocaleString(),
    },
    {
      title: '期望值',
      dataIndex: 'expected_value',
      key: 'expected',
      width: 100,
      render: (v: number | null) => v ? v.toLocaleString() : '-',
    },
    {
      title: '异常得分',
      key: 'score',
      width: 100,
      render: (_: any, r: AlertItem) => {
        if (r.z_score !== null) {
          const color = Math.abs(r.z_score) > 3.5 ? '#ff4d4f' : '#faad14';
          return <span style={{ color, fontWeight: 600 }}>z={r.z_score.toFixed(2)}</span>;
        }
        if (r.anomaly_score !== null) {
          const color = r.anomaly_score > 0.75 ? '#ff4d4f' : '#faad14';
          return <span style={{ color, fontWeight: 600 }}>{(r.anomaly_score * 100).toFixed(0)}%</span>;
        }
        return '-';
      },
    },
    {
      title: '严重程度',
      dataIndex: 'severity',
      key: 'severity',
      width: 100,
      render: (v: string) => (
        <Tag color={v === 'critical' ? 'red' : 'orange'}>
          {v === 'critical' ? '🔴 严重' : '⚠️ 警告'}
        </Tag>
      ),
    },
    {
      title: '方向',
      key: 'direction',
      width: 75,
      render: (_: any, r: AlertItem) => {
        if (r.method !== 'zscore' || !r.z_score) return '-';
        return r.z_score > 0
          ? <Tag color="red">↑ 激增</Tag>
          : <Tag color="green">↓ 骤降</Tag>;
      },
    },
  ];

  return (
    <Card
      title={
        <Space>
          <AlertOutlined style={{ color: '#ff4d4f' }} />
          异常检测
          <Tag color="red">17 Critical</Tag>
          <Tag color="orange">65 Warning</Tag>
        </Space>
      }
      extra={
        <Space>
          <Button
            size="small"
            icon={<ReloadOutlined />}
            onClick={fetchAlerts}
            loading={loading}
          >
            刷新
          </Button>
          <Button
            type="primary"
            size="small"
            danger
            icon={<AlertOutlined />}
            onClick={runDetection}
            loading={detecting}
          >
            重新检测
          </Button>
        </Space>
      }
      className="chart-card"
    >
      <Spin spinning={loading}>
        <Table
          dataSource={alerts}
          columns={columns}
          rowKey={(r: AlertItem, i?: number) => `${r.alert_date}_${r.method}_${i ?? 0}`}
          size="small"
          pagination={{ pageSize: 10, showSizeChanger: false }}
          scroll={{ x: 800 }}
        />
      </Spin>
    </Card>
  );
};

export default AnomalyPanel;
