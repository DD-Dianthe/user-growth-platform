/** Dashboard API 请求层 */
import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api';
const api = axios.create({ baseURL: API_BASE });

export interface DashboardOverview {
  dau: number;
  new_users: number;
  gmv: number;
  paying_users: number;
  conversion_rate: number;
}

export interface DashboardResponse {
  date: string;
  overview: DashboardOverview;
}

export interface FunnelStep {
  step: string;
  count: number;
  rate: number | null;
}

export interface FunnelResponse {
  steps: FunnelStep[];
  overall_rate: number;
}

export interface RetentionItem {
  date: string;
  new_users: number;
  day1_retention: number | null;
  day7_retention: number | null;
}

export interface RetentionResponse {
  items: RetentionItem[];
}

export interface TrendItem {
  date: string;
  dau: number;
  gmv: number;
}

export interface TrendResponse {
  items: TrendItem[];
}

export interface SourceItem {
  channel: string;
  count: number;
}

export interface SourceResponse {
  items: SourceItem[];
}

/** 核心指标概览 */
export async function fetchDashboard(date?: string): Promise<DashboardResponse> {
  const { data } = await api.get<DashboardResponse>('/dashboard', {
    params: date ? { target_date: date } : {},
  });
  return data;
}

/** 转化漏斗 */
export async function fetchFunnel(start?: string, end?: string): Promise<FunnelResponse> {
  const { data } = await api.get<FunnelResponse>('/funnel', {
    params: { start_date: start, end_date: end },
  });
  return data;
}

/** 留存分析 */
export async function fetchRetention(start?: string, end?: string): Promise<RetentionResponse> {
  const { data } = await api.get<RetentionResponse>('/retention', {
    params: { start_date: start, end_date: end },
  });
  return data;
}

/** DAU & GMV 趋势 */
export async function fetchTrends(start?: string, end?: string): Promise<TrendResponse> {
  const { data } = await api.get<TrendResponse>('/trends', {
    params: { start_date: start, end_date: end },
  });
  return data;
}

/** 用户来源分布 */
export async function fetchSource(): Promise<SourceResponse> {
  const { data } = await api.get<SourceResponse>('/source');
  return data;
}

/** 渠道中文名映射 */
export const CHANNEL_NAMES: Record<string, string> = {
  organic: '自然流量',
  paid_search: '付费搜索',
  social_media: '社交媒体',
  referral: '推荐引流',
  email: '邮件营销',
};

// ═══════════════════════════════════════════════
//  用户画像 - 分群 API
// ═══════════════════════════════════════════════

export interface SegmentOverview {
  segment: string;
  user_count: number;
  avg_login: number;
  avg_view: number;
  avg_purchase: number;
  avg_amount: number;
  avg_days_inactive: number;
  total_amount: number;
}

export interface SegmentsResponse {
  total_users: number;
  total_gmv: number;
  segments: SegmentOverview[];
}

export interface SegmentDetailItem {
  user_id: number;
  segment: string;
  login_count: number;
  view_count: number;
  purchase_count: number;
  total_amount: number;
  days_since_last_active: number;
  cluster_id: number;
}

export interface SegmentDetailResponse {
  total: number;
  page: number;
  page_size: number;
  items: SegmentDetailItem[];
}

/** 用户分群概览 */
export async function fetchSegmentsOverview(): Promise<SegmentsResponse> {
  const { data } = await api.get<SegmentsResponse>('/user-segments/overview');
  return data;
}

/** 运行用户分群聚类 */
export async function runSegmentation(): Promise<any> {
  const { data } = await api.post('/user-segments/run');
  return data;
}

// ═══════════════════════════════════════════════
//  流失预测 API
// ═══════════════════════════════════════════════

export interface ChurnOverview {
  total_users: number;
  predicted_churn: number;
  high_risk: number;
  avg_probability: number;
  max_probability: number;
  min_probability: number;
}

export interface ChurnDistribution {
  probability_bucket: string;
  user_count: number;
  avg_prob: number;
}

export interface ChurnProfileItem {
  is_high_risk: number;
  user_count: number;
  avg_login: number;
  avg_view: number;
  avg_purchase: number;
  avg_amount: number;
  avg_days_inactive: number;
}

export interface ChurnOverviewResponse {
  overview: ChurnOverview;
  distribution: ChurnDistribution[];
  profile: ChurnProfileItem[];
}

export interface ChurnHighRiskItem {
  user_id: number;
  churn_probability: number;
  predicted_churn: number;
  is_high_risk: number;
  predicted_at: string;
  login_count: number;
  view_count: number;
  purchase_count: number;
  total_amount: number;
  days_inactive: number;
  segment: string;
}

export interface ChurnHighRiskResponse {
  total: number;
  offset: number;
  limit: number;
  items: ChurnHighRiskItem[];
}

export interface ChurnRunResponse {
  status: string;
  message: string;
  model_metrics: {
    accuracy: number;
    precision: number;
    recall: number;
    auc: number;
    cv_auc_mean: number;
    cv_auc_std: number;
    confusion_matrix: { tp: number; fp: number; tn: number; fn: number };
    top_features: { feature: string; importance: number }[];
  };
  summary: {
    total_users: number;
    predicted_churn: number;
    high_risk_users: number;
    avg_churn_probability: number;
  };
}

/** 获取流失风险概览 */
export async function fetchChurnOverview(): Promise<ChurnOverviewResponse> {
  const { data } = await api.get<ChurnOverviewResponse>('/churn/overview');
  return data;
}

/** 获取高风险用户列表 */
export async function fetchChurnHighRisk(
  limit = 50,
  offset = 0,
  sortBy = 'probability'
): Promise<ChurnHighRiskResponse> {
  const { data } = await api.get<ChurnHighRiskResponse>('/churn/high-risk', {
    params: { limit, offset, sort_by: sortBy },
  });
  return data;
}

/** 运行流失预测 */
export async function runChurnPrediction(): Promise<ChurnRunResponse> {
  const { data } = await api.post<ChurnRunResponse>('/churn/run');
  return data;
}

// ═══════════════════════════════════════════════
//  自助上传分析 API
// ═══════════════════════════════════════════════

export interface ColumnInfo {
  name: string;
  dtype: string;
  category: 'numeric' | 'categorical' | 'datetime' | 'text';
  null_count: number;
  unique_count: number;
  sample_values: any[];
  null_ratio: number;
  stats?: Record<string, number | string | null>;
  distribution?: Record<string, number>;
}

export interface UploadResponse {
  session_id: string;
  filename: string;
  rows: number;
  columns: number;
  columns_info: ColumnInfo[];
}

export interface PreviewResponse {
  session_id: string;
  rows: Record<string, any>[];
  total_rows: number;
}

export interface AnalysisRequest {
  session_id: string;
  methods: string[];
  target_column?: string;
  feature_columns?: string[];
  n_clusters?: number;
  contamination?: number;
}

/** 上传数据文件 */
export async function uploadDataFile(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append('file', file);
  const { data } = await api.post<UploadResponse>('/data/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
}

/** 预览上传数据 */
export async function previewData(sessionId: string, limit = 50): Promise<PreviewResponse> {
  const { data } = await api.get<PreviewResponse>(`/data/${sessionId}/preview`, {
    params: { limit },
  });
  return data;
}

/** 运行自动分析 */
export async function runAutoAnalysis(req: AnalysisRequest): Promise<any> {
  const { data } = await api.post('/auto-analyze/run', req);
  return data;
}
