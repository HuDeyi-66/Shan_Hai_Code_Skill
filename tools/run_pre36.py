"""Small synthetic showcase and retained native safety modules; no archive dependency."""
import argparse,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SELECTION={'test_operators_v1': ['StructureAcceptance.test_typed_observations_and_native_text_facts', 'StructureAcceptance.test_nine_language_unicode_oracle_spans', 'StructureAcceptance.test_modified_bytes_refused', 'StructureAcceptance.test_incorrect_representation_identity_refused', 'ReferenceAcceptance.test_unique_source_label_match_is_not_legal_correctness', 'ReferenceAcceptance.test_duplicate_labels_preserve_all_candidates_in_source_order'], 'test_chunking_v1': ['ChunkingTests.test_all_nine_languages_exact_whitespace_unicode_and_citations', 'ChunkingTests.test_native_citation_and_result_mutations_refuse']}
def main():
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['showcase','essential'],nargs='?',default='showcase');a=p.parse_args()
 sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
 suite=unittest.TestSuite()
 for module,cases in SELECTION.items():
  if '/' in module:
   directory,name=module.rsplit('/',1);sys.path.insert(0,str(ROOT/directory));module=name
  if a.mode=='essential':suite.addTests(unittest.defaultTestLoader.loadTestsFromName(module))
  else:
   for case in cases:suite.addTests(unittest.defaultTestLoader.loadTestsFromName(module+'.'+case))
 result=unittest.TextTestRunner(verbosity=1).run(suite)
 print(json.dumps({'mode':a.mode,'ran':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped)}))
 return 0 if result.wasSuccessful() and not result.skipped else 1
if __name__=='__main__':raise SystemExit(main())
