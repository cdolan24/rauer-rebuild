## ADDED Requirements

### Requirement: Duplicate Entity Merging
The system SHALL support merging entities of the same type that represent the same underlying entity under different name variants, consolidating their mentions onto a single surviving entity without re-reading source documents.

#### Scenario: Merging name-variant duplicates
- **WHEN** a deduplication pass identifies entities of the same type that are confidently the same underlying entity (e.g. a nickname, partial name, or repeated mention noted as "(again)")
- **THEN** all of their mentions are consolidated onto a single surviving entity, and the duplicate entity records are removed

#### Scenario: Distinct entities are not merged
- **WHEN** two entities of the same type have similar but not confidently-matching names or descriptions
- **THEN** they are left as separate entities rather than merged
