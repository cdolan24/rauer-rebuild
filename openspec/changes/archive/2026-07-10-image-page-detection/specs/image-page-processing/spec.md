## ADDED Requirements

### Requirement: Image-Heavy Page Detection
The system SHALL classify each extracted page as image-heavy or not, using a deterministic heuristic (embedded-image coverage of the page area combined with sparse extracted text), computed automatically for every page during extraction at no additional cost.

#### Scenario: A comic-style or heavily-illustrated page is flagged
- **WHEN** a page's embedded images cover a large fraction of the page area and it has little extracted running text
- **THEN** the page is flagged as image-heavy

#### Scenario: A normal prose page is not flagged
- **WHEN** a page has substantial extracted running text
- **THEN** the page is not flagged as image-heavy, regardless of any images also present on it

### Requirement: Optional Vision-Model Description
The system SHALL support describing image-heavy pages with a local vision model via Ollama, replacing that page's near-empty extracted text with the model's description. This SHALL be disabled unless a vision model is explicitly configured - the vision model SHALL NOT be used by default or for any page not flagged as image-heavy.

#### Scenario: Vision description is disabled by default
- **WHEN** no vision model is configured
- **THEN** image-heavy pages keep whatever text `get_text()` extracted (however sparse), and no vision-model call is made

#### Scenario: Vision description runs only for flagged pages
- **WHEN** a vision model is configured and a document has one or more image-heavy pages
- **THEN** only those flagged pages are described by the vision model; pages with substantial extracted text are never sent to it

#### Scenario: A vision-description failure doesn't fail ingestion
- **WHEN** the vision model is unreachable or fails while describing a page
- **THEN** ingestion still completes, and that page keeps its original (sparse) extracted text rather than blocking the document

### Requirement: Source-Type Tracking Through Retrieval and Citations
Content derived from a vision-model description SHALL be distinguishable from directly-extracted text throughout chunking, storage, retrieval, and chat citations, so a chat answer can treat it with appropriately lower confidence.

#### Scenario: A citation reflects its source type
- **WHEN** a chat answer cites a chunk whose content came from a vision-model description
- **THEN** the citation and the context passed to the chat model both indicate it is a visual description, not directly-extracted text

#### Scenario: Directly-extracted text is unaffected
- **WHEN** a chat answer cites a chunk of directly-extracted text
- **THEN** the citation and prompt context indicate it as directly-extracted text, exactly as before this capability existed
