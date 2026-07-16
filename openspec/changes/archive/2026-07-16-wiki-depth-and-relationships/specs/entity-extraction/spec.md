## ADDED Requirements

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
