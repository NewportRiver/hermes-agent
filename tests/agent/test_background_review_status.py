from agent.background_review import summarize_background_review_actions


def test_summary_prefers_structured_skill_status():
    review_messages = [
        {"role": "assistant", "tool_calls": [{"id": "1", "function": {"name": "skill_manage", "arguments": '{"action":"create","name":"x"}'}}]},
        {"role": "tool", "tool_call_id": "1", "content": '{"success": true, "status": "CREATED_TRANSIENTLY", "message": "Skill \'x\' created.", "discovery_result": "FAIL"}'}
    ]
    summary = summarize_background_review_actions(review_messages, [], notification_mode="on")
    assert summary == ["Skill created transiently"]


def test_summary_reports_no_change_structurally():
    review_messages = [
        {"role": "assistant", "tool_calls": [{"id": "1", "function": {"name": "skill_manage", "arguments": '{"action":"edit","name":"x"}'}}]},
        {"role": "tool", "tool_call_id": "1", "content": '{"success": true, "status": "NO_CHANGE", "message": "No changes needed."}'}
    ]
    summary = summarize_background_review_actions(review_messages, [], notification_mode="on")
    assert summary == ["Skill no change"]
