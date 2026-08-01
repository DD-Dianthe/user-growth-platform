/** KPI 指标卡片 */
import React from 'react';
import { Card, Statistic } from 'antd';
import { ArrowUpOutlined, ArrowDownOutlined } from '@ant-design/icons';

interface Props {
  title: string;
  value: number | string;
  prefix?: React.ReactNode;
  suffix?: string;
  trend?: 'up' | 'down';
  trendLabel?: string;
  icon: React.ReactNode;
  iconColor: string;
  loading?: boolean;
  formatter?: (v: number) => string;
}

const KpiCard: React.FC<Props> = ({
  title, value, prefix, suffix, trend, trendLabel,
  icon, iconColor, loading, formatter,
}) => {
  const displayValue = typeof value === 'number' && formatter
    ? formatter(value)
    : value;

  return (
    <Card loading={loading} bordered={false} className="kpi-card">
      <div className="kpi-card-inner">
        <div className="kpi-icon" style={{ background: iconColor }}>
          {icon}
        </div>
        <div className="kpi-info">
          <div className="kpi-title">{title}</div>
          <div className="kpi-value">
            {prefix}
            <span>{displayValue}</span>
            {suffix && <span className="kpi-suffix">{suffix}</span>}
          </div>
          {trend && (
            <div className={`kpi-trend ${trend}`}>
              {trend === 'up' ? <ArrowUpOutlined /> : <ArrowDownOutlined />}
              <span>{trendLabel}</span>
            </div>
          )}
        </div>
      </div>
    </Card>
  );
};

export default KpiCard;
