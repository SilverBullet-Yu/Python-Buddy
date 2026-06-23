"""
自适应难度调节工具
根据学生掌握度自动调整练习难度，实现因材施教。
"""
from typing import Any, cast
from langchain.tools import tool
from postgrest.exceptions import APIError
from storage.database.supabase_client import get_supabase_client


def _get_client():
    return get_supabase_client()


@tool
def get_difficulty_level(student_id: str, topic: str) -> str:
    """获取学生对某知识点的当前难度等级和建议。

    参数:
        student_id: 学生唯一标识
        topic: 知识点名称

    返回:
        难度等级（1-3）和出题建议
    """
    client = _get_client()
    try:
        resp = (
            client.table("student_progress")
            .select("mastery_level,difficulty_level,exercises_completed,exercises_correct")
            .eq("student_id", student_id)
            .eq("topic", topic)
            .maybe_single()
            .execute()
        )
    except APIError as e:
        return f"❌ 查询难度失败：{e.message}"

    if not resp or not resp.data:
        return (
            f"📐 学生 {student_id} 尚未学习「{topic}」，建议难度等级：1（入门）\n"
            f"出题建议：从最基础的概念理解题开始，用生活化场景。"
        )

    record = cast(dict[str, Any], resp.data)
    mastery = int(record["mastery_level"])
    current_level = int(record.get("difficulty_level", 1))
    completed = int(record["exercises_completed"])
    correct = int(record["exercises_correct"])

    # 自动计算推荐难度
    if mastery >= 85:
        recommended = min(3, current_level + 1)
    elif mastery >= 60:
        recommended = current_level
    else:
        recommended = max(1, current_level - 1)

    level_desc = {
        1: "入门 — 基础概念理解，单步操作，有明确提示",
        2: "进阶 — 组合多个概念，需要独立思考，减少提示",
        3: "挑战 — 综合应用，开放性问题，需要自己设计解法",
    }

    return (
        f"📐 学生 {student_id} 在「{topic}」的难度评估：\n"
        f"   掌握度：{mastery}/100\n"
        f"   当前难度：Lv.{current_level}\n"
        f"   推荐难度：Lv.{recommended}\n"
        f"   正确率：{correct}/{completed}\n"
        f"\n"
        f"📋 难度说明：\n"
        f"   Lv.1 {level_desc[1]}\n"
        f"   Lv.2 {level_desc[2]}\n"
        f"   Lv.3 {level_desc[3]}\n"
        f"\n"
        f"💡 本次出题建议：{level_desc[recommended]}"
    )


@tool
def update_difficulty_level(student_id: str, topic: str, new_level: int) -> str:
    """手动调整学生对某知识点的难度等级。

    参数:
        student_id: 学生唯一标识
        topic: 知识点名称
        new_level: 新难度等级（1-3）

    返回:
        更新结果
    """
    if new_level not in (1, 2, 3):
        return "❌ 难度等级只能是 1、2 或 3。"

    client = _get_client()
    try:
        resp = (
            client.table("student_progress")
            .select("id")
            .eq("student_id", student_id)
            .eq("topic", topic)
            .maybe_single()
            .execute()
        )
        if not resp or not resp.data:
            return f"❌ 学生 {student_id} 尚未学习「{topic}」，无法调整难度。"

        record = cast(dict[str, Any], resp.data)
        client.table("student_progress").update({
            "difficulty_level": new_level,
        }).eq("id", record["id"]).execute()

        level_names = {1: "入门", 2: "进阶", 3: "挑战"}
        return f"✅ 已将「{topic}」难度调整为 Lv.{new_level}（{level_names[new_level]}）"
    except APIError as e:
        return f"❌ 更新难度失败：{e.message}"
