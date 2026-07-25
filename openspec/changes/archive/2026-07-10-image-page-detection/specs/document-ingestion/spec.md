## MODIFIED Requirements

### Requirement: PDF Text Extraction
The system SHALL extract text content and per-page boundaries from PDF documents placed in the `data/` directory. Each extracted page SHALL also be classified as image-heavy or not, using a deterministic heuristic based on embedded-image coverage and extracted text density - no LLM call required for this classification.

#### Scenario: Extracting a valid story PDF
- **WHEN** a valid PDF (e.g. `MalifauxStories_M1E_DRAFT_5.17.2023.pdf`) is submitted for processing
- **THEN** the system extracts the full text content along with page numbers for each extracted segment

#### Scenario: Handling a corrupted or unreadable PDF
- **WHEN** a PDF file cannot be opened or parsed
- **THEN** the system records the document as failed with an error message, without crashing the ingestion run

#### Scenario: Classifying an image-heavy page
- **WHEN** a page's embedded images cover a large fraction of the page area and the page has little extracted text
- **THEN** the page is classified as image-heavy

#### Scenario: A normal prose page is not classified as image-heavy
- **WHEN** a page has substantial extracted text, regardless of any embedded images it also contains
- **THEN** the page is not classified as image-heavy

### Requirement: Semantic Chunking with Metadata
The system SHALL split extracted document text into overlapping chunks and attach metadata to each chunk sufficient to trace it back to its source, including whether the chunk's content came from directly-extracted text or a vision-model description.

#### Scenario: Chunk metadata is complete
- **WHEN** a document is chunked
- **THEN** every resulting chunk has a unique `chunk_id`, its parent `document_id`, the source `page_start`/`page_end`, and a `source_type` of either `text` or `visual`

#### Scenario: Chunk overlap preserves context
- **WHEN** a document is split into more than one chunk
- **THEN** adjacent chunks share a configurable amount of overlapping text so that context is not lost at chunk boundaries

#### Scenario: A source-type change is a hard chunk boundary
- **WHEN** consecutive content in a document changes from directly-extracted text to a vision-model description (or vice versa)
- **THEN** that transition forces a new chunk, and no chunk mixes content from both source types
