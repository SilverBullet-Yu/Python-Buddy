"""
对话历史与学习进度 API
提供前端所需的对话持久化、进度查询和代码执行接口
"""
import logging
from typing import Any, Optional, cast

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from postgrest.exceptions import APIError

from storage.database.supabase_client import get_supabase_client
from tools.python_executor import run_python_code

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["api"])


def _get_client():
    return get_supabase_client()


def _cast_records(data: Any) -> list[dict[str, Any]]:
    return cast(list[dict[str, Any]], data)


def _cast_record(data: Any) -> dict[str, Any]:
    return cast(dict[str, Any], data)


# ============ Request/Response Models ============

class SaveMessageRequest(BaseModel):
    student_id: str
    role: str  # "user" or "assistant"
    content: str


class ConversationItem(BaseModel):
    id: int
    student_id: str
    role: str
    content: str
    created_at: str


class ProgressItem(BaseModel):
    topic: str
    topic_cn: str
    mastery_level: int
    exercises_completed: int
    exercises_correct: int


class ProgressResponse(BaseModel):
    student_id: str
    overall_mastery: int
    total_exercises: int
    total_correct: int
    topics: list[ProgressItem]


# ============ Conversation History ============

@router.post("/conversations")
async def save_message(req: SaveMessageRequest):
    """保存一条对话消息"""
    client = _get_client()
    try:
        client.table("conversations").insert({
            "student_id": req.student_id,
            "role": req.role,
            "content": req.content,
        }).execute()
        return {"status": "ok"}
    except APIError as e:
        logger.error(f"Failed to save conversation: {e.message}")
        raise HTTPException(status_code=500, detail=f"保存对话失败: {e.message}")


@router.get("/conversations/{student_id}")
async def get_conversations(
    student_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    before_id: Optional[int] = Query(default=None, description="加载此 ID 之前的消息"),
):
    """获取学生的对话历史"""
    client = _get_client()
    try:
        query = (
            client.table("conversations")
            .select("*")
            .eq("student_id", student_id)
            .order("created_at", desc=True)
            .limit(limit)
        )
        if before_id:
            query = query.lt("id", before_id)
        response = query.execute()

        raw_data = response.data
        if not raw_data:
            return {"messages": [], "has_more": False}

        records = _cast_records(raw_data)
        # Return in chronological order (oldest first)
        records.reverse()
        messages = [
            {
                "id": r["id"],
                "role": r["role"],
                "content": r["content"],
                "created_at": str(r["created_at"]),
            }
            for r in records
        ]
        return {
            "messages": messages,
            "has_more": len(records) >= limit,
            "oldest_id": records[0]["id"] if records else None,
        }
    except APIError as e:
        logger.error(f"Failed to get conversations: {e.message}")
        raise HTTPException(status_code=500, detail=f"获取对话历史失败: {e.message}")


@router.delete("/conversations/{student_id}")
async def clear_conversations(student_id: str):
    """清空学生的对话历史"""
    client = _get_client()
    try:
        client.table("conversations").delete().eq("student_id", student_id).execute()
        return {"status": "ok", "message": "对话历史已清空"}
    except APIError as e:
        logger.error(f"Failed to clear conversations: {e.message}")
        raise HTTPException(status_code=500, detail=f"清空对话失败: {e.message}")


# ============ Learning Progress ============

TOPIC_CN_MAP: dict[str, str] = {
    "variables": "变量",
    "data_types": "数据类型",
    "control_flow": "条件判断",
    "functions": "函数",
    "loops": "循环",
    "lists": "列表",
    "dicts": "字典",
    "strings": "字符串",
    "input_output": "输入输出",
    "errors": "错误处理",
}


@router.get("/progress/{student_id}")
async def get_progress(student_id: str):
    """获取学生的学习进度（供前端侧边栏使用）"""
    client = _get_client()
    try:
        response = (
            client.table("student_progress")
            .select("*")
            .eq("student_id", student_id)
            .order("mastery_level", desc=True)
            .execute()
        )
    except APIError as e:
        logger.error(f"Failed to get progress: {e.message}")
        raise HTTPException(status_code=500, detail=f"获取进度失败: {e.message}")

    raw_data = response.data
    if not raw_data:
        return {
            "student_id": student_id,
            "overall_mastery": 0,
            "total_exercises": 0,
            "total_correct": 0,
            "topics": [],
        }

    progress_list = _cast_records(raw_data)
    total_exercises = sum(int(p["exercises_completed"]) for p in progress_list)
    total_correct = sum(int(p["exercises_correct"]) for p in progress_list)
    avg_mastery = int(sum(int(p["mastery_level"]) for p in progress_list) / len(progress_list)) if progress_list else 0

    topics = [
        {
            "topic": str(p["topic"]),
            "topic_cn": TOPIC_CN_MAP.get(str(p["topic"]), str(p["topic"])),
            "mastery_level": int(p["mastery_level"]),
            "exercises_completed": int(p["exercises_completed"]),
            "exercises_correct": int(p["exercises_correct"]),
        }
        for p in progress_list
    ]

    return {
        "student_id": student_id,
        "overall_mastery": avg_mastery,
        "total_exercises": total_exercises,
        "total_correct": total_correct,
        "topics": topics,
    }


# ============ Code Execution ============

class RunCodeRequest(BaseModel):
    code: str
    stdin_input: str = ""


class RunCodeResponse(BaseModel):
    success: bool
    output: str
    error: str
    friendly_error: str


@router.post("/run_code", response_model=RunCodeResponse)
async def run_code(req: RunCodeRequest):
    """安全执行 Python 代码（供前端代码块一键运行使用）"""
    result = run_python_code(req.code, req.stdin_input)
    return RunCodeResponse(
        success=result["success"],
        output=result["output"],
        error=result["error"],
        friendly_error=result["friendly_error"],
    )


# ============ Regenerate ============

class RegenerateRequest(BaseModel):
    student_id: str
    last_user_message: str


@router.post("/regenerate")
async def regenerate(req: RegenerateRequest):
    """删除最后一轮对话（用户消息 + AI 回复），返回被删除的用户消息供前端重新发送"""
    client = _get_client()
    try:
        # 找到该学生最近的两条消息（assistant + user），删除它们
        resp = (
            client.table("conversations")
            .select("id, role")
            .eq("student_id", req.student_id)
            .order("created_at", desc=True)
            .limit(2)
            .execute()
        )
        records = _cast_records(resp.data) if resp.data else []
        for r in records:
            client.table("conversations").delete().eq("id", r["id"]).execute()

        return {"status": "ok", "deleted_count": len(records)}
    except APIError as e:
        logger.error(f"Failed to regenerate: {e.message}")
        raise HTTPException(status_code=500, detail=f"重新生成失败: {e.message}")
