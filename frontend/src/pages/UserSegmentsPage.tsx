/** 用户分群分析 */
import UserSegmentsPanel from '../components/UserSegmentsPanel';
import './Dashboard.css';

const UserSegmentsPage = () => {
  return (
    <div className="dashboard-page">
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 600, color: 'rgba(0,0,0,0.85)', marginBottom: 4 }}>用户分群分析</h1>
        <p style={{ fontSize: 13, color: 'rgba(0,0,0,0.45)', margin: 0 }}>
          基于 KMeans 聚类算法，自动将用户划分为高价值、潜力、普通、流失四类群体，洞察用户画像特征
        </p>
      </div>
      <UserSegmentsPanel />
    </div>
  );
};

export default UserSegmentsPage;
