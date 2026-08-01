/** 用户来源分布玫瑰图 */
import React, { useEffect, useState } from 'react';
import ReactECharts from 'echarts-for-react';
import { Card, Spin } from 'antd';
import { fetchSource, type SourceItem, CHANNEL_NAMES } from '../api/dashboard';

const SourceChart: React.FC = () => {
  const [data, setData] = useState<SourceItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSource()
      .then((res) => setData(res.items))
      .finally(() => setLoading(false));
  }, []);

  const total = data.reduce((s, d) => s + d.count, 0);

  const option = {
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(255,255,255,0.95)',
      borderColor: '#e8e8e8',
      textStyle: { color: '#333' },
      formatter: (params: any) => {
        const pct = ((params.value / total) * 100).toFixed(1);
        return `${params.name}<br/>人数: ${params.value?.toLocaleString()}<br/>占比: ${pct}%`;
      },
    },
    legend: {
      bottom: 0,
      textStyle: { color: '#666' },
    },
    series: [{
      type: 'pie',
      radius: ['40%', '72%'],
      center: ['50%', '46%'],
      roseType: 'area',
      itemStyle: { borderRadius: 4, borderColor: '#fff', borderWidth: 2 },
      label: {
        formatter: '{b}\n{d}%',
        fontSize: 12,
      },
      data: data.map((d) => ({
        name: CHANNEL_NAMES[d.channel] || d.channel,
        value: d.count,
      })),
      color: ['#1677ff', '#52c41a', '#fa8c16', '#722ed1', '#13c2c2'],
    }],
  };

  return (
    <Card title="用户来源分布" className="chart-card">
      <Spin spinning={loading}>
        <ReactECharts option={option} style={{ height: 320 }} />
      </Spin>
    </Card>
  );
};

export default SourceChart;
