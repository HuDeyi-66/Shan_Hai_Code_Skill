"""Mode A: profile proposals with explicit drafting-family abstention."""
import re
from .integrity import TextView,ContractError
from .profiles import PROFILES

def analyze_auto(raw,*,artifact_id,source_id):
    from .analyzer import analyze,_label_candidates,stable
    view=TextView.from_bytes(raw);value=view.matching
    if re.search('[ぁ-ゖァ-ヺ]',value):languages=['ja']
    elif re.search('[\u0600-\u06ff]',value):languages=['ar']
    elif re.search('[А-Яа-яЁё]',value):languages=['ru']
    elif re.search('[\u3400-\u9fff]',value):languages=['zh','ja']
    else:languages=['en','fr','de','es','pt']
    proposed=[p.profile_id for p in PROFILES.values() if p.language in languages and _label_candidates(view,p)]
    result=dict(mode='A',status='selected_profile' if len(proposed)==1 else ('ambiguous_profile' if proposed else 'unsupported_structure'),
                profile_candidates=proposed,evidence=None,source_text_preserved=True)
    if len(proposed)==1:result['evidence']=analyze(raw,profile_id=proposed[0],artifact_id=artifact_id,source_id=source_id)
    result['selection_digest']=stable({k:v for k,v in result.items() if k!='evidence'})
    return result
