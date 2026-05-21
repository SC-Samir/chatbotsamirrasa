from app.copilot.conversation.websocket_handler import WebSocketV2Handler


def test_rule_based_fallback_extracts_git_ref_with_on_branch_syntax():
    command, entities = WebSocketV2Handler._rule_based_fallback(
        "create and deploy samirtest3 to osc-fr1 with https://github.com/Scalingo/sample-go-gin on branch master"
    )

    assert command == "legacy.create_and_deploy"
    assert entities["app_name"] == "samirtest3"
    assert entities["region"] == "osc-fr1"
    assert entities["github_repo"] == "https://github.com/Scalingo/sample-go-gin"
    assert entities["git_ref"] == "master"


def test_extract_explicit_git_ref_handles_on_branch_phrase():
    assert (
        WebSocketV2Handler._extract_explicit_git_ref(
            "create and deploy samirtest3 to osc-fr1 with https://github.com/Scalingo/sample-go-gin on branch master"
        )
        == "master"
    )


def test_rule_based_fallback_matches_show_logs_command():
    command, entities = WebSocketV2Handler._rule_based_fallback("show logs of samirtest4 on osc-fr1")

    assert command == "legacy.show_logs"
    assert entities["app_name"] == "samirtest4"
    assert entities["region"] == "osc-fr1"
