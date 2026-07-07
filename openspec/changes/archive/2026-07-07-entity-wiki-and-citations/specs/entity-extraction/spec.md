## ADDED Requirements

### Requirement: Named Entity Extraction Per Document
The system SHALL identify named entities (characters, locations, factions, items) mentioned in an ingested document using the local LLM, processing chunks in batches rather than individually.

#### Scenario: Extracting entities from a processed document
- **WHEN** a document has been chunked and embedded
- **THEN** the system produces a list of named entities mentioned in that document, each with a name, a type (character/location/faction/item), and a short description

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
