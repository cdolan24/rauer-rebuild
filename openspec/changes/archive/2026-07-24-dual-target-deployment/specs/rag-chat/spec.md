## MODIFIED Requirements

### Requirement: Local-Only Model Execution Is Conditional On The Configured Chat Backend
Embedding generation SHALL always use locally-served models via Ollama, with no calls to external/cloud providers at runtime, regardless of configuration. Chat generation SHALL use locally-served models via Ollama with no external calls when `chat_backend` is `ollama` (the default); when `chat_backend` is `hosted_api`, chat generation calls are explicitly permitted to reach a configured hosted LLM API.

#### Scenario: Chat request processed with the default (Ollama) chat backend
- **WHEN** a chat request is handled and `chat_backend` is `ollama`
- **THEN** the only LLM/embedding calls made are to the local Ollama service, and no request is sent to any cloud LLM provider

#### Scenario: Chat request processed with the hosted-API chat backend configured
- **WHEN** a chat request is handled and `chat_backend` is `hosted_api`
- **THEN** the chat-generation call is sent to the configured hosted LLM API, while the embedding call for retrieval still goes only to the local Ollama service
