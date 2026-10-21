"""Ordinary bounded parsing functions. No legal authority or temporal inference."""
import json
import re
from .integrity import ContractError,TextView,digest
from .profiles import (SCHEMA,VERSION,LABELS,CONTAINERS,CUE_WORDS,CUE_TYPES,
                       get_profile,identifier,numeral)
from .heading_rules import inline_heading,container_line

def stable(value):return digest(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode('utf-8'))

def tokenize(text):
    """Small Unicode lexer; spans are in the matching view, never citation offsets."""
    for m in re.finditer(r'\d+|[^\W\d_]+|[^\w\s]',text,re.UNICODE):
        yield dict(value=m[0],start=m.start(),end=m.end(),kind='number' if m[0].isdecimal() else ('word' if m[0].isalpha() else 'punctuation'))

def _line_bounds(text,position):
    start=text.rfind('\n',0,position)+1;end=text.find('\n',position)
    return start,len(text) if end<0 else end

def _span_text(view,span):return view.text[span['char_start']:span['char_end']]

def _label_candidates(view,profile):
    found=[]
    for pattern,kind in LABELS[profile.language]:
        for m in re.finditer(pattern,view.matching):
            if profile.language not in ('zh','ja','ar') and m.end()<len(view.matching) and view.matching[m.end()].isalnum():continue
            try:label=identifier(m,profile.language)
            except ContractError:label=None
            span=view.original_span(m.start(),m.end())
            found.append(dict(kind=kind,label=label,span=span,match_start=m.start(),match_end=m.end()))
    # Never let overlapping article spellings duplicate a marker.
    found.sort(key=lambda r:(r['match_start'],-r['match_end']))
    result=[]
    for row in found:
        if result and row['match_start']<result[-1]['match_end']:continue
        result.append(row)
    return result

def _sub_label(line,language):
    tokens=list(tokenize(line))
    if not tokens:return None
    # Explicit marker grammar: paragraph labels precede item labels.
    patterns=[(r'(?P<id>\d+)\s*[.、)]\s+','paragraph'),
              (r'\((?P<id>[0-9]+)\)\s*','paragraph'),
              (r'\((?P<id>[ivxlcdm]+)\)\s*','subitem'),
              (r'\((?P<id>[a-z]+)\)\s*','item'),
              (r'(?P<id>[ivxlcdm]+)\s*[-.)]\s+','item'),
              (r'(?P<id>[a-z])\)\s+','subitem' if language=='pt' else 'item')]
    if language in ('zh','ja'):
        patterns.insert(0,(r'第(?P<id>['+('〇零一二三四五六七八九十百千万萬亿億0-9')+r']+)[款項项号號]\s*','paragraph'))
        patterns.insert(1,(r'[（(](?P<id>[〇零一二三四五六七八九十百0-9]+)[）)]\s*','item'))
        if language=='ja':patterns.insert(0,(r'(?P<id>\d+)\s+','paragraph'))
    if language=='pt':patterns.insert(0,(r'n\.?\s*\.?o\s*(?P<id>\d+)\s*','paragraph'))
    for pattern,kind in patterns:
        m=re.match(pattern,line)
        if m:
            raw=m['id']
            try:value=str(numeral(raw)) if language in ('zh','ja') and (raw.isdecimal() or not raw.isascii()) else raw
            except ContractError:return None
            return kind,value,m.end()
    return None

def analyze(raw,*,profile_id,artifact_id,source_id,expected_digest=None,heading_offsets=None):
    """Parse declared profile; optional heading offsets are caller source assertions.

    Version 1.1 adds bounded nominative Russian titles and Arabic issuance
    qualifiers. CJK inline article starts exclude citation suffix contexts.
    Other ambiguous line-initial sentences remain explicitly uncertain.
    """
    if not isinstance(artifact_id,str) or not artifact_id or not isinstance(source_id,str) or not source_id:
        raise ContractError('invalid_input','nonempty artifact_id/source_id required')
    profile=get_profile(profile_id);view=TextView.from_bytes(raw)
    if expected_digest is not None and expected_digest!=digest(raw):raise ContractError('integrity_failure','artifact digest mismatch')
    explicit=None
    if heading_offsets is not None:
        if not isinstance(heading_offsets,(list,tuple)) or any(type(x) is not int or not 0<=x<len(view.text) for x in heading_offsets):
            raise ContractError('invalid_input','heading_offsets must be original code-point starts')
        explicit=set(heading_offsets)
    candidates=_label_candidates(view,profile);heads=[];diagnostics=list(view.diagnostics)
    for row in candidates:
        a,b=_line_bounds(view.matching,row['match_start'])
        line_initial=not view.matching[a:row['match_start']].strip()
        tail=view.matching[row['match_end']:b].strip()
        heading=(row['span']['char_start'] in explicit) if explicit is not None else (line_initial and not tail)
        if explicit is None and profile.heading_policy=='cjk_line' and line_initial:
            heading=not re.match(r'^(?:の規定|に|を|によ|第|规定|規定|所称|所稱|至|から)',tail)
        if explicit is None and profile.language=='ru' and row['kind']=='article' and not view.matching[row['match_start']:row['match_end']].startswith('статья '):heading=False
        if explicit is None and re.match(r'^(?:articles|artículos|artigos)\b',view.matching[row['match_start']:row['match_end']]):heading=False
        if row['label'] is None:
            diagnostics.append(('unsupported_number',row['span']['char_start'],row['span']['char_end']));continue
        basis='source_declared' if explicit is not None else profile.heading_policy;scope_hint=None
        if explicit is None and not heading and line_initial:
            orig_tail=view.text[row['span']['char_end']:view.original_span(row['match_start'],max(row['match_end'],b))['char_end']]
            heading,new_basis,scope_hint=inline_heading(profile,view.matching[row['match_start']:row['match_end']],tail,orig_tail)
            if heading:basis=new_basis
        if heading:
            h={**row,'kind':row['kind'],'heading_basis':basis,'scope_hint':scope_hint}
            h['heading_end']=view.original_span(row['match_start'],max(row['match_end'],b))['char_end']
            if profile.language=='ar' and tail=='(إصدار)':h['scope_hint']='promulgation'
            if profile.language=='ja' and row['kind']=='article':
                previous_end=a-1
                if previous_end>=0:
                    previous_start=view.matching.rfind('\n',0,previous_end)+1
                    previous=view.matching[previous_start:previous_end].strip()
                    if re.fullmatch(r'[（(][^\n]+[）)]',previous):
                        h['boundary_start']=view.original_span(previous_start,previous_end)['char_start']
            heads.append(h)
        elif line_initial and tail:diagnostics.append(('heading_or_reference_uncertain',row['span']['char_start'],row['span']['char_end']))
    # Containers require exact lexical heading prefix, not arbitrary prose search.
    for m in re.finditer(r'[^\r\n]+',view.matching):
        line=m[0].strip()
        if container_line(profile.language,line,CONTAINERS[profile.language]):
            first=m.start()+len(m[0])-len(m[0].lstrip());span=view.original_span(first,m.end())
            heads.append(dict(kind='annex',label=line,span=span,match_start=first,match_end=m.end(),heading_basis='container_lexicon'))
    heads.sort(key=lambda r:r['span']['char_start'])
    levels={'annex':0,'chapter':1,'article':2,'section':2,'paragraph':3,'item':4,'subitem':5}
    # Subordinate line markers are recognized only inside an established provision.
    position=0;main_heads=tuple(heads);implicit_counts={}
    for original_line in view.text.splitlines(keepends=True):
        start=position;position+=len(original_line)
        preceding=[h for h in main_heads if h['span']['char_start']<start]
        if not preceding or preceding[-1]['kind'] not in ('article','section'):continue
        if any(h.get('boundary_start')==start for h in main_heads):continue
        line_view=TextView.from_bytes(original_line.encode('utf-8'))
        whitespace=len(line_view.matching)-len(line_view.matching.lstrip())
        sub=_sub_label(line_view.matching.lstrip(),profile.language)
        if sub:
            kind,label,end=sub;local=line_view.original_span(whitespace,whitespace+end)
            span=view.span(start+local['char_start'],start+local['char_end'])
            heads.append(dict(kind=kind,label=label,span=span,heading_basis='subordinate_marker'))
        elif original_line.strip() and not any(h['span']['char_start']>=start and h['span']['char_start']<position for h in main_heads):
            owner=preceding[-1]['span']['char_start'];implicit_counts[owner]=implicit_counts.get(owner,0)+1
            a=start+len(original_line)-len(original_line.lstrip());b=position-len(original_line)+len(original_line.rstrip('\r\n'))
            heads.append(dict(kind='paragraph',label='position:'+str(implicit_counts[owner]),span=view.span(a,b),heading_basis='physical_line_candidate'))
    heads.sort(key=lambda r:r['span']['char_start'])
    nodes=[];stack=[];scope='document';annex_count=0
    for i,h in enumerate(heads):
        level=levels[h['kind']]
        while stack and levels[stack[-1]['kind']]>=level:stack.pop()
        if h['kind']=='annex':annex_count+=1;scope='annex:'+str(annex_count)
        if h['kind'] in ('article','section'):
            wanted='promulgation:1' if h.get('scope_hint')=='promulgation' else ('document' if scope=='promulgation:1' else scope)
            if wanted!=scope:stack=[];scope=wanted
        end=len(view.text)
        for later in heads[i+1:]:
            if levels[later['kind']]<=level:end=later.get('boundary_start',later['span']['char_start']);break
        span=view.span(h.get('boundary_start',h['span']['char_start']),end)
        heading_span=view.span(h.get('boundary_start',h['span']['char_start']),h.get('heading_end',h['span']['char_end']))
        address=dict(artifact_id=artifact_id,artifact_digest=digest(raw),profile_id=profile_id,profile_version=VERSION,scope=scope,kind=h['kind'],label=h['label'],span=span)
        unit_id=stable(address)
        node=dict(unit_id=unit_id,parent_id=stack[-1]['unit_id'] if stack else None,scope=scope,kind=h['kind'],label=h['label'],span=span,heading_span=heading_span,heading_text=_span_text(view,heading_span),marker_span=h['span'],marker_text=_span_text(view,h['span']),text=_span_text(view,span),heading_basis=h['heading_basis'])
        nodes.append(node);stack.append(node)
    heading_spans=[h['span'] for h in heads if h['kind'] in ('article','section','chapter','annex')];references=[]
    for row in candidates:
        if row['kind']=='chapter' or any(s['char_start']==row['span']['char_start'] for s in heading_spans):continue
        span=row['span'];pre=[n for n in nodes if n['kind'] in ('article','section') and n['span']['char_start']<=span['char_start']<n['span']['char_end']]
        context=pre[-1] if pre else None;scope=context['scope'] if context else None
        possible=[n for n in nodes if n['kind']==row['kind'] and n['label']==row['label'] and (scope is None or n['scope']==scope)]
        tail=view.matching[row['match_end']:row['match_end']+80]
        prefix=view.matching[max(0,row['match_start']-45):row['match_start']]
        components=[]
        chain=re.match(r'(?:(?:\s*第['+('0-9〇零一二三四五六七八九十百')+r']+[款項项号號])|(?:\s*(?:absatz|abs\.|satz|nummer|nr\.|alinéa|paragraph|пункт[а-я]*)\s*\d+)|(?:\s*\([0-9a-z]+\)))+',tail)
        if chain:components=list(tokenize(chain[0]));span=view.original_span(row['match_start'],row['match_end']+chain.end())
        reverse=bool(profile.language=='ru' and re.search(r'(?:пункт[а-я]*|част[а-я]*)\s+\d+\s*$',prefix))
        external=bool(profile.language=='de' and re.match(r'\s*(?:bgb|hgb|stgb|baunvo)\b',tail[chain.end():] if chain else tail))
        ranged=bool(re.match(r'\s*(?:-|to\b|bis\b|à\b|a\b|по\b|إلى|至|から)\s*\d+',tail))
        range_match=re.match(r'\s*(?:-|to\b|bis\b|à\b|a\b|по\b|إلى|至|から)\s*\d+',tail)
        if range_match:span=view.original_span(row['match_start'],row['match_end']+range_match.end())
        if reverse:
            reverse_match=re.search(r'(?:пункт[а-я]*|част[а-я]*)\s+\d+\s*$',prefix)
            span=view.original_span(max(0,row['match_start']-45)+reverse_match.start(),row['match_end'])
        if row['label'] is None:status='unsupported_number'
        elif external:status='external_unresolved'
        elif ranged:status='range_unresolved'
        elif chain or reverse:status='granularity_unresolved'
        elif scope is None:status='unknown_scope'
        elif len(possible)>1:status='ambiguous'
        elif not possible:status='missing'
        else:status='resolved'
        references.append(dict(kind=row['kind'],label=row['label'],span=span,text=_span_text(view,span),scope=scope,status=status,candidates=[n['unit_id'] for n in possible],components=components,reverse_chain=reverse))
    relative_words={'zh':('前条','前條','本条','本條'),'ja':('前条','同条','本条'),'en':('previous article','this article'),
                    'ru':('предыдущей статьи','настоящей статьи'),'fr':('article précédent','présent article'),
                    'ar':('المادة السابقة','هذه المادة'),'de':('vorherigen artikel','dieser artikel'),
                    'es':('artículo anterior','presente artículo'),'pt':('artigo anterior','presente artigo')}
    for phrase in relative_words[profile.language]:
        for m in re.finditer(re.escape(phrase),view.matching):
            span=view.original_span(m.start(),m.end())
            references.append(dict(kind='relative',label=phrase,span=span,text=_span_text(view,span),scope=None,status='relative_unresolved',candidates=[],components=[],reverse_chain=False))
    references.sort(key=lambda r:r['span']['char_start'])
    cues=[]
    for kind,word in zip(CUE_TYPES,CUE_WORDS[profile.language]):
        pattern=re.escape(TextView.from_bytes(word.encode('utf-8')).matching)
        if profile.language not in ('zh','ja'):pattern=r'(?<!\w)'+pattern+r'(?!\w)'
        for m in re.finditer(pattern,view.matching):
            span=view.original_span(m.start(),m.end());cues.append(dict(cue_type=kind,span=span,text=_span_text(view,span),status='lexical_observation_only'))
    if not nodes:diagnostics.append(('unsupported_structure',0,len(view.text)))
    if any(('a'<=c<='z') for c in view.matching) and profile.language=='ru':diagnostics.append(('latin_present_confusable_not_folded',0,len(view.text)))
    if profile.language=='ar' and re.search(r'ةدام(?:لا)?',view.matching):diagnostics.append(('visual_order_suspected_not_reversed',0,len(view.text)))
    result=dict(schema=SCHEMA,profile=profile.as_dict(),artifact_id=artifact_id,source_id=source_id,artifact_digest=digest(raw),original_text=view.text,original_byte_length=len(raw),normalization='cluster-NFKC-casefold-decimal-arabic-matching-only/2',heading_offsets=sorted(explicit) if explicit is not None else None,nodes=nodes,references=references,cues=cues,diagnostics=[dict(code=a,char_start=b,char_end=c) for a,b,c in diagnostics],authority_assessed=False,temporal_assessed=False)
    result['result_digest']=stable(result)
    return result

def resolve(result,*,kind,label,scope=None):
    if kind not in ('article','section','chapter','paragraph','item','subitem','annex') or not isinstance(label,str):
        raise ContractError('invalid_input','typed kind and string label required')
    matches=[n['unit_id'] for n in result['nodes'] if n['kind']==kind and n['label']==label and (scope is None or n['scope']==scope)]
    return dict(status='ambiguous' if len(matches)>1 else ('resolved' if matches else 'missing'),candidates=matches)

def citation(result,unit_id):
    matches=[n for n in result['nodes'] if n['unit_id']==unit_id]
    if len(matches)!=1:raise ContractError('missing' if not matches else 'ambiguous','unit identity')
    n=matches[0]
    return dict(schema=SCHEMA,artifact_id=result['artifact_id'],source_id=result['source_id'],artifact_digest=result['artifact_digest'],profile_id=result['profile']['profile_id'],profile_version=VERSION,unit_id=unit_id,span=n['span'].copy(),heading_span=n['heading_span'].copy(),heading_text=n['heading_text'],marker_span=n['marker_span'].copy(),marker_text=n['marker_text'],text=n['text'],text_digest=digest(n['text'].encode('utf-8')))

def reconstruct(raw,result,record):
    """Reparse the bound artifact, compare entire result and full native citation."""
    if not isinstance(result,dict) or not isinstance(record,dict):raise ContractError('invalid_input','object required')
    if result.get('schema')!=SCHEMA or record.get('schema')!=SCHEMA:raise ContractError('unsupported_schema','explicit version adapter required')
    try:
        rebuilt=analyze(raw,profile_id=result['profile']['profile_id'],artifact_id=result['artifact_id'],source_id=result['source_id'],expected_digest=result['artifact_digest'],heading_offsets=result['heading_offsets'])
        if rebuilt!=result:raise ContractError('integrity_failure','parse result mutated or incompatible')
        expected=citation(rebuilt,record['unit_id'])
        if record!=expected:raise ContractError('integrity_failure','citation fields disagree')
        return TextView.from_bytes(raw).extract(record['span'])
    except (KeyError,TypeError) as e:raise ContractError('invalid_input','malformed evidence/citation') from e

def validate_result(raw,result):
    """Deterministic semantic validation also covers empty/unsupported results."""
    if not isinstance(result,dict):raise ContractError('invalid_input','result object required')
    try:
        expected=analyze(raw,profile_id=result['profile']['profile_id'],artifact_id=result['artifact_id'],source_id=result['source_id'],expected_digest=result['artifact_digest'],heading_offsets=result['heading_offsets'])
        if expected!=result:raise ContractError('integrity_failure','noncanonical or altered result')
    except (KeyError,TypeError) as e:raise ContractError('invalid_input','malformed result') from e
    return True

def alignment_candidates(left,right,relationship):
    """No language similarity or equivalence inference; declaration is mandatory."""
    required={'relationship_id','left_digest','right_digest','type'}
    if not isinstance(relationship,dict) or set(relationship)!=required or relationship['type']!='declared_translation' or not relationship['relationship_id']:
        raise ContractError('undeclared_translation','explicit exact-artifact relationship required')
    if relationship['left_digest']!=left['artifact_digest'] or relationship['right_digest']!=right['artifact_digest']:
        raise ContractError('integrity_failure','relationship artifact mismatch')
    output=[]
    for node in left['nodes']:
        same=[n for n in right['nodes'] if (n['scope'],n['kind'],n['label'])==(node['scope'],node['kind'],node['label'])]
        left_count=sum((n['scope'],n['kind'],n['label'])==(node['scope'],node['kind'],node['label']) for n in left['nodes'])
        output.append(dict(left=node['unit_id'],right_candidates=[n['unit_id'] for n in same],status=('ambiguous' if left_count>1 else 'structural_candidate') if len(same)==1 else ('ambiguous' if same else 'missing'),legal_equivalence=False,authority_assessed=False))
    return output
