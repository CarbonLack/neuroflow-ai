from neuroflow.ai_presentation import (
    build_readable_ai_view,
    full_response_html,
    readable_view_html,
)


def test_compact_view_prioritizes_conclusion_action_and_next_step():
    answer = """结论：当前数据已经完成原始质控，可以进入预处理。

我读取了项目摘要、坏通道统计和最近一次质控结果。
下一步：先确认 2 个疑似坏通道，再运行预处理预览。
技术细节：这里还有一段很长的参数解释，不应默认挤满聊天窗口。"""
    view = build_readable_ai_view(
        answer,
        warnings=["2 个通道仍需人工确认。"],
        suggested_next_stage="preprocess",
        query_evidence=[{"evidence_id": "Q-1"}, {"evidence_id": "Q-2"}],
        language="zh_CN",
    )

    assert view.conclusion.startswith("结论")
    assert "2 项证据" in view.activity
    assert view.next_step.startswith("下一步")
    assert "人工确认" in view.warning
    assert view.has_details is True


def test_compact_html_links_to_preserved_detail():
    view = build_readable_ai_view(
        "Conclusion: QC passed.\nNext: review the flagged channel.\n" + "detail " * 90,
        language="en_US",
    )
    html = readable_view_html(
        view,
        detail_url="neuroephys://ai-detail/4",
        language="en_US",
    )

    assert "View full answer and evidence" in html
    assert "neuroephys://ai-detail/4" in html


def test_full_detail_keeps_scientific_limits_and_proposals():
    html = full_response_html(
        {
            "answer": "The effect is associated with the event.",
            "warnings": ["This is not causal evidence."],
            "scientific_interpretation": {
                "limitations": ["Only one session was analysed."],
            },
            "tool_calls": [
                {"name": "run_raw_qc", "reason": "Confirm signal quality."}
            ],
            "query_evidence": [{"evidence_id": "Q-7"}],
        },
        "en_US",
    )

    assert "This is not causal evidence" in html
    assert "Only one session" in html
    assert "not yet run" in html
    assert "Q-7" in html
