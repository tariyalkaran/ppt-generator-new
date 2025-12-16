# AI PPT Generator (Chroma + Azure OpenAI) — v2

This project uses:
- Azure OpenAI (via the `openai` package and `AzureOpenAI` client)
- Local ChromaDB for vector storage (persisted under CHROMA_PERSIST_DIR)
- Azure Blob Storage for input PPTs (`ppt-dataset`) and output (`generated-presentations`)
- Streamlit UI to generate and preview PPTs (DALL·E images optional per-slide)

Quick start:
1. Copy `.env.example` to `.env` and fill values.
2. Create venv and install deps:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. Upload sample PPTs to your Azure Blob container `ppt-dataset`.
4. Run ingestion:
   ```bash
   python ingestion_chroma.py
   ```
5. Run the UI:
   ```bash
   streamlit run app.py
   ```

Notes:
- `EMBEDDING_DIM` is auto-detected from model name but you can override it in `.env`.
- Keep `chroma_db/` out of git. In CI, either persist the chroma_db artifact or run ingestion as a job.
