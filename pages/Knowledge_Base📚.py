# pages/0_📚_Knowledge_Base.py

import streamlit as st
from utils import logger
from azure_blob_utils import (
    upload_source_ppt_to_blob,
    list_source_ppt_blobs,
    delete_source_ppt_from_blob,
)
from ingestion_chroma import (
    process_blob as ingest_process_blob,
    delete_ppt_from_chroma,
)

st.set_page_config(page_title="Knowledge Base", layout="wide")
st.title("📚 Knowledge Base")

st.write(
    "Upload sample PowerPoint files to build your knowledge base. "
    "These slides will be indexed and used for search, Q&A, and generation."
)

st.markdown("---")

# ============================================================
# 📥 Upload PPTs
# ============================================================
st.subheader("➕ Add PPTs to Knowledge Base")

uploaded_files = st.file_uploader(
    "Upload .pptx files",
    type=["pptx"],
    accept_multiple_files=True,
)

if st.button("📥 Upload & Index") and uploaded_files:
    with st.spinner("Uploading and indexing PPTs..."):
        for upl in uploaded_files:
            try:
                ppt_bytes = upl.read()
                blob_name = upl.name

                # Upload to Azure Blob
                upload_source_ppt_to_blob(ppt_bytes, blob_name)

                # Index into Chroma
                ingest_process_blob(blob_name)

                st.success(f"✅ Uploaded & indexed: {blob_name}")

            except Exception as e:
                logger.exception("Failed to upload/index PPT")
                st.error(f"❌ Error processing {upl.name}: {e}")

st.markdown("---")

# ============================================================
# 📂 Existing Knowledge Base PPTs
# ============================================================
st.subheader("📂 Knowledge Base PPTs")

try:
    kb_files = list_source_ppt_blobs()
except Exception as e:
    logger.exception("Failed to list KB PPTs")
    st.error("❌ Failed to load knowledge base PPTs")
    kb_files = []

if not kb_files:
    st.caption("No PPTs found in the knowledge base.")
else:
    for ppt_name in kb_files:
        col1, col2 = st.columns([4, 1])

        with col1:
            st.write(ppt_name)

        with col2:
            if st.button("🗑️ Delete", key=f"del_{ppt_name}"):
                try:
                    # Delete from Blob
                    delete_source_ppt_from_blob(ppt_name)

                    # Delete from Chroma
                    delete_ppt_from_chroma(ppt_name)

                    st.success(f"🗑️ Removed: {ppt_name}")
                    st.rerun()

                except Exception as e:
                    logger.exception("Failed to delete PPT")
                    st.error(f"❌ Failed to delete {ppt_name}: {e}")

st.markdown("---")

st.info(
    "ℹ️ Changes here immediately affect search, slide selection, and Q&A. "
    "Deleted PPTs are fully removed from Chroma."
)