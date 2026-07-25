## 1. Detection heuristic (pure, no LLM)

- [x] 1.1 `src/pipeline/pdf_extractor.py`: add `analyze_page_images(page, text) -> bool` (image coverage ratio >= 0.4 AND extracted text <= 200 chars), and an `is_image_heavy` field on `ExtractedPage`, computed automatically for every page during `extract_pdf()`.
- [x] 1.2 Unit tests using real synthetic PDFs (via PyMuPDF): a page with a large embedded image and no text is flagged; a normal prose page (with or without an incidental image) is not.

## 2. Optional vision-model description stage

- [x] 2.1 New `src/pipeline/image_extractor.py`: `describe_image_heavy_pages(pdf_path, document, ollama_client, vision_model) -> ExtractedDocument` - re-renders each image-heavy page via `get_pixmap()`, calls the vision model (via the existing `OllamaClient.chat()`, using its message-level `images` field - no client changes needed), and returns a new document with those pages' text replaced by the description.
- [x] 2.2 `src/utils/config.py`: add `ollama.vision_model: str | None`, defaulting to unset/disabled.
- [x] 2.3 `src/pipeline/ingest.py`: wire the stage in after `extract_pdf()`, only if `vision_model` is configured and the document has image-heavy pages; wrap in the same "enhancement, not core to success" try/except pattern as entity extraction.
- [x] 2.4 Tests: vision description only touches flagged pages; disabled (no config) leaves pages untouched; a vision-model failure doesn't fail ingestion.

## 3. Carry source_type through chunking, storage, retrieval, citations

- [x] 3.1 `src/pipeline/chunker.py`: add `source_type` to `_Unit` and `Chunk`; a source-type change is a hard break (same mechanism as the story-boundary fix), no overlap carried across it.
- [x] 3.2 `src/database/vector_store.py`: include `source_type` in chunk metadata on `add_chunks`; read it back (with a `text` default for pre-existing chunks) in `search()` and `get_chunks_by_document()`.
- [x] 3.3 `src/rag/retriever.py` / `src/database/vector_store.py`: add `source_type` to `SearchResult`.
- [x] 3.4 `src/rag/chat_engine.py`: add `source_type` to `Citation`, populated from the retrieved `SearchResult`.
- [x] 3.5 `src/rag/prompt_builder.py`: annotate each context block with its source type; update `SYSTEM_PROMPT` to instruct the model to treat `visual` context as a rough description, not directly quotable fact.
- [x] 3.6 `src/api/schemas.py` / `src/api/routes/chat.py`: add `source_type` to `SourceModel`, populated in both `/chat` and `/chat/stream`.
- [x] 3.7 Tests covering the above: chunking hard-breaks on source-type change; a chunk's source_type round-trips through the vector store; a citation for a vision-derived chunk carries `source_type: "visual"`.

## 4. Verify

- [x] 4.1 Run the full test suite, confirm green.
- [x] 4.2 Live smoke-test: build a synthetic image-heavy PDF, ingest it with `vision_model` configured, confirm the resulting chat citation for that content reports `source_type: "visual"`.
- [x] 4.3 Update the session 6 log.
- [x] 4.4 Archive this OpenSpec change (sync specs first), commit and push to `session-6`.
