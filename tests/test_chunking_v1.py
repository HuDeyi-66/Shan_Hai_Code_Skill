"""Bounded source-chunk contract tests. All examples are synthetic development data."""
import copy,hashlib,json,random,unittest
import _bootstrap
from skills.shanhai.chunking import (LANGUAGES,ChunkConfig,ChunkingError,chunk,
    citation,make_representation,reconstruct,reconstruct_many,validate_result)

TEXTS={'zh':'\ufeff　第一条　海事规则。\r\n第二条　原文尾部。  ',
       'en':'\ufeff Preamble\r\nArticle 1. Maritime café evidence.\nTail \t',
       'ja':'\ufeff（目的）\n第一条　船舶の証拠。\n末尾　',
       'ru':'\ufeff Преамбула\nСтатья 1. Морской ёж.\nКонец  ',
       'fr':'\ufeff Préambule\nArticle 1. Éléments maritimes.\nFin  ',
       'ar':'\ufeff\u200fالمادة ١\nسَفِينَةٌ وبيّنة\u200e\nالنهاية  ',
       'de':'\ufeff Präambel\n§ 1. Schifffahrt und Größe.\nEnde  ',
       'es':'\ufeff Preámbulo\nArtículo 1. Navegación.\nFin  ',
       'pt':'\ufeff Preâmbulo\nArtigo 1.º Navegação.\nFim  '}
def sha(raw):return hashlib.sha256(raw).hexdigest()
def rep(raw):
    return make_representation(raw,source_id='synthetic-development',artifact_id='synthetic-A',artifact_sha256=sha(raw),source_uri='urn:synthetic:development',qualification_id='synthetic-C-not-acceptance',
        derivation=dict(schema='shanhai-text-derivation/1.0.0',method='identity-utf8',artifact_sha256=sha(raw),representation_sha256=sha(raw),mapping_sha256=None,qualification_receipt_sha256=None,exclusions=[],generated_layout=[],information_loss=[]))
def cue(raw,position,id='cue',verification='independently_verified'):
    return dict(position=position,kind='source_observed_break',verification=verification,evidence_id=id,evidence_sha256='1'*64,representation_sha256=sha(raw))
class ChunkingTests(unittest.TestCase):
    def test_all_nine_languages_exact_whitespace_unicode_and_citations(self):
        for language,text in TEXTS.items():
            raw=text.encode();r=chunk(raw,representation=rep(raw),language=language,config=ChunkConfig(8,3))
            with self.subTest(language=language):
                self.assertEqual(''.join(c['text'] for c in r['primary_chunks']),text)
                records=[citation(r,c['chunk_id']) for c in r['primary_chunks']+r['secondary_chunks']]
                self.assertEqual(reconstruct_many(raw,r,records),[c['text'] for c in r['primary_chunks']+r['secondary_chunks']])
                self.assertTrue(validate_result(raw,r));self.assertEqual(r,chunk(raw,representation=rep(raw),language=language,config=ChunkConfig(8,3)))
    def test_primary_partition_excludes_secondary_from_denominator(self):
        raw=b'  preamble\n0123456789\n tail  ';r=chunk(raw,representation=rep(raw),language='en',config=ChunkConfig(5,5))
        self.assertEqual(r['coverage']['primary_codepoints'],len(raw));self.assertEqual(r['coverage']['primary_overlap'],0)
        self.assertGreater(sum(len(c['text']) for c in r['primary_chunks']+r['secondary_chunks']),len(raw))
        self.assertFalse(r['coverage']['secondary_in_primary_denominator'])
    def test_verified_cues_candidates_and_oversized_fallback(self):
        raw=b'012345678901234567890';cues=[cue(raw,3),cue(raw,5,'ignored','candidate'),cue(raw,18,'later')]
        r=chunk(raw,representation=rep(raw),language='en',config=ChunkConfig(6),cues=cues)
        self.assertEqual([c['span']['char_end'] for c in r['primary_chunks']],[3,9,15,21])
        self.assertEqual(r['primary_chunks'][0]['boundary_status'],'verified_source_cue')
        self.assertEqual(r['primary_chunks'][1]['boundary_status'],'budget_split_without_eligible_verified_cue')
        self.assertEqual(r['uncertainty']['candidate_cues_ignored'],1)
        self.assertTrue(all(c['legal_unit_type'] is None for c in r['primary_chunks']))
    def test_no_cues_uses_deterministic_unclassified_fallback(self):
        raw='没有条款编号\n???'.encode();r=chunk(raw,representation=rep(raw),language='zh',config=ChunkConfig(2))
        self.assertEqual(r['primary_chunks'][0]['boundary_status'],'no_verified_cues_fallback')
        self.assertTrue(all(c['citation']['reference_target_status']=='not_assessed' for c in r['primary_chunks']))
    def test_combining_emoji_bidi_sequences_and_budget_one(self):
        raw=' e\u0301👩\u200d🚢\u202eم\u202c\r\n\u00a0'.encode();r=chunk(raw,representation=rep(raw),language='ar',config=ChunkConfig(1))
        self.assertTrue(all(len(c['text'])==1 for c in r['primary_chunks']));self.assertEqual(''.join(c['text'] for c in r['primary_chunks']).encode(),raw)
        self.assertFalse(r['uncertainty']['grapheme_preservation_guaranteed'])
    def test_invalid_configuration_per_language(self):
        for language in LANGUAGES:
            raw=TEXTS[language].encode()
            for width in [0,-1,True,1.5,'8',None]:
                with self.subTest(language=language,width=width),self.assertRaises(ChunkingError) as error:chunk(raw,representation=rep(raw),language=language,config=ChunkConfig(width))
                self.assertEqual(error.exception.code,'invalid_config')
        for context in [-1,True,1.5,9]:
            with self.assertRaises(ChunkingError):chunk(b'x',representation=rep(b'x'),language='en',config=ChunkConfig(8,context))
    def test_unsupported_language_profile_and_auto_are_distinct(self):
        raw=b'Article 1'
        for kw,code in [({'language':'xx'},'unsupported_language'),({'language':'en','profile_id':'de:source-faithful-text/1.0.0'},'unsupported_profile'),({'language':'en','language_mode':'auto'},'automatic_detection_not_supported')]:
            with self.assertRaises(ChunkingError) as error:chunk(raw,representation=rep(raw),**kw)
            self.assertEqual(error.exception.code,code)
    def test_empty_and_invalid_utf8(self):
        r=chunk(b'',representation=rep(b''),language='en');self.assertEqual(r['status'],'EMPTY_INPUT');self.assertEqual(r['primary_chunks'],[])
        for raw in [b'\xff',bytearray(b'x'),'text']:
            with self.assertRaises(ChunkingError):chunk(raw,representation=rep(b'x'),language='en')
    def test_representation_integrity_and_external_projection_binding(self):
        raw='船舶\n'.encode();record=rep(raw);record['artifact_sha256']='2'*64
        with self.assertRaises(ChunkingError):chunk(raw,representation=record,language='zh')
        derivation=dict(schema='shanhai-text-derivation/1.0.0',method='qualified-external-projection',artifact_sha256='2'*64,representation_sha256=sha(raw),mapping_sha256='3'*64,qualification_receipt_sha256='4'*64,exclusions=[{'reason':'declared markup outside text'}],generated_layout=[{'text':'\n'}],information_loss=['visual style'])
        record=make_representation(raw,source_id='synthetic',artifact_id='A-xml',artifact_sha256='2'*64,source_uri='urn:synthetic:A',qualification_id='synthetic-only',derivation=derivation)
        r=chunk(raw,representation=record,language='zh');self.assertNotEqual(r['representation']['artifact_sha256'],r['representation']['representation_sha256'])
        self.assertEqual(r['primary_chunks'][0]['citation']['byte_end'],len(raw))
        bad=copy.deepcopy(record);bad['derivation']['mapping_sha256']=None
        with self.assertRaises(ChunkingError):chunk(raw,representation=bad,language='zh')
    def test_bad_cues_missing_duplicate_and_unbound(self):
        raw=b'0123456789'
        for cues in [[cue(raw,True)],[cue(raw,99)],[cue(raw,1),cue(raw,2)], [{**cue(raw,1),'representation_sha256':'0'*64}], [{'position':1}]]:
            with self.assertRaises(ChunkingError):chunk(raw,representation=rep(raw),language='en',cues=cues)
    def test_native_citation_and_result_mutations_refuse(self):
        raw='é海\r\n原文  '.encode();r=chunk(raw,representation=rep(raw),language='zh',config=ChunkConfig(3));record=citation(r,r['primary_chunks'][0]['chunk_id'])
        for key,value in [('artifact_sha256','0'*64),('char_end',99),('byte_start',1),('reference_target_status','resolved'),('schema','old')]:
            bad={**record,key:value}
            with self.subTest(key=key),self.assertRaises(ChunkingError):reconstruct(raw,r,bad)
        for field in ['text','role','span']:
            bad=copy.deepcopy(r)
            if field=='text':bad['primary_chunks'][0]['text']='invented'
            if field=='role':bad['primary_chunks'][0]['role']='secondary_context'
            if field=='span':bad['primary_chunks'][0]['span']['char_start']=1
            with self.subTest(field=field),self.assertRaises(ChunkingError):validate_result(raw,bad)
        with self.assertRaises(ChunkingError):reconstruct(raw+b' ',r,record)
        with self.assertRaises(ChunkingError):citation(r,'missing')
    def test_cue_order_does_not_change_result_and_no_input_mutation(self):
        raw=b'01234567890123456789';cues=[cue(raw,3,'a'),cue(raw,8,'b')];saved=copy.deepcopy(cues);representation=rep(raw);before=copy.deepcopy(representation)
        a=chunk(raw,representation=representation,language='en',cues=cues,config=ChunkConfig(6));b=chunk(raw,representation=representation,language='en',cues=list(reversed(cues)),config=ChunkConfig(6))
        self.assertEqual(a,b);self.assertEqual(cues,saved);self.assertEqual(representation,before)
    def test_deterministic_partition_property_over_unicode_inputs(self):
        rng=random.Random(3401);alphabet=' \r\n\t海あéёم\u200f\u0301👩\u200d'
        for case in range(60):
            text=''.join(rng.choice(alphabet) for _ in range(rng.randrange(100)));raw=text.encode();width=rng.randrange(1,15);r=chunk(raw,representation=rep(raw),language=LANGUAGES[case%9],config=ChunkConfig(width,rng.randrange(width+1)))
            self.assertEqual(''.join(c['text'] for c in r['primary_chunks']),text)
            previous=0
            for c in r['primary_chunks']:
                self.assertEqual(c['span']['char_start'],previous);previous=c['span']['char_end'];self.assertLessEqual(len(c['text']),width)
            self.assertEqual(previous,len(text));self.assertTrue(validate_result(raw,r))
    def test_legacy_multilingual_interface_remains_separate_and_usable(self):
        from skills.shanhai import multilingual as legacy
        raw=b'Article 1\nOriginal.\nArticle 2\nMore original.\n'
        profile=next(p.profile_id for p in legacy.PROFILES.values() if p.language=='en')
        old=legacy.analyze(raw,profile_id=profile,artifact_id='legacy-artifact',source_id='legacy-source')
        native=legacy.citation(old,old['nodes'][0]['unit_id']);self.assertTrue(legacy.reconstruct(raw,old,native))
        result=chunk(raw,representation=rep(raw),language='en')
        with self.assertRaises(ChunkingError) as error:reconstruct(raw,result,native)
        self.assertEqual(error.exception.code,'unsupported_citation')
        with self.assertRaises(ChunkingError) as error:validate_result(raw,old)
        self.assertEqual(error.exception.code,'unsupported_schema')
        prefixed=rep(raw);prefixed['artifact_sha256']='sha256:'+sha(raw)
        with self.assertRaises(ChunkingError):chunk(raw,representation=prefixed,language='en')
if __name__=='__main__':unittest.main(verbosity=2)
