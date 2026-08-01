"""共享状态管理 — 跨 router 共享上传 session 信息"""

_upload_sessions: dict[str, dict] = {}


def get_session(session_id: str) -> dict | None:
    return _upload_sessions.get(session_id)


def set_session(session_id: str, info: dict):
    _upload_sessions[session_id] = info
