## MODIFIED Requirements

### Requirement: Health Endpoint
The system SHALL expose a health endpoint reporting the status of its dependencies: the local Ollama embeddings service (always a dependency, in every chat-backend configuration) and the configured chat backend (Ollama or the hosted API, whichever is active), plus the vector database.

#### Scenario: Healthy system with the Ollama chat backend
- **WHEN** a client sends `GET /api/health` while `chat_backend` is `ollama`, Ollama is reachable, and the vector database is accessible
- **THEN** the system returns a healthy status including Ollama connectivity (covering both embeddings and chat) and the count of indexed documents

#### Scenario: Healthy system with the hosted-API chat backend
- **WHEN** a client sends `GET /api/health` while `chat_backend` is `hosted_api`, the hosted API and local Ollama embeddings are both reachable, and the vector database is accessible
- **THEN** the system returns a healthy status reporting Ollama connectivity for embeddings and hosted-API connectivity for chat, separately, and the count of indexed documents

#### Scenario: Embeddings dependency unreachable
- **WHEN** a client sends `GET /api/health` while local Ollama is not reachable, regardless of the configured chat backend
- **THEN** the system reports an unhealthy/degraded status identifying Ollama (embeddings) as a failing dependency

#### Scenario: Configured chat backend unreachable
- **WHEN** a client sends `GET /api/health` while the configured chat backend (Ollama or the hosted API) is not reachable
- **THEN** the system reports an unhealthy/degraded status identifying the active chat backend as a failing dependency
