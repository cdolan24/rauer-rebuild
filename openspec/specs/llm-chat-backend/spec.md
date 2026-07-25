# llm-chat-backend

## Purpose
Defines how chat-generation call sites (RAG answers, wiki entity summaries, entity extraction, entity deduplication, relationship extraction) select and use a backend - local Ollama or a hosted LLM API - independent of embeddings and vision, which always run locally.

## Requirements

### Requirement: Config-Selectable Chat Backend
The system SHALL select between a local Ollama chat backend and a hosted-API chat backend for all chat-generation call sites (RAG answers, wiki entity summaries, entity extraction, entity deduplication, relationship extraction) based on a single `chat_backend` configuration value, defaulting to `ollama` when unset.

#### Scenario: Config selects Ollama (default)
- **WHEN** `chat_backend` is unset or set to `ollama` in configuration
- **THEN** every chat-generation call site uses the local Ollama chat model, and no hosted API is contacted for chat generation

#### Scenario: Config selects the hosted API
- **WHEN** `chat_backend` is set to `hosted_api` in configuration
- **THEN** every chat-generation call site uses the configured hosted API instead of local Ollama, and Ollama is not contacted for chat generation

### Requirement: Embeddings and Vision Model Are Unaffected By Chat Backend Selection
Embedding generation and the optional vision-model page description SHALL always use local Ollama, regardless of the configured chat backend.

#### Scenario: Hosted API selected for chat, document ingestion still embeds locally
- **WHEN** `chat_backend` is set to `hosted_api` and a document is ingested
- **THEN** chunk embeddings are still generated via the local Ollama embeddings endpoint, unaffected by the chat backend setting

#### Scenario: Hosted API selected for chat, image-heavy page description still uses local Ollama
- **WHEN** `chat_backend` is set to `hosted_api` and a page is flagged image-heavy with a vision model configured
- **THEN** the page description is still generated via the local Ollama vision model, unaffected by the chat backend setting

### Requirement: Hosted Backend Uses a Configured Model and Bounded Output
When `chat_backend` is `hosted_api`, the system SHALL send requests to the configured hosted model identifier and SHALL apply a configured maximum output token count to every request, since the hosted API requires an explicit bound unlike Ollama's optional cap.

#### Scenario: A chat-generation call omits an explicit token limit
- **WHEN** a call site invokes chat generation without specifying its own output token limit and `chat_backend` is `hosted_api`
- **THEN** the request to the hosted API includes the configured default maximum output token count, not an unbounded request

### Requirement: Hosted Backend Credentials Are Never Committed
The hosted API key SHALL be read from local configuration that is excluded from version control, following the same pattern as the existing admin password, and SHALL NOT be logged or included in error messages.

#### Scenario: Hosted backend configured without a key
- **WHEN** `chat_backend` is set to `hosted_api` but no API key is configured
- **THEN** the application fails fast at startup with a clear configuration error, rather than failing on the first chat request

### Requirement: Chat Backend Failures Are Reported Uniformly
Both chat backends SHALL raise a common error type on failure (unreachable service, invalid credentials, or API error), so calling code does not need backend-specific error handling.

#### Scenario: Hosted API request fails
- **WHEN** a request to the hosted API fails for any reason (network error, authentication error, rate limit)
- **THEN** the system raises the same error type that local Ollama failures raise, with the underlying cause preserved
