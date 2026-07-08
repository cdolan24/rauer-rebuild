## MODIFIED Requirements

### Requirement: Source Citations
Every answer SHALL include citations identifying the source document and page(s) the answer was derived from. When multiple retrieved chunks meet the relevance threshold, the system SHALL cite all of them rather than narrowing to a single source, so users can see the full breadth of material an answer draws from.

#### Scenario: Citations attached to a grounded answer
- **WHEN** the system generates an answer using retrieved chunks
- **THEN** the response includes, for each retrieved chunk used, the document identifier/title and page number(s)

#### Scenario: Multiple sources cited for one answer
- **WHEN** more than one retrieved chunk meets the relevance threshold for a question
- **THEN** the answer's citations include all of them, not just the single highest-scoring chunk

## ADDED Requirements

### Requirement: Bounded Conversation History
The system SHALL cap the number of prior conversation turns resent to the model on each request, so prompt evaluation time doesn't grow unboundedly as a conversation lengthens.

#### Scenario: Conversation history within the bound
- **WHEN** a conversation has fewer prior turns than the configured cap
- **THEN** all prior turns are included in the prompt sent to the model

#### Scenario: Conversation history exceeds the bound
- **WHEN** a conversation has more prior turns than the configured cap
- **THEN** only the most recent turns, up to the cap, are included in the prompt sent to the model
