"""Bounded source-layout rules 1.1.0; no legal-effect interpretation."""
import re

def inline_heading(profile,marker,matching_tail,original_tail):
    """Return recognized/basis/scope hint. Unrecognized forms remain uncertain."""
    tail=matching_tail.strip()
    if profile.language=='ar' and tail=='(إصدار)':
        return True,'observed_issuance_qualifier','promulgation'
    if profile.language=='ru' and re.fullmatch(r'статья\s+[0-9]+(?:\.[0-9]+)*',marker.strip()):
        # The official source has nominative label + number + period + nominal
        # title. Inflected references and obvious sentence openings abstain.
        title=re.match(r'^\.\s+([А-ЯЁ][^\n]*)$',original_tail.strip())
        if title:
            first=title[1].split()[0].casefold().strip('.,:;')
            blocked=('это','применяется','применяются','устанавливает','предусматривает','гласит','не','должна','должен','может','согласно')
            if first not in blocked and not re.search(r'[!?;]|\.\s+[А-ЯЁ]',title[1]):
                return True,'nominative_dot_nominal_title',None
    # Explicit title separators have a bounded, visible layout role. Bare
    # line-initial prose such as "Article 1 applies ..." is never upgraded.
    if profile.language=='fr' and re.match(r'^\s*[-:]\s*\S',matching_tail):
        return True,'explicit_title_separator',None
    return False,None,None

def container_line(language,line,words):
    for word in words:
        prefix=re.escape(word)
        if language=='ja' and word in ('附則','附 則'):prefix=r'附\s*則'
        if re.fullmatch(prefix+r'(?:\s+[0-9ivxlcdm]+)?(?:\s*[（(][^\n]*[）)])?',line):return True
        if language=='es' and word.startswith('disposición') and re.fullmatch(prefix+r'\s+(?:primera|segunda|tercera|cuarta|quinta)\.?',line):return True
    return False
