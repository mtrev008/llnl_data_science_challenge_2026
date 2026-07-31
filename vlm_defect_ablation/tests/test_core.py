import json
import tempfile
import unittest
from pathlib import Path
import numpy as np
import tifffile

from src.stack_builder import valid_centers, build_stack, select_centers
from src.contact_sheet import create_contact_sheet
from src.leakage_check import check_leakage
from src.geometry_adapter import normalize_geometry
from src.schema_validation import validate
from src.code_safety import inspect_code
from src.consistency_analysis import bbox_iou
from src.stability_analysis import compare_repeats

ROOT=Path(__file__).resolve().parents[1]
class CoreTests(unittest.TestCase):
 def setUp(self): self.volume=np.arange(761*4*5,dtype=np.uint16).reshape(761,4,5)
 def test_755_valid_stacks_and_boundaries(self):
  self.assertEqual(valid_centers(761),list(range(3,758))); self.assertEqual(len(valid_centers(761)),755)
  with self.assertRaises(ValueError): build_stack(self.volume,2)
 def test_stack_preserves_order(self):
  s=build_stack(self.volume,100); self.assertEqual(s.indices,(97,98,99,100,101,102,103)); self.assertTrue(np.array_equal(s.arrays[3],self.volume[100]))
 def test_seeded_selection(self):
  args={"size":7,"stride":1,"random_count":3,"random_seed":8}; self.assertEqual(select_centers(761,args),select_centers(761,args))
 def test_contact_sheet(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"stack_000100.png"; meta=create_contact_sheet(build_stack(self.volume,100),p,100); self.assertTrue(p.is_file()); self.assertEqual(meta["original_dimensions"],[4,5])
 def test_leakage(self): self.assertTrue(check_leakage("images_only",{"geometry":{"x":1}},[])); self.assertFalse(check_leakage("images_only",{"condition":"images_only","center_slice":1},[]))
 def test_geometry_normalization_and_unregistered(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"lattice.json"; p.write_text(json.dumps({"junctions":[{"id":1,"position":[1,2,3]},{"id":2,"position":[4,5,6]}],"struts":[{"id":7,"junction0":1,"junction1":2}]})); out=normalize_geometry(p,False); self.assertFalse(out["metadata"]["registered_to_tiff"]); self.assertEqual(out["struts"][0]["strut_id"],7)
 def test_schema_validation(self): self.assertTrue(validate({},ROOT/"schemas"/"agent1_output.schema.json"))
 def test_unsafe_code(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"x.py"; p.write_text("import subprocess\nsubprocess.run(['x'])"); self.assertTrue(inspect_code(p))
 def test_iou_and_stability(self):
  self.assertEqual(bbox_iou({"x_min":0,"y_min":0,"x_max":2,"y_max":2},{"x_min":0,"y_min":0,"x_max":2,"y_max":2}),1.0)
  d={"detections":[]}; self.assertIsNone(compare_repeats([d])["stable"])
 def test_no_labeled_metrics_in_schema(self):
  text=(ROOT/"schemas"/"agent2_output.schema.json").read_text().lower()
  for forbidden in ("precision","recall","f1","confusion", "true_positive"): self.assertNotIn(forbidden,text)
