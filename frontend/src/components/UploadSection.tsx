import { useState, useCallback } from 'react';
import {
  Upload, Card, Table, Tag, Button, Checkbox, Select, Slider, Row, Col,
  Statistic, Spin, Alert, message, Divider, Empty, InputNumber, Tabs,
} from 'antd';
import {
  InboxOutlined, PlayCircleOutlined, DatabaseOutlined, ExperimentOutlined,
  BarChartOutlined, ClusterOutlined, WarningOutlined,
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import type { UploadFile } from 'antd/es/upload/interface';
import {
  uploadDataFile, previewData, runAutoAnalysis,
  type ColumnInfo, type UploadResponse,
} from '../api/dashboard';

const { Dragger } = Upload;

const CATEGORY_COLORS: Record<string, string> = {
  numeric: '#1677ff',
  categorical: '#52c41a',
  datetime: '#722ed1',
  text: '#8c8c8c',
};

const CATEGORY_LABELS: Record<string, string> = {
  numeric: '数值',
  categorical: '分类',
  datetime: '日期',
  text: '文本',
};

const ML_METHODS = [
  { key: 'auto_dashboard', label: '自动看板', desc: '自动生成统计图表', icon: <BarChartOutlined /> },
  { key: 'kmeans', label: 'KMeans 聚类', desc: '无监督用户分群', icon: <ClusterOutlined /> },
  { key: 'isolation_forest', label: '异常检测', desc: 'Isolation Forest', icon: <WarningOutlined /> },
  { key: 'xgboost', label: 'XGBoost 预测', desc: '分类/回归预测', icon: <ExperimentOutlined /> },
];

export default function UploadSection() {
  const [uploading, setUploading] = useState(false);
  const [uploadInfo, setUploadInfo] = useState<UploadResponse | null>(null);
  const [previewRows, setPreviewRows] = useState<Record<string, any>[]>([]);
  const [selectedMethods, setSelectedMethods] = useState<string[]>(['auto_dashboard']);
  const [nClusters, setNClusters] = useState(4);
  const [contamination, setContamination] = useState(5);
  const [targetColumn, setTargetColumn] = useState<string | undefined>(undefined);
  const [analyzing, setAnalyzing] = useState(false);
  const [results, setResults] = useState<any>(null);

  // ── 上传处理 ──
  const handleUpload = useCallback(async (file: File) => {
    setUploading(true);
    setResults(null);
    try {
      const res = await uploadDataFile(file);
      setUploadInfo(res);

      // 获取预览数据
      const preview = await previewData(res.session_id, 50);
      setPreviewRows(preview.rows);

      // 自动选中第一个数值列作为 XGBoost 目标
      const firstNumeric = res.columns_info.find(c => c.category === 'numeric');
      setTargetColumn(firstNumeric?.name);

      message.success(`上传成功：${res.rows} 行 × ${res.columns} 列`);
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.message || '上传失败';
      message.error(msg);
    } finally {
      setUploading(false);
    }
    return false; // 阻止 antd 默认上传行为
  }, []);

  // ── 分析处理 ──
  const handleAnalyze = async () => {
    if (!uploadInfo) return;
    if (selectedMethods.length === 0) {
      message.warning('请至少选择一种分析方法');
      return;
    }

    setAnalyzing(true);
    setResults(null);
    try {
      const res = await runAutoAnalysis({
        session_id: uploadInfo.session_id,
        methods: selectedMethods,
        target_column: selectedMethods.includes('xgboost') ? targetColumn : undefined,
        n_clusters: nClusters,
        contamination: contamination / 100,
      });
      setResults(res.results);
      message.success('分析完成');
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.message || '分析失败';
      message.error(msg);
    } finally {
      setAnalyzing(false);
    }
  };

  // ── 渲染看板图表 ──
  const renderDashboard = (charts: any[]) => {
    if (!charts || charts.length === 0) return <Empty description="无图表数据" />;
    return (
      <Row gutter={[16, 16]}>
        {charts.map((chart, idx) => {
          if (chart.type === 'overview') {
            const entries = Object.entries(chart.data || {});
            return (
              <Col span={24} key={idx}>
                <Card size="small" title={chart.title} style={{ background: '#fafafa' }}>
                  <Row gutter={16}>
                    {entries.map(([k, v]) => (
                      <Col key={k} span={Math.max(4, Math.floor(24 / entries.length))}>
                        <Statistic title={k} value={v as any} />
                      </Col>
                    ))}
                  </Row>
                </Card>
              </Col>
            );
          }
          if (chart.type === 'stats_table') {
            return (
              <Col span={24} key={idx}>
                <Card size="small" title={chart.title}>
                  <Table
                    dataSource={chart.data}
                    rowKey="column"
                    pagination={false}
                    size="small"
                    scroll={{ x: 'max-content' }}
                  />
                </Card>
              </Col>
            );
          }
          if (chart.type === 'bar') {
            return (
              <Col xs={24} sm={12} key={idx}>
                <Card size="small" title={chart.title}>
                  <ReactECharts
                    option={{
                      tooltip: { trigger: 'axis' },
                      xAxis: { type: 'category', data: chart.categories, axisLabel: { rotate: 30 } },
                      yAxis: { type: 'value', name: chart.y_label },
                      series: [{ type: 'bar', data: chart.values, itemStyle: { color: '#1677ff' } }],
                      grid: { bottom: 60 },
                    }}
                    style={{ height: 260 }}
                  />
                </Card>
              </Col>
            );
          }
          if (chart.type === 'pie') {
            return (
              <Col xs={24} sm={12} key={idx}>
                <Card size="small" title={chart.title}>
                  <ReactECharts
                    option={{
                      tooltip: { trigger: 'item' },
                      legend: { bottom: 0, type: 'scroll' },
                      series: [{
                        type: 'pie',
                        radius: ['40%', '70%'],
                        data: chart.data,
                        label: { formatter: '{b}: {d}%' },
                      }],
                    }}
                    style={{ height: 260 }}
                  />
                </Card>
              </Col>
            );
          }
          if (chart.type === 'line') {
            return (
              <Col xs={24} sm={12} key={idx}>
                <Card size="small" title={chart.title}>
                  <ReactECharts
                    option={{
                      tooltip: { trigger: 'axis' },
                      xAxis: { type: 'category', data: chart.categories, axisLabel: { rotate: 30 } },
                      yAxis: { type: 'value', name: chart.y_label },
                      series: [{ type: 'line', data: chart.values, smooth: true, areaStyle: { opacity: 0.15 }, itemStyle: { color: '#722ed1' } }],
                      grid: { bottom: 60 },
                    }}
                    style={{ height: 260 }}
                  />
                </Card>
              </Col>
            );
          }
          return null;
        })}
      </Row>
    );
  };

  // ── 渲染 KMeans 结果 ──
  const renderKmeans = (data: any) => {
    if (data?.error) return <Alert type="error" title={data.error} />;
    const clusterStats = data.cluster_stats || [];
    const radarData = data.radar_data || {};
    const features = data.features || [];
    const radarKeys = Object.keys(radarData);

    const radarOption = radarKeys.length > 0 ? {
      tooltip: {},
      legend: { data: radarKeys, bottom: 0 },
      radar: {
        indicator: features.map((f: string) => ({ name: f, max: Math.max(...radarKeys.map(k => Math.max(...radarData[k]))) * 1.2 })),
      },
      series: [{
        type: 'radar',
        data: radarKeys.map(k => ({ name: k, value: radarData[k], areaStyle: { opacity: 0.1 } })),
      }],
    } : null;

    return (
      <div>
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={6}><Statistic title="聚类数" value={data.n_clusters} /></Col>
          <Col span={6}><Statistic title="特征数" value={features.length} /></Col>
          <Col span={6}><Statistic title="Inertia" value={data.inertia} /></Col>
        </Row>
        {radarOption && (
          <Card size="small" title="聚类特征雷达图" style={{ marginBottom: 16 }}>
            <ReactECharts option={radarOption} style={{ height: 320 }} />
          </Card>
        )}
        <Card size="small" title="各簇统计">
          <Table dataSource={clusterStats} rowKey="cluster_id" pagination={false} size="small" scroll={{ x: 'max-content' }} />
        </Card>
      </div>
    );
  };

  // ── 渲染 XGBoost 结果 ──
  const renderXgboost = (data: any) => {
    if (data?.error) return <Alert type="error" title={data.error} />;
    const metrics = data.metrics || {};
    const importance = data.feature_importance || [];

    const barOption = importance.length > 0 ? {
      tooltip: { trigger: 'axis' },
      xAxis: { type: 'value', name: '重要性' },
      yAxis: { type: 'category', data: importance.map((i: any) => i.feature).reverse() },
      series: [{
        type: 'bar',
        data: importance.map((i: any) => i.importance).reverse(),
        itemStyle: { color: '#fa8c16' },
      }],
      grid: { left: 120 },
    } : null;

    return (
      <div>
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={6}><Statistic title="任务类型" value={data.task_type === 'classification' ? '分类' : '回归'} /></Col>
          <Col span={6}><Statistic title="目标列" value={data.target} /></Col>
          <Col span={6}>
            <Statistic
              title={data.task_type === 'classification' ? 'Accuracy' : 'R²'}
              value={metrics.accuracy}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title={data.task_type === 'classification' ? 'Precision' : 'MAE'}
              value={metrics.precision}
            />
          </Col>
        </Row>
        {barOption && (
          <Card size="small" title="特征重要性">
            <ReactECharts option={barOption} style={{ height: 300 }} />
          </Card>
        )}
      </div>
    );
  };

  // ── 渲染 IsolationForest 结果 ──
  const renderIsolationForest = (data: any) => {
    if (data?.error) return <Alert type="error" title={data.error} />;
    const samples = data.anomaly_samples || [];

    const pieOption = {
      tooltip: { trigger: 'item' },
      legend: { bottom: 0 },
      series: [{
        type: 'pie',
        radius: ['40%', '70%'],
        data: [
          { name: '正常', value: data.normal_count, itemStyle: { color: '#52c41a' } },
          { name: '异常', value: data.anomaly_count, itemStyle: { color: '#ff4d4f' } },
        ],
        label: { formatter: '{b}: {d}%' },
      }],
    };

    return (
      <div>
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={6}><Statistic title="异常数" value={data.anomaly_count} styles={{ content: { color: '#ff4d4f' } }} /></Col>
          <Col span={6}><Statistic title="正常数" value={data.normal_count} styles={{ content: { color: '#52c41a' } }} /></Col>
          <Col span={6}><Statistic title="异常比例" value={data.anomaly_ratio} /></Col>
          <Col span={6}><Statistic title="特征数" value={(data.features || []).length} /></Col>
        </Row>
        <Row gutter={16}>
          <Col xs={24} sm={10}>
            <Card size="small" title="正常 vs 异常">
              <ReactECharts option={pieOption} style={{ height: 240 }} />
            </Card>
          </Col>
          <Col xs={24} sm={14}>
            <Card size="small" title="异常样本（前 10 条）">
              <Table dataSource={samples} rowKey="_index" pagination={false} size="small" scroll={{ x: 'max-content' }} />
            </Card>
          </Col>
        </Row>
      </div>
    );
  };

  // ── 预览表格列定义 ──
  const previewColumns = uploadInfo
    ? uploadInfo.columns_info.map(c => ({
        title: (
          <div>
            <div>{c.name}</div>
            <Tag color={CATEGORY_COLORS[c.category]} style={{ fontSize: 10 }}>
              {CATEGORY_LABELS[c.category]}
            </Tag>
          </div>
        ),
        dataIndex: c.name,
        key: c.name,
        ellipsis: true,
        width: 150,
        render: (val: any) => (val === null || val === undefined ? <span style={{ color: '#ccc' }}>NULL</span> : String(val)),
      }))
    : [];

  return (
    <div>
      {/* ── 上传区域 ── */}
      {!uploadInfo && (
        <Card>
          <Dragger
            accept=".csv,.xlsx,.xls"
            multiple={false}
            showUploadList={false}
            beforeUpload={handleUpload}
            disabled={uploading}
          >
            {uploading ? (
              <Spin description="上传解析中..." size="large" style={{ padding: 40 }} />
            ) : (
              <div style={{ padding: 40 }}>
                <p className="ant-upload-drag-icon">
                  <InboxOutlined style={{ fontSize: 48, color: '#1677ff' }} />
                </p>
                <p className="ant-upload-text" style={{ fontSize: 16 }}>
                  点击或拖拽文件到此区域上传
                </p>
                <p className="ant-upload-hint">
                  支持 CSV、Excel 文件，最大 50MB，不超过 10 万行
                </p>
              </div>
            )}
          </Dragger>
          <Alert
            style={{ marginTop: 16 }}
            type="info"
            showIcon
            title="上传你的数据后，系统会自动识别列类型、生成看板图表，并支持选择 ML 方法进行分析"
          />
        </Card>
      )}

      {/* ── 上传成功后：数据信息 + 分析配置 ── */}
      {uploadInfo && (
        <div>
          {/* 文件信息 */}
          <Card size="small" style={{ marginBottom: 16 }}>
            <Row gutter={16} align="middle">
              <Col flex="auto">
                <Row gutter={24}>
                  <Col><Statistic title="文件名" value={uploadInfo.filename} styles={{ content: { fontSize: 14 } }} /></Col>
                  <Col><Statistic title="行数" value={uploadInfo.rows} /></Col>
                  <Col><Statistic title="列数" value={uploadInfo.columns} /></Col>
                </Row>
              </Col>
              <Col>
                <Button
                  onClick={() => {
                    setUploadInfo(null);
                    setPreviewRows([]);
                    setResults(null);
                  }}
                >
                  重新上传
                </Button>
              </Col>
            </Row>
          </Card>

          {/* 列类型卡片 */}
          <Row gutter={[8, 8]} style={{ marginBottom: 16 }}>
            {uploadInfo.columns_info.map(col => (
              <Col key={col.name} xs={12} sm={8} md={6} lg={4}>
                <Card size="small" style={{ height: '100%' }}>
                  <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 4, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {col.name}
                  </div>
                  <Tag color={CATEGORY_COLORS[col.category]} style={{ marginBottom: 4 }}>
                    {CATEGORY_LABELS[col.category]}
                  </Tag>
                  <div style={{ fontSize: 11, color: '#999' }}>
                    {col.unique_count} 种值 · {col.null_count} 空值
                  </div>
                  {col.stats && col.category === 'numeric' && (
                    <div style={{ fontSize: 11, color: '#666', marginTop: 4 }}>
                      均值 {col.stats.mean} · 范围 [{col.stats.min}, {col.stats.max}]
                    </div>
                  )}
                </Card>
              </Col>
            ))}
          </Row>

          {/* 数据预览 */}
          <Card size="small" title={<><DatabaseOutlined /> 数据预览（前 50 行）</>} style={{ marginBottom: 16 }}>
            <Table
              dataSource={previewRows}
              columns={previewColumns}
              rowKey={(record) => JSON.stringify(record)}
              pagination={{ pageSize: 10, size: 'small' }}
              size="small"
              scroll={{ x: 'max-content' }}
            />
          </Card>

          {/* 分析方法选择 */}
          <Card
            size="small"
            title={<><ExperimentOutlined /> 选择分析方法</>}
            style={{ marginBottom: 16 }}
          >
            <Checkbox.Group
              value={selectedMethods}
              onChange={(vals) => setSelectedMethods(vals as string[])}
              style={{ width: '100%' }}
            >
              <Row gutter={[16, 12]}>
                {ML_METHODS.map(m => (
                  <Col key={m.key} xs={24} sm={12}>
                    <Checkbox value={m.key} style={{ width: '100%' }}>
                      <span style={{ marginLeft: 4 }}>
                        {m.icon} <strong>{m.label}</strong>
                        <span style={{ color: '#999', marginLeft: 8, fontSize: 12 }}>{m.desc}</span>
                      </span>
                    </Checkbox>
                  </Col>
                ))}
              </Row>
            </Checkbox.Group>

            {/* 参数配置 */}
            <Divider style={{ margin: '12px 0' }} />
            <Row gutter={24}>
              {selectedMethods.includes('kmeans') && (
                <Col xs={24} sm={8}>
                  <div style={{ marginBottom: 8, fontWeight: 500 }}>KMeans 聚类数</div>
                  <Row gutter={8} align="middle">
                    <Col flex="auto">
                      <Slider min={2} max={10} value={nClusters} onChange={setNClusters} />
                    </Col>
                    <Col><InputNumber min={2} max={10} value={nClusters} onChange={v => v && setNClusters(v)} style={{ width: 60 }} /></Col>
                  </Row>
                </Col>
              )}
              {selectedMethods.includes('isolation_forest') && (
                <Col xs={24} sm={8}>
                  <div style={{ marginBottom: 8, fontWeight: 500 }}>异常检测灵敏度（异常比例 %）</div>
                  <Row gutter={8} align="middle">
                    <Col flex="auto">
                      <Slider min={1} max={30} value={contamination} onChange={setContamination} />
                    </Col>
                    <Col><InputNumber min={1} max={30} value={contamination} onChange={v => v && setContamination(v)} style={{ width: 60 }} /></Col>
                  </Row>
                </Col>
              )}
              {selectedMethods.includes('xgboost') && (
                <Col xs={24} sm={8}>
                  <div style={{ marginBottom: 8, fontWeight: 500 }}>XGBoost 目标列</div>
                  <Select
                    style={{ width: '100%' }}
                    value={targetColumn}
                    onChange={setTargetColumn}
                    placeholder="选择目标列"
                    options={uploadInfo.columns_info
                      .filter(c => c.category === 'numeric')
                      .map(c => ({ label: `${c.name}（${CATEGORY_LABELS[c.category]}）`, value: c.name }))}
                  />
                </Col>
              )}
            </Row>

            <div style={{ marginTop: 16, textAlign: 'center' }}>
              <Button
                type="primary"
                size="large"
                icon={<PlayCircleOutlined />}
                onClick={handleAnalyze}
                loading={analyzing}
                disabled={selectedMethods.length === 0}
              >
                {analyzing ? '分析中...' : '开始分析'}
              </Button>
            </div>
          </Card>

          {/* 分析结果 */}
          {analyzing && (
            <Card>
              <div style={{ textAlign: 'center', padding: 40 }}>
                <Spin size="large" description="正在运行机器学习分析..." />
              </div>
            </Card>
          )}

          {results && !analyzing && (
            <Card>
              {Object.keys(results).length === 0 ? (
                <Empty description="无分析结果" />
              ) : (
                <Tabs
                  items={Object.entries(results).map(([key, val]: [string, any]) => ({
                    key,
                    label: key === 'dashboard' ? '自动看板' :
                           key === 'kmeans' ? 'KMeans 聚类' :
                           key === 'xgboost' ? 'XGBoost 预测' :
                           key === 'isolation_forest' ? '异常检测' : key,
                    children: key === 'dashboard'
                      ? renderDashboard(val)
                      : key === 'kmeans'
                      ? renderKmeans(val)
                      : key === 'xgboost'
                      ? renderXgboost(val)
                      : key === 'isolation_forest'
                      ? renderIsolationForest(val)
                      : <pre>{JSON.stringify(val, null, 2)}</pre>,
                  }))}
                />
              )}
            </Card>
          )}
        </div>
      )}
    </div>
  );
}
