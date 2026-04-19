from agent_bench.suites import load_suite
from agent_bench.suites.coding import CodingSuite
from agent_bench.suites.reasoning import ReasoningSuite
from agent_bench.suites.tool_use import ToolUseSuite
from agent_bench.suites.writing import WritingSuite


def test_load_suite_returns_instance():
    assert isinstance(load_suite("reasoning"), ReasoningSuite)
    assert isinstance(load_suite("coding"), CodingSuite)
    assert isinstance(load_suite("writing"), WritingSuite)
    assert isinstance(load_suite("tool-use"), ToolUseSuite)


def test_reasoning_correct_answer_passes():
    suite = ReasoningSuite()
    task = next(t for t in suite.tasks() if t.id == "math-1")
    score = suite.score(task, "Work: 60/1.5 = 40.\nAnswer: 40 mph", [])
    assert score.passed
    assert score.accuracy == 1.0
    assert score.format_compliance == 1.0


def test_reasoning_wrong_answer_fails():
    suite = ReasoningSuite()
    task = next(t for t in suite.tasks() if t.id == "math-1")
    score = suite.score(task, "Answer: 45", [])
    assert not score.passed
    assert score.accuracy == 0.0


def test_reasoning_missing_format_penalized():
    suite = ReasoningSuite()
    task = next(t for t in suite.tasks() if t.id == "math-1")
    score = suite.score(task, "The answer is 40 mph.", [])
    # final-line fallback catches the answer; format compliance is what breaks.
    assert score.format_compliance == 0.0


def test_coding_suite_scores_passing_solution():
    suite = CodingSuite()
    task = next(t for t in suite.tasks() if t.id == "code-fizzbuzz")
    solution = (
        "```python\n"
        "def fizzbuzz(n):\n"
        "    out = []\n"
        "    for i in range(1, n + 1):\n"
        "        if i % 15 == 0: out.append('FizzBuzz')\n"
        "        elif i % 3 == 0: out.append('Fizz')\n"
        "        elif i % 5 == 0: out.append('Buzz')\n"
        "        else: out.append(str(i))\n"
        "    return out\n"
        "```"
    )
    score = suite.score(task, solution, [])
    assert score.passed
    assert score.accuracy == 1.0


def test_coding_suite_handles_broken_code():
    suite = CodingSuite()
    task = next(t for t in suite.tasks() if t.id == "code-fizzbuzz")
    # no function at all
    score = suite.score(task, "```python\nprint('hi')\n```", [])
    assert not score.passed
    assert score.accuracy == 0.0


def test_writing_bullets_strict_pass():
    suite = WritingSuite()
    task = next(t for t in suite.tasks() if t.id == "write-bullets-benefits-of-unit-testing")
    output = (
        "- Faster feedback on regressions\n"
        "- Acts as executable documentation for expected behavior\n"
        "- Encourages smaller, decoupled units that are easier to refactor\n"
        "- Lowers the cost of making infrastructure changes later\n"
        "- Provides a safety net when onboarding new contributors to the codebase\n"
    )
    score = suite.score(task, output, [])
    assert score.format_compliance == 1.0
    assert score.passed


def test_tool_use_scores_correct_call():
    suite = ToolUseSuite()
    task = next(t for t in suite.tasks() if t.id == "tool-weather-basic")
    tool_calls = [{"name": "get_weather", "arguments": {"city": "Paris", "unit": "celsius"}}]
    score = suite.score(task, "", tool_calls)
    assert score.passed
    assert score.accuracy == 1.0


def test_tool_use_missing_tool_fails():
    suite = ToolUseSuite()
    task = next(t for t in suite.tasks() if t.id == "tool-weather-basic")
    score = suite.score(task, "", [])
    assert not score.passed
    assert score.accuracy == 0.0
