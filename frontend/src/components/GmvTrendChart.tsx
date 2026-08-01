/** GMV 交易额趋势图（柱状 + 折线混合） */
import React, { useEffect, useState } from 'react';
import ReactECharts from 'echarts-for-react';
import { Card, Spin } from 'antd';
import { fetchTrends, type TrendItem } from '../api/dashboard';
import dayjs from 'dayjs';

const GmvTrendChart: React.FC = () => {
  const [data, setData] = useState<TrendItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const end = dayjs().format('YYYY-MM-DD');
    const start = dayjs().subtract(30, 'day').format('YYYY-MM-DD');
    fetchTrends(start, end)
      .then((res) => setData(res.items))
      .finally(() => setLoading(false));
  }, []);

  const option = {
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(255,255,255,0.95)',
      borderColor: '#e8e8e8',
      textStyle: { color: '#333' },
      formatter: (params: any) => {
        const gmvVal = params[0]?.value ?? 0;
        return `${params[0]?.axisValue}<br/>GMV: ¥${Number(gmvVal).toLocaleString()}`;
      },
    },
    grid: { top: 20, right: 20, bottom: 20, left: 60 },
    xAxis: {
      type: 'category',
      data: data.map((d) => dayjs(d.date).format('MM-DD')),
      axisLine: { lineStyle: { color: '#e8e8e8' } },
      axisLabel: { color: '#999' },
    },
    yAxis: {
      type: 'value',
      name: '¥',
      nameTextStyle: { color: '#999' },
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: '#f0f0f0' } },
      axisLabel: { formatter: (v: number) => v >= 1000 ? `${(v / 1000).toFixed(0)}k` : v },
    },
    series: [{
      name: 'GMV',
      type: 'bar',
      barWidth: 16,
      itemStyle: {
        borderRadius: [4, 4, 0, 0],
        color: {
          type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: '#fa8c16' },
            { offset: 1, color: '#ffd666' },
          ],
        },
      },
      data: data.map((d) => d.gmv),
    }],
    dataZoom: [
      { type: 'inside', start: 0, end: 100 },
    ],
  };

  return (
    <Card title="GMV 趋势" className="chart-card">
      <Spin spinning={loading}>
        <ReactECharts option={option} style={{ height: 320 }} />
      </Spin>
    </Card>
  );
};

export default GmvTrendChart;
