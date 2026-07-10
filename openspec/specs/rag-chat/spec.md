# rag-chat Specification

## Purpose
Defines the retrieve-then-generate chat behavior: answering questions from retrieved context with source citations, running entirely on local Ollama models, with bounded multi-turn history and streamed responses.

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

### Requirement: Entity-Aware Retrieval Boost
When a question names a known entity, the system SHALL prioritize chunks tagged as mentioning that entity alongside plain vector similarity ranking.

#### Scenario: Question names a known entity
- **WHEN** a user's question contains the name of an entity identified during entity extraction
- **THEN** chunks tagged as mentioning that entity receive a retrieval boost relative to equally-similar untagged chunks

#### Scenario: Question does not name a known entity
- **WHEN** a user's question does not match any known entity name
- **THEN** retrieval proceeds using plain vector similarity, unaffected by entity tagging

### Requirement: Streamed Response Generation
The system SHALL support generating a chat response as a stream of incremental content, so a caller can display partial output before generation completes.

#### Scenario: Streaming a grounded answer
- **WHEN** a chat request is made via the streaming interface
- **THEN** the system emits the answer incrementally as it is generated, followed by the citations once generation completes

#### Scenario: Streaming falls back gracefully with no relevant content
- **WHEN** a chat request is made via the streaming interface and no relevant content is found
- **THEN** the system emits the "no information" response as a single event rather than an empty stream

### Requirement: Bounded Generation Length
The system SHALL cap the maximum length of a single generated response to bound worst-case response time.

#### Scenario: Generation reaches the length cap
- **WHEN** a generated response reaches the configured maximum length
- **THEN** generation stops rather than continuing indefinitely

### Requirement: Bounded Conversation History
The system SHALL cap the number of prior conversation turns resent to the model on each request, so prompt evaluation time doesn't grow unboundedly as a conversation lengthens.

#### Scenario: Conversation history within the bound
- **WHEN** a conversation has fewer prior turns than the configured cap
- **THEN** all prior turns are included in the prompt sent to the model

#### Scenario: Conversation history exceeds the bound
- **WHEN** a conversation has more prior turns than the configured cap
- **THEN** only the most recent turns, up to the cap, are included in the prompt sent to the model
