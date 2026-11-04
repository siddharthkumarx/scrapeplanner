#!/usr/bin/env python3
"""Check commit messages against the project's commit-message policy.

Policy (docs/decisions.md, D-008):

* no trailers except ``Signed-off-by``;
* no "Generated with" footer.

Usage::

    check_commit_msg.py FILE          # check one message file (commit-msg hook)
    check_commit_msg.py --git REV...  # check every commit in ``git rev-list REV...``

Standard library only, so the hook works before ``uv sync``.
"""

from __future__ import annotations

import re
import subprocess
import sys
from collections.abc import Sequence

ALLOWED_TRAILERS = frozenset({"signed-off-by"})

SCISSORS = "# ------------------------ >8 ------------------------"
# A trailer line as git sees it: a token without spaces, a colon, a value.
TRAILER_RE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9-]*)\s*:\s*\S")
# "...-by:" lines are trailers wherever they appear (Reviewed-by, Acked-by, ...).
BY_LINE_RE = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9-]*-by)\s*:", re.IGNORECASE)
GENERATED_RE = re.compile(r"^\W*generated\s+with\b", re.IGNORECASE)


def _clean(message: str) -> list[str]:
    """Drop git comments and anything below the scissors line."""
    lines: list[str] = []
    for line in message.splitlines():
        if line.startswith(SCISSORS):
            break
        if line.startswith("#"):
            continue
        lines.append(line.rstrip())
    while lines and not lines[-1]:
        lines.pop()
    return lines


def _paragraphs(lines: Sequence[str]) -> list[list[str]]:
    paragraphs: list[list[str]] = []
    current: list[str] = []
    for line in lines:
        if line.strip():
            current.append(line)
        elif current:
            paragraphs.append(current)
            current = []
    if current:
        paragraphs.append(current)
    return paragraphs


def _trailer_block(paragraph: Sequence[str]) -> list[str]:
    """Return trailer keys if the paragraph is a trailer block, else []."""
    keys: list[str] = []
    for line in paragraph:
        if line[:1].isspace() and keys:  # folded continuation line
            continue
        match = TRAILER_RE.match(line)
        if not match:
            return []
        keys.append(match.group(1))
    return keys


def check_message(message: str) -> list[str]:
    """Return a list of policy violations; empty means the message is fine."""
    lines = _clean(message)
    problems: list[str] = []
    if not lines:
        return ["empty commit message"]

    seen: set[str] = set()

    def flag(key: str) -> None:
        if key.lower() in ALLOWED_TRAILERS or key.lower() in seen:
            return
        seen.add(key.lower())
        problems.append(f"trailer not allowed: {key!r} (only Signed-off-by)")

    paragraphs = _paragraphs(lines)
    if len(paragraphs) > 1:
        for key in _trailer_block(paragraphs[-1]):
            flag(key)
    for line in lines[1:]:
        by = BY_LINE_RE.match(line)
        if by:
            flag(by.group(1))
        if GENERATED_RE.match(line):
            problems.append(f"'Generated with' footer not allowed: {line.strip()!r}")
    return problems


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], check=True, capture_output=True, text=True
    ).stdout


def check_revisions(revs: Sequence[str]) -> int:
    commits = _git("rev-list", "--no-merges", *revs).split()
    failed = 0
    for sha in commits:
        problems = check_message(_git("log", "-1", "--format=%B", sha))
        if problems:
            failed += 1
            subject = _git("log", "-1", "--format=%s", sha).strip()
            print(f"{sha[:12]} {subject}", file=sys.stderr)
            for problem in problems:
                print(f"    {problem}", file=sys.stderr)
    print(f"checked {len(commits)} commit(s), {failed} with problems", file=sys.stderr)
    return 1 if failed else 0


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args[:1] == ["--git"] and len(args) > 1:
        return check_revisions(args[1:])
    if len(args) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    with open(args[0], encoding="utf-8") as handle:
        problems = check_message(handle.read())
    for problem in problems:
        print(f"commit-msg: {problem}", file=sys.stderr)
    if problems:
        print("commit-msg: see docs/decisions.md (D-008)", file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
