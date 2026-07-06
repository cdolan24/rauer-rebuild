# document-ingestion Specification

## Purpose
TBD - created by archiving change rebuild-mvp. Update Purpose after archive.

## Requirements

### Requirement: PDF Text Extraction
The system SHALL extract text content and per-page boundaries from PDF documents placed in the `data/` directory.

#### Scenario: Extracting a valid story PDF
- **WHEN** a valid PDF (e.g. `MalifauxStories_M1E_DRAFT_5.17.2023.pdf`) is submitted for processing
- **THEN** the system extracts the full text content along with page numbers for each extracted segment

#### Scenario: Handling a corrupted or unreadable PDF
- **WHEN** a PDF file cannot be opened or parsed
- **THEN** the system records the document as failed with an error message, without crashing the ingestion run

### Requirement: Semantic Chunking with Metadata
The system SHALL split extracted document text into overlapping chunks and attach metadata to each chunk sufficient to trace it back to its source.

#### Scenario: Chunk metadata is complete
- **WHEN** a document is chunked
- **THEN** every resulting chunk has a unique `chunk_id`, its parent `document_id`, and the source `page_start`/`page_end`

#### Scenario: Chunk overlap preserves context
- **WHEN** a document is split into more than one chunk
- **THEN** adjacent chunks share a configurable amount of overlapping text so that context is not lost at chunk boundaries

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
