from agent_boundary_runtime.prompt_budget import enforce_prompt_budget, estimate_prompt_chars


def test_caps_and_drops_sections_until_under_budget() -> None:
    messages = [
        {"role": "system", "content": "system"},
        {
            "role": "user",
            "content": "\n\n".join(
                [
                    "[mode]\nanswer naturally",
                    "[style examples]\n" + ("example " * 500),
                    "[context]\n" + ("context " * 500),
                    "[task]\nPreserve this final instruction.",
                ]
            ),
        },
    ]

    out, report = enforce_prompt_budget(messages, mode="greeting", max_chars=900)

    assert estimate_prompt_chars(out) <= 900
    assert report["dropped_sections"] or report["capped_sections"]
    assert "Preserve this final instruction" in out[-1]["content"]


def test_leaves_small_prompt_unchanged() -> None:
    messages = [{"role": "system", "content": "s"}, {"role": "user", "content": "Hello\nAssistant:"}]

    out, report = enforce_prompt_budget(messages, mode="greeting", max_chars=900)

    assert out == messages
    assert report["before_chars"] == report["after_chars"]


def test_estimates_nested_content() -> None:
    messages = [{"role": "user", "content": [{"text": "hello"}, {"content": "world"}]}]

    assert estimate_prompt_chars(messages) >= len("hello world")
