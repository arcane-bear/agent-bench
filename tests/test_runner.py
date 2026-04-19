import json

from agent_bench.core import BenchmarkRunner, RunResult
from agent_bench.reports import (
    render_markdown,
    render_terminal,
    write_csv,
    write_html,
    write_markdown,
)
from agent_bench.suites.reasoning import ReasoningSuite
from tests.fake_provider import FakeProvider


def test_runner_end_to_end_reasoning_pass(tmp_path):
    # a responder that looks up the expected answer from the task prompt keyword set
    def responder(prompt: str) -> str:
        answers = {
            "60 miles": "40",
            "3x + 7": "5",
            "12 * 11": "80",
            "bloops": "yes",
            "Alice is taller": "Carol",
            "ducks and cows": "5",
        }
        for key, answer in answers.items():
            if key in prompt:
                return f"Reasoning...\nAnswer: {answer}"
        return "Answer: unknown"

    runner = BenchmarkRunner(
        providers=[FakeProvider(model="fake-pass", responder=responder)],
        suites=[ReasoningSuite()],
    )
    result = runner.run()
    assert result.duration_s >= 0
    assert len(result.tasks) == len(ReasoningSuite().tasks())
    assert all(t.passed for t in result.tasks)

    path = tmp_path / "results.json"
    result.save(path)
    data = json.loads(path.read_text())
    assert data["tasks"][0]["metrics"]["accuracy"] == 1.0


def test_runner_wrong_answers_fail():
    runner = BenchmarkRunner(
        providers=[FakeProvider(responder="Answer: wrong")],
        suites=[ReasoningSuite()],
    )
    result = runner.run()
    assert all(not t.passed for t in result.tasks)


def test_reports_render_from_run(tmp_path):
    runner = BenchmarkRunner(
        providers=[FakeProvider(responder="Answer: 40")],
        suites=[ReasoningSuite()],
    )
    result = runner.run()
    path = tmp_path / "r.json"
    result.save(path)
    data = RunResult.load(path)

    # markdown
    md = render_markdown(data)
    assert "agent-bench" in md
    assert "| fake |" in md

    write_markdown(data, tmp_path / "r.md")
    assert (tmp_path / "r.md").read_text().startswith("# agent-bench")

    write_csv(data, tmp_path / "r.csv")
    csv_text = (tmp_path / "r.csv").read_text()
    assert "suite,task_id,provider" in csv_text

    write_html(data, tmp_path / "r.html")
    html = (tmp_path / "r.html").read_text()
    assert "<canvas id=\"c-radar\"" in html
    assert "Chart(" in html

    # terminal — just make sure it doesn't raise
    render_terminal(data)


def test_custom_yaml_suite(tmp_path):
    from agent_bench.custom import load_custom_suite

    yaml_path = tmp_path / "c.yaml"
    yaml_path.write_text(
        """
name: toy
tasks:
  - id: hi
    prompt: "say hi"
    expected:
      contains: "hello"
"""
    )
    suite = load_custom_suite(yaml_path)
    task = suite.tasks()[0]
    good = suite.score(task, "hello there", [])
    bad = suite.score(task, "nope", [])
    assert good.passed
    assert not bad.passed
