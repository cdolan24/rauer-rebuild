# document-ingestion Specification

## Purpose
Defines the pipeline that turns a PDF into searchable, cited content: text extraction, semantic chunking, embedding generation, vector storage, and the document registry that tracks per-document ingestion status.

## Requirements

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

### Requirement: Embedding Generation
The system SHALL generate a vector embedding for every chunk using a locally-served embedding model.

#### Scenario: Successful embedding of a chunk
- **WHEN** a text chunk is passed to the embedding step
- **THEN** the system returns a fixed-dimension embedding vector for that chunk via the local Ollama embeddings endpoint

#### Scenario: Embedding service unavailable
- **WHEN** the local embedding model/service cannot be reached
- **THEN** the ingestion run fails clearly for the affected document(s) rather than silently storing chunks without embeddings

### Requirement: Vector Storage and Document Registry
The system SHALL persist chunk embeddings and metadata in a local vector database, and SHALL track each document's ingestion status in a document registry.

#### Scenario: Chunks are retrievable after ingestion
- **WHEN** a document has been successfully ingested
- **THEN** its chunks are queryable from the vector database by semantic similarity

#### Scenario: Registry reflects processing status
- **WHEN** a document ingestion run starts, succeeds, or fails
- **THEN** the document registry records the corresponding status (`pending`, `processed`, or `failed`) for that document

### Requirement: Batch Processing of Multiple Documents
The system SHALL support ingesting multiple PDFs in a single run via a command-line script.

#### Scenario: Processing all PDFs in the data directory
- **WHEN** the ingestion script is run without a specific file argument
- **THEN** the system processes every PDF found in `data/` and reports a summary of successes and failures
