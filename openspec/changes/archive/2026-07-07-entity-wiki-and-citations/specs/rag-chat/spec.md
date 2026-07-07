## ADDED Requirements

### Requirement: Entity-Aware Retrieval Boost
When a question names a known entity, the system SHALL prioritize chunks tagged as mentioning that entity alongside plain vector similarity ranking.

#### Scenario: Question names a known entity
- **WHEN** a user's question contains the name of an entity identified during entity extraction
- **THEN** chunks tagged as mentioning that entity receive a retrieval boost relative to equally-similar untagged chunks

#### Scenario: Question does not name a known entity
- **WHEN** a user's question does not match any known entity name
- **THEN** retrieval proceeds using plain vector similarity, unaffected by entity tagging
