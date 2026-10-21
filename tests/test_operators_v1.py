"""B-stage acceptance: hand-authored source oracles, no operator-generated gold."""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _bootstrap  # noqa: F401,E402
from skills.shanhai.operators_v1 import (Representation, SourceBinding, ReferenceRequest,
    STRUCTURE, RESOLVE_REFS)
from skills.shanhai.multilingual.integrity import digest


def build(text='Article 1\nSee Article 2.\nArticle 2\nBody.\n', profile='en-EU-act', offsets=None):
    raw = text.encode('utf-8')
    r = Representation(raw, 'R:oracle')
    b = SourceBinding('source:oracle', 'R:oracle', digest(raw), 'A:caller-declared')
    return r, b, STRUCTURE(r, profile, b, heading_offsets=offsets)


class StructureAcceptance(unittest.TestCase):
    def test_typed_observations_and_native_text_facts(self):
        r, binding, result = build()
        self.assertEqual(result.status, 'observed')
        self.assertEqual(result.binding, binding)
        self.assertEqual(result.input_digest, digest(r.raw))
        self.assertEqual(result.source_qualification, 'unavailable')
        articles = [o for o in result.observations if o.kind == 'article']
        self.assertEqual([o.label for o in articles], ['1', '2'])
        self.assertEqual(articles[0].text, 'Article 1\nSee Article 2.\n')
        self.assertEqual(articles[0].marker_span, dict(char_start=0, char_end=9, byte_start=0, byte_end=9))
        self.assertEqual(articles[0].structure_basis, 'heuristic_observation')
        self.assertTrue(all(o.text_basis == 'R_bytes_verified' for o in result.observations))
        self.assertTrue(all(o.parent_basis == 'heuristic_observation' for o in result.observations))

    def test_modified_bytes_refused(self):
        r, b, _ = build()
        self.assertEqual(STRUCTURE(replace(r, raw=r.raw+b'x'), 'en-EU-act', b).status, 'refused')

    def test_modified_digest_refused(self):
        r, b, _ = build()
        self.assertEqual(STRUCTURE(r, 'en-EU-act', replace(b, expected_digest='sha256:wrong')).status, 'refused')

    def test_incorrect_representation_identity_refused(self):
        r, b, _ = build()
        bad = STRUCTURE(replace(r, representation_id='R:other'), 'en-EU-act', b)
        self.assertEqual(bad.diagnostics[0].code, 'representation_mismatch')

    def test_caller_headings_are_assertions(self):
        r, b, result = build('Article 7 A prose sentence.\n', offsets=[0])
        self.assertEqual(result.observations[0].heading_basis, 'source_declared')
        self.assertEqual(result.observations[0].structure_basis, 'caller_assertion')

    def test_source_qualification_refused(self):
        r, b, _ = build()
        result = STRUCTURE(r, 'en-EU-act', replace(b, require_source_qualification=True))
        self.assertEqual(result.status, 'refused')
        self.assertEqual(result.diagnostics[0].code, 'source_qualification_unavailable')

    def test_unavailable_structure(self):
        self.assertEqual(build('ordinary text without markers')[2].status, 'unavailable')

    def test_parent_relations_preserved_as_heuristics(self):
        result = build('Article 1\n(1) A paragraph.\n(a) An item.\n')[2]
        nodes = {o.unit_id: o for o in result.observations}
        children = [o for o in result.observations if o.parent_id]
        self.assertTrue(children)
        self.assertTrue(all(o.parent_id in nodes and o.parent_basis == 'heuristic_observation' for o in children))

    def test_nine_language_unicode_oracle_spans(self):
        cases = [('zh-CN-statute', '第一条'), ('en-EU-act', 'Article 1'),
            ('ja-egov-statute', '第一条'), ('ru-federal-statute', 'Статья 1'),
            ('fr-code', 'Article 1'), ('ar-QA-statute', 'المادة ١'),
            ('de-federal-statute', 'Artikel 1'), ('es-EU-act', 'Artículo 1'),
            ('pt-EU-act', 'Artigo 1')]
        prefix = '🌊 e\u0301\r\n'
        for profile, marker in cases:
            with self.subTest(profile=profile):
                text = prefix + marker + '\r\n正文 café العربية\n'
                r, _, result = build(text, profile, [len(prefix)])
                self.assertEqual(result.status, 'observed')
                article = next(o for o in result.observations if o.kind == 'article')
                self.assertEqual(article.marker_text, marker)
                expected = dict(char_start=len(prefix), char_end=len(prefix)+len(marker),
                    byte_start=len(prefix.encode('utf-8')), byte_end=len((prefix+marker).encode('utf-8')))
                self.assertEqual(article.marker_span, expected)
                for o in result.observations:
                    for key in ('span', 'heading_span', 'marker_span'):
                        span = getattr(o, key)
                        self.assertEqual(r.raw[span['byte_start']:span['byte_end']].decode(),
                                         text[span['char_start']:span['char_end']])

    def test_deterministic_without_input_mutation(self):
        r, b, result = build()
        before = deepcopy(result)
        self.assertEqual(result, STRUCTURE(r, 'en-EU-act', b))
        self.assertEqual(result, before)


class ReferenceAcceptance(unittest.TestCase):
    def test_unique_source_label_match_is_not_legal_correctness(self):
        r, _, s = build()
        out = RESOLVE_REFS(r, s, ReferenceRequest(observation_index=0))
        self.assertEqual(out.status, 'unique_source_label_match')
        self.assertEqual(out.candidates[0]['marker_text'], 'Article 2')
        self.assertEqual(out.reference['text'], 'Article 2')
        self.assertEqual(out.legal_reference_correctness, 'not_assessed')
        self.assertEqual(out.contextual_uniqueness, 'not_established')

    def test_mutated_analysis_even_with_recomputed_digest_refused(self):
        from skills.shanhai.multilingual.analyzer import stable
        r, _, result = build()
        for field, value in [('text', 'invented'), ('label', '999'), ('parent_id', 'fake')]:
            with self.subTest(field=field):
                bad = deepcopy(result)
                bad.analysis['nodes'][0][field] = value
                body = {k: v for k, v in bad.analysis.items() if k != 'result_digest'}
                bad.analysis['result_digest'] = stable(body)
                self.assertEqual(RESOLVE_REFS(r, bad, ReferenceRequest(kind='article', label='1', scope='document')).status, 'refused')

    def test_mutated_wrapper_classification_refused(self):
        r, _, result = build()
        bad = replace(result, observations=(replace(result.observations[0], text_basis='legal_verified'),))
        self.assertEqual(RESOLVE_REFS(r, bad, ReferenceRequest(kind='article', label='1')).status, 'refused')

    def test_wrong_R_identity_and_modified_bytes_refused(self):
        r, _, s = build()
        for bad in (replace(r, representation_id='other'), replace(r, raw=r.raw+b'x')):
            self.assertEqual(RESOLVE_REFS(bad, s, ReferenceRequest(observation_index=0)).status, 'refused')

    def test_duplicate_labels_preserve_all_candidates_in_source_order(self):
        r, _, s = build('Article 2\nOne.\nArticle 2\nTwo.\n')
        out = RESOLVE_REFS(r, s, ReferenceRequest(kind='article', label='2', scope='document'))
        self.assertEqual(out.status, 'ambiguous')
        self.assertEqual(len(out.candidates), 2)
        self.assertEqual([c['text'] for c in out.candidates], ['Article 2\nOne.\n', 'Article 2\nTwo.\n'])

    def test_missing_known_scope_and_unknown_scope(self):
        r, _, s = build()
        self.assertEqual(RESOLVE_REFS(r, s, ReferenceRequest(kind='article', label='99', scope='document')).status, 'missing')
        self.assertEqual(RESOLVE_REFS(r, s, ReferenceRequest(kind='article', label='1', scope='annex:99')).status, 'unknown_scope')

    def test_scope_free_single_match_not_contextual_uniqueness(self):
        r, _, s = build()
        out = RESOLVE_REFS(r, s, ReferenceRequest(kind='article', label='1'))
        self.assertEqual(out.status, 'unknown_scope')
        self.assertEqual(len(out.candidates), 1)
        self.assertEqual(out.label_search_status, 'resolved')

    def test_relative_range_external_granularity_states(self):
        cases = [('en-EU-act', 'Article 1\nSee previous article.\n', 'relative'),
                 ('en-EU-act', 'Article 1\nSee Article 2 to 4.\nArticle 2\nText.\n', 'range'),
                 ('de-federal-statute', 'Artikel 1\nSiehe Artikel 2 BGB.\nArtikel 2\nText.\n', 'external'),
                 ('en-EU-act', 'Article 1\nSee Article 2(1).\nArticle 2\nText.\n', 'granularity_unresolved')]
        for profile, text, state in cases:
            with self.subTest(state=state):
                r, _, s = build(text, profile)
                out = RESOLVE_REFS(r, s, ReferenceRequest(observation_index=0))
                self.assertEqual(out.status, state)

    def test_unknown_observation_scope(self):
        r, _, s = build('See Article 2.\nArticle 2\nText.\n')
        out = RESOLVE_REFS(r, s, ReferenceRequest(observation_index=0))
        self.assertEqual(out.status, 'unknown_scope')
        self.assertEqual(len(out.candidates), 1)

    def test_unsupported_number_observation(self):
        r, _, s = build('第一条\n见第十百条。\n', 'zh-CN-statute')
        out = RESOLVE_REFS(r, s, ReferenceRequest(observation_index=0))
        self.assertEqual(out.status, 'unsupported')
        self.assertEqual(out.candidates, ())

    def test_unsupported_kind_and_conflicting_request_refused(self):
        r, _, s = build()
        self.assertEqual(RESOLVE_REFS(r, s, ReferenceRequest(kind='foreign-law', label='1')).status, 'refused')
        self.assertEqual(RESOLVE_REFS(r, s, ReferenceRequest(observation_index=0, scope='document')).status, 'refused')

    def test_deterministic_and_nonmutating(self):
        r, _, s = build()
        before = deepcopy(s)
        req = ReferenceRequest(observation_index=0)
        self.assertEqual(RESOLVE_REFS(r, s, req), RESOLVE_REFS(r, s, req))
        self.assertEqual(s, before)


if __name__ == '__main__':
    unittest.main()
