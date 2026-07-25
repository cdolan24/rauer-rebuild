## MODIFIED Requirements

### Requirement: Source Citations
Every answer SHALL include citations identifying the source document and page(s) the answer was derived from, and whether that content was directly-extracted text or a vision-model description of an image-heavy page. When multiple retrieved chunks meet the relevance threshold, the system SHALL cite all of them rather than narrowing to a single source, so users can see the full breadth of material an answer draws from.

#### Scenario: Citations attached to a grounded answer
- **WHEN** the system generates an answer using retrieved chunks
- **THEN** the response includes, for each retrieved chunk used, the document identifier/title, page number(s), and its content source type

#### Scenario: Multiple sources cited for one answer
- **WHEN** more than one retrieved chunk meets the relevance threshold for a question
- **THEN** the answer's citations include all of them, not just the single highest-scoring chunk

#### Scenario: A vision-derived citation is distinguishable from directly-extracted text
- **WHEN** a retrieved chunk's content came from a vision-model description rather than direct text extraction
- **THEN** its citation and the context passed to the chat model indicate this, so the answer can treat it with appropriately lower confidence
