from __future__ import annotations

import os
import re
from pathlib import Path

_CHAT_BACKEND_LINE_RE = re.compile(r"^chat_backend:.*$", re.MULTILINE)
_HOSTED_LLM_KEY_RE = re.compile(r"^api_key:\s*\"?([^\"\n]*)\"?\s*$")

_DEFAULT_MODEL = "claude-haiku-4-5"
_DEFAULT_MAX_TOKENS = 1024
_PLACEHOLDER_API_KEY = "changeme"


def _extract_hosted_llm_block(lines: list[str]) -> tuple[int, int, list[str]]:
    """Find the top-level `hosted_llm:` block (the key line plus every
    immediately-following indented line). Returns (start, end, block_lines) -
    `end` is exclusive; (-1, -1, []) if no live (uncommented, top-level)
    `hosted_llm:` key exists."""
    for i, line in enumerate(lines):
        if re.match(r"^hosted_llm:", line):
            j = i + 1
            while j < len(lines) and lines[j][:1] in (" ", "\t"):
                j += 1
            return i, j, lines[i:j]
    return -1, -1, []


def _existing_api_key(hosted_llm_block: list[str]) -> str | None:
    for line in hosted_llm_block[1:]:
        match = _HOSTED_LLM_KEY_RE.match(line.strip())
        if match:
            value = match.group(1).strip()
            return value or None
    return None


def update_chat_backend_config(
    config_path: str | Path,
    chat_backend: str,
    hosted_llm_model: str | None = None,
    hosted_llm_api_key: str | None = None,
    hosted_llm_max_tokens: int | None = None,
) -> None:
    """Patch only the `chat_backend`/`hosted_llm` lines of `config_path`,
    leaving every other line (including all comments) byte-identical - a
    full YAML round-trip via yaml.safe_load/safe_dump was measured to strip
    every comment and reorder every top-level key, unacceptable for this
    hand-annotated file. Mirrors the sed-based technique deploy/setup_ec2.sh
    already uses for the same two keys.

    Omitted/blank `hosted_llm_api_key` preserves whatever key is already
    configured, so switching chat_backend back and forth doesn't force
    re-entering it every time.
    """
    path = Path(config_path)
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)

    start, end, hosted_block = _extract_hosted_llm_block(lines)
    existing_key = _existing_api_key(hosted_block) if hosted_block else None
    resolved_key = (hosted_llm_api_key or existing_key or _PLACEHOLDER_API_KEY).strip()
    was_freshly_appended = start == -1

    if not was_freshly_appended:
        del lines[start:end]
    else:
        start = len(lines)

    new_hosted_block = (
        "hosted_llm:\n"
        f'  provider: "anthropic"\n'
        f'  model: "{hosted_llm_model or _DEFAULT_MODEL}"\n'
        f'  api_key: "{resolved_key}"\n'
        f"  max_tokens: {hosted_llm_max_tokens or _DEFAULT_MAX_TOKENS}\n"
    )
    if was_freshly_appended:
        if lines and not lines[-1].endswith("\n"):
            lines[-1] += "\n"
        new_hosted_block = "\n" + new_hosted_block
    lines[start:start] = [new_hosted_block]

    text = "".join(lines)
    if _CHAT_BACKEND_LINE_RE.search(text):
        text = _CHAT_BACKEND_LINE_RE.sub(f'chat_backend: "{chat_backend}"', text, count=1)
    else:
        if not text.endswith("\n"):
            text += "\n"
        text += f'\nchat_backend: "{chat_backend}"\n'

    _atomic_write(path, text)


def _atomic_write(path: Path, text: str) -> None:
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(text, encoding="utf-8")
    os.replace(tmp_path, path)
