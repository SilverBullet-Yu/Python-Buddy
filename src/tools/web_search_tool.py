"""
联网搜索工具 — 使用 coze-coding-dev-sdk SearchClient
为 Python 教学场景搜索相关资料、最新文档和编程资源。
"""

from langchain.tools import tool
from coze_coding_dev_sdk import SearchClient
from coze_coding_utils.runtime_ctx.context import new_context
from coze_coding_utils.log.write_log import request_context


@tool
def search_python_resources(query: str) -> str:
    """联网搜索 Python 编程相关资源，获取最新资料、教程和文档。

    适用场景：
    - 学生问到超出内置知识范围的问题
    - 查找 Python 官方文档或最新特性
    - 搜索编程练习题和示例代码
    - 获取 Python 社区最佳实践

    参数：
        query: 搜索关键词，建议使用中文描述。
               例如："Python for 循环用法示例"、"Python 列表和元组的区别"

    返回：
        搜索结果摘要（包含标题、来源和内容摘要）
    """
    ctx = request_context.get() or new_context(method="search_python_resources")

    client = SearchClient(ctx=ctx)

    try:
        response = client.web_search_with_summary(
            query=f"Python {query}",
            count=5,
        )

        if not response.web_items:
            return f"🔍 未找到与「{query}」相关的搜索结果，请尝试换个关键词。"

        result_parts = []
        if response.summary:
            result_parts.append(f"📋 **AI 摘要**：\n{response.summary}\n")

        result_parts.append(f"📎 **搜索结果**（共 {len(response.web_items)} 条）：\n")
        for i, item in enumerate(response.web_items, 1):
            title = item.title or "无标题"
            snippet = (item.snippet or "")[:200]
            site = item.site_name or "未知来源"
            result_parts.append(f"{i}. **{title}**\n   来源：{site}\n   摘要：{snippet}\n")

        return "\n".join(result_parts)

    except Exception as e:
        return f"❌ 搜索失败：{str(e)}\n请稍后重试。"
