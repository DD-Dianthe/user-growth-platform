"""自动分析与机器学习 API

根据上传的数据自动生成看板图表，并运行用户选择的 ML 方法。
"""

import json, uuid
from typing import Any, Optional

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.cluster import KMeans
from sklearn.ensemble import IsolationForest
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score

from app.database import engine
from app.core.session_state import get_session

router = APIRouter(prefix="/api/auto-analyze", tags=["auto-analyze"])

_analysis_cache: dict[str, dict] = {}


class NumpyEncoder(json.JSONEncoder):
    def default(self, obj: Any) -> Any:
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(round(obj, 4))
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)


class AnalysisRequest(BaseModel):
    session_id: str
    methods: list[str]  # ["auto_dashboard", "kmeans", "xgboost", "isolation_forest"]
    target_column: Optional[str] = None  # XGBoost 需要的目标列
    feature_columns: Optional[list[str]] = None  # ML 特征列（为空则自动选择数值列）
    n_clusters: Optional[int] = 4  # KMeans 聚类数
    contamination: Optional[float] = 0.05  # IForest 异常比例


def _load_data(session_id: str) -> tuple[pd.DataFrame, dict]:
    """从 SQLite/MySQL 加载上传的数据"""
    session = get_session(session_id)
    if not session:
        raise HTTPException(404, "Session 不存在或数据已过期")

    table_name = session["table_name"]
    df = pd.read_sql(f"SELECT * FROM {table_name}", engine)
    return df, {"table_name": table_name}


def _auto_dashboard(df: pd.DataFrame) -> list[dict]:
    """自动生成看板图表配置"""
    charts = []
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    cat_cols = [
        c for c in df.columns
        if c not in numeric_cols and df[c].nunique() <= 30 and df[c].nunique() > 1
    ]
    date_cols = df.select_dtypes(include=["datetime64"]).columns.tolist()

    # 尝试自动检测日期列
    for c in df.columns:
        if c not in date_cols and c not in numeric_cols:
            try:
                s = pd.to_datetime(df[c], errors="coerce")
                valid_ratio = s.notna().sum() / len(s)
                if valid_ratio > 0.8:
                    date_cols.append(c)
            except Exception:
                pass

    # 1. 数值列统计摘要
    if numeric_cols:
        stats_rows = []
        for c in numeric_cols[:10]:
            s = df[c].dropna()
            stats_rows.append({
                "column": c,
                "min": float(round(s.min(), 2)),
                "max": float(round(s.max(), 2)),
                "mean": float(round(s.mean(), 2)),
                "median": float(round(s.median(), 2)),
                "std": float(round(s.std(), 2)),
                "count": int(len(s)),
            })
        charts.append({
            "type": "stats_table",
            "title": "数值列统计摘要",
            "description": f"共 {len(numeric_cols)} 个数值列",
            "data": stats_rows,
        })

    # 2. 数值列分布直方图（前 6 列）
    for c in numeric_cols[:6]:
        s = df[c].dropna()
        bins = min(20, max(5, int(np.sqrt(len(s)))))
        hist, bin_edges = np.histogram(s, bins=bins)
        charts.append({
            "type": "bar",
            "title": f"{c} 分布直方图",
            "x_label": c,
            "y_label": "频数",
            "categories": [f"{round(bin_edges[i], 1)}-{round(bin_edges[i+1], 1)}" for i in range(len(bin_edges)-1)],
            "values": hist.tolist(),
        })

    # 3. 分类列饼图（前 4 列）
    for c in cat_cols[:4]:
        vc = df[c].value_counts().head(10)
        charts.append({
            "type": "pie",
            "title": f"{c} 分布",
            "data": [{"name": str(k), "value": int(v)} for k, v in vc.items()],
        })

    # 4. 日期列趋势图
    if date_cols and numeric_cols:
        try:
            date_col = date_cols[0]
            s_date = pd.to_datetime(df[date_col], errors="coerce")
            numeric_col = numeric_cols[0]
            df_temp = pd.DataFrame({numeric_col: df[numeric_col].values, "_date": s_date.dt.date.values})
            df_temp = df_temp.dropna(subset=["_date"])
            grouped = df_temp.groupby("_date")[numeric_col].sum().sort_index().tail(60)
            if len(grouped) > 1:
                charts.append({
                    "type": "line",
                    "title": f"{numeric_col} 日趋势 (按 {date_col})",
                    "x_label": date_col,
                    "y_label": numeric_col,
                    "categories": [str(x) for x in grouped.index.tolist()],
                    "values": [float(v) for v in grouped.values.tolist()],
                })
        except Exception:
            pass

    # 5. 整体概览指标
    overview = {
        "总行数": len(df),
        "总列数": len(df.columns),
        "数值列数": len(numeric_cols),
        "分类列数": len(cat_cols),
        "缺失值总计": int(df.isna().sum().sum()),
        "完整行比例": f"{round((1 - df.isna().any(axis=1).sum() / len(df)) * 100, 1)}%",
    }
    charts.insert(0, {
        "type": "overview",
        "title": "数据概览",
        "data": overview,
    })

    return charts


def _run_kmeans(df: pd.DataFrame, n_clusters: int = 4, feature_cols: Optional[list[str]] = None) -> dict:
    """运行 KMeans 聚类"""
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if feature_cols:
        numeric_cols = [c for c in feature_cols if c in numeric_cols]
    if not numeric_cols:
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()[:5]

    # 限制特征数量
    use_cols = numeric_cols[:min(len(numeric_cols), 8)]

    X = df[use_cols].fillna(df[use_cols].median()).values
    X_scaled = StandardScaler().fit_transform(X)
    n = min(n_clusters, max(2, int(len(df) ** 0.3)))

    km = KMeans(n_clusters=n, random_state=42, n_init=10)
    labels = km.fit_predict(X_scaled)

    # 计算每个簇的统计
    cluster_stats = []
    df_labeled = df.copy()
    df_labeled["_cluster"] = labels
    for i in range(n):
        cluster_data = df_labeled[df_labeled["_cluster"] == i]
        stats = {"cluster_id": i, "count": len(cluster_data), "percentage": f"{round(len(cluster_data)/len(df)*100, 1)}%"}
        for c in use_cols[:5]:
            stats[f"avg_{c}"] = round(float(cluster_data[c].mean()), 2)
        cluster_stats.append(stats)

    # 聚类中心分布（用于雷达图）
    centers = km.cluster_centers_
    radar_data = {}
    for i in range(n):
        radar_data[f"Cluster {i}"] = [round(float(v), 4) for v in centers[i].tolist()]

    return {
        "method": "KMeans",
        "n_clusters": n,
        "features": use_cols,
        "inertia": round(float(km.inertia_), 2),
        "cluster_stats": cluster_stats,
        "radar_data": radar_data,
        "labels": labels.tolist(),
    }


def _run_xgboost(df: pd.DataFrame, target_col: str, feature_cols: Optional[list[str]] = None) -> dict:
    """运行 XGBoost 分类/回归"""
    try:
        import xgboost as xgb
    except ImportError:
        return {"method": "XGBoost", "error": "xgboost 未安装"}

    if target_col not in df.columns:
        return {"method": "XGBoost", "error": f"目标列 '{target_col}' 不存在"}

    y_raw = df[target_col].dropna()
    df_clean = df.loc[y_raw.index]

    numeric_cols = df_clean.select_dtypes(include=[np.number]).columns.tolist()
    numeric_cols = [c for c in numeric_cols if c != target_col]

    if feature_cols:
        numeric_cols = [c for c in feature_cols if c in numeric_cols]
    if not numeric_cols:
        return {"method": "XGBoost", "error": "无可用数值特征列"}

    use_cols = numeric_cols[:min(len(numeric_cols), 12)]
    X = df_clean[use_cols].fillna(df_clean[use_cols].median()).values
    y = y_raw.values

    # 判断分类还是回归
    if len(np.unique(y)) <= 20 and np.issubdtype(y.dtype, np.integer):
        # 分类任务
        le = LabelEncoder()
        y_enc = le.fit_transform(y)
        X_train, X_test, y_train, y_test = train_test_split(X, y_enc, test_size=0.2, random_state=42)
        model = xgb.XGBClassifier(n_estimators=100, max_depth=6, learning_rate=0.1, random_state=42, eval_metric="mlogloss")
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        acc = round(float(accuracy_score(y_test, y_pred)), 4)
        prec = round(float(precision_score(y_test, y_pred, average="weighted", zero_division=0)), 4)
        rec = round(float(recall_score(y_test, y_pred, average="weighted", zero_division=0)), 4)
        task_type = "classification"
    else:
        # 回归任务
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        model = xgb.XGBRegressor(n_estimators=100, max_depth=6, learning_rate=0.1, random_state=42)
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        from sklearn.metrics import r2_score, mean_absolute_error
        r2 = round(float(r2_score(y_test, y_pred)), 4)
        mae = round(float(mean_absolute_error(y_test, y_pred)), 2)
        acc = r2
        prec = mae
        rec = 0
        task_type = "regression"

    # 特征重要性
    importance = sorted(
        zip(use_cols, model.feature_importances_.tolist()),
        key=lambda x: x[1], reverse=True
    )[:10]

    return {
        "method": "XGBoost",
        "task_type": task_type,
        "target": target_col,
        "features": use_cols,
        "metrics": {"accuracy": acc, "precision": prec, "recall": rec},
        "feature_importance": [{"feature": f, "importance": round(float(imp), 4)} for f, imp in importance],
        "num_classes": int(len(np.unique(y))) if task_type == "classification" else None,
    }


def _run_isolation_forest(df: pd.DataFrame, contamination: float = 0.05, feature_cols: Optional[list[str]] = None) -> dict:
    """运行 Isolation Forest 异常检测"""
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if feature_cols:
        numeric_cols = [c for c in feature_cols if c in numeric_cols]
    if not numeric_cols:
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()[:5]

    use_cols = numeric_cols[:min(len(numeric_cols), 10)]
    X = df[use_cols].fillna(df[use_cols].median()).values

    if len(X) < 5:
        return {"method": "IsolationForest", "error": "数据太少，最少需要 5 行"}

    model = IsolationForest(
        n_estimators=200,
        contamination=min(contamination, 0.4),
        random_state=42,
    )
    labels = model.fit_predict(X)
    anomaly_count = int((labels == -1).sum())
    normal_count = int((labels == 1).sum())

    # 异常样本 vs 正常样本对比
    anomaly_idx = np.where(labels == -1)[0][:10].tolist()
    normal_idx = np.where(labels == 1)[0][:10].tolist()

    anomaly_samples = []
    for idx in anomaly_idx:
        row = df.iloc[idx]
        sample: dict[str, Any] = {"_index": int(idx)}
        for c in use_cols[:5]:
            val = row[c]
            if pd.isna(val):
                sample[c] = None
            elif isinstance(val, (np.integer,)):
                sample[c] = int(val)
            elif isinstance(val, (np.floating,)):
                sample[c] = float(round(val, 4))
            else:
                sample[c] = str(val)
        anomaly_samples.append(sample)

    return {
        "method": "IsolationForest",
        "features": list(use_cols),
        "anomaly_count": int(anomaly_count),
        "normal_count": int(normal_count),
        "anomaly_ratio": f"{round(anomaly_count / len(df) * 100, 2)}%",
        "anomaly_samples": anomaly_samples,
    }


@router.post("/run")
def run_analysis(req: AnalysisRequest):
    """运行自动分析和 ML 方法"""
    df, meta = _load_data(req.session_id)

    task_id = uuid.uuid4().hex[:10]
    results: dict[str, Any] = {"task_id": task_id, "session_id": req.session_id, "results": {}}

    for method in req.methods:
        try:
            if method == "auto_dashboard":
                results["results"]["dashboard"] = _auto_dashboard(df)

            elif method == "kmeans":
                results["results"]["kmeans"] = _run_kmeans(
                    df,
                    n_clusters=req.n_clusters or 4,
                    feature_cols=req.feature_columns,
                )

            elif method == "xgboost":
                if not req.target_column:
                    results["results"]["xgboost"] = {"method": "XGBoost", "error": "请指定目标列 (target_column)"}
                else:
                    results["results"]["xgboost"] = _run_xgboost(
                        df,
                        target_col=req.target_column,
                        feature_cols=req.feature_columns,
                    )

            elif method == "isolation_forest":
                results["results"]["isolation_forest"] = _run_isolation_forest(
                    df,
                    contamination=req.contamination or 0.05,
                    feature_cols=req.feature_columns,
                )
        except Exception as e:
            results["results"][method] = {"method": method, "error": str(e)}

    _analysis_cache[task_id] = results
    return results


@router.get("/results/{task_id}")
def get_results(task_id: str):
    """获取分析结果"""
    cached = _analysis_cache.get(task_id)
    if not cached:
        raise HTTPException(404, "分析结果不存在或已过期")
    return cached
