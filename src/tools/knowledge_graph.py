"""
知识图谱工具
定义 Python 知识点之间的前置依赖关系，支持前置检查和学习路径推荐。
"""
from typing import Any, cast
from langchain.tools import tool
from postgrest.exceptions import APIError
from storage.database.supabase_client import get_supabase_client


# 知识点依赖图谱：key → 需要先掌握的前置知识点
KNOWLEDGE_GRAPH: dict[str, list[str]] = {
    "variables": [],                          # 变量：无前置
    "data_types": ["variables"],              # 数据类型：需要先懂变量
    "input_output": ["variables"],            # 输入输出：需要先懂变量
    "strings": ["variables", "data_types"],   # 字符串：需要变量和数据类型
    "control_flow": ["variables", "data_types"],  # 条件判断：需要变量和比较
    "loops": ["control_flow"],                # 循环：需要先懂条件判断
    "lists": ["variables", "loops"],          # 列表：需要变量和循环
    "dicts": ["lists"],                       # 字典：需要先懂列表
    "functions": ["variables", "control_flow", "loops"],  # 函数：综合前置
    "errors": ["control_flow", "functions"],  # 错误处理：需要条件和函数
}

TOPIC_NAMES: dict[str, str] = {
    "variables": "变量",
    "data_types": "数据类型",
    "input_output": "输入输出",
    "strings": "字符串操作",
    "control_flow": "条件判断",
    "loops": "循环",
    "lists": "列表",
    "dicts": "字典",
    "functions": "函数",
    "errors": "错误处理",
}


def _get_client():
    return get_supabase_client()


@tool
def check_prerequisites(student_id: str, topic: str) -> str:
    """检查学生学习某知识点前是否已掌握所有前置知识。

    参数:
        student_id: 学生唯一标识
        topic: 要检查的知识点名称

    返回:
        前置检查结果，包括已掌握和未掌握的前置知识点
    """
    prerequisites = KNOWLEDGE_GRAPH.get(topic)
    topic_cn = TOPIC_NAMES.get(topic, topic)

    if prerequisites is None:
        return f"❌ 未知知识点「{topic}」，支持的知识点：{', '.join(KNOWLEDGE_GRAPH.keys())}"

    if not prerequisites:
        return f"✅ 「{topic_cn}」没有前置依赖，可以直接开始学习。"

    client = _get_client()
    try:
        resp = (
            client.table("student_progress")
            .select("topic,mastery_level")
            .eq("student_id", student_id)
            .in_("topic", prerequisites)
            .execute()
        )
    except APIError as e:
        return f"❌ 查询前置知识失败：{e.message}"

    studied = {}
    if resp and resp.data:
        for r in cast(list[dict[str, Any]], resp.data):
            studied[str(r["topic"])] = int(r["mastery_level"])

    mastered = []
    not_mastered = []
    not_studied = []

    for prereq in prerequisites:
        prereq_cn = TOPIC_NAMES.get(prereq, prereq)
        if prereq not in studied:
            not_studied.append(f"{prereq_cn}（{prereq}）")
        elif studied[prereq] < 50:
            not_mastered.append(f"{prereq_cn}（{prereq}）— 掌握度 {studied[prereq]}/100")
        else:
            mastered.append(f"{prereq_cn}（{prereq}）— 掌握度 {studied[prereq]}/100")

    parts = [f"🔍 「{topic_cn}」前置知识检查：", ""]

    if mastered:
        parts.append(f"✅ 已掌握：{'、'.join(mastered)}")

    if not_mastered:
        parts.append(f"⚠️ 掌握不足：{'、'.join(not_mastered)}")

    if not_studied:
        parts.append(f"❌ 尚未学习：{'、'.join(not_studied)}")

    if not_mastered or not_studied:
        parts.append("")
        parts.append(f"💡 建议先补上未掌握的前置知识，再学习「{topic_cn}」。")
        all_missing = [p.split("（")[0] for p in not_studied + not_mastered]
        parts.append(f"📖 推荐学习顺序：{' → '.join(all_missing)} → {topic_cn}")
    else:
        parts.append("")
        parts.append(f"✅ 前置知识全部达标，可以开始学习「{topic_cn}」！")

    return '\n'.join(parts)


@tool
def get_learning_path(student_id: str) -> str:
    """为学生生成个性化学习路径，基于已掌握知识和依赖关系推荐下一步。

    参数:
        student_id: 学生唯一标识

    返回:
        推荐的学习路径
    """
    client = _get_client()
    try:
        resp = (
            client.table("student_progress")
            .select("topic,mastery_level")
            .eq("student_id", student_id)
            .execute()
        )
    except APIError as e:
        return f"❌ 查询学习进度失败：{e.message}"

    studied: dict[str, int] = {}
    if resp and resp.data:
        for r in cast(list[dict[str, Any]], resp.data):
            studied[str(r["topic"])] = int(r["mastery_level"])

    ready_to_learn = []
    need_review = []
    blocked = []

    for topic, prereqs in KNOWLEDGE_GRAPH.items():
        topic_cn = TOPIC_NAMES.get(topic, topic)
        if topic in studied:
            if studied[topic] < 50:
                need_review.append((topic, topic_cn, studied[topic]))
            continue

        if not prereqs:
            ready_to_learn.append((topic, topic_cn, 0))
        else:
            all_mastered = all(
                studied.get(p, 0) >= 50 for p in prereqs
            )
            if all_mastered:
                ready_to_learn.append((topic, topic_cn, len(prereqs)))
            else:
                missing = [TOPIC_NAMES.get(p, p) for p in prereqs if studied.get(p, 0) < 50]
                blocked.append((topic, topic_cn, missing))

    parts = [f"🗺️ 学生 {student_id} 的个性化学习路径：", ""]

    if not studied:
        parts.append("🎬 尚未开始学习，建议从最基础开始：")
        parts.append("   1. 变量（variables）— 编程的起点")
        parts.append("   2. 数据类型（data_types）— 认识不同的数据")
        parts.append("   3. 输入输出（input_output）— 让程序和你对话")
        return '\n'.join(parts)

    if ready_to_learn:
        parts.append("📖 可以立即学习：")
        for topic, name, deps in ready_to_learn[:5]:
            tag = "🆕 零基础入口" if deps == 0 else f"📎 需 {deps} 个前置（已满足）"
            parts.append(f"   • {name}（{topic}）— {tag}")

    if need_review:
        parts.append("")
        parts.append("🔄 需要复习巩固：")
        for topic, name, mastery in need_review[:5]:
            parts.append(f"   • {name}（{topic}）— 掌握度 {mastery}/100")

    if blocked:
        parts.append("")
        parts.append("🔒 前置知识不足，暂不建议学习：")
        for topic, name, missing in blocked[:3]:
            parts.append(f"   • {name}（{topic}）— 需先学：{'、'.join(missing)}")

    if not ready_to_learn and not need_review:
        parts.append("🎉 所有知识点已掌握！可以尝试综合项目练习。")

    return '\n'.join(parts)
