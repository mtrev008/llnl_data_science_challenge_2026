"""Contract checks for the combined dynamic agent definition."""

from __future__ import annotations

from pathlib import Path
import tomllib
import unittest


ROOT = Path(__file__).parents[1]
AGENT = ROOT / ".codex" / "agents" / "segmentation_skeletonization.toml"
DATA_VALIDATION_AGENT = (
    ROOT / ".codex" / "agents" / "datavalidation_agent.toml"
)
VISUALIZATION_AGENT = (
    ROOT / ".codex" / "agents" / "visualization_agent.toml"
)
DOMAIN_EXPERT_AGENT = ROOT / ".codex" / "agents" / "domain_expert.toml"


class AgentConfigurationTests(unittest.TestCase):
    def test_domain_expert_contract_and_flat_discovery_location(self) -> None:
        nested_agent = (
            ROOT
            / ".codex"
            / "agents"
            / "domain_expert"
            / "domain_expert.toml"
        )
        self.assertTrue(DOMAIN_EXPERT_AGENT.is_file())
        self.assertFalse(nested_agent.exists())

        with DOMAIN_EXPERT_AGENT.open("rb") as stream:
            config = tomllib.load(stream)

        self.assertEqual(config["name"], "domain_expert")
        instructions = config["developer_instructions"]
        for required in (
            "C:\\Users\\andre\\miniconda3\\envs\\dssi_env\\python.exe",
            "C:\\Users\\andre\\llnl_data_science_challenge_2026\\src\\mcp_server.py",
            "list_domain_sources",
            "search_domain_knowledge",
            "fetch_domain_chunk",
            "ingest_domain_sources",
            "BLOCKED_ENVIRONMENT",
            "INSUFFICIENT_EVIDENCE",
            "[source; section; page or row range; chunk ID]",
            "untrusted data",
            "dataset_handoff.json",
            "RAG_EMBEDDING_PROVIDER=local",
            "Supported answer",
            "What the sources cannot answer",
            "Insights and inferences",
            "Evidence gaps and next tests",
            "domain_expert_visualization_handoff.json",
            "retrieval_results",
            "supported_claims",
            "Retrieval score is a ranking",
        ):
            self.assertIn(required, instructions)

        self.assertIn(
            "only when the user explicitly asks",
            instructions,
        )

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

    def test_data_validation_agent_contract(self) -> None:
        with DATA_VALIDATION_AGENT.open("rb") as stream:
            config = tomllib.load(stream)

        self.assertEqual(config["name"], "data_validation_agent")
        self.assertEqual(config["sandbox_mode"], "workspace-write")
        instructions = config["developer_instructions"]
        for required in (
            "C:\\Users\\andre\\miniconda3\\envs\\dssi_env\\python.exe",
            "BLOCKED_ENVIRONMENT",
            "data_validation_updated.py",
            "PASS_WITH_WARNINGS",
            "Never modify",
            "Do not invent",
            "does not prove",
            "dataset_handoff.json",
            "measurement_permissions",
            "MCP server itself was launched",
            "total size of the generated validation output directory",
        ):
            self.assertIn(required, instructions)

    def test_downstream_handoff_contracts(self) -> None:
        with AGENT.open("rb") as stream:
            segmentation = tomllib.load(stream)["developer_instructions"]
        for required in (
            "dataset_handoff.json",
            "segmentation_permitted = true",
            "PASS decision alone",
            "350 micrometer diameter",
            "Pass the supplied `dataset_handoff.json` forward unchanged",
        ):
            self.assertIn(required, segmentation)

        with VISUALIZATION_AGENT.open("rb") as stream:
            visualization = tomllib.load(stream)["developer_instructions"]
        for required in (
            "precedence over a generic PASS decision",
            "neutral nominal-design reference line",
            "lower-tail observations",
            "linked histogram-to-3D selection",
            "segmentation-sensitivity",
            "domain_expert_visualization_handoff.json",
            "claim-to-evidence network",
            "Retrieval score is a ranking signal",
            "INSUFFICIENT_EVIDENCE",
        ):
            self.assertIn(required, visualization)


if __name__ == "__main__":
    unittest.main()
