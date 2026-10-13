"""Byte/path regression requirements for the published API, without a runtime."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import _bootstrap
from skills.shanhai import TextArtifact, ShanHaiLegalTextEvidence, run_legal_text_evidence, legal_text_artifact

class PublicInputHardening(unittest.TestCase):
    RAW='第一条\n合成测试，不作法律结论。\n'.encode('utf-8')
    def test_byte_units_are_bound_to_original_bytes(self):
        result=run_legal_text_evidence(self.RAW,source_id='synthetic')
        self.assertTrue(result.units)
        self.assertFalse(result.diagnostics.has_fatal_error)
        self.assertTrue(result.artifact.verify_bytes(self.RAW))
        self.assertTrue(all(u.provenance==result.artifact.content_digest for u in result.units))
        self.assertIsNone(result.artifact.location)
        self.assertNotIn('payload_bytes',result.artifact.as_dict())
        json.dumps(result.as_dict())
    def test_memory_digest_mismatch_fails_before_parsing(self):
        artifact=legal_text_artifact(self.RAW)
        artifact.digest='0'*64
        result=ShanHaiLegalTextEvidence().run(artifact,source_id='synthetic')
        self.assertTrue(result.diagnostics.has_fatal_error)
        self.assertFalse(result.units)
    def test_missing_path_serializes_without_fabricated_digest(self):
        result=run_legal_text_evidence(_bootstrap.PROJECT_ROOT/'artifacts/never-existing-input.txt')
        self.assertTrue(result.diagnostics.has_fatal_error)
        self.assertFalse(result.units)
        self.assertFalse(result.is_complete_success)
        self.assertIsNone(result.artifact)
        self.assertIsNone(json.loads(json.dumps(result.as_dict()))['artifact'])
    def test_permission_error_becomes_typed_input_failure(self):
        with patch.object(TextArtifact,'from_file',side_effect=PermissionError('synthetic denied input')):
            result=run_legal_text_evidence(Path('denied.txt'))
        self.assertTrue(result.diagnostics.has_fatal_error)
        self.assertEqual(result.diagnostics.errors[0].code,'artifact_input_unreadable')
    def test_invalid_utf8_bytes_cannot_be_success(self):
        result=run_legal_text_evidence(b'\xff\xfe',source_id='synthetic')
        self.assertTrue(result.diagnostics.has_fatal_error)
        self.assertFalse(result.is_complete_success)
    def test_empty_bytes_keep_empty_distinct_from_missing_file(self):
        result=run_legal_text_evidence(b'',source_id='synthetic')
        self.assertIsNotNone(result.artifact)
        self.assertTrue(result.artifact.verify_bytes(b''))
        self.assertFalse(result.is_complete_success)
        self.assertTrue(any('empty' in u.loss for u in result.units))

if __name__=='__main__':unittest.main()
