# Public input contract hardening

`run_legal_text_evidence` accepts paths, immutable UTF-8 bytes, bytearrays (copied to immutable bytes), or a `TextArtifact`. Byte input uses the existing parser and verifies the artifact digest before extraction. It does not create a temporary file or infer legal authority. `TextArtifact.payload_bytes` is Skill-owned input storage; exported artifact metadata does not include the raw payload. A metadata-only round trip requires the original bytes to be supplied again before extraction.

Unreadable paths, including missing or permission-denied files, return a `TextRunResult` with fatal `artifact_input_unreadable`, zero units and `artifact = null`. No digest is fabricated for bytes that could not be read. `is_complete_success` is false and the result serializes to JSON. Lower-level `TextArtifact.from_file` and `legal_text_artifact` still raise their construction errors. Caller-supplied artifacts retain their recorded digest; integrity mismatches return failed runs.

The default reader supports in-memory bytes. An explicitly injected reader without `load_bytes` returns an attributable backend failure rather than silently selecting a different reader. Path-only injected readers remain compatible. The Skill version is `0.1.1-provisional`; the shared SeaFlow Core is unchanged.
