## MODIFIED Requirements

### Requirement: Duplicate Entity Merging
The system SHALL automatically merge entities of the same type that represent the same underlying entity under different name variants as part of document ingestion, consolidating their mentions onto a single surviving entity without re-reading source documents, and without requiring a separate manual pass.

#### Scenario: Merging name-variant duplicates
- **WHEN** a document finishes ingestion and a deduplication pass identifies entities of the same type that are confidently the same underlying entity (e.g. a nickname, partial name, or repeated mention noted as "(again)")
- **THEN** all of their mentions are consolidated onto a single surviving entity, and the duplicate entity records are removed, without any manual step required

#### Scenario: Distinct entities are not merged
- **WHEN** two entities of the same type have similar but not confidently-matching names or descriptions
- **THEN** they are left as separate entities rather than merged

#### Scenario: Deduplication runs across the whole entity store, not just the new document
- **WHEN** a newly-ingested document introduces an entity that is actually the same as one already extracted from a different, previously-ingested document
- **THEN** the automatic deduplication pass still identifies and merges them, since it considers all entities of that type regardless of which document they came from

#### Scenario: A deduplication failure doesn't fail ingestion
- **WHEN** the automatic deduplication pass encounters an error (e.g. the local LLM is temporarily unreachable)
- **THEN** ingestion still completes and the document is marked processed, with deduplication left for a later pass
