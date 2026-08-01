/** 用户流失风险预测 */
import ChurnPanel from '../components/ChurnPanel';
import './Dashboard.css';

const ChurnPredictionPage = () => {
  return (
    <div className="dashboard-page">
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 600, color: 'rgba(0,0,0,0.85)', marginBottom: 4 }}>用户流失风险预测</h1>
        <p style={{ fontSize: 13, color: 'rgba(0,0,0,0.45)', margin: 0 }}>
          基于 XGBoost 算法，利用用户行为特征预测未来流失概率，识别高风险用户
        </p>
      </div>
      <ChurnPanel />
    </div>
  );
};

export default ChurnPredictionPage;
