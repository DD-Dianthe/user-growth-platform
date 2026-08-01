/** 异常检测中心 */
import AnomalyPanel from '../components/AnomalyPanel';
import './Dashboard.css';

const AnomalyCenter = () => {
  return (
    <div className="dashboard-page">
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 600, color: 'rgba(0,0,0,0.85)', marginBottom: 4 }}>异常检测中心</h1>
        <p style={{ fontSize: 13, color: 'rgba(0,0,0,0.45)', margin: 0 }}>
          基于 Z-Score + Isolation Forest 算法，自动发现 DAU、GMV、用户行为等关键指标的异常波动
        </p>
      </div>
      <AnomalyPanel />
    </div>
  );
};

export default AnomalyCenter;
