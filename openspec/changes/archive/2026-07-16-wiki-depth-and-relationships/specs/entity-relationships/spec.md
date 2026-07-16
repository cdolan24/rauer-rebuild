## ADDED Requirements

### Requirement: Relationship Extraction From Mention Context
The system SHALL identify relationships between entities using the local LLM, grounded in the actual text of each entity's mentions (not just its stored one-sentence description), and SHALL run this as part of document ingestion.

#### Scenario: Extracting a relationship between two co-occurring entities
- **WHEN** an entity's mention context references another already-known entity in a way that implies a relationship (e.g. membership, rivalry, location)
- **THEN** the system records a relationship between the two entities with a short free-text description of the relationship's nature

#### Scenario: No relationship is inferred when context is insufficient
- **WHEN** an entity's mention context does not clearly indicate a relationship to any other known entity
- **THEN** no relationship is recorded for that entity from that context

#### Scenario: Relationship extraction failure doesn't fail ingestion
- **WHEN** the local LLM is unreachable or fails during relationship extraction for a document
- **THEN** ingestion still completes and the document is marked processed, with relationship extraction left for a later pass

### Requirement: Relationship Storage
The system SHALL persist extracted relationships so they can be queried without re-running extraction, retrievable regardless of which side of the relationship an entity is on.

#### Scenario: Querying relationships for an entity
- **WHEN** a relationship has been recorded between entity A and entity B
- **THEN** querying relationships for either entity A or entity B returns that relationship

### Requirement: Relationship Backfill Without Full Reprocess
The system SHALL support running relationship extraction against already-ingested documents, without requiring the source PDF to be reprocessed from scratch.

#### Scenario: Backfilling relationships for a previously-ingested document
- **WHEN** relationship extraction is run against a document that was ingested before this capability existed
- **THEN** relationships are extracted and stored using the document's already-extracted entities and already-embedded chunks, without re-reading the source PDF
