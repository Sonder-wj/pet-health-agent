from langchain_core.tools import tool


@tool
def final_answer(message: str) -> dict:
    """当信息充足、不需要再调用其他工具时，向用户输出最终回复。

    Args:
        message: 要发送给用户的最终回复文本。包含所有建议、分析和安抚信息。
    """
    return {"response": message, "done": True}
