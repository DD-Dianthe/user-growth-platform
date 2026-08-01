import { Layout, Divider } from 'antd';
import { BarChartOutlined, CloudUploadOutlined } from '@ant-design/icons';

import Dashboard from './pages/Dashboard';
import AnomalyPanel from './components/AnomalyPanel';
import ChurnPanel from './components/ChurnPanel';
import UserSegmentsPanel from './components/UserSegmentsPanel';
import UploadSection from './components/UploadSection';

const { Header, Content } = Layout;

function App() {
  return (
    <Layout style={{ minHeight: '100vh', background: '#f5f5f5' }}>
      {/* ── 顶部导航栏 ── */}
      <Header
        style={{
          background: '#001529',
          padding: '0 24px',
          height: 56,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          position: 'sticky',
          top: 0,
          zIndex: 100,
          boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <BarChartOutlined style={{ fontSize: 20, color: '#1677ff' }} />
          <span style={{ color: '#fff', fontSize: 16, fontWeight: 600, letterSpacing: 0.5 }}>
            用户增长智能分析平台
          </span>
        </div>
        <span style={{ fontSize: 12, color: 'rgba(255,255,255,0.45)' }}>
          Growth Analytics v1.0
        </span>
      </Header>

      {/* ── 内容区（单页滚动） ── */}
      <Content style={{ padding: 24, maxWidth: 1400, margin: '0 auto', width: '100%' }}>
        {/* ── 第 0 节：自助上传分析 ── */}
        <section style={{ marginBottom: 32 }}>
          <div style={{ marginBottom: 16 }}>
            <h1 style={{ fontSize: 22, fontWeight: 600, color: 'rgba(0,0,0,0.85)', marginBottom: 4 }}>
              <CloudUploadOutlined style={{ marginRight: 8, color: '#1677ff' }} />
              自助数据分析
            </h1>
            <p style={{ fontSize: 13, color: 'rgba(0,0,0,0.45)', margin: 0 }}>
              上传你自己的 CSV / Excel 数据，系统自动识别列类型、生成看板图表，并支持选择 KMeans、XGBoost、Isolation Forest 等机器学习方法
            </p>
          </div>
          <UploadSection />
        </section>

        <Divider style={{ margin: '0 0 32px', borderColor: '#e8e8e8' }} />

        {/* ── 第 1 节：概览看板 ── */}
        <section style={{ marginBottom: 32 }}>
          <div style={{ marginBottom: 16 }}>
            <h1 style={{ fontSize: 22, fontWeight: 600, color: 'rgba(0,0,0,0.85)', marginBottom: 4 }}>
              概览看板
            </h1>
            <p style={{ fontSize: 13, color: 'rgba(0,0,0,0.45)', margin: 0 }}>
              核心运营指标一览：DAU、新增用户、GMV、转化率及趋势分析
            </p>
          </div>
          <Dashboard />
        </section>

        <Divider style={{ margin: '0 0 32px', borderColor: '#e8e8e8' }} />

        {/* ── 第 2 节：异常检测 ── */}
        <section style={{ marginBottom: 32 }}>
          <div style={{ marginBottom: 16 }}>
            <h1 style={{ fontSize: 22, fontWeight: 600, color: 'rgba(0,0,0,0.85)', marginBottom: 4 }}>
              异常检测
            </h1>
            <p style={{ fontSize: 13, color: 'rgba(0,0,0,0.45)', margin: 0 }}>
              基于 Z-Score + Isolation Forest 算法，自动发现 DAU、GMV、用户行为等关键指标的异常波动
            </p>
          </div>
          <AnomalyPanel />
        </section>

        <Divider style={{ margin: '0 0 32px', borderColor: '#e8e8e8' }} />

        {/* ── 第 3 节：用户流失预测 ── */}
        <section style={{ marginBottom: 32 }}>
          <div style={{ marginBottom: 16 }}>
            <h1 style={{ fontSize: 22, fontWeight: 600, color: 'rgba(0,0,0,0.85)', marginBottom: 4 }}>
              用户流失预测
            </h1>
            <p style={{ fontSize: 13, color: 'rgba(0,0,0,0.45)', margin: 0 }}>
              基于 XGBoost 算法，利用用户行为特征预测未来流失概率，识别高风险用户
            </p>
          </div>
          <ChurnPanel />
        </section>

        <Divider style={{ margin: '0 0 32px', borderColor: '#e8e8e8' }} />

        {/* ── 第 4 节：用户分群 ── */}
        <section style={{ marginBottom: 32 }}>
          <div style={{ marginBottom: 16 }}>
            <h1 style={{ fontSize: 22, fontWeight: 600, color: 'rgba(0,0,0,0.85)', marginBottom: 4 }}>
              用户分群分析
            </h1>
            <p style={{ fontSize: 13, color: 'rgba(0,0,0,0.45)', margin: 0 }}>
              基于 KMeans 聚类算法，自动将用户划分为高价值、潜力、普通、流失四类群体
            </p>
          </div>
          <UserSegmentsPanel />
        </section>
      </Content>
    </Layout>
  );
}

export default App;
