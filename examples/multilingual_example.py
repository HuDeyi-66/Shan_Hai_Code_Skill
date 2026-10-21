"""Synthetic standalone example; not an authentic legal source."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from skills.shanhai.multilingual import analyze,citation,reconstruct
raw='المادة (١)\nيجب التحقق.\nالمادة (٢)\nوفق المادة (١).\n'.encode('utf-8')
result=analyze(raw,profile_id='ar-QA-statute',artifact_id='synthetic-example',source_id='synthetic')
first=result['nodes'][0];record=citation(result,first['unit_id'])
assert reconstruct(raw,result,record)==first['text']
print(result['schema'],len(result['nodes']),[r['status'] for r in result['references']])
