"""
学习报告生成工具 — 使用 coze-coding-dev-sdk DocumentGenerationClient
为学生生成 PDF 格式的学习报告，包含学习进度、知识点掌握情况和练习记录。
"""

from langchain.tools import tool
from coze_coding_dev_sdk import DocumentGenerationClient, PDFConfig
from coze_coding_utils.runtime_ctx.context import new_context
from coze_coding_utils.log.write_log import request_context


@tool
def generate_learning_report(
    student_name: str,
    progress_summary: str,
    topic_details: str,
    exercise_stats: str,
    suggestions: str,
) -> str:
    """为学生生成一份 PDF 格式的 Python 学习报告。

    报告包含：学习进度总览、各知识点掌握情况、练习统计、个性化学习建议。

    参数：
        student_name: 学生姓名或昵称
        progress_summary: 学习进度总结（如"已学习 5 个知识点，完成 12 道练习"）
        topic_details: 各知识点详情（Markdown 格式，如表格列出知识点名称、掌握度、练习次数）
        exercise_stats: 练习统计（如"正确率 85%，共完成 20 题"）
        suggestions: 个性化学习建议（如"建议加强循环语句练习"）

    返回：
        生成的 PDF 报告下载链接（24 小时内有效）
    """
    ctx = request_context.get() or new_context(method="generate_learning_report")

    config = PDFConfig(page_size="A4")
    client = DocumentGenerationClient(pdf_config=config)

    markdown_content = f"""# 🐍 Python 学习报告

---

## 👤 学生信息

**姓名**：{student_name}

---

## 📊 学习进度总览

{progress_summary}

---

## 📚 知识点掌握详情

{topic_details}

---

## 📝 练习统计

{exercise_stats}

---

## 💡 个性化学习建议

{suggestions}

---

> 📅 报告生成时间：由系统自动生成
> 🎯 继续加油，编程之路每一步都算数！
"""

    try:
        url = client.create_pdf_from_markdown(markdown_content, "python_learning_report")
        return (
            f"✅ 学习报告已生成！\n"
            f"📄 PDF 下载链接：{url}\n"
            f"📌 链接 24 小时内有效，请及时下载保存。"
        )
    except Exception as e:
        return f"❌ 报告生成失败：{str(e)}\n请稍后重试。"
