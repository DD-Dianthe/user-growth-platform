import { HashRouter, Routes, Route, useNavigate, useLocation } from 'react-router-dom';
import { Layout, Menu } from 'antd';
import type { MenuProps } from 'antd';
import {
  DashboardOutlined,
  AlertOutlined,
  WarningOutlined,
  ClusterOutlined,
  BarChartOutlined,
} from '@ant-design/icons';

import Overview from './pages/Dashboard';
import AnomalyCenter from './pages/AnomalyCenter';
import ChurnPrediction from './pages/ChurnPredictionPage';
import UserSegments from './pages/UserSegmentsPage';

const { Sider, Content, Header } = Layout;

const menuItems: MenuProps['items'] = [
  { key: '/overview', icon: <DashboardOutlined />, label: '概览看板' },
  { key: '/anomaly', icon: <AlertOutlined />, label: '异常检测' },
  { key: '/churn', icon: <WarningOutlined />, label: '流失预测' },
  { key: '/segments', icon: <ClusterOutlined />, label: '用户分群' },
];

const pageTitles: Record<string, string> = {
  '/overview': '概览看板',
  '/anomaly': '异常检测中心',
  '/churn': '流失风险预测',
  '/segments': '用户分群分析',
};

function AppLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const currentPath = location.pathname === '/' ? '/overview' : location.pathname;
  const currentTitle = pageTitles[currentPath] || '概览看板';

  return (
    <Layout style={{ minHeight: '100vh' }}>
      {/* ── 侧边栏 ── */}
      <Sider
        width={220}
        style={{
          background: '#001529',
          boxShadow: '2px 0 8px rgba(0,0,0,0.15)',
          overflow: 'auto',
        }}
      >
        <div
          style={{
            height: 56,
            display: 'flex',
            alignItems: 'center',
            padding: '0 20px',
            borderBottom: '1px solid rgba(255,255,255,0.08)',
          }}
        >
          <BarChartOutlined style={{ fontSize: 20, color: '#1677ff', marginRight: 10 }} />
          <span style={{ color: '#fff', fontSize: 15, fontWeight: 600, letterSpacing: 0.5 }}>
            用户增长分析
          </span>
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[currentPath]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
          style={{ borderRight: 0, marginTop: 4 }}
        />
      </Sider>

      {/* ── 右侧内容 ── */}
      <Layout>
        <Header
          style={{
            background: '#fff',
            padding: '0 24px',
            height: 56,
            lineHeight: '56px',
            borderBottom: '1px solid #f0f0f0',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            position: 'sticky',
            top: 0,
            zIndex: 10,
          }}
        >
          <div>
            <h1 style={{ fontSize: 17, fontWeight: 600, margin: 0, color: 'rgba(0,0,0,0.85)' }}>
              {currentTitle}
            </h1>
          </div>
          <span style={{ fontSize: 12, color: 'rgba(0,0,0,0.45)' }}>
            Growth Analytics v1.0
          </span>
        </Header>
        <Content style={{ padding: 24, background: '#f5f5f5', minHeight: 'calc(100vh - 56px)' }}>
          <Routes>
            <Route path="/" element={<Overview />} />
            <Route path="/overview" element={<Overview />} />
            <Route path="/anomaly" element={<AnomalyCenter />} />
            <Route path="/churn" element={<ChurnPrediction />} />
            <Route path="/segments" element={<UserSegments />} />
          </Routes>
        </Content>
      </Layout>
    </Layout>
  );
}

export default function App() {
  return (
    <HashRouter>
      <AppLayout />
    </HashRouter>
  );
}
