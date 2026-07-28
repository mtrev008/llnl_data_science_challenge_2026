"""Contract checks for the combined dynamic agent definition."""

from __future__ import annotations

from pathlib import Path
import tomllib
import unittest


ROOT = Path(__file__).parents[1]
AGENT = ROOT / ".codex" / "agents" / "segmentation_skeletonization.toml"


class AgentConfigurationTests(unittest.TestCase):
    def test_combined_agent_contract(self) -> None:
        with AGENT.open("rb") as stream:
            config = tomllib.load(stream)

        self.assertEqual(config["name"], "segmentation_skeletonization_agent")
        instructions = config["developer_instructions"]
        for required in (
            "C:\\Users\\andre\\miniconda3\\envs\\dssi_env\\python.exe",
            "BLOCKED_ENVIRONMENT",
            "segment_ct_global_threshold",
            "segment_ct_brightness_corrected",
            "segmented_mask.tif",
            "skeleton.tif",
            "threshold_profile.csv",
            "optimization_history.json",
            "selected_segmentation.py",
            "10 total candidates",
            "3 consecutive candidates",
        ):
            self.assertIn(required, instructions)


if __name__ == "__main__":
    unittest.main()
