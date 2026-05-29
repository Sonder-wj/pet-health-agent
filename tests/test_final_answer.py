from app.agent.tools.final_answer import final_answer


class TestFinalAnswer:
    def test_returns_markdown_response(self):
        result = final_answer.invoke({"message": "您的爱宠目前状况稳定"})
        assert result["response"] == "您的爱宠目前状况稳定"
        assert result["done"] is True

    def test_handles_empty_message(self):
        result = final_answer.invoke({"message": ""})
        assert result["response"] == ""
        assert result["done"] is True

    def test_handles_multiline_message(self):
        msg = "1. 居家护理建议\n2. 注意观察\n3. 及时就医"
        result = final_answer.invoke({"message": msg})
        assert msg in result["response"]
