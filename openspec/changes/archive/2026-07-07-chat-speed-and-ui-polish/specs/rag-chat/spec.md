## ADDED Requirements

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
