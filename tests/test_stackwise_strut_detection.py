from __future__ import annotations

import unittest
import json
import tempfile
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image
from unittest.mock import patch

from src.stackwise_strut_detection import (
    decision_from_measurement,
    merge_records,
    StackwiseConfig,
    agent1_contract,
    agent2_adjudication_contract,
    candidate_score,
    candidate_selection_key,
    candidate_summary,
    parse_agent1_review_pairs,
    parse_agent2_assessments,
    run_stackwise_detector,
    _provider_request,
    _completion_payload,
    _export_original_slice_images,
    evidence_tile_bounds,
    struts_intersecting_z,
    vlm_included_z_slices,
    window_intersects_z_ranges,
    validate_window,
)


class StackwiseStrutDetectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.junctions = {0: {"position": [0, 0, 1]}, 1: {"position": [4, 0, 8]}}
        self.struts = [{"id": 19, "junction0": 0, "junction1": 1}]

    def test_window_must_be_odd(self) -> None:
        with self.assertRaises(ValueError):
            validate_window(6, 1)
        validate_window(7, 1)

    def test_z_intersection_preserves_source_id(self) -> None:
        selected = struts_intersecting_z(self.struts, self.junctions, 4, 5)
        self.assertEqual(selected[0]["id"], 19)
        self.assertEqual(struts_intersecting_z(self.struts, self.junctions, 9, 10), [])

    def test_vlm_excluded_z_range_uses_inclusive_window_overlap(self) -> None:
        excluded = ((1, 26), (740, 761))
        self.assertFalse(window_intersects_z_ranges(0, 0, excluded))
        self.assertTrue(window_intersects_z_ranges(0, 1, excluded))
        self.assertFalse(window_intersects_z_ranges(733, 739, excluded))
        self.assertTrue(window_intersects_z_ranges(737, 743, excluded))
        self.assertTrue(window_intersects_z_ranges(761, 767, excluded))
        self.assertEqual(vlm_included_z_slices(737, 743, excluded), [737, 738, 739])
        self.assertEqual(vlm_included_z_slices(0, 6, excluded), [0])

    def test_quarter_evidence_tiles_cover_source_without_overlap(self) -> None:
        bounds = [evidence_tile_bounds((10, 11), row, column, 2) for row in range(2) for column in range(2)]
        covered = np.zeros((10, 11), dtype=np.uint8)
        for x0, x1, y0, y1 in bounds:
            covered[y0:y1, x0:x1] += 1
        self.assertEqual(bounds[0], (0, 5, 0, 5))
        self.assertEqual(bounds[-1], (5, 11, 5, 10))
        self.assertTrue(np.all(covered == 1))

    def test_quarter_grid_exports_exactly_four_multimodal_images(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            source = np.full((1, 10, 12), 32768, dtype=np.uint16)
            outputs = _export_original_slice_images(Path(temp), "batch", 0, source, source > 0, source > 0, grid_size=2)
            self.assertEqual(len(outputs), 4)
            self.assertTrue(all("Multimodal tile" in description for description, _ in outputs))
            with Image.open(outputs[0][1]) as image:
                self.assertEqual(image.mode, "RGB")
                self.assertEqual(image.size, (18, 5))

    def test_agent1_contract_has_explicit_multimodal_prompt(self) -> None:
        contract = agent1_contract("stack_0001_0007", 1, 7, self.struts, {"spacing": [1, 1, 1]})
        prompt = contract["vlm_prompt"]
        self.assertIn("source-array evidence", prompt)
        self.assertIn("registered-junction manifest", prompt)
        self.assertIn("missing-strut triage handoff", prompt)
        self.assertIn("substantially absent in raw CT", prompt)
        self.assertIn("all four local lattice sides/directions", prompt)
        self.assertIn("junction-to-junction bridge", prompt)
        self.assertIn("row-by-column order", prompt)
        self.assertIn("four lateral sides of the scan", prompt)
        self.assertIn("Agent 2, which makes the final VLM label", prompt)
        self.assertNotIn("deterministic measurement", prompt)
        self.assertEqual(contract["registered_junction_connection_manifest"][0]["junction0_id"], 0)
        self.assertEqual(contract["registered_junction_connection_manifest"][0]["junction1_id"], 1)
        self.assertIn("agent2_missing_review_junction_pairs", contract["required_output_schema"])
        self.assertNotIn("maximum 6", contract["required_output_schema"]["potential_missing_observations"])

    def test_agent2_contract_requests_final_label_and_reasoning(self) -> None:
        adjudication = agent2_adjudication_contract("stack_0001_0007", {"agent1_analysis": {"observations": []}, "required_features": [], "threshold_rule": "median/MAD", "persistence_rule": "two windows", "required_output_schema": {}})
        self.assertEqual(adjudication["agent"], "agent2_multimodal_final_adjudicator")
        self.assertIn("missing or not_missing", adjudication["vlm_prompt"])
        self.assertNotIn("deterministic", adjudication["vlm_prompt"].lower())
        self.assertIn("all four local lattice sides/directions", adjudication["vlm_prompt"])
        self.assertIn("two registered junctions/nodes", adjudication["vlm_prompt"])
        self.assertIn("lateral scan boundary", adjudication["vlm_prompt"])
        assessment = adjudication["required_output_schema"]["final_assessments"][0]
        self.assertIn("junction0_id", assessment)
        self.assertIn("junction1_id", assessment)
        self.assertIn("reasoning", assessment)
        self.assertNotIn("deterministic_follow_up", assessment)

    def test_parse_agent2_assessments_keeps_only_valid_labels(self) -> None:
        response = {"choices": [{"message": {"content": '```json\n{"final_assessments":[{"junction0_id":1,"junction1_id":2,"final_label":"missing","confidence":1.2,"reasoning":"empty corridor"},{"junction0_id":3,"junction1_id":4,"final_label":"invalid","confidence":0.5}]}\n```'}}]}
        self.assertEqual(parse_agent2_assessments(response), [{"junction0_id": 1, "junction1_id": 2, "final_label": "missing", "confidence": 1.0, "reasoning": "empty corridor", "agent1_agreement": ""}])

    def test_parse_agent1_review_pairs_accepts_only_manifest_pairs(self) -> None:
        response = {"choices": [{"message": {"content": '{"agent2_missing_review_junction_pairs":[{"junction0_id":1,"junction1_id":2},{"junction0_id":9,"junction1_id":9}],"potential_missing_observations":[{"junction0_id":3,"junction1_id":4}]}'}}]}
        self.assertEqual(parse_agent1_review_pairs(response, [(1, 2), (3, 4)]), [(1, 2), (3, 4)])

    def test_parse_agent2_assessments_recovers_missing_outer_brace(self) -> None:
        response = {"choices": [{"message": {"content": '{"final_assessments":[{"junction0_id":1,"junction1_id":2,"final_label":"not_missing","confidence":0.8,"reasoning":"continuous"}]}'[:-1]}}]}
        self.assertEqual(parse_agent2_assessments(response)[0]["junction0_id"], 1)

    def test_decision_boundaries(self) -> None:
        base = {"sample_count": 10, "alignment_quality": "acceptable", "occupancy_ratio": .9, "maximum_gap_length": 0, "raw_ct_corroboration": .8, "mean_thickness": 10, "curvature": 0, "maximum_deviation": 0}
        self.assertEqual(decision_from_measurement({**base, "occupancy_ratio": 0, "raw_ct_corroboration": 0}, None)[0], "missing")
        self.assertEqual(decision_from_measurement({**base, "occupancy_ratio": .5, "maximum_gap_length": 3}, None)[0], "broken")
        self.assertEqual(decision_from_measurement({**base, "mean_thickness": 4}, (10, 1))[0], "thin")
        self.assertEqual(decision_from_measurement({**base, "curvature": .2}, None)[0], "normal")
        self.assertEqual(decision_from_measurement({**base, "curvature": .2}, None, (0.02, 0.02, 0.5, 0.5))[0], "bent")
        self.assertEqual(decision_from_measurement({**base, "occupancy_ratio": .2, "raw_ct_corroboration": .6}, None)[0], "uncertain")

    def test_candidate_summary_is_math_based_and_excludes_normal(self) -> None:
        record = {"strut_id": 19, "classification": "broken", "confidence": .8, "reason": "gap", "stack_id": "s", "sample_count": 10, "maximum_gap_length": 4, "occupancy_ratio": .5, "endpoint_connection": True, "mean_thickness": 2., "maximum_deviation": 1., "curvature": 0., "raw_ct_corroboration": .7, "alignment_quality": "acceptable"}
        self.assertGreater(candidate_score(record), .9)
        self.assertEqual(candidate_summary(record)["candidate_label"], "broken")

    def test_candidate_selection_prefers_stronger_observation(self) -> None:
        base = {"strut_id": 19, "classification": "broken", "sample_count": 10, "maximum_gap_length": 3, "occupancy_ratio": .5, "raw_ct_corroboration": .6, "alignment_quality": "acceptable", "full_span_observation": False, "stack_range": [5, 11]}
        stronger = {**base, "maximum_gap_length": 5, "full_span_observation": True, "stack_range": [8, 14]}
        self.assertGreater(candidate_selection_key(stronger), candidate_selection_key(base))

    def test_merge_identical_overlapping_defects(self) -> None:
        records = [{"strut_id": 19, "classification": "broken", "confidence": .8, "stack_id": "a"}, {"strut_id": 19, "classification": "broken", "confidence": .9, "stack_id": "b"}]
        merged = merge_records(records)
        self.assertEqual(merged[0]["classification"], "broken")
        self.assertEqual(merged[0]["overlap_evidence_count"], 2)

    def test_synthetic_run_writes_stack_and_merged_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            raw = np.zeros((5, 12, 12), dtype=np.uint8)
            mask = np.zeros_like(raw)
            raw[:, 6, 3:9] = 200
            mask[:, 6, 3:9] = 1
            for name, volume in (("raw.tif", raw), ("mask.tif", mask), ("skeleton.tif", mask)):
                tifffile.imwrite(root / name, volume)
            geometry = {"junctions": [{"id": 1, "position": [3, 6, 0]}, {"id": 2, "position": [8, 6, 4]}], "struts": [{"id": 44, "junction0": 1, "junction1": 2}]}
            (root / "geometry.json").write_text(json.dumps(geometry), encoding="utf-8")
            result = run_stackwise_detector(StackwiseConfig(raw_tif=root / "raw.tif", segmentation_tif=root / "mask.tif", skeleton_tif=root / "skeleton.tif", geometry_json=root / "geometry.json", output_dir=root / "out", stack_size=3, center_z=2, use_providers=False))
            self.assertEqual(result["status"], "passed")
            self.assertEqual(result["metadata"]["clustering"], "not used")
            self.assertEqual(result["coverage"]["unique_measured_struts"], 1)
            self.assertTrue((root / "out" / "merged_per_strut_results.json").exists())
            self.assertTrue((root / "out" / "candidate_struts.json").exists())
            self.assertTrue((root / "out" / "coverage_report.json").exists())
            self.assertFalse(list((root / "out" / "overlays").glob("*.png")))
            self.assertFalse(list((root / "out" / "agent1_triage").glob("*.json")))
            self.assertFalse(list((root / "out" / "agent2_adjudications").glob("*.json")))

    def test_single_stack_failure_does_not_stop_later_stacks(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            raw = np.zeros((5, 10, 10), dtype=np.uint8); mask = np.zeros_like(raw)
            raw[:, 5, 2:8] = 100; mask[:, 5, 2:8] = 1
            for name, volume in (("raw.tif", raw), ("mask.tif", mask)):
                tifffile.imwrite(root / name, volume)
            geometry = {"junctions": [{"id": 1, "position": [2, 5, 0]}, {"id": 2, "position": [7, 5, 4]}], "struts": [{"id": 9, "junction0": 1, "junction1": 2}]}
            (root / "geometry.json").write_text(json.dumps(geometry), encoding="utf-8")
            from src.stackwise_strut_detection import measure_strut as original_measure
            calls = {"count": 0}
            def fail_once(*args, **kwargs):
                calls["count"] += 1
                if calls["count"] == 1:
                    raise RuntimeError("synthetic stack failure")
                return original_measure(*args, **kwargs)
            with patch("src.stackwise_strut_detection.measure_strut", side_effect=fail_once):
                run_stackwise_detector(StackwiseConfig(raw_tif=root / "raw.tif", segmentation_tif=root / "mask.tif", skeleton_tif=None, geometry_json=root / "geometry.json", output_dir=root / "out", stack_size=3, use_providers=False))
            self.assertTrue((root / "out" / "failures.jsonl").exists())
            self.assertTrue((root / "out" / "merged_per_strut_results.json").exists())

    def test_provider_request_uses_inference_client_chat_api(self) -> None:
        class Completion:
            def model_dump(self):
                return {"choices": [{"message": {"content": "ok"}}]}
        with patch("src.stackwise_strut_detection.InferenceClient") as client_type:
            client_type.return_value.chat.completions.create.return_value = Completion()
            response = _provider_request("model:provider", {"task": "preflight"}, "not-a-real-token")
        self.assertEqual(response["choices"][0]["message"]["content"], "ok")
        create = client_type.return_value.chat.completions.create
        self.assertEqual(create.call_args.kwargs["model"], "model:provider")

    def test_completion_payload_reads_choice_objects_without_model_dump(self) -> None:
        message = type("Message", (), {"role": "assistant", "content": '{"disagreements": []}'})()
        choice = type("Choice", (), {"finish_reason": "stop", "message": message})()
        payload = _completion_payload(type("Completion", (), {"choices": [choice]})())
        self.assertEqual(payload["choices"][0]["message"]["content"], '{"disagreements": []}')


if __name__ == "__main__":
    unittest.main()
