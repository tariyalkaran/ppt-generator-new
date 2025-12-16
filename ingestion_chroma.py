import os
import uuid
import tempfile
from pptx import Presentation
from azure.storage.blob import BlobServiceClient
from openai import AzureOpenAI
from chromadb import PersistentClient
from utils import get_env, logger, now_ts, get_embedding_dim

# === CONFIG ===
BLOB_CONN = get_env("AZURE_BLOB_CONN", required=True)
BLOB_CONTAINER = get_env("AZURE_BLOB_CONTAINER", "ppt-dataset")
EMBEDDING_MODEL = get_env("EMBEDDING_MODEL", "text-embedding-3-small")
CHROMA_PERSIST_DIR = get_env("CHROMA_PERSIST_DIR", "./chroma_db")

# === AZURE OPENAI CLIENT ===
text_client = AzureOpenAI(
    azure_endpoint=get_env("OPENAI_API_BASE", required=True),
    api_key=get_env("OPENAI_API_KEY", required=True),
    api_version=get_env("OPENAI_API_VERSION", "2024-05-01-preview")
)

# === AZURE BLOB CLIENT ===
blob_client = BlobServiceClient.from_connection_string(BLOB_CONN)
container_client = blob_client.get_container_client(BLOB_CONTAINER)

# === CHROMA CLIENT ===
chroma_client = PersistentClient(path=CHROMA_PERSIST_DIR)
try:
    collection = chroma_client.get_collection("ppt_slides")
except Exception:
    collection = chroma_client.create_collection("ppt_slides")

EMBEDDING_DIM = get_embedding_dim(EMBEDDING_MODEL)

# -------------------------------------------------
# FUNCTIONS
# -------------------------------------------------
def extract_slides(local_path):
    """Extract text content from all slides in a PPT."""
    prs = Presentation(local_path)
    slides = []
    for i, slide in enumerate(prs.slides):
        texts = []
        for shape in slide.shapes:
            if hasattr(shape, "text") and shape.text and shape.text.strip():
                texts.append(shape.text.strip())
        slides.append({
            "index": i,
            "text": "\n".join(texts)
        })
    return slides


def simple_tagger(text):
    text_l = text.lower()
    tags = set()

    if any(k in text_l for k in ["design", "architecture", "ui", "ux"]):
        tags.add("Design")
    if any(k in text_l for k in ["test", "qa", "verification"]):
        tags.add("Test")
    if any(k in text_l for k in ["migration", "migrate"]):
        tags.add("Migration")

    for domain in ["claims", "membership", "provider", "finance", "medicaid", "commercial"]:
        if domain in text_l:
            tags.add(domain.capitalize())

    return list(tags) or ["General"]


def ppt_already_indexed(ppt_name):
    try:
        res = collection.query(where={"ppt_name": ppt_name}, n_results=1)
        return bool(res.get("ids", [[]])[0])
    except Exception:
        return False


def azure_embed_func(texts):
    try:
        resp = text_client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=texts
        )
        return [d.embedding for d in resp.data]
    except Exception as e:
        logger.exception(f"Embedding failed: {e}")
        return []


def process_blob(blob_name):
    logger.info(f"Processing blob: {blob_name}")

    tmp_path = os.path.join(
        tempfile.gettempdir(),
        blob_name.replace("/", "_")
    )

    with open(tmp_path, "wb") as fp:
        stream = container_client.download_blob(blob_name)
        stream.readinto(fp)

    slides = extract_slides(tmp_path)
    if not slides:
        logger.warning(f"No slides found in {blob_name}")
        return

    if ppt_already_indexed(blob_name):
        logger.info(f"Skipping '{blob_name}' — already indexed.")
        return

    docs, metadatas, ids, texts = [], [], [], []
    ppt_base = os.path.splitext(os.path.basename(blob_name))[0]

    for s in slides:
        slide_index = s["index"]
        slide_id = f"{ppt_base}_Slide_{slide_index:02d}"
        text = s.get("text", "") or ""

        metadata = {
            # 🔑 CORE IDS (exact retrieval)
            "ppt_name": blob_name,
            "ppt_base": ppt_base,
            "slide_id": slide_id,
            "slide_index": slide_index,     # ✅ INT (FIX)
            "title": text.split("\n", 1)[0] if text else "",

            # 🔍 Optional helpers
            "tags": ", ".join(simple_tagger(text)),   # ✅ LIST (FIX)
            "indexed_on": str(now_ts())
        }

        ids.append(str(uuid.uuid4()))
        docs.append(text)
        metadatas.append(metadata)
        texts.append(text)

    embeddings = azure_embed_func(texts)
    if not embeddings or len(embeddings) != len(docs):
        logger.error("Embedding failed or mismatch; aborting.")
        return

    try:
        collection.add(
            documents=docs,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )
        logger.info(f"Indexed {len(docs)} slides from {blob_name}")
    except Exception as e:
        logger.exception(f"Failed to insert slides from {blob_name}: {e}")


def delete_ppt_from_chroma(ppt_name: str) -> None:
    logger.info(f"Deleting Chroma indexes for PPT: {ppt_name}")
    try:
        collection.delete(where={"ppt_name": ppt_name})
        logger.info(f"Deleted Chroma indexes for PPT: {ppt_name}")
    except Exception as e:
        logger.exception("Delete failed")
        raise e


def main():
    logger.info("Starting ingestion into Chroma...")
    for b in container_client.list_blobs():
        if b.name.lower().endswith((".pptx", ".ppt")):
            try:
                process_blob(b.name)
            except Exception as e:
                logger.exception(f"Failed to process {b.name}: {e}")
    logger.info("Ingestion complete.")


if __name__ == "__main__":
    main()