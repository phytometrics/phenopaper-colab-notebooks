import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import generation

class GenerationTests(unittest.TestCase):
 def test_capture_explicit_variant_and_configured_effort_without_credentials(self):
  config={'provider':{'spark-local':{'options':{'apiKey':'secret'},'models':{'GLM':{'options':{'temperature':0.2},'variants':{'high':{'reasoningEffort':'high','apiKey':'secret'}}}}}}}
  value=generation.invocation(['opencode','run','--model','spark-local/GLM','--variant','high','--command','reproduce'],config,'1.2.3')
  self.assertEqual(value['parameters'],{'variant':'high','reasoning_effort':'high','temperature':0.2})
  self.assertNotIn('secret',json.dumps(value))
 def test_validation_is_not_authoring(self):
  self.assertIsNone(generation.invocation(['opencode','run','--model','spark-local/GLM','--command','validate-t4'],{}))
 def test_variant_does_not_invent_effort_when_not_recorded(self):
  value=generation.invocation(['opencode','run','--model','spark-local/GLM','--variant','low','--command','reproduce'],{})
  self.assertEqual(value['parameters'],{'variant':'low'})
 def test_preserve_generation_across_validation_or_model_changes(self):
  value=generation.invocation(['opencode','run','--model','spark-local/GLM','--variant','low','--command','reproduce'],{})
  with tempfile.TemporaryDirectory() as directory:
   path=Path(directory);(path/'generation.json').write_text(json.dumps(value))
   with patch('generation.read_current',side_effect=AssertionError('must preserve original')):
    self.assertEqual(generation.for_run(path),value)
 def test_reject_unbounded_and_secret_parameters(self):
  value={'harness':'OpenCode','harness_version':None,'model':'model','parameters':{'api_key':'secret'},'source':'host_process','run_id':None}
  with self.assertRaises(ValueError):generation.validate(value)

if __name__=='__main__':unittest.main()
