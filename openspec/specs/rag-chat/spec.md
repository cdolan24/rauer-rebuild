# rag-chat Specification

## Purpose
TBD - created by archiving change rebuild-mvp. Update Purpose after archive.

## Requirements

### Requirement: Question Answering with Retrieved Context
The system SHALL answer natural-language questions by retrieving semantically relevant chunks from the vector database and generating a response with a locally-served LLM.

#### Scenario: Question with relevant content available
- **WHEN** a user asks a question that matches content in the ingested documents
- **THEN** the system retrieves the most relevant chunks and returns a generated answer grounded in that retrieved content

#### Scenario: Question with no relevant content
- **WHEN** a user asks a question with no matching content in the vector database
- **THEN** the system responds indicating it has no information about that topic, rather than fabricating an answer

### Requirement: Source Citations
Every answer SHALL include citations identifying the source document and page(s) the answer was derived from.

#### Scenario: Citations attached to a grounded answer
- **WHEN** the system generates an answer using retrieved chunks
- **THEN** the response includes, for each retrieved chunk used, the document identifier/title and page number(s)

### Requirement: Explanatory Response Style
Responses SHALL be detailed and explanatory rather than terse, suitable for a reader with no prior knowledge of the document contents.

#### Scenario: Answering without assuming prior knowledge
- **WHEN** a user asks about an entity or concept mentioned in the documents
- **THEN** the response explains relevant context and terminology rather than assuming the user already knows it

### Requirement: Multi-Turn Conversation Context
The system SHALL maintain conversation context across multiple turns within a single conversation session.

#### Scenario: Follow-up question referencing prior turn
- **WHEN** a user asks a follow-up question that depends on a previous question/answer in the same conversation
- **THEN** the system uses the prior conversation context to interpret and answer the follow-up correctly

### Requirement: Local-Only Model Execution
The system SHALL perform all embedding and generation using locally-served models (via Ollama), with no calls to external/cloud LLM APIs at runtime.

#### Scenario: Chat request processed without network access to external LLM providers
- **WHEN** a chat request is handled
- **THEN** the only LLM/embedding calls made are to the local Ollama service, and no request is sent to any cloud LLM provider
