"""Writing suite: coherence heuristics + strict format compliance."""

from __future__ import annotations

import re

from agent_bench.suites.base import Score, Suite, Task


def _bullets_task(topic: str, n: int) -> Task:
    return Task(
        id=f"write-bullets-{topic.replace(' ', '-')}",
        system=(
            f"Write exactly {n} concise bullet points about the topic. "
            "Each bullet must begin with '- ' and be on its own line. "
            "Do not add a title, intro, or closing line. Bullets only."
        ),
        prompt=f"Topic: {topic}",
        expected={"format": "bullets", "n": n},
        max_tokens=400,
        meta={"type": "writing"},
    )


def _paragraph_task(topic: str, min_words: int, max_words: int) -> Task:
    return Task(
        id=f"write-paragraph-{topic.replace(' ', '-')}",
        system=(
            f"Write a single coherent paragraph of {min_words}-{max_words} words on the topic. "
            "Output only the paragraph — no heading, no bullets, no quotes."
        ),
        prompt=f"Topic: {topic}",
        expected={"format": "paragraph", "min": min_words, "max": max_words},
        max_tokens=400,
        meta={"type": "writing"},
    )


_TASKS: list[Task] = [
    _bullets_task("benefits of unit testing", 5),
    _bullets_task("tips for writing clear commit messages", 4),
    _paragraph_task("why developers should learn to read tracebacks", 60, 120),
    _paragraph_task("the trade-offs of microservices versus monoliths", 80, 140),
]


_BULLET_LINE_RE = re.compile(r"^\s*[-*]\s+\S")


def _check_bullets(output: str, n: int) -> tuple[bool, float]:
    lines = [ln for ln in output.strip().splitlines() if ln.strip()]
    bullet_lines = [ln for ln in lines if _BULLET_LINE_RE.match(ln)]
    strict = len(lines) == n and len(bullet_lines) == n
    # partial credit if the bullet count is right even if extra lines are present
    partial = 1.0 if strict else (0.5 if len(bullet_lines) == n else 0.0)
    return strict, partial


def _check_paragraph(output: str, min_w: int, max_w: int) -> tuple[bool, float]:
    text = output.strip()
    lines = [ln for ln in text.splitlines() if ln.strip()]
    # a single paragraph is a single non-empty line (no blank lines splitting it)
    single = len(lines) == 1
    words = len(re.findall(r"\S+", text))
    within = min_w <= words <= max_w
    strict = single and within
    partial = 1.0 if strict else (0.5 if within else 0.0)
    return strict, partial


def _coherence(output: str) -> float:
    """Crude coherence proxy: length in a reasonable range and low trigram repetition."""
    words = re.findall(r"[A-Za-z']+", output.lower())
    if len(words) < 20:
        return 0.3
    trigrams = [tuple(words[i : i + 3]) for i in range(len(words) - 2)]
    if not trigrams:
        return 0.3
    unique_ratio = len(set(trigrams)) / len(trigrams)
    # map [0.5, 1.0] → [0, 1]; anything below 0.5 is very repetitive.
    return max(0.0, min(1.0, (unique_ratio - 0.5) * 2))


class WritingSuite(Suite):
    name = "writing"

    def tasks(self) -> list[Task]:
        return list(_TASKS)

    def score(self, task: Task, output: str, tool_calls: list[dict]) -> Score:
        fmt = task.expected["format"]
        if fmt == "bullets":
            strict, partial = _check_bullets(output, task.expected["n"])
        elif fmt == "paragraph":
            strict, partial = _check_paragraph(
                output, task.expected["min"], task.expected["max"]
            )
        else:
            strict, partial = False, 0.0
        coherence = _coherence(output)
        accuracy = 0.5 * partial + 0.5 * coherence
        return Score(
            accuracy=round(accuracy, 3),
            format_compliance=1.0 if strict else partial,
            passed=strict and coherence >= 0.5,
            detail=f"format_partial={partial:.2f} coherence={coherence:.2f}",
        )
