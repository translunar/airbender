"""Plot modification frequency of Claude Code system prompts.

Produces an SVG scatter plot: lifespan (days) vs modification count,
with removed prompts visually distinct and MagicDocs highlighted.

Usage:
    python3 plot_prompt_history.py /path/to/claude-code-system-prompts output.svg
"""

import json
import subprocess
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches


# Cyberpunk palette (matches translunar.io)
BG_COLOR: str = "#0d0a14"
TEXT_COLOR: str = "#e2ddf0"
BRAND_COLOR: str = "#a87dc8"
BRAND_LIGHT: str = "#c9a0dc"
PINK: str = "#f4a7c0"
GRID_COLOR: str = "#2a2040"
ACTIVE_COLOR: str = "#c9a0dc"
REMOVED_COLOR: str = "#6b5e8a"
HIGHLIGHT_COLOR: str = "#f4a7c0"


def main() -> None:
    if len(sys.argv) < 3:
        print("Usage: plot_prompt_history.py /path/to/repo output.svg",
              file=sys.stderr)
        sys.exit(2)

    repo = Path(sys.argv[1])
    output = Path(sys.argv[2])

    # Get data from prompt_history.py
    result = subprocess.run(
        [sys.executable, str(Path(__file__).parent / "prompt_history.py"), str(repo)],
        capture_output=True,
        text=True,
        timeout=180,
    )
    result.check_returncode()
    data = json.loads(result.stdout)
    prompts = data["prompts"]

    # Separate active, removed, and highlighted
    active = [p for p in prompts if not p["removed"] and "magic" not in p["filename"].lower()]
    removed = [p for p in prompts if p["removed"] and "magic" not in p["filename"].lower()]
    magic = [p for p in prompts if "magic" in p["filename"].lower()]

    # Set up the figure with dark theme
    fig, ax = plt.subplots(figsize=(12, 7))
    fig.patch.set_facecolor(BG_COLOR)
    ax.set_facecolor(BG_COLOR)

    # Style axes
    ax.spines["bottom"].set_color(GRID_COLOR)
    ax.spines["left"].set_color(GRID_COLOR)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(colors=TEXT_COLOR, which="both")
    ax.xaxis.label.set_color(TEXT_COLOR)
    ax.yaxis.label.set_color(TEXT_COLOR)
    ax.title.set_color(TEXT_COLOR)
    ax.grid(True, color=GRID_COLOR, alpha=0.5, linewidth=0.5)

    # Plot active prompts
    if active:
        ax.scatter(
            [p["lifespan_days"] for p in active],
            [p["modification_count"] for p in active],
            c=ACTIVE_COLOR,
            s=30,
            alpha=0.6,
            label=f"Active ({len(active)})",
            zorder=2,
        )

    # Plot removed prompts
    if removed:
        ax.scatter(
            [p["lifespan_days"] for p in removed],
            [p["modification_count"] for p in removed],
            c=REMOVED_COLOR,
            s=30,
            alpha=0.6,
            marker="x",
            label=f"Removed ({len(removed)})",
            zorder=2,
        )

    # Highlight MagicDocs
    if magic:
        for p in magic:
            ax.scatter(
                p["lifespan_days"],
                p["modification_count"],
                c=HIGHLIGHT_COLOR,
                s=120,
                marker="D",
                zorder=3,
                edgecolors="#ffffff",
                linewidths=0.8,
            )
            ax.annotate(
                "MagicDocs",
                xy=(p["lifespan_days"], p["modification_count"]),
                xytext=(15, 15),
                textcoords="offset points",
                color=HIGHLIGHT_COLOR,
                fontsize=11,
                fontweight="bold",
                arrowprops=dict(
                    arrowstyle="->",
                    color=HIGHLIGHT_COLOR,
                    lw=1.2,
                ),
            )

    # Labels
    ax.set_xlabel("Lifespan (days)", fontsize=12)
    ax.set_ylabel("Modification count", fontsize=12)
    ax.set_title(
        "Claude Code System Prompt Modification Frequency",
        fontsize=14,
        fontweight="bold",
        pad=15,
    )

    # Legend
    legend = ax.legend(
        loc="upper left",
        facecolor=BG_COLOR,
        edgecolor=GRID_COLOR,
        labelcolor=TEXT_COLOR,
        fontsize=10,
    )
    # Add MagicDocs to legend manually
    magic_patch = mpatches.Patch(color=HIGHLIGHT_COLOR, label="MagicDocs (removed)")
    handles, labels = ax.get_legend_handles_labels()
    handles.append(magic_patch)
    labels.append("MagicDocs (removed)")
    ax.legend(
        handles,
        labels,
        loc="upper left",
        facecolor=BG_COLOR,
        edgecolor=GRID_COLOR,
        labelcolor=TEXT_COLOR,
        fontsize=10,
    )

    # Annotate the top few most-modified prompts
    top_prompts = sorted(prompts, key=lambda p: p["modification_count"], reverse=True)[:3]
    for p in top_prompts:
        if "magic" in p["filename"].lower():
            continue
        short_name = p["filename"].replace("system-prompt-", "").replace("tool-description-", "").replace("agent-prompt-", "").replace(".md", "")
        ax.annotate(
            short_name,
            xy=(p["lifespan_days"], p["modification_count"]),
            xytext=(10, -10),
            textcoords="offset points",
            color=REMOVED_COLOR if p["removed"] else ACTIVE_COLOR,
            fontsize=8,
            alpha=0.8,
        )

    plt.tight_layout()
    fig.savefig(str(output), format="svg", facecolor=BG_COLOR)
    plt.close(fig)


if __name__ == "__main__":
    main()
