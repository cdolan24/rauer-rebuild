## MODIFIED Requirements

### Requirement: Named Entity Extraction Per Document
The system SHALL identify named entities mentioned in an ingested document using the local LLM, processing chunks in batches rather than individually. Each entity SHALL be typed as one of: character, faction, item, location, real-person, creature, or event.

#### Scenario: Extracting entities from a processed document
- **WHEN** a document has been chunked and embedded
- **THEN** the system produces a list of named entities mentioned in that document, each with a name, a type (character/faction/item/location/real-person/creature/event), and a short description

#### Scenario: Distinguishing real people from fictional characters
- **WHEN** the source text credits a real person (e.g. an author, artist, or producer) rather than describing a fictional character
- **THEN** the entity is typed as `real-person`, not `character`

## ADDED Requirements

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
