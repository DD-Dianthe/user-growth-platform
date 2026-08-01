"""数据上传 & 自动分析 API

支持用户上传 CSV/Excel 文件，自动识别列类型，生成看板图表，运行自选 ML 方法。
"""

import uuid, json, os, tempfile
from datetime import datetime
from typing import Any

import pandas as pd
import numpy as np
from fastapi import APIRouter, UploadFile, File, HTTPException
from sqlalchemy import text

from app.database import engine
from app.core.session_state import set_session, get_session

router = APIRouter(prefix="/api/data", tags=["data"])

# 上传文件大小限制: 50MB
MAX_FILE_SIZE = 50 * 1024 * 1024


class NumpyEncoder(json.JSONEncoder):
    def default(self, obj: Any) -> Any:
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(round(obj, 4))
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, pd.Timestamp):
            return obj.isoformat()
        if pd.isna(obj):
            return None
        return super().default(obj)


def detect_column_type(series: pd.Series) -> dict:
    """自动识别单列的数据类型和统计信息"""
    dtype = str(series.dtype)
    null_count = int(series.isna().sum())
    unique_count = int(series.nunique())
    total = len(series)
    sample_values = series.dropna().head(5).tolist()

    info: dict[str, Any] = {
        "name": str(series.name),
        "dtype": dtype,
        "null_count": null_count,
        "unique_count": unique_count,
        "sample_values": sample_values,
        "null_ratio": round(null_count / total, 4) if total > 0 else 0,
    }

    if pd.api.types.is_numeric_dtype(series):
        info["category"] = "numeric"
        info["stats"] = {
            "min": float(round(series.min(), 2)) if not pd.isna(series.min()) else None,
            "max": float(round(series.max(), 2)) if not pd.isna(series.max()) else None,
            "mean": float(round(series.mean(), 2)) if not pd.isna(series.mean()) else None,
            "median": float(round(series.median(), 2)) if not pd.isna(series.median()) else None,
            "std": float(round(series.std(), 2)) if not pd.isna(series.std()) else None,
        }
    elif pd.api.types.is_datetime64_any_dtype(series):
        info["category"] = "datetime"
        info["stats"] = {
            "min": series.min().isoformat() if not pd.isna(series.min()) else None,
            "max": series.max().isoformat() if not pd.isna(series.max()) else None,
        }
    elif unique_count <= 30:
        info["category"] = "categorical"
        top_values = series.dropna().value_counts().head(10).to_dict()
        info["distribution"] = {str(k): int(v) for k, v in top_values.items()}
    else:
        info["category"] = "text"

    return info


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """上传 CSV 或 Excel 文件，自动识别列类型，返回 schema 信息"""
    # 校验文件类型
    filename = file.filename or "unknown"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ("csv", "xlsx", "xls"):
        raise HTTPException(400, f"不支持的文件格式: .{ext}，请上传 CSV 或 Excel 文件")

    # 读取文件内容
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(400, f"文件过大 (最大 50MB)")

    # 临时保存
    session_id = uuid.uuid4().hex[:12]
    tmp_dir = tempfile.mkdtemp(prefix="upload_")
    tmp_path = os.path.join(tmp_dir, f"data.{ext}")
    with open(tmp_path, "wb") as f:
        f.write(content)

    try:
        # pandas 解析
        if ext == "csv":
            df = pd.read_csv(tmp_path, encoding="utf-8", nrows=50000)
        else:
            df = pd.read_excel(tmp_path, nrows=50000, engine="openpyxl")

        # 限制行数
        if len(df) > 100000:
            raise HTTPException(400, f"数据行数过多: {len(df)} 行 (上限 10 万行)")

        if len(df) == 0:
            raise HTTPException(400, "上传的文件为空")

        # 自动检测列类型
        columns = [detect_column_type(df[col]) for col in df.columns]

        # 存入 SQLite 临时表
        table_name = f"upload_{session_id}"
        df.to_sql(table_name, engine, if_exists="replace", index=False)

        # 保存 session 元信息
        set_session(session_id, {
            "filename": filename,
            "rows": len(df),
            "columns": len(columns),
            "table_name": table_name,
            "columns_info": columns,
            "uploaded_at": datetime.now().isoformat(),
        })

        return {
            "session_id": session_id,
            "filename": filename,
            "rows": len(df),
            "columns": len(columns),
            "columns_info": columns,
        }

    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(500, f"文件解析失败: {str(e)}")
    finally:
        # 清理临时文件
        try:
            os.remove(tmp_path)
            os.rmdir(tmp_dir)
        except Exception:
            pass


@router.get("/{session_id}/preview")
def preview_data(session_id: str, limit: int = 50):
    """预览上传数据的前 N 行"""
    session = get_session(session_id)
    if not session:
        raise HTTPException(404, "Session 不存在或已过期")

    table_name = session["table_name"]
    df = pd.read_sql(f"SELECT * FROM {table_name} LIMIT {min(limit, 100)}", engine)
    rows = df.to_dict(orient="records")

    return {"session_id": session_id, "rows": rows, "total_rows": session["rows"]}


@router.get("/{session_id}/schema")
def get_schema(session_id: str):
    """获取已上传数据的 schema 信息"""
    session = get_session(session_id)
    if not session:
        raise HTTPException(404, "Session 不存在或已过期")
    return {"session_id": session_id, "columns_info": session["columns_info"]}
