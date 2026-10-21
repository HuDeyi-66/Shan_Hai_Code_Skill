"""Opt-in source-faithful chunking 1.0.0; no legal-semantic claims."""
from .api import (
    CONTRACT, LANGUAGES, ChunkConfig, ChunkingError, chunk, citation,
    make_representation, reconstruct, reconstruct_many, validate_result,
)

__all__ = ['CONTRACT', 'LANGUAGES', 'ChunkConfig', 'ChunkingError', 'chunk',
           'citation', 'make_representation', 'reconstruct', 'reconstruct_many', 'validate_result']
