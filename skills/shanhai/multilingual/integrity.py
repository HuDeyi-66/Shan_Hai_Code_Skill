"""L0: immutable originals and original-anchored Unicode matching views."""
from dataclasses import dataclass
import hashlib
import unicodedata as ud

class ContractError(ValueError):
    def __init__(self, code, detail):
        self.code=code
        super().__init__(code+': '+detail)

def digest(raw):
    return 'sha256:'+hashlib.sha256(raw).hexdigest()

@dataclass(frozen=True)
class TextView:
    original: bytes
    text: str
    matching: str
    anchors: tuple
    byte_offsets: tuple
    diagnostics: tuple

    @classmethod
    def from_bytes(cls, raw):
        if not isinstance(raw,bytes):raise ContractError('invalid_input','immutable UTF-8 bytes required')
        try:text=raw.decode('utf-8')
        except UnicodeDecodeError as e:raise ContractError('encoding_failure',str(e)) from e
        matching=[];anchors=[];diagnostics=[];offsets=[0];i=0
        for ch in text:offsets.append(offsets[-1]+len(ch.encode('utf-8')))
        while i<len(text):
            start=i;i+=1
            while i<len(text) and ud.combining(text[i]):i+=1
            cluster=text[start:i]
            if any(ud.category(c)=='Cf' for c in cluster):diagnostics.append(('format_mark',start,i))
            value=ud.normalize('NFKC',''.join(c for c in cluster if ud.category(c)!='Cf')).casefold()
            retained=''.join(c for c in value if c!='\u0640' and not ('\u064b'<=c<='\u065f' or c=='\u0670'))
            if retained!=value:diagnostics.append(('arabic_matching_elision',start,i))
            value=retained
            for c in value:
                if c in '‐‑‒–—−':c='-'
                if c.isspace() and c not in '\r\n':c=' '
                try:c=str(ud.decimal(c))
                except ValueError:pass
                matching.append(c);anchors.append((start,i))
        if text.startswith('\ufeff'):diagnostics.append(('bom_preserved',0,1))
        if '\ufffd' in text:diagnostics.append(('replacement_character_present',text.index('\ufffd'),text.index('\ufffd')+1))
        return cls(raw,text,''.join(matching),tuple(anchors),tuple(offsets),tuple(diagnostics))

    def span(self,start,end):
        if type(start) is not int or type(end) is not int or not 0<=start<=end<=len(self.text):
            raise ContractError('invalid_span','original code-point interval required')
        return dict(char_start=start,char_end=end,byte_start=self.byte_offsets[start],byte_end=self.byte_offsets[end])

    def original_span(self,start,end):
        if type(start) is not int or type(end) is not int or not 0<=start<end<=len(self.matching):raise ContractError('invalid_span','nonempty matching interval required')
        return self.span(self.anchors[start][0],self.anchors[end-1][1])

    def extract(self,span):
        if not isinstance(span,dict):raise ContractError('invalid_span','span object required')
        expected=self.span(span.get('char_start'),span.get('char_end'))
        if expected!=span:raise ContractError('integrity_failure','byte/character offsets disagree')
        return self.text[expected['char_start']:expected['char_end']]
