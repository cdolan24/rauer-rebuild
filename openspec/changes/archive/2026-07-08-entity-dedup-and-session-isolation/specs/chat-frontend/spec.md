## ADDED Requirements

### Requirement: Independent Per-Session Conversation History
Each browser session SHALL be assigned its own conversation identifier, independent of any other concurrent session, so conversation history is never shared between different users or browser tabs opened as separate sessions.

#### Scenario: Two independent sessions get distinct conversation history
- **WHEN** two separate browser sessions each open the chat frontend and send a message
- **THEN** each session's message is recorded under a different conversation identifier, and neither session's conversation history includes the other's messages
