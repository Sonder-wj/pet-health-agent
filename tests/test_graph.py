from app.agent.graph import MAX_ITERATIONS, _detect_loop, after_tools, after_triage, should_continue


class FakeToolMessage:
    def __init__(self, tool_calls=None):
        self.tool_calls = tool_calls or []


class FakeTextMessage:
    def __init__(self, content=""):
        self.tool_calls = None
        self.content = content


def _make_tool_msg(name):
    return FakeToolMessage([{"name": name}])


class TestLoopDetection:
    def test_no_loop_with_few_messages(self):
        assert _detect_loop([]) is False
        assert _detect_loop([FakeTextMessage()]) is False

    def test_no_loop_with_different_tools(self):
        messages = [
            _make_tool_msg("collect_symptoms"),
            _make_tool_msg("search_pet_knowledge"),
        ]
        assert _detect_loop(messages) is False

    def test_no_loop_with_text_between_tools(self):
        messages = [
            _make_tool_msg("collect_symptoms"),
            FakeTextMessage("回答"),
            _make_tool_msg("search_pet_knowledge"),
        ]
        # Loop detection only looks at consecutive tool calls from the end
        assert _detect_loop(messages) is False

    def test_detects_loop_with_consecutive_same_tool(self):
        messages = [
            _make_tool_msg("collect_symptoms"),
            _make_tool_msg("collect_symptoms"),
        ]
        assert _detect_loop(messages) is True

    def test_detects_loop_with_three_same_consecutive(self):
        # loop detection collects all consecutive tool calls from the end,
        # then checks if the last LOOP_DETECTION_WINDOW (2) are identical.
        # All 3 the same → last 2 are identical → loop detected.
        messages = [
            _make_tool_msg("search_pet_knowledge"),
            _make_tool_msg("search_pet_knowledge"),
            _make_tool_msg("search_pet_knowledge"),
        ]
        assert _detect_loop(messages) is True

    def test_no_loop_when_last_two_different(self):
        messages = [
            _make_tool_msg("collect_symptoms"),
            _make_tool_msg("search_pet_knowledge"),
            _make_tool_msg("medication_guide"),
        ]
        assert _detect_loop(messages) is False


class TestShouldContinue:
    def test_ends_when_final_response_present(self):
        state = {"messages": [], "final_response": "done", "iteration_count": 0}
        assert should_continue(state) == "end"

    def test_ends_when_awaiting_user_input(self):
        state = {"messages": [], "awaiting_user_input": True, "iteration_count": 0}
        assert should_continue(state) == "end"

    def test_ends_when_max_iterations_reached(self):
        state = {"messages": [], "iteration_count": MAX_ITERATIONS}
        assert should_continue(state) == "end"

    def test_ends_when_max_iterations_exceeded(self):
        state = {"messages": [], "iteration_count": MAX_ITERATIONS + 5}
        assert should_continue(state) == "end"

    def test_ends_when_last_message_has_no_tool_calls(self):
        state = {
            "messages": [FakeTextMessage("hello")],
            "iteration_count": 0,
        }
        assert should_continue(state) == "end"

    def test_ends_with_empty_messages(self):
        state = {"messages": [], "iteration_count": 0}
        assert should_continue(state) == "end"

    def test_continues_when_last_message_has_tool_calls(self):
        state = {
            "messages": [_make_tool_msg("collect_symptoms")],
            "iteration_count": 0,
        }
        assert should_continue(state) == "tools"


class TestAfterTriage:
    def test_er_now_routes_to_er_response(self):
        state = {"triage_level": "er_now"}
        assert after_triage(state) == "er_response"

    def test_schedule_visit_routes_to_agent(self):
        state = {"triage_level": "schedule_visit"}
        assert after_triage(state) == "agent"

    def test_home_care_routes_to_agent(self):
        state = {"triage_level": "home_care"}
        assert after_triage(state) == "agent"

    def test_no_triage_routes_to_agent(self):
        state = {}
        assert after_triage(state) == "agent"


class TestAfterTools:
    def test_waiting_for_user_input_ends_after_tools(self):
        state = {"awaiting_user_input": True}
        assert after_tools(state) == "end"

    def test_final_response_ends_after_tools(self):
        state = {"final_response": "done"}
        assert after_tools(state) == "end"

    def test_normal_flow_returns_to_agent(self):
        state = {"awaiting_user_input": False, "final_response": None}
        assert after_tools(state) == "agent"
