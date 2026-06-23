"""
学习进度追踪工具
用于记录和查询学生的学习进度、练习记录，支持个性化学习路径推荐。
"""
from typing import Any, Optional, cast
from langchain.tools import tool
from postgrest.exceptions import APIError
from storage.database.supabase_client import get_supabase_client


def _get_client():
    """获取 Supabase 客户端（服务端操作，使用 service_role_key）"""
    return get_supabase_client()


def _cast_record(data: Any) -> dict[str, Any]:
    """将 Supabase 返回的单条记录转为 dict 类型"""
    return cast(dict[str, Any], data)


def _cast_records(data: Any) -> list[dict[str, Any]]:
    """将 Supabase 返回的多条记录转为 list[dict] 类型"""
    return cast(list[dict[str, Any]], data)


@tool
def record_exercise_result(
    student_id: str,
    topic: str,
    question: str,
    student_code: str,
    is_correct: bool,
    error_info: str = "",
    feedback: str = "",
) -> str:
    """记录学生的一次练习结果，并更新学习进度。
    
    参数:
        student_id: 学生唯一标识
        topic: 知识点名称，如 variables, data_types, control_flow, functions, lists, dicts, loops, strings
        question: 题目内容
        student_code: 学生提交的代码
        is_correct: 是否正确
        error_info: 错误信息（如果有）
        feedback: 教师反馈建议
    
    返回:
        记录结果和更新后的学习进度
    """
    client = _get_client()
    
    try:
        # 1. 插入练习记录
        record_data = {
            "student_id": student_id,
            "topic": topic,
            "question": question,
            "student_code": student_code,
            "is_correct": is_correct,
            "error_info": error_info if error_info else None,
            "feedback": feedback if feedback else None,
        }
        client.table("exercise_records").insert(record_data).execute()
    except APIError as e:
        return f"❌ 记录练习结果失败：{e.message}"

    try:
        # 2. 查询该学生该知识点的现有进度
        progress_resp = (
            client.table("student_progress")
            .select("*")
            .eq("student_id", student_id)
            .eq("topic", topic)
            .maybe_single()
            .execute()
        )

        if progress_resp is None or progress_resp.data is None:
            # 首次练习该知识点，创建进度记录
            initial_mastery = 80 if is_correct else 30
            progress_data = {
                "student_id": student_id,
                "topic": topic,
                "mastery_level": initial_mastery,
                "exercises_completed": 1,
                "exercises_correct": 1 if is_correct else 0,
            }
            client.table("student_progress").insert(progress_data).execute()
            new_mastery = initial_mastery
            total_completed = 1
            total_correct = 1 if is_correct else 0
        else:
            # 更新已有进度
            existing = _cast_record(progress_resp.data)
            total_completed = int(existing["exercises_completed"]) + 1
            total_correct = int(existing["exercises_correct"]) + (1 if is_correct else 0)
            # 掌握度计算：正确率 * 100，但加入平滑因子避免波动过大
            raw_mastery = int((total_correct / total_completed) * 100)
            # 平滑：新掌握度 = 旧掌握度 * 0.6 + 新计算 * 0.4
            old_mastery = int(existing["mastery_level"])
            new_mastery = int(old_mastery * 0.6 + raw_mastery * 0.4)
            new_mastery = max(0, min(100, new_mastery))

            client.table("student_progress").update({
                "mastery_level": new_mastery,
                "exercises_completed": total_completed,
                "exercises_correct": total_correct,
            }).eq("id", existing["id"]).execute()

    except APIError as e:
        return f"❌ 更新学习进度失败：{e.message}"

    # 3. 构建返回结果
    level_emoji = "🌟" if new_mastery >= 80 else ("👍" if new_mastery >= 50 else "📚")
    result_parts = [
        f"{'✅ 回答正确！' if is_correct else '❌ 回答有误，继续加油！'}",
        "",
        f"📊 知识点「{topic}」学习进度：",
        f"   {level_emoji} 掌握程度：{new_mastery}/100",
        f"   📝 已完成练习：{total_completed} 题",
        f"   ✔️ 正确率：{total_correct}/{total_completed} ({int(total_correct/total_completed*100)}%)",
    ]
    return '\n'.join(result_parts)


@tool
def get_learning_progress(student_id: str) -> str:
    """查询学生的学习进度，包括各知识点的掌握程度和练习统计。
    
    参数:
        student_id: 学生唯一标识
    
    返回:
        学生的学习进度概览
    """
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
        return f"❌ 查询学习进度失败：{e.message}"

    raw_data = response.data
    if not raw_data:
        return (
            f"📭 学生 {student_id} 还没有学习记录。\n"
            f"让我们开始第一个 Python 知识点吧！建议从「变量与数据类型」开始学习。"
        )

    progress_list = _cast_records(raw_data)
    total_exercises = sum(int(p["exercises_completed"]) for p in progress_list)
    total_correct = sum(int(p["exercises_correct"]) for p in progress_list)
    avg_mastery = int(sum(int(p["mastery_level"]) for p in progress_list) / len(progress_list)) if progress_list else 0

    # 知识点中文映射
    topic_names: dict[str, str] = {
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

    parts = [
        f"📊 学生 {student_id} 的学习报告",
        "",
        f"🎯 综合掌握程度：{avg_mastery}/100",
        f"📝 总练习量：{total_exercises} 题",
        f"✔️ 总正确率：{total_correct}/{total_exercises}" + (f" ({int(total_correct/total_exercises*100)}%)" if total_exercises > 0 else ""),
        "",
        "📋 各知识点详情：",
    ]

    for p in progress_list:
        topic_val: str = str(p["topic"])
        topic_cn = topic_names.get(topic_val, topic_val)
        completed: int = int(p["exercises_completed"])
        correct: int = int(p["exercises_correct"])
        mastery: int = int(p["mastery_level"])
        rate = int(correct / completed * 100) if completed > 0 else 0
        bar = _mastery_bar(mastery)
        parts.append(f"   {bar} {topic_cn}：{mastery}/100（{correct}/{completed} 正确）")

    # 推荐下一步学习方向
    weak_topics = [p for p in progress_list if int(p["mastery_level"]) < 60]
    if weak_topics:
        weak_names = [topic_names.get(str(p["topic"]), str(p["topic"])) for p in weak_topics[:3]]
        parts.append("")
        parts.append(f"💡 建议重点复习：{'、'.join(weak_names)}")

    studied_topics: set[str] = {str(p["topic"]) for p in progress_list}
    unstudied = set(topic_names.keys()) - studied_topics
    if unstudied:
        next_topics = [topic_names[t] for t in list(unstudied)[:3]]
        parts.append(f"📖 尚未学习的知识点：{'、'.join(next_topics)}")

    return '\n'.join(parts)


@tool
def get_exercise_history(student_id: str, topic: Optional[str] = None, limit: int = 10) -> str:
    """查询学生的练习历史记录，包括题目、代码和结果。
    
    参数:
        student_id: 学生唯一标识
        topic: 可选，按知识点筛选
        limit: 返回记录数，默认 10
    
    返回:
        练习历史记录
    """
    client = _get_client()

    try:
        query = (
            client.table("exercise_records")
            .select("*")
            .eq("student_id", student_id)
            .order("created_at", desc=True)
            .limit(limit)
        )
        if topic:
            query = query.eq("topic", topic)
        response = query.execute()
    except APIError as e:
        return f"❌ 查询练习历史失败：{e.message}"

    raw_data = response.data
    if not raw_data:
        topic_hint = f"「{topic}」" if topic else ""
        return f"📭 学生 {student_id} 在{topic_hint}还没有练习记录。"

    records = _cast_records(raw_data)
    topic_cn_map: dict[str, str] = {
        "variables": "变量", "data_types": "数据类型", "control_flow": "条件判断",
        "functions": "函数", "loops": "循环", "lists": "列表",
        "dicts": "字典", "strings": "字符串", "input_output": "输入输出", "errors": "错误处理",
    }

    parts = [f"📝 学生 {student_id} 最近 {len(records)} 条练习记录：", ""]
    for i, record in enumerate(records, 1):
        status = "✅" if record["is_correct"] else "❌"
        topic_val: str = str(record["topic"])
        topic_cn = topic_cn_map.get(topic_val, topic_val)
        question: str = str(record["question"])
        parts.append(f"{i}. {status} [{topic_cn}] {question[:50]}...")

    return '\n'.join(parts)


def _mastery_bar(level: int) -> str:
    """生成掌握程度进度条"""
    filled = level // 10
    empty = 10 - filled
    return f"[{'█' * filled}{'░' * empty}]"
