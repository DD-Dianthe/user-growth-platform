/** DAU 日活跃用户趋势折线图 */
import React, { useEffect, useState } from 'react';
import ReactECharts from 'echarts-for-react';
import { Card, Spin } from 'antd';
import { fetchTrends, type TrendItem } from '../api/dashboard';
import dayjs from 'dayjs';

const DauTrendChart: React.FC = () => {
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
    },
    grid: { top: 20, right: 20, bottom: 20, left: 50 },
    xAxis: {
      type: 'category',
      data: data.map((d) => dayjs(d.date).format('MM-DD')),
      axisLine: { lineStyle: { color: '#e8e8e8' } },
      axisLabel: { color: '#999' },
    },
    yAxis: {
      type: 'value',
      name: '人数',
      nameTextStyle: { color: '#999' },
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: '#f0f0f0' } },
    },
    series: [{
      name: 'DAU',
      type: 'line',
      smooth: true,
      symbol: 'circle',
      symbolSize: 4,
      lineStyle: { color: '#1677ff', width: 2 },
      areaStyle: {
        color: {
          type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(22,119,255,0.25)' },
            { offset: 1, color: 'rgba(22,119,255,0.02)' },
          ],
        },
      },
      data: data.map((d) => d.dau),
    }],
  };

  return (
    <Card title="DAU 趋势" className="chart-card">
      <Spin spinning={loading}>
        <ReactECharts option={option} style={{ height: 320 }} />
      </Spin>
    </Card>
  );
};

export default DauTrendChart;
