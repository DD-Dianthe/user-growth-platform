/** 用户转化漏斗图 */
import React, { useEffect, useState } from 'react';
import ReactECharts from 'echarts-for-react';
import { Card, Spin } from 'antd';
import { fetchFunnel, type FunnelStep } from '../api/dashboard';

const FunnelChart: React.FC = () => {
  const [steps, setSteps] = useState<FunnelStep[]>([]);
  const [overallRate, setOverallRate] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchFunnel()
      .then((res) => {
        setSteps(res.steps);
        setOverallRate(res.overall_rate);
      })
      .finally(() => setLoading(false));
  }, []);

  const option = {
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(255,255,255,0.95)',
      borderColor: '#e8e8e8',
      textStyle: { color: '#333' },
      formatter: (params: any) => {
        const rate = steps[params.dataIndex]?.rate;
        const rateStr = rate !== null && rate !== undefined
          ? `<br/>转化率: ${(rate * 100).toFixed(1)}%`
          : '';
        return `${params.name}<br/>人数: ${params.value?.toLocaleString()}${rateStr}`;
      },
    },
    series: [{
      type: 'funnel',
      left: '15%',
      right: '15%',
      top: 20,
      bottom: 20,
      width: '70%',
      minSize: '25%',
      gap: 2,
      label: {
        show: true,
        position: 'inside',
        fontSize: 14,
        fontWeight: 'bold',
        formatter: '{b}',
      },
      labelLine: { show: false },
      itemStyle: { borderColor: '#fff', borderWidth: 2 },
      data: steps.map((s, i) => {
        const colors = ['#1677ff', '#52c41a', '#fa8c16'];
        const rateText = s.rate !== null ? ` (${(s.rate * 100).toFixed(1)}%)` : '';
        return {
          name: s.step,
          value: s.count,
          itemStyle: { color: colors[i] || '#722ed1' },
          tooltip: { formatter: `${s.step}: ${s.count.toLocaleString()}${rateText}` },
        };
      }),
    }],
  };

  return (
    <Card
      title="转化漏斗"
      className="chart-card"
      extra={
        <span style={{ fontSize: 13, color: '#999' }}>
          整体转化率: <strong style={{ color: '#1677ff' }}>{(overallRate * 100).toFixed(1)}%</strong>
        </span>
      }
    >
      <Spin spinning={loading}>
        <ReactECharts option={option} style={{ height: 320 }} />
      </Spin>
    </Card>
  );
};

export default FunnelChart;
