## ADDED Requirements

### Requirement: Streaming Chat Endpoint
The system SHALL expose a streaming endpoint that emits a chat response incrementally, in addition to the existing non-streaming chat endpoint.

#### Scenario: Streaming a chat response
- **WHEN** a client sends a request to the streaming chat endpoint with a message and conversation id
- **THEN** the system returns a stream of response events ending with the source citations

#### Scenario: Non-streaming endpoint unaffected
- **WHEN** a client sends a request to the existing `POST /api/chat` endpoint
- **THEN** the system responds exactly as before, with the full answer and citations in a single response
