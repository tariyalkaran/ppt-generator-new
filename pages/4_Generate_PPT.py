# pages/4_Generate_PPT.py
import os
import streamlit as st
from generate_ppt import generate_presentation
from utils import logger
 
st.set_page_config(page_title="4 - Generate PPT", layout="wide")
st.title("4 — Generate & Download")
 
payload = st.session_state.get("generation_payload")
 
if not payload:
    st.warning("No generation payload found. Complete Q&A first.")
    st.stop()
 
st.write("Generating final PPT from your selected slides and answers...")
 
try:
    # ✅ CORRECT CALL — SINGLE PAYLOAD
    out_path = generate_presentation(payload)
 
    st.success("PPT generated successfully!")
    st.markdown(f"**File:** `{os.path.basename(out_path)}`")
 
    with open(out_path, "rb") as f:
        st.download_button(
            "⬇️ Download PPT",
            f,
            file_name=os.path.basename(out_path),
            mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
        )
 
except Exception as e:
    logger.exception("Generation failed")
    st.error(f"Failed to generate PPT: {e}")
 
if st.button("Back to Home"):
    st.switch_page("pages/1_Home.py")
 