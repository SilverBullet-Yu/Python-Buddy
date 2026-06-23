"""
错题本工具
自动收集错题、支持错题回顾和定期复习推送。
"""
from typing import Any, Optional, cast
from langchain.tools import tool
from postgrest.exceptions import APIError
from storage.database.supabase_client import get_supabase_client


def _get_client():
    return get_supabase_client()


def _cast_records(data: Any) -> list[dict[str, Any]]:
    return cast(list[dict[str, Any]], data)


@tool
def record_wrong_answer(
    student_id: str,
    topic: str,
    question: str,
    student_code: str,
    error_info: str = "",
    correct_hint: str = "",
) -> str:
    """将做错的题目记录到错题本，用于后续复习。

    参数:
        student_id: 学生唯一标识
        topic: 知识点名称
        question: 题目内容
        student_code: 学生提交的错误代码
        error_info: 错误信息
        correct_hint: 正确思路提示

    返回:
        记录结果
    """
    client = _get_client()
    try:
        client.table("error_notebook").insert({
            "student_id": student_id,
            "topic": topic,
            "question": question,
            "student_code": student_code,
            "error_info": error_info or None,
            "correct_hint": correct_hint or None,
        }).execute()
        return f"📒 已记录错题「{question[:30]}...」到错题本，下次复习时会提醒你。"
    except APIError as e:
        return f"❌ 记录错题失败：{e.message}"


@tool
def get_wrong_answers(
    student_id: str,
    topic: Optional[str] = None,
    limit: int = 5,
) -> str:
    """查询学生的错题本，获取需要复习的错题。

    参数:
        student_id: 学生唯一标识
        topic: 可选，按知识点筛选
        limit: 返回数量，默认 5

    返回:
        错题列表
    """
    client = _get_client()
    try:
        query = (
            client.table("error_notebook")
            .select("*")
            .eq("student_id", student_id)
            .order("review_count", desc=False)
            .order("last_reviewed_at", desc=True)
            .limit(limit)
        )
        if topic:
            query = query.eq("topic", topic)
        response = query.execute()
    except APIError as e:
        return f"❌ 查询错题本失败：{e.message}"

    raw_data = response.data
    if not raw_data:
        topic_hint = f"「{topic}」" if topic else ""
        return f"🎉 学生 {student_id} 在{topic_hint}没有错题记录，继续保持！"

    records = _cast_records(raw_data)
    topic_cn_map: dict[str, str] = {
        "variables": "变量", "data_types": "数据类型", "control_flow": "条件判断",
        "functions": "函数", "loops": "循环", "lists": "列表",
        "dicts": "字典", "strings": "字符串", "input_output": "输入输出", "errors": "错误处理",
    }

    parts = [f"📒 学生 {student_id} 的错题本（共 {len(records)} 题需复习）：", ""]
    for i, r in enumerate(records, 1):
        topic_val: str = str(r["topic"])
        topic_cn = topic_cn_map.get(topic_val, topic_val)
        question: str = str(r["question"])
        review_count: int = int(r["review_count"])
        hint: str = str(r.get("correct_hint") or "暂无提示")
        parts.append(f"{i}. [{topic_cn}] {question[:60]}")
        parts.append(f"   错误代码：{str(r['student_code'])[:80]}")
        parts.append(f"   💡 提示：{hint[:80]}")
        parts.append(f"   📊 已复习 {review_count} 次")
        parts.append("")
    parts.append("💪 选一道试试重新写一遍？")
    return '\n'.join(parts)


@tool
def mark_error_reviewed(student_id: str, topic: str, question: str) -> str:
    """标记错题已被复习，更新复习次数和时间。

    参数:
        student_id: 学生唯一标识
        topic: 知识点名称
        question: 题目内容（用于匹配）

    返回:
        更新结果
    """
    client = _get_client()
    try:
        # Find the error record
        resp = (
            client.table("error_notebook")
            .select("id,review_count")
            .eq("student_id", student_id)
            .eq("topic", topic)
            .eq("question", question)
            .maybe_single()
            .execute()
        )
        if not resp or not resp.data:
            return "未找到对应错题记录。"

        record = cast(dict[str, Any], resp.data)
        new_count = int(record["review_count"]) + 1
        client.table("error_notebook").update({
            "review_count": new_count,
            "last_reviewed_at": "now()",
        }).eq("id", record["id"]).execute()

        if new_count >= 3:
            # 复习 3 次后可从错题本移除
            client.table("error_notebook").delete().eq("id", record["id"]).execute()
            return f"✅ 已复习 {new_count} 次，这道题从错题本毕业了！"
        return f"✅ 已复习 {new_count} 次，再复习 {3 - new_count} 次就能从错题本毕业。"
    except APIError as e:
        return f"❌ 更新错题状态失败：{e.message}"
