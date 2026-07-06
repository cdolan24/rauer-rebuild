
"""
This script runs a realistic orchestrator test on the 'data' directory with a short timeout.
It validates timeout and error logging for PDF processing.

NOTE: This test should be runnable manually by any admin user in the final product.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import asyncio
from src.pipeline.chunker import SemanticChunker, ChunkPipeline
from src.database.vector_store import VectorStore
from src.pipeline.orchestrator import PipelineOrchestrator

async def main():
    chunker = SemanticChunker(chunk_size=500, chunk_overlap=50)
    chunk_pipeline = ChunkPipeline(chunker)
    vector_store = VectorStore()
    orchestrator = PipelineOrchestrator(chunk_pipeline, vector_store)
    stats = await orchestrator.process_directory(Path('data'), recursive=False, pdf_timeout=5)
    print(stats)

if __name__ == "__main__":
    asyncio.run(main())
