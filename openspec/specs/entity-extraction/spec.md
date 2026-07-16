# entity-extraction Specification

## Purpose
Defines how named entities (characters, locations, factions, items, real people, creatures, events) are extracted from ingested documents, classified into the curated taxonomy, indexed by mention, and deduplicated - the data the wiki is generated from.

## Requirements

### Requirement: Named Entity Extraction Per Document
The system SHALL identify named entities mentioned in an ingested document using the local LLM, processing chunks in batches rather than individually. Each entity SHALL be typed as one of: character, faction, item, location, real-person, creature, or event.

#### Scenario: Extracting entities from a processed document
- **WHEN** a document has been chunked and embedded
- **THEN** the system produces a list of named entities mentioned in that document, each with a name, a type (character/faction/item/location/real-person/creature/event), and a short description

#### Scenario: Distinguishing real people from fictional characters
- **WHEN** the source text credits a real person (e.g. an author, artist, or producer) rather than describing a fictional character
- **THEN** the entity is typed as `real-person`, not `character`

### Requirement: Threshold-Gated Dynamic Tagging
During a reclassification pass, the system SHALL allow the model to propose a novel entity type beyond the curated set, but a novel type SHALL only be retained as a real category if at least 3 entities are assigned to it; otherwise those entities revert to their prior type.

#### Scenario: A novel tag reaches the threshold
- **WHEN** a reclassification pass assigns a novel tag to 3 or more entities
- **THEN** those entities keep the novel tag and it becomes a visible wiki category

#### Scenario: A novel tag does not reach the threshold
- **WHEN** a reclassification pass assigns a novel tag to fewer than 3 entities
- **THEN** those entities revert to their type from before the reclassification pass, and the novel tag is discarded

### Requirement: Entity Reclassification
The system SHALL support reclassifying existing entities into an updated taxonomy without re-running extraction from source text, using each entity's stored name and description.

#### Scenario: Reclassifying existing entities
- **WHEN** a reclassification pass is run against already-extracted entities
- **THEN** each entity's type is re-evaluated against the current taxonomy and updated in place, without any new LLM calls against the source documents

### Requirement: Entity Mention Indexing
The system SHALL index which chunks and pages mention each identified entity, using case-insensitive name matching against existing chunk text.

#### Scenario: Indexing mentions of an entity
- **WHEN** an entity has been identified for a document
- **THEN** the system records every chunk in that document whose text contains the entity's name, along with the page(s) that chunk spans

### Requirement: Entity Storage
The system SHALL persist identified entities and their mentions so they can be queried without re-running extraction.

#### Scenario: Querying an entity's mentions after extraction
- **WHEN** entity extraction has completed for a document
- **THEN** the entity and all of its indexed mentions are retrievable from storage without invoking the LLM again

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

### Requirement: Entity Extraction Coverage Auditing
The system SHALL provide a way to determine whether every chunk in a document was included in some successful entity-extraction batch, so a coverage gap (e.g. from a batch that failed or timed out) is detectable rather than silently reducing the entity set.

#### Scenario: Detecting a coverage gap after extraction
- **WHEN** entity extraction completes for a document and one or more batches failed
- **THEN** the system can report which chunks were not covered by any successful batch

#### Scenario: No coverage gap
- **WHEN** entity extraction completes for a document with every batch succeeding
- **THEN** the coverage report shows no uncovered chunks

### Requirement: Failed-Batch Retry
The system SHALL retry a failed entity-extraction batch at least once before treating its chunks as uncovered, since a single timeout under concurrent load does not necessarily mean the batch would fail again.

#### Scenario: A batch fails once and succeeds on retry
- **WHEN** an entity-extraction batch fails (e.g. times out) and is retried
- **THEN** entities found on the successful retry are included in the document's extracted entities, the same as if the first attempt had succeeded

#### Scenario: A batch fails on retry as well
- **WHEN** an entity-extraction batch fails on both its original attempt and its retry
- **THEN** the batch's chunks are treated as uncovered (see Entity Extraction Coverage Auditing) and extraction for the rest of the document proceeds unaffected
