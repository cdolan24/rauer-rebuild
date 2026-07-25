## Why

The current pipeline only ever calls `page.get_text()`, so a comic-style or heavily-illustrated page (little or no real running text, most of the content conveyed visually) would ingest as an almost-empty chunk - unsearchable, uncited, effectively invisible to the wiki and chat. Session 5's research into vision models concluded that a local model can produce a useful scene/caption-level description today, but shouldn't be trusted at the same level as directly-extracted prose text. The user wants this handled automatically: the default pipeline should detect an image-heavy page itself and shift to a vision model for just that page, without the vision model becoming the default for everything.

## What Changes

- `pdf_extractor.py` gains a deterministic, non-LLM heuristic (image coverage vs. page area, combined with sparse extracted text) that flags a page as image-heavy during normal extraction - always computed, no cost, no new dependency.
- A new, optional pipeline stage (`src/pipeline/image_extractor.py`) describes only the pages flagged image-heavy using a local vision model via Ollama, replacing their near-empty extracted text with the model's description. Disabled unless `ollama.vision_model` is explicitly set in config - the vision model is never the default.
- The distinction between directly-extracted text and a vision-model description is carried all the way through the pipeline - chunking (a page-type change is a hard break, same mechanism as the story-boundary fix), the vector store's metadata, retrieval results, and chat citations - so the chat prompt can tell the model to treat visually-described content as less certain than directly-extracted text, and a citation in the UI can eventually be labeled accordingly.

## Capabilities

### New Capabilities

- `image-page-processing`: detecting image-heavy pages and optionally describing them with a local vision model, with the origin (`text` vs `visual`) tracked through chunking, storage, and citations.

### Modified Capabilities

- `document-ingestion`: extraction now also classifies each page's content origin; ingestion optionally runs the new vision-description stage before chunking.
- `rag-chat`: citations and prompt context now distinguish directly-extracted text from vision-model-described content.

## Impact

- `src/pipeline/pdf_extractor.py` (heuristic + `ExtractedPage.is_image_heavy`), `src/pipeline/image_extractor.py` (new), `src/pipeline/chunker.py` (`Chunk.source_type`, hard break on source-type change), `src/database/vector_store.py` (metadata), `src/rag/retriever.py` (`SearchResult.source_type`), `src/rag/chat_engine.py` (`Citation.source_type`), `src/rag/prompt_builder.py` (context annotation + system prompt), `src/api/schemas.py`/`src/api/routes/chat.py` (`SourceModel.source_type`), `src/utils/config.py` (`ollama.vision_model`, optional), `src/pipeline/ingest.py` (wiring).
