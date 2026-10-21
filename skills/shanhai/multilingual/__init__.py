"""Opt-in multilingual evidence 1.0.0; legacy ShanHai API is unchanged."""
from .analyzer import analyze,citation,reconstruct,alignment_candidates,tokenize,resolve,validate_result
from .integrity import ContractError,TextView,digest
from .profiles import PROFILES,VERSION,SCHEMA,get_profile,numeral
from .discovery import analyze_auto

__all__=['analyze','analyze_auto','citation','reconstruct','alignment_candidates','tokenize','resolve','validate_result',
         'ContractError','TextView','digest','PROFILES','VERSION','SCHEMA',
         'get_profile','numeral']
