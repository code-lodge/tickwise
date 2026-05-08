"""LLM prompt construction for activity classification.

`SYSTEM_PROMPT` is the unchanging persona/contract — both Anthropic and
OpenAI receive the same text. `build_user_prompt()` interpolates the
per-tick context (active app, redacted screen text, browser URL, project
list) into the message that's sent to the model.
"""

from __future__ import annotations

from dataclasses import dataclass

SYSTEM_PROMPT = """You are a time tracking classifier for a freelance software engineer.
Your job is to determine which project and task category the user is currently working on,
based on their screen context.

You will receive:
- The application name (process)
- The window title (may be partially redacted)
- Visible screen text (redacted for privacy — items like [EMAIL], [API_KEY], [PATH] are placeholders)
- Browser URL and page title (if available, may be redacted)

Respond with ONLY a JSON object, no other text:
{
    "project": "exact project name from the list, or null if unclear",
    "task": "one of the allowed task categories",
    "confidence": 0.0 to 1.0,
    "reasoning": "one sentence explaining your classification"
}

Rules:
- If the activity clearly matches a project, set confidence >= 0.8
- If it's ambiguous between projects, pick the most likely one with lower confidence
- If it doesn't match any project (e.g. personal browsing, system settings), set project to null
- Always assign a task category even if project is null
- Redacted placeholders like [EMAIL], [CODE_BLOCK] still provide structural hints — use them"""


@dataclass(frozen=True, slots=True)
class ClassificationContext:
    """Pre-redacted context for one classification call."""

    process_name: str
    redacted_title: str
    redacted_ocr_text: str
    redacted_url: str | None = None
    redacted_browser_title: str | None = None


@dataclass(frozen=True, slots=True)
class ProjectChoice:
    """A project the LLM may pick, with optional client name."""

    name: str
    client: str | None = None
    is_active: bool = True


def build_user_prompt(
    context: ClassificationContext,
    projects: list[ProjectChoice],
    task_categories: list[str],
    *,
    snippet_chars: int = 800,
) -> str:
    """Render the user-message string sent to the LLM."""
    project_list = (
        "\n".join(f"- {p.name}" + (f" (client: {p.client})" if p.client else "") for p in projects if p.is_active)
        or "- (no active projects yet)"
    )
    snippet = (context.redacted_ocr_text or "")[:snippet_chars]
    return (
        f"Active projects:\n{project_list}\n\n"
        f"Allowed task categories: {', '.join(task_categories) or '(none)'}\n\n"
        f"Current context:\n"
        f"- Application: {context.process_name or 'N/A'}\n"
        f"- Window title: {context.redacted_title or 'N/A'}\n"
        f"- Browser URL: {context.redacted_url or 'N/A'}\n"
        f"- Browser page title: {context.redacted_browser_title or 'N/A'}\n"
        f"- Visible text: {snippet}"
    )
