# pages/1_Home.py
import os
import tempfile
import streamlit as st
from pptx import Presentation

from search_utils import semantic_search
from azure_blob_utils import download_source_ppt_from_blob
from slide_renderer import extract_slide_structure
from utils import logger

st.set_page_config(page_title="1 - Home", layout="wide")
st.title("1 — Home: Enter prompt and load reference slides")

# -------------------------------------------------
# Session initialization
# -------------------------------------------------
st.session_state.setdefault("slides_catalog", [])
st.session_state.setdefault("selected_slides", [])

prompt = st.text_area("Enter presentation prompt:", height=120)

if st.button("Search dataset & Load Slides"):
    if not prompt.strip():
        st.error("Please enter a prompt.")
        st.stop()

    with st.spinner("Searching dataset and loading reference slides..."):

        st.session_state["slides_catalog"] = []
        st.session_state["selected_slides"] = []

        # 1️⃣ Semantic search → identify relevant PPTs
        refs = semantic_search(prompt, top_k=6)  # PPT discovery only

        if not refs:
            st.warning("No relevant slides found.")
            st.stop()

        # Unique PPTs in relevance order
        ppt_blobs = []
        for r in refs:
            if r["ppt_name"] not in ppt_blobs:
                ppt_blobs.append(r["ppt_name"])

        for ppt_blob in ppt_blobs:
            try:
                local_ppt = os.path.join(
                    tempfile.gettempdir(),
                    ppt_blob.replace("/", "_")
                )

                if not os.path.exists(local_ppt):
                    download_source_ppt_from_blob(ppt_blob, local_ppt)

                prs = Presentation(local_ppt)
                slide_count = len(prs.slides)

                # 2️⃣ Always include title slide
                slide_struct = extract_slide_structure(local_ppt, 0)
                slide_struct["ppt_blob"] = ppt_blob
                slide_struct["slide_id"] = f"{ppt_blob}_slide_0"
                st.session_state["slides_catalog"].append(slide_struct)

                # 3️⃣ Include first few CONTENT slides (skip title)
                for idx in range(1, slide_count - 1):
                    slide_struct = extract_slide_structure(local_ppt, idx)
                    slide_struct["ppt_blob"] = ppt_blob
                    slide_struct["slide_id"] = f"{ppt_blob}_slide_{idx}"
                    st.session_state["slides_catalog"].append(slide_struct)

                    if len(st.session_state["slides_catalog"]) >= 11:
                        break

                # 4️⃣ Include thank-you slide (last slide)
                if slide_count > 1 and len(st.session_state["slides_catalog"]) < 12:
                    last_idx = slide_count - 1
                    slide_struct = extract_slide_structure(local_ppt, last_idx)
                    slide_struct["ppt_blob"] = ppt_blob
                    slide_struct["slide_id"] = f"{ppt_blob}_slide_{last_idx}"
                    st.session_state["slides_catalog"].append(slide_struct)

                if len(st.session_state["slides_catalog"]) >= 12:
                    break

            except Exception as e:
                logger.exception(f"Failed loading slides from {ppt_blob}: {e}")

        if st.session_state["slides_catalog"]:
            st.success(
                f"Loaded {len(st.session_state['slides_catalog'])} reference slides"
            )
            st.switch_page("pages/2_🖼️_Slide_Selection.py")
        else:
            st.warning("No slides could be loaded.")