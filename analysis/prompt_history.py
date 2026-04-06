"""Analyze modification frequency of Claude Code system prompts.

Walks the git history of the Piebald-AI/claude-code-system-prompts repo
to count how often each prompt file was modified, when it was created,
when it was removed (if applicable), and its lifespan.

Usage:
    python3 prompt_history.py /path/to/claude-code-system-prompts
"""

import json
import subprocess
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional


PROMPTS_DIR: str = "system-prompts"


@dataclass
class PromptInfo:
    filename: str
    modification_count: int
    first_seen: str
    last_seen: str
    removed: bool
    lifespan_days: int
    category: str


def _run_git(repo: Path, *args: str) -> str:
    """Run a git command in the repo and return stdout."""
    result = subprocess.run(
        ["git", "-C", str(repo)] + list(args),
        capture_output=True,
        text=True,
        timeout=60,
    )
    result.check_returncode()
    return result.stdout


def _get_current_files(repo: Path) -> set[str]:
    """Get the set of prompt filenames currently in the repo."""
    prompts_path = repo / PROMPTS_DIR
    if not prompts_path.exists():
        return set()
    return {f.name for f in prompts_path.iterdir() if f.suffix == ".md"}


def _categorize(filename: str) -> str:
    """Categorize a prompt by its filename prefix."""
    if filename.startswith("agent-prompt-"):
        return "agent"
    elif filename.startswith("system-prompt-"):
        return "system"
    elif filename.startswith("skill-"):
        return "skill"
    elif filename.startswith("tool-description-"):
        return "tool"
    elif filename.startswith("data-"):
        return "data"
    else:
        return "other"


def get_prompt_modification_counts(repo: Path) -> dict[str, int]:
    """Count commits that touched each prompt file."""
    log = _run_git(
        repo, "log", "--all", "--name-only", "--pretty=format:", "--diff-filter=AMRD",
        "--", f"{PROMPTS_DIR}/*.md",
    )
    counts: dict[str, int] = {}
    for line in log.strip().split("\n"):
        line = line.strip()
        if not line or not line.endswith(".md"):
            continue
        filename = line.split("/")[-1]
        counts[filename] = counts.get(filename, 0) + 1
    return counts


def get_prompt_lifespan(repo: Path) -> dict[str, PromptInfo]:
    """Get creation date, last modification, and removal status for each prompt."""
    current_files = _get_current_files(repo)
    counts = get_prompt_modification_counts(repo)

    result: dict[str, PromptInfo] = {}
    for filename, count in counts.items():
        # First commit that introduced this file
        first_log = _run_git(
            repo, "log", "--all", "--diff-filter=A", "--format=%aI",
            "--reverse", "--", f"{PROMPTS_DIR}/{filename}",
        )
        first_lines = [l.strip() for l in first_log.strip().split("\n") if l.strip()]
        first_seen = first_lines[0] if first_lines else "unknown"

        # Last commit that touched this file
        last_log = _run_git(
            repo, "log", "--all", "-1", "--format=%aI",
            "--", f"{PROMPTS_DIR}/{filename}",
        )
        last_seen = last_log.strip() or "unknown"

        removed = filename not in current_files

        # Calculate lifespan in days
        lifespan_days = 0
        if first_seen != "unknown" and last_seen != "unknown":
            from datetime import datetime, timezone
            try:
                first_dt = datetime.fromisoformat(first_seen)
                last_dt = datetime.fromisoformat(last_seen)
                lifespan_days = (last_dt - first_dt).days
            except ValueError:
                pass

        result[filename] = PromptInfo(
            filename=filename,
            modification_count=count,
            first_seen=first_seen,
            last_seen=last_seen,
            removed=removed,
            lifespan_days=lifespan_days,
            category=_categorize(filename),
        )

    return result


def get_prompt_details(repo: Path, filename: str) -> list[dict[str, str]]:
    """Get detailed commit history for a specific prompt file."""
    log = _run_git(
        repo, "log", "--all", "--format=%aI|%s",
        "--", f"{PROMPTS_DIR}/{filename}",
    )
    entries: list[dict[str, str]] = []
    for line in log.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        parts = line.split("|", 1)
        date = parts[0]
        message = parts[1] if len(parts) > 1 else ""
        # Extract version from commit message (format: "v2.1.91 (+N tokens)")
        version = ""
        if message.startswith("v"):
            version = message.split(" ")[0]
        entries.append({"date": date, "version": version, "message": message})
    return entries


def generate_report(repo: Path) -> dict:
    """Generate a full report of all prompt modification histories."""
    lifespans = get_prompt_lifespan(repo)

    prompts = sorted(
        [asdict(info) for info in lifespans.values()],
        key=lambda x: x["modification_count"],
        reverse=True,
    )

    # Summary stats
    active = [p for p in prompts if not p["removed"]]
    removed = [p for p in prompts if p["removed"]]
    active_counts = [p["modification_count"] for p in active]
    removed_counts = [p["modification_count"] for p in removed]

    summary = {
        "total_prompts_ever": len(prompts),
        "currently_active": len(active),
        "removed": len(removed),
        "avg_modifications_active": (
            sum(active_counts) / len(active_counts) if active_counts else 0
        ),
        "avg_modifications_removed": (
            sum(removed_counts) / len(removed_counts) if removed_counts else 0
        ),
        "most_modified": prompts[0]["filename"] if prompts else None,
        "least_modified_active": (
            min(active, key=lambda x: x["modification_count"])["filename"]
            if active else None
        ),
    }

    return {"summary": summary, "prompts": prompts}


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: prompt_history.py /path/to/claude-code-system-prompts",
              file=sys.stderr)
        sys.exit(2)

    repo = Path(sys.argv[1])
    report = generate_report(repo)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
