"""Versioned language × drafting family × document family declarations."""
from dataclasses import dataclass,asdict
import re
from .integrity import ContractError

VERSION='1.1.0'
SCHEMA='shanhai-multilingual-evidence/1.1.0'
CJK='0-9〇零一二三四五六七八九十百千万萬亿億兩两壹貳贰參叁肆伍陸陆柒捌玖拾佰仟'

@dataclass(frozen=True)
class Profile:
    profile_id:str
    language:str
    variant:str
    drafting_family:str
    document_family:str
    version:str=VERSION
    heading_policy:str='standalone_or_explicit'
    def as_dict(self):return asdict(self)

_SPECS=[('zh-CN-statute','zh','zh-CN','modern-Chinese','statute','cjk_line'),
('en-EU-act','en','en-EU','EU','act','standalone_or_explicit'),
('en-commonlaw-statute','en','en','common-law','statute','standalone_or_explicit'),
('ja-egov-statute','ja','ja-JP','e-Gov','statute','cjk_line'),
('ru-federal-statute','ru','ru-RU','federal','statute','nominative_dot_nominal_title'),
('fr-EU-act','fr','fr-EU','EU','act','standalone_or_explicit'),
('fr-code','fr','fr-FR','French-code','code','standalone_or_explicit'),
('ar-QA-statute','ar','ar-QA','Qatar','statute','standalone_or_issuance_qualifier'),
('de-EU-act','de','de-EU','EU','act','standalone_or_explicit'),
('de-federal-statute','de','de-DE','federal','statute','standalone_or_explicit'),
('es-EU-act','es','es-EU','EU','act','standalone_or_explicit'),
('es-ordinal-statute','es','es','Iberian-ordinal','statute','standalone_or_explicit'),
('pt-EU-act','pt','pt-PT','European-Portuguese','act','standalone_or_explicit'),
('pt-BR-statute','pt','pt-BR','Brazilian','statute','standalone_or_explicit')]
PROFILES={s[0]:Profile(*s[:5],heading_policy=s[5]) for s in _SPECS}

def get_profile(profile_id):
    if not isinstance(profile_id,str):raise ContractError('invalid_input','profile_id must be a string')
    if profile_id not in PROFILES:raise ContractError('unsupported_profile',str(profile_id))
    return PROFILES[profile_id]

_CJK_DIGITS={c:i for i,c in enumerate('零一二三四五六七八九')}
_CJK_DIGITS['〇']=0
_TRAD=str.maketrans('萬億兩两壹貳贰參叁肆伍陸陆柒捌玖拾佰仟','万亿二二一二二三三四五六六七八九十百千')
def numeral(value):
    v=value.strip().translate(_TRAD)
    if v.isdecimal():return int(v)
    if not v:raise ContractError('unsupported_number','empty')
    if all(c in _CJK_DIGITS for c in v):return int(''.join(str(_CJK_DIGITS[c]) for c in v))
    total=section=current=0;last_small=10000;previous_digit=False
    for c in v:
        if c in _CJK_DIGITS:
            if previous_digit and current!=0:raise ContractError('unsupported_number','consecutive digits in unit-form numeral')
            current=_CJK_DIGITS[c];previous_digit=True
        elif c in '十百千':
            unit={'十':10,'百':100,'千':1000}[c]
            if unit>=last_small:raise ContractError('unsupported_number',value)
            section+=(current or 1)*unit;current=0;last_small=unit;previous_digit=False
        elif c in '万亿':
            section+=current;current=0
            if c=='万':total+=(section or 1)*10000
            else:total=(total+section or 1)*100000000
            section=0;last_small=10000;previous_digit=False
        else:raise ContractError('unsupported_number',value)
    return total+section+current

# Label grammar is per language. Regexes are lexical recognizers, not resolvers.
_ID=r'(?P<id>[0-9]+(?:\.[0-9]+)*(?:\.?[ºo])?(?:[a-np-z])?(?:-[0-9a-z]+)*|[ivxlcdm]+)'
LABELS={
'zh':[(r'第\s*(?P<id>['+CJK+r']+)\s*[条條](?P<suffix>(?:之['+CJK+r']+)*)','article'),(r'第\s*(?P<id>['+CJK+r']+)\s*章','chapter')],
'ja':[(r'第\s*(?P<id>['+CJK+r']+)\s*[条條](?P<suffix>(?:[のノ]['+CJK+r']+)*)','article'),(r'第\s*(?P<id>['+CJK+r']+)\s*章','chapter')],
'en':[(r'\barticles?\s+'+_ID,'article'),(r'\bsections?\s+'+_ID,'section'),(r'\bchapters?\s+'+_ID,'chapter')],
'ru':[(r'\bстать(?:я|и|е|ю|ёй|ей|ях|ями)\s+'+_ID,'article'),(r'\bглав(?:а|ы|е)\s+'+_ID,'chapter')],
'fr':[(r'\barticles?\s+(?P<id>premier|1er|(?:[lr]\.?\s*)?[0-9]+(?:-[0-9]+)*(?:\s*(?:bis|ter))?)','article'),(r'\bchapitre\s+'+_ID,'chapter')],
'ar':[(r'(?:ال)?ماد[ةه]\s*(?P<open>\()?\s*(?P<id>[0-9]+)(?(open)\s*\))','article'),(r'الباب\s+(?P<id>[0-9]+)','chapter')],
'de':[(r'\bartikel\s+'+_ID,'article'),(r'§{1,2}\s*'+_ID,'section'),(r'\bkapitel\s+'+_ID,'chapter')],
'es':[(r'\bart[íi]culos?\s+'+_ID,'article'),(r'\bcap[íi]tulo\s+'+_ID,'chapter')],
'pt':[(r'\bartigos?\s+'+_ID,'article'),(r'\bart\.\s*'+_ID,'article'),(r'\bcap[íi]tulo\s+'+_ID,'chapter')]}
# A label cannot eat a physical newline and silently absorb its body text.
LABELS={language:[(pattern.replace(r'\s',r'[^\S\r\n]'),kind) for pattern,kind in rules] for language,rules in LABELS.items()}
CONTAINERS={
'zh':('附则','附則','附件'),'ja':('附則','附 則','別表','付録'),
'en':('annex','schedule','supplementary provisions'),'ru':('приложение',),
'fr':('annexe',),'ar':('ملحق',),'de':('anhang','anlage'),
'es':('anexo','disposición adicional','disposición transitoria'),
'pt':('anexo','disposições transitórias','disposições adicionais')}

def identifier(match,language):
    raw=match.group('id').strip()
    if language=='fr' and raw in ('premier','1er'):return '1'
    if language in ('zh','ja'):
        result=str(numeral(raw));suffix=match.groupdict().get('suffix') or ''
        for s in re.split('[之のノ]',suffix)[1:]:result+='~'+str(numeral(s))
        return result
    raw=re.sub(r'\s+','',raw)
    raw=re.sub(r'\.?[ºo](?=-|$)','',raw)
    if re.fullmatch('[ivxlcdm]+',raw):
        values={'i':1,'v':5,'x':10,'l':50,'c':100,'d':500,'m':1000};n=0;prev=0
        for c in reversed(raw):n+=-values[c] if values[c]<prev else values[c];prev=max(prev,values[c])
        parts=[];remaining=n
        for k,v in [(1000,'m'),(900,'cm'),(500,'d'),(400,'cd'),(100,'c'),(90,'xc'),(50,'l'),(40,'xl'),(10,'x'),(9,'ix'),(5,'v'),(4,'iv'),(1,'i')]:
            while remaining>=k:parts.append(v);remaining-=k
        if ''.join(parts)!=raw:raise ContractError('unsupported_number',raw)
        return str(n)
    return raw.replace('l.','l.').replace('r.','r.')

CUE_WORDS={
'zh':('应当','可以','不得','如果','除外','不','是指','修改'),
'en':('shall','may','must not','if','except','not','means','amended'),
'ja':('しなければならない','できる','してはならない','場合','除く','ない','とは','改正'),
'ru':('обязан','может','запрещается','если','кроме','не','означает','изменение'),
'fr':('doit','peut','interdit','si','sauf','ne','entend par','modifié'),
'ar':('يجب','يجوز','يحظر','إذا','باستثناء','لا','يقصد','تعديل'),
'de':('muss','darf','darf nicht','wenn','außer','nicht','bedeutet','geändert'),
'es':('deberá','podrá','prohíbe','si','excepto','no','significa','modificado'),
'pt':('deve','pode','proibido','se','salvo','não','entende-se','alterado')}
CUE_TYPES=('obligation_wording','permission_wording','prohibition_wording','condition_wording','exception_wording','negation_wording','definition_wording','amendment_wording')
