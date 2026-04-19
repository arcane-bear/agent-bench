# agent-bench

[![CI](https://github.com/arcane-bear/agent-bench/actions/workflows/ci.yml/badge.svg)](https://github.com/arcane-bear/agent-bench/actions/workflows/ci.yml)
[![PyPI - Python Version](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Benchmark LLM agents across providers on speed, cost, and quality — and get an honest report card.**

Most LLM "evals" focus on one axis: cost, or latency, or a single accuracy number.
`agent-bench` runs the same standardized tasks against multiple providers and reports all three, side by side, with charts.

> If you're looking for cost-only tracking, `agent-cost-cli` is the right tool. `agent-bench` is complementary — it measures actual answer **quality** and end-to-end **speed** on top of cost.

Built by [Rapid Claw](https://rapidclaw.dev) — deploy and benchmark AI agents in production.

---

## What it does

- Runs **standardized benchmark suites** against any combination of LLM providers.
- Collects **latency (TTFT, total), throughput (tokens/sec), cost per task, accuracy, and format compliance**.
- Produces a **report card** as a terminal table, Markdown, CSV, or a self-contained HTML page with bar and radar charts.
- Lets you **define your own benchmark tasks** in a short YAML file.

### Built-in suites

| Suite        | What it measures                                                       |
| ------------ | ---------------------------------------------------------------------- |
| `reasoning`  | Math + logic problems with short final answers. Exact-match grading.   |
| `coding`     | Generates a Python function, extracts it, and verifies against tests.  |
| `writing`    | Coherence heuristics + strict format compliance (bullet counts, length). |
| `tool-use`   | Function-calling accuracy — did the model pick the right tool & args?  |

### Supported providers

| Provider     | Install extra               | Auth                     |
| ------------ | --------------------------- | ------------------------ |
| OpenAI       | `agent-bench[openai]`       | `OPENAI_API_KEY`         |
| Anthropic    | `agent-bench[anthropic]`    | `ANTHROPIC_API_KEY`      |
| Google Gemini| `agent-bench[gemini]`       | `GOOGLE_API_KEY`         |
| Ollama (local)| `agent-bench[ollama]`      | none (local daemon)      |

Each SDK is imported lazily, so you only install what you use.

---

## Install

```bash
# core + all providers
pip install 'agent-bench[all]'

# or pick and choose
pip install 'agent-bench[openai,anthropic]'
```

From source:

```bash
git clone https://github.com/arcane-bear/agent-bench
cd agent-bench
pip install -e '.[dev,all]'
```

---

## Quickstart

```bash
# run reasoning + coding against two providers, write HTML + MD reports
export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-ant-...

agent-bench run \
  --providers openai,anthropic \
  --suite reasoning --suite coding \
  --output results.json \
  --html report.html \
  --md report.md
```

Pin specific models with `provider:model` syntax:

```bash
agent-bench run \
  --providers 'openai:gpt-4o-mini,anthropic:claude-haiku-4-5,gemini:gemini-1.5-flash,ollama:llama3.2' \
  --suite reasoning
```

Regenerate reports later without re-running:

```bash
agent-bench report results.json --html report.html --md report.md --csv rows.csv
```

List built-in suites:

```bash
agent-bench list-suites
```

---

## Example output

Terminal:

```
                         agent-bench — report card
┏━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━┳━━━━━┓
┃ Provider   ┃ Model               ┃    Pass ┃ Accuracy ┃ Format ┃ TTFT (s) ┃ Total (s) ┃ tok/s ┃ Cost ($) ┃ Err ┃
┡━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━╇━━━━━┩
│ anthropic  │ claude-haiku-4-5    │  8/9 (89%) │  0.91 │  1.00 │  0.34 │   2.10 │  85.2 │  0.0041 │   0 │
│ openai     │ gpt-4o-mini         │  7/9 (78%) │  0.83 │  0.94 │  0.21 │   1.75 │ 110.4 │  0.0008 │   0 │
│ gemini     │ gemini-1.5-flash    │  6/9 (67%) │  0.74 │  0.89 │  0.29 │   1.62 │ 120.9 │  0.0004 │   0 │
│ ollama     │ llama3.2            │  4/9 (44%) │  0.52 │  0.78 │  0.05 │   4.90 │  28.7 │  0.0000 │   0 │
└────────────┴─────────────────────┴─────────┴──────────┴────────┴──────────┴───────────┴───────┴──────────┴─────┘
```

HTML report (written by `--html report.html`) shows:

- Overall table (same data as terminal).
- Bar charts: accuracy, latency, throughput, and total cost per provider.
- A radar chart plotting each provider's accuracy profile across all suites — great for spotting "good at reasoning, weak at tool-use" patterns at a glance.

Markdown report (`--md report.md`) is the same table, plus a per-suite accuracy breakdown, which pastes cleanly into GitHub issues or PRs.

---

## Custom benchmark suites

Drop a YAML file anywhere and point `--custom` at it:

```yaml
# examples/custom_suite.yaml
name: my-team-evals
tasks:
  - id: capital-france
    system: "Answer with just the city name."
    prompt: "What is the capital of France?"
    expected:
      contains: "paris"
    max_tokens: 32

  - id: json-output
    system: "Respond with a JSON object only."
    prompt: 'Return {"status": "ok", "version": 1} exactly.'
    expected:
      regex: '"status"\s*:\s*"ok"'
      format_regex: '^\{'
    max_tokens: 64
```

Then:

```bash
agent-bench run \
  --providers openai,anthropic \
  --custom examples/custom_suite.yaml \
  --html report.html
```

Supported `expected` checks:

| Key             | Meaning                                                      |
| --------------- | ------------------------------------------------------------ |
| `contains`      | Substring must appear in the output (case-insensitive).      |
| `equals`        | Whole output must equal the value (whitespace-normalized).   |
| `regex`         | Regex must match somewhere in the output.                    |
| `format_regex`  | Regex presence → contributes to **format compliance** score. |

---

## Use from Python

```python
from agent_bench import BenchmarkRunner
from agent_bench.providers import load_provider
from agent_bench.suites import load_suite
from agent_bench.reports import write_html

runner = BenchmarkRunner(
    providers=[load_provider("openai:gpt-4o-mini"), load_provider("anthropic")],
    suites=[load_suite("reasoning"), load_suite("coding")],
)
result = runner.run()
result.save("results.json")

import json
write_html(json.load(open("results.json")), "report.html")
```

---

## Metrics, defined

| Metric                | How it's measured                                                     |
| --------------------- | --------------------------------------------------------------------- |
| **TTFT** (s)          | Wall clock from request start to first streamed token.                |
| **Total** (s)         | Wall clock for the full completion, including stream close.           |
| **tokens/sec**        | `completion_tokens / total_s`.                                        |
| **cost (USD)**        | Provider-reported token counts × a small built-in pricing table.     |
| **accuracy**          | Per-suite check — exact-match, unit-test pass rate, or regex match.   |
| **format compliance** | Suite-specific: did output match the required shape (e.g. `Answer:`)?|

Pricing lives in [`src/agent_bench/metrics.py`](src/agent_bench/metrics.py) — update it as vendors change prices.

---

## Development

```bash
pip install -e '.[dev]'
pytest
ruff check src tests
```

Tests use a `FakeProvider` so the full pipeline (runner → scoring → reports) is exercised without hitting any real APIs.

---

## Learn More

Learn more about [LLM performance benchmarking](https://rapidclaw.dev/blog/how-to-understand-performance-tests) on the Rapid Claw blog.

Visit [rapidclaw.dev](https://rapidclaw.dev) for the full suite of AI agent deployment tools.

## License

MIT — see [LICENSE](LICENSE).
