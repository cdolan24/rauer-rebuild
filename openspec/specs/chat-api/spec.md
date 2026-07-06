# chat-api Specification

## Purpose
TBD - created by archiving change rebuild-mvp. Update Purpose after archive.

## Requirements

### Requirement: Chat Endpoint
The system SHALL expose a REST endpoint to send a user message and receive a generated response with sources.

#### Scenario: Successful chat request
- **WHEN** a client sends `POST /api/chat` with a message and conversation id
- **THEN** the system returns a 200 response containing the generated answer text and a list of source citations

### Requirement: Conversation History Endpoints
The system SHALL expose endpoints to retrieve and clear a conversation's history.

#### Scenario: Retrieving conversation history
- **WHEN** a client sends `GET /api/conversations/{id}` for an existing conversation
- **THEN** the system returns the ordered list of prior messages for that conversation

#### Scenario: Clearing a conversation
- **WHEN** a client sends `DELETE /api/conversations/{id}`
- **THEN** the system removes the stored history for that conversation id

### Requirement: Document Listing and Detail Endpoints
The system SHALL expose endpoints to list ingested documents and retrieve details/content for a specific document.

#### Scenario: Listing documents
- **WHEN** a client sends `GET /api/documents`
- **THEN** the system returns metadata (id, title, page count, processing status) for every ingested document

#### Scenario: Retrieving a document's content
- **WHEN** a client sends `GET /api/documents/{id}/content`
- **THEN** the system returns the extracted text/markdown content for that document

### Requirement: Document Upload Endpoint
The system SHALL expose an endpoint to upload a new PDF for ingestion.

#### Scenario: Uploading a new PDF
- **WHEN** a client sends `POST /api/documents/upload` with a PDF file
- **THEN** the system accepts the file, begins ingestion, and returns a job/document identifier the client can use to check status

### Requirement: Search Endpoint
The system SHALL expose an endpoint for direct vector search across ingested documents, independent of the chat flow.

#### Scenario: Direct search request
- **WHEN** a client sends `POST /api/search` with a query string
- **THEN** the system returns the top matching chunks with their similarity scores and source metadata

### Requirement: Health Endpoint
The system SHALL expose a health endpoint reporting the status of its dependencies.

#### Scenario: Healthy system
- **WHEN** a client sends `GET /api/health` while Ollama is reachable and the vector database is accessible
- **THEN** the system returns a healthy status including Ollama connectivity and the count of indexed documents

#### Scenario: Ollama unreachable
- **WHEN** a client sends `GET /api/health` while the local Ollama service is not reachable
- **THEN** the system reports an unhealthy/degraded status identifying Ollama as the failing dependency
