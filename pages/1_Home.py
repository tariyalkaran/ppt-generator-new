# pages/1_Home.py
import os
import tempfile
import streamlit as st
from pptx import Presentation
from search_utils import collection
from search_utils import semantic_search
from azure_blob_utils import download_source_ppt_from_blob
from slide_renderer import extract_slide_structure
from utils import logger

st.set_page_config(page_title="1 - Home", layout="wide")
st.title(" Step 1 — Start Your Presentation")

# -----------------------------
# Session state init
# -----------------------------
st.session_state.setdefault("slides_catalog", [])
st.session_state.setdefault("selected_slides", [])

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def get_slide_title_from_chroma(ppt_name,slide_index):

    if ppt_name is None or slide_index is None:
        return None

    try:
        res = collection.get(
            where={
                "$and": [
                    {"ppt_name": ppt_name},
                    {"slide_index": slide_index}
                ]
            }
        )

        metas = res.get("metadatas", [])
        if metas and metas[0].get("title"):
            return metas[0]["title"].strip()

    except Exception:
        logger.exception("Failed to fetch slide title from Chroma")

    return None

# -----------------------------
# Hard-coded keyword → PPT map
# -----------------------------
PROMPT_PPT_MAP = {
    "proposal": "Proposed Approach for CareFirst Global Design - September 2021 - V4.10.pptx",
    "propose": "Proposed Approach for CareFirst Global Design - September 2021 - V4.10.pptx",
    "proposed": "Proposed Approach for CareFirst Global Design - September 2021 - V4.10.pptx"
}

prompt = st.text_area("Enter presentation prompt:", height=120)

# -----------------------------
# Theme selection
# -----------------------------
theme = st.selectbox(
    "Select Presentation Theme",
    ["auto", "cognizant"],
    index=0
)

st.session_state["ppt_theme"] = theme

# -----------------------------
# Main action
# -----------------------------
if st.button("Search dataset & Load Slides"):
    if not prompt.strip():
        st.error("Please enter a prompt.")
        st.stop()

    with st.spinner("Searching dataset and loading relevant slides..."):
        st.session_state["slides_catalog"] = []
        st.session_state["selected_slides"] = []

        prompt_l = prompt.lower()

        # ---------------------------------
        # 1️⃣ Check keyword override
        # ---------------------------------
        matched_ppt = None
        for kw, ppt in PROMPT_PPT_MAP.items():
            if kw in prompt_l:
                matched_ppt = ppt
                break

        # ---------------------------------
        # 2️⃣ Keyword-based PPT loading
        # ---------------------------------
        if matched_ppt:
            logger.info(f"Keyword match found → using PPT: {matched_ppt}")

            local_ppt = os.path.join(
                tempfile.gettempdir(),
                matched_ppt.replace("/", "_")
            )

            if not os.path.exists(local_ppt):
                download_source_ppt_from_blob(matched_ppt, local_ppt)

            prs = Presentation(local_ppt)

            for idx in range(len(prs.slides)):
                slide_struct = extract_slide_structure(local_ppt, idx)
                chroma_title = get_slide_title_from_chroma(matched_ppt,idx).lower()

                # ❌ Exclude agenda & thank-you
                if "agenda" in chroma_title or "thank" in chroma_title:
                    continue

                slide_struct["ppt_blob"] = matched_ppt
                slide_struct["slide_id"] = f"{matched_ppt}_Slide_{idx:02d}"

                st.session_state["slides_catalog"].append(slide_struct)

        # ---------------------------------
        # 3️⃣ Default semantic search flow
        # ---------------------------------
        else:
            refs = semantic_search(prompt, top_k=12)

            if not refs:
                st.warning("No relevant slides found.")
                st.stop()

            for r in refs:
                try:
                    ppt_blob = r["ppt_name"]
                    slide_index = r["slide_index"]

                    local_ppt = os.path.join(
                        tempfile.gettempdir(),
                        ppt_blob.replace("/", "_")
                    )

                    if not os.path.exists(local_ppt):
                        download_source_ppt_from_blob(ppt_blob, local_ppt)

                    slide_struct = extract_slide_structure(local_ppt, slide_index)
                    slide_struct["ppt_blob"] = ppt_blob
                    slide_struct["slide_id"] = r["slide_id"]

                    st.session_state["slides_catalog"].append(slide_struct)

                except Exception as e:
                    logger.exception(f"Failed loading slide: {e}")

        # ---------------------------------
        # 4️⃣ Finish
        # ---------------------------------
        if not st.session_state["slides_catalog"]:
            st.warning("No slides loaded.")
            st.stop()

        st.success(
            f"Loaded {len(st.session_state['slides_catalog'])} reference slides"
        )
        st.switch_page("pages/2_🖼️_Slide_Selection.py")