"""Tests for prompt history plotting."""

import json
import subprocess
import unittest
from pathlib import Path


PROMPTS_REPO = Path.home() / "Projects" / "claude-code-system-prompts"


class TestPlotGeneration(unittest.TestCase):
    """The plot script should produce an SVG file."""

    def test_produces_svg_output(self) -> None:
        output_path = Path("/tmp/test-prompt-history.svg")
        if output_path.exists():
            output_path.unlink()

        result = subprocess.run(
            ["python3", str(Path(__file__).parent / "plot_prompt_history.py"),
             str(PROMPTS_REPO), str(output_path)],
            capture_output=True,
            text=True,
            timeout=180,
        )
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        self.assertTrue(output_path.exists(), "SVG file not created")
        content = output_path.read_text()
        self.assertIn("<svg", content)
        self.assertGreater(len(content), 1000)

    def test_svg_contains_magicdocs_label(self) -> None:
        """MagicDocs should be highlighted/labeled in the plot."""
        output_path = Path("/tmp/test-prompt-history.svg")
        if not output_path.exists():
            subprocess.run(
                ["python3", str(Path(__file__).parent / "plot_prompt_history.py"),
                 str(PROMPTS_REPO), str(output_path)],
                capture_output=True,
                timeout=180,
            )
        content = output_path.read_text()
        self.assertIn("magic", content.lower())

    def test_svg_distinguishes_removed_from_active(self) -> None:
        """Removed prompts should be visually distinct from active ones."""
        output_path = Path("/tmp/test-prompt-history.svg")
        if not output_path.exists():
            subprocess.run(
                ["python3", str(Path(__file__).parent / "plot_prompt_history.py"),
                 str(PROMPTS_REPO), str(output_path)],
                capture_output=True,
                timeout=180,
            )
        content = output_path.read_text()
        # Should have at least two different colors/markers
        self.assertIn("removed", content.lower())


if __name__ == "__main__":
    unittest.main()
