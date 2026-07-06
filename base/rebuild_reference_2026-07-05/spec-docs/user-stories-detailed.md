# Detailed User Stories & Requirements

## Primary User: Faraday (Creative Explorer)

**User Profile**: Faraday is a creative professional (writer, artist, game designer) who wants to extract ideas and inspiration from document collections. Faraday has little to no prior knowledge of the document contents and needs comprehensive, explanatory responses that provide context and connections. Every concept should be explained clearly with relevant background information.

**Core Needs**:
- Understanding content without prior knowledge
- Discovering creative connections and patterns
- Extracting visual and textual elements for inspiration
- Exploring themes, motifs, and relationships
- Getting thorough explanations, not just brief answers

### Story 1: Question Answering with Rich Context
**As Faraday, I want to ask questions about the PDF content and receive detailed, explanatory answers so that I can understand concepts even without prior knowledge.**

#### Acceptance Criteria
- [ ] I can input natural language questions via a command-line interface
- [ ] The system retrieves relevant passages from the processed documents
- [ ] Answers are detailed and explanatory, not assuming prior knowledge
- [ ] Answers include context, background, and connections to related concepts
- [ ] Answers include citations with document name and page number
- [ ] The system can handle follow-up questions maintaining context
- [ ] Response time is under 5 seconds for most queries
- [ ] The system gracefully handles questions with no relevant content ("I don't have information about that")
- [ ] Responses explain terminology and provide definitions where helpful

#### Example Interactions
```
User: "Who is Aragorn?"
System: "Aragorn is a central character who appears throughout the documents. Let me explain:

         IDENTITY & ROLE:
         Aragorn is a ranger - a wandering warrior and protector. He is human and male,
         with a hidden noble heritage that becomes important to the story.

         SIGNIFICANCE:
         He plays a crucial leadership role and serves as a bridge between different
         groups and cultures in the narrative.

         KEY LOCATIONS:
         - Bree: Where he first appears, working as a ranger (pages 3, 15)
         - Rivendell: An elven refuge where important decisions are made (page 87)
         - Minas Tirith: A major city connected to his heritage (page 203)

         CREATIVE NOTES:
         His character embodies themes of hidden identity, destiny, and the contrast
         between humble appearances and noble purposes.

         [Source: fellowship.pdf, pages 3, 15, 42, 87, 203]"

User: "What's the significance of Bree?"
System: "Bree is a location that serves several narrative functions:

         DESCRIPTION:
         Bree is a town that appears early in the story, serving as a meeting place
         and transition point between different regions.

         THEMATIC ROLE:
         It represents a crossroads - both literally (as a trading town) and
         symbolically (where different storylines intersect).

         KEY EVENTS:
         - First major meeting of central characters (page 3)
         - Introduction of Aragorn to other protagonists (page 15)
         - Inn scenes that establish group dynamics (pages 18-22)

         CREATIVE ELEMENTS:
         The inn setting provides intimacy and tension - a safe haven that feels
         potentially dangerous. Useful for stories needing a neutral meeting ground.

         [Source: fellowship.pdf, pages 3-42]"
```

#### Technical Requirements
- Semantic search across vector database
- Context window management for long documents
- Citation tracking system
- Conversation history (last 5-10 exchanges for creatives who dive deep)
- Prompt engineering for explanatory, educational responses
- Thematic analysis and connection generation

---

### Story 2: Summarization
**As Faraday, I want to get summaries of specific elements (characters, locations, items) so that I can understand key information without being overwhelmed.**

#### Acceptance Criteria
- [ ] I can request summaries by entity type (characters, locations, items)
- [ ] I can request a summary of a specific named entity (e.g., "Summarize Gandalf")
- [ ] Summaries are concise (2-5 paragraphs) but comprehensive
- [ ] Summaries include key attributes and relationships
- [ ] I can request different summary lengths (brief, standard, detailed)
- [ ] Summaries include source references

#### Example Interactions
```
User: "Summarize all characters"
System: "I found 23 characters in the processed documents. Here's a summary:

         Main Characters:
         - Aragorn: Human ranger, appears in Bree and Rivendell...
         - Gandalf: Wizard, mentor figure...

         Supporting Characters:
         - Barliman Butterbur: Innkeeper in Bree...

         [Type 'more' for full list or 'detail {name}' for specific character]"

User: "Detail Aragorn"
System: "Aragorn (Human, Male)
         Role: Ranger and future king
         Locations: Bree, Rivendell, Minas Tirith
         Relationships: Friend of Gandalf, leader of the Fellowship
         Key Attributes: Skilled warrior, noble heritage
         Mentions: 47 times across 3 documents
         [Sources: fellowship.pdf (32 mentions), towers.pdf (10), return.pdf (5)]"
```

#### Technical Requirements
- Entity aggregation across documents
- Template-based summary generation
- Configurable summary depth
- Relationship graph traversal

---

### Story 3: Categorization & Filtering
**As Faraday, I want to filter entities by attributes so that I can find specific subsets of information (e.g., "all male characters in Bree").**

#### Acceptance Criteria
- [ ] I can filter by entity type (character, location, item)
- [ ] I can filter characters by attributes (gender, role, species)
- [ ] I can filter by location presence
- [ ] I can combine multiple filters (AND/OR logic)
- [ ] Results show count and can be paginated
- [ ] I can sort results by relevance or mentions

#### Example Interactions
```
User: "Show all male characters in Bree"
System: "Found 5 male characters who appear in Bree:
         1. Aragorn (Ranger, 12 mentions in Bree)
         2. Barliman Butterbur (Innkeeper, 8 mentions in Bree)
         3. Frodo Baggins (Hobbit, 15 mentions in Bree)
         4. Samwise Gamgee (Hobbit, 10 mentions in Bree)
         5. Meriadoc Brandybuck (Hobbit, 8 mentions in Bree)

         [Type 'detail {name}' for more info or 'expand' for descriptions]"

User: "Filter to only humans"
System: "Found 2 male human characters in Bree:
         1. Aragorn (Ranger, 12 mentions in Bree)
         2. Barliman Butterbur (Innkeeper, 8 mentions in Bree)"
```

#### Technical Requirements
- Structured entity database with queryable attributes
- Query parser for natural language filters
- Multi-attribute filtering logic
- Efficient indexing for fast lookups

---

### Story 4: Discovery & Exploration
**As Faraday, I want to explore related content so that I can discover connections between entities and topics.**

#### Acceptance Criteria
- [ ] I can ask "What else appears with [entity]?"
- [ ] System suggests related entities and topics
- [ ] I can navigate relationships (e.g., "Show me locations visited by Aragorn's companions")
- [ ] System tracks my exploration path for easy backtracking

#### Example Interactions
```
User: "What locations are associated with Aragorn?"
System: "Aragorn appears in 7 locations:
         - Bree (12 mentions)
         - Rivendell (24 mentions)
         - Minas Tirith (18 mentions)
         - Helm's Deep (9 mentions)
         ...

         [Type 'explore {location}' to see what else is there]"

User: "Explore Rivendell"
System: "Rivendell is an Elven refuge in Eriador.

         Characters present: Aragorn, Gandalf, Elrond, Arwen, Frodo, ...
         Events: Council of Elrond, Fellowship formation
         Items: Narsil/Andúril, Ring of Power

         [Source: fellowship.pdf, pages 82-156]"
```

#### Technical Requirements
- Relationship graph database or structured links
- Co-occurrence analysis
- Navigation history stack
- Graph traversal algorithms

---

### Story 5: Image Extraction & Visual Elements
**As Faraday, I want to extract and view images from PDFs (covers, chapter headings, illustrations) so that I can gather visual inspiration alongside textual content.**

#### Acceptance Criteria
- [ ] System automatically extracts images during PDF processing
- [ ] I can query for images by document ("Show me images from fellowship.pdf")
- [ ] I can query for images by type ("Show me all cover images" or "Show me chapter headings")
- [ ] Images are saved with metadata (document source, page number, image type)
- [ ] I can view image thumbnails in CLI or export to files
- [ ] Images are categorized automatically (cover, illustration, diagram, heading, etc.)
- [ ] I can ask about visual elements ("What does the cover of X look like?")

#### Example Interactions
```
User: "Show me all cover images"
System: "I found 5 cover images in the processed documents:

         1. fellowship.pdf - Cover (page 1)
            Saved as: processed/images/fellowship_cover_p1.png
            Description: [AI-generated description of cover imagery]

         2. towers.pdf - Cover (page 1)
            Saved as: processed/images/towers_cover_p1.png

         [Type 'describe image 1' for detailed analysis]"

User: "Describe image 1"
System: "Cover image from fellowship.pdf (page 1):

         VISUAL ELEMENTS:
         - Title typography and placement
         - Color scheme and mood
         - Imagery and symbolism
         - Layout and composition

         CREATIVE NOTES:
         The design choices suggest [thematic analysis]

         File location: processed/images/fellowship_cover_p1.png"

User: "Extract all chapter headings from fellowship.pdf"
System: "Extracting chapter headings...

         Found 23 chapter heading images:
         - Chapter 1: [Image] 'The Long Expected Party' (page 5)
         - Chapter 2: [Image] 'The Shadow of the Past' (page 23)
         ...

         All images saved to: processed/images/fellowship/chapters/
         [View metadata: processed/images/fellowship/chapters/manifest.json]"
```

#### Technical Requirements
- PDF image extraction library (PyMuPDF supports image extraction)
- Image classification model (cover, heading, illustration, diagram)
- OCR for text in images (for headings, captions)
- Image metadata storage (JSON with image type, page, dimensions, description)
- Optional: Vision model (Claude/GPT-4 Vision) for image description
- Image storage structure: `processed/images/{document_name}/{type}/`

#### Implementation Suggestions
- **Image Extraction**: PyMuPDF's `get_images()` and `extract_image()`
- **Classification**: Rule-based (page 1 = cover, specific positions = headings) + optional ML
- **OCR**: pytesseract or cloud OCR (Google Vision, AWS Textract)
- **Vision Description**: Claude/GPT-4 Vision API for rich descriptions
- **Storage**: JPEG/PNG with JSON manifest per document
- **CLI Display**: ASCII art preview + file paths, or open in default viewer

---

## Secondary User: Albert (Administrator)

**User Profile**: Albert is the system administrator responsible for uploading documents, monitoring system health, and managing the document collection. Albert needs tools to efficiently manage content, track usage, and maintain system quality.

**Core Needs**:
- Document lifecycle management
- System health monitoring
- Usage analytics and metrics
- Access control and security
- File retrieval and inspection
- Performance optimization

### Story 6: Document Management & Lifecycle
**As Albert, I want to add new PDFs retroactively and manage the document lifecycle so that the system grows with new content.**

#### Acceptance Criteria
- [ ] I can add PDFs to the `data/` directory at any time
- [ ] System detects and processes new PDFs automatically (watch mode) OR on command
- [ ] Processing status is visible (in progress, completed, failed)
- [ ] I can reprocess documents if needed
- [ ] I can delete documents and remove them from the system (with data cleanup)
- [ ] System maintains a processing log
- [ ] I can easily find and retrieve any processed file
- [ ] I can access both markdown and text versions of processed files
- [ ] I can view document metadata and processing history

#### Commands
```
# Add new PDF (automatic detection)
$ cp new_document.pdf data/
$ buddharauer process --watch  # Auto-processes new files

# Manual processing
$ buddharauer process --file data/new_document.pdf

# Find a document
$ buddharauer find "fellowship"
# Output:
Found 1 document matching "fellowship":
  - fellowship.pdf (processed 2025-01-15)
    Text: processed/text/fellowship.txt
    Markdown: processed/markdown/fellowship.md
    Metadata: processed/metadata/fellowship.json
    Images: processed/images/fellowship/ (23 images)

# View processed file
$ buddharauer view fellowship --format markdown
# Opens fellowship.md in viewer or displays in terminal

$ buddharauer view fellowship --format text
# Shows text version

# Document info
$ buddharauer info fellowship
# Output:
Document: fellowship.pdf
Status: Processed
Processed: 2025-01-15 14:23:01
Pages: 432
Chunks: 284
Images: 23 (5 covers, 18 chapter headings)
Entities: 47 characters, 23 locations, 15 items
Size: 2.3 MB (original), 1.8 MB (processed)

# Reprocess document
$ buddharauer reprocess fellowship.pdf

# Reprocess all
$ buddharauer reprocess --all

# Remove document (with confirmation)
$ buddharauer remove fellowship.pdf --purge-data
# Removes: PDF, text, markdown, metadata, images, vector embeddings, entities
```

#### Implementation Suggestions
- **Document Registry**: SQLite database or JSON file tracking all documents
- **Search Index**: Full-text search on filenames and metadata
- **File Viewers**: Integration with `less`, `bat`, or custom markdown renderer
- **Cleanup**: Comprehensive removal across all storage locations
- **Metadata**: Track processing timestamps, versions, status

---

### Story 7: System Monitoring & Health
**As Albert, I want to monitor system health and processing status so that I can ensure reliable operation.**

#### Acceptance Criteria
- [ ] View processing statistics (docs processed, success rate, avg time)
- [ ] See vector database size and query performance
- [ ] Review error logs for failed documents
- [ ] Check embeddings quality metrics
- [ ] Monitor API usage and costs
- [ ] Track system resource usage (disk, memory)

#### Commands
```
$ buddharauer status
# Output:
=== Buddharauer System Status ===
Documents processed: 47 total (45 successful, 2 failed)
Total chunks: 3,245
Total images: 287
Vector DB size: 1.2 GB
Disk usage: 4.8 GB total (1.2 GB vector, 2.1 GB images, 1.5 GB text/markdown)
Last processed: 2025-01-15 14:23:01
Avg processing time: 28 seconds/document
Uptime: 15 days

$ buddharauer errors --recent
# Shows recent processing errors with stack traces

$ buddharauer stats --detailed
# Detailed performance metrics
Processing Stats:
  - Total documents: 47
  - Success rate: 95.7%
  - Avg extraction time: 12s
  - Avg embedding time: 16s
  - Total processing time: 22 minutes

API Usage (Last 30 days):
  - Embedding API calls: 3,245
  - LLM API calls: 1,847
  - Estimated cost: $12.34

Performance:
  - Avg query response: 2.1s
  - 95th percentile: 4.3s
  - Slowest query: 8.9s

$ buddharauer health
# System health check
✓ Vector database: Healthy
✓ Document registry: Healthy
✓ API connectivity: Healthy
✓ Disk space: 45% used (65 GB free)
⚠ Failed documents: 2 (see errors.log)
```

#### Implementation Suggestions
- **Metrics Storage**: Time-series database (SQLite with timestamps) or JSON logs
- **API Cost Tracking**: Log all API calls with cost estimation
- **Performance Monitoring**: Track query times, cache hit rates
- **Alerting**: Optional email/webhook alerts for failures or thresholds
- **Dashboard**: Terminal UI with `rich` library for real-time stats

---

### Story 8: Usage Analytics & Query Metrics
**As Albert, I want to gather metrics on popular queries and user behavior so that I can optimize the system and understand usage patterns.**

#### Acceptance Criteria
- [ ] Track all user queries with timestamps
- [ ] View most popular queries
- [ ] See most queried entities (characters, locations, items)
- [ ] Identify slow queries or failed queries
- [ ] Track query response times and quality metrics
- [ ] Generate usage reports

#### Commands
```
$ buddharauer analytics --popular-queries
# Top 10 Popular Queries (Last 30 days):
1. "Who is Aragorn?" (47 times)
2. "Summarize all characters" (32 times)
3. "Show all male characters in Bree" (18 times)
...

$ buddharauer analytics --popular-entities
# Top Entities:
Characters:
  1. Aragorn (124 queries)
  2. Gandalf (98 queries)
  3. Frodo (87 queries)

Locations:
  1. Bree (76 queries)
  2. Rivendell (65 queries)

$ buddharauer analytics --slow-queries
# Slowest Queries (>5 seconds):
1. "Summarize all relationships between characters" (8.9s)
2. "Show me all locations with more than 10 characters" (7.2s)
...

$ buddharauer analytics --report --format json > usage_report.json
# Generate comprehensive usage report

$ buddharauer analytics --export-queries --since "2025-01-01"
# Export query log for analysis
```

#### Implementation Suggestions
- **Query Logging**: SQLite or JSON logs with query text, timestamp, response time, user
- **Analytics Engine**: Pandas for data analysis, matplotlib for optional visualizations
- **Privacy**: Hash or anonymize query data if needed
- **Reports**: Generate CSV/JSON/PDF reports
- **Real-time**: Optional WebSocket for live query feed

---

### Story 9: Authentication & Access Control
**As Albert, I want to log into an admin account with a password so that I can securely manage the system.**

#### Acceptance Criteria
- [ ] Admin login with username and password
- [ ] Secure password storage (hashed, not plaintext)
- [ ] Session management for CLI
- [ ] Different permission levels (admin, viewer, user)
- [ ] Audit log of admin actions
- [ ] Password reset capability

#### Commands
```
$ buddharauer login
Username: albert
Password: ********
✓ Logged in as albert (admin)

$ buddharauer logout
✓ Logged out

$ buddharauer users list
# List all users (admin only)
Users:
  - albert (admin) - Last login: 2025-01-15 14:23
  - faraday (user) - Last login: 2025-01-14 09:12

$ buddharauer users add
Username: new_user
Password: ********
Role: [admin/user/viewer]: user
✓ User created

$ buddharauer users remove new_user
✓ User removed

$ buddharauer audit-log --recent
# Recent admin actions:
2025-01-15 14:23:01 - albert - Processed fellowship.pdf
2025-01-15 13:45:22 - albert - Removed old_document.pdf
2025-01-14 16:30:15 - albert - Created user: faraday
```

#### Implementation Suggestions
- **Authentication**: Simple file-based (JSON) or SQLite user database
- **Password Hashing**: bcrypt or argon2
- **Sessions**: JWT tokens or simple session files
- **Roles**:
  - `admin`: Full access (manage docs, users, system)
  - `user`: Query documents, view processed files
  - `viewer`: Read-only access to queries
- **Audit Log**: Append-only log file or database table
- **Security**: Store credentials in secure location, file permissions
- **Future**: OAuth/SSO integration for Phase 11+ (web interface)

---

## Future Enhancements (Post-MVP)

### Advanced Search
- Boolean search operators (AND, OR, NOT)
- Fuzzy matching for names
- Date range filtering
- Full-text search within specific documents

### Export & Sharing
- Export filtered results to CSV/JSON
- Generate PDF reports of summaries
- Share specific queries/results

### Visualization
- Character relationship graphs
- Location maps (if geographic data available)
- Timeline visualization
- Entity mention frequency charts

### Multi-user Support
- User accounts and authentication
- Personal query history
- Saved searches and filters
- Collaborative annotations

### Advanced NLP
- Sentiment analysis of character descriptions
- Theme extraction
- Automatic story arc identification
- Character development tracking
