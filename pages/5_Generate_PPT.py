# pages/5_Generate_PPT.py
import os
import streamlit as st
from datetime import datetime
from utils import logger

st.set_page_config(page_title="5 - Generate PPT", layout="wide")
st.title("Step 5 — Generate & Download Presentation")

# ------------------------------------------------------------
# Session state init (SAFE)
# ------------------------------------------------------------
if "generated_ppts" not in st.session_state:
    st.session_state["generated_ppts"] = []

payload = st.session_state.get("generation_payload")
theme = st.session_state.get("ppt_theme", "auto")

if not payload:
    st.warning("No generation payload found. Please complete Preview first.")
    st.stop()

st.write("Generating final PowerPoint from preview slides...")

# ------------------------------------------------------------
# Helper: get title from preview slides
# ------------------------------------------------------------
def extract_title_from_payload(payload):
    slides = payload.get("slides", [])
    if slides and isinstance(slides[0], dict):
        return slides[0].get("title", "").strip() or "Generated_Presentation"
    return "Generated_Presentation"


# ------------------------------------------------------------
# Generate PPT ONCE per payload (no duplicates)
# ------------------------------------------------------------
already_generated = any(
    item.get("payload_id") == id(payload)
    for item in st.session_state["generated_ppts"]
)

if not already_generated:
    try:
        # ---- Generate PPT ----
        if theme == "cognizant":
            from generate_ppt_cognizant import generate_presentation_cognizant
            out_path = generate_presentation_cognizant(payload)
        else:
            from generate_ppt_llm import generate_presentation
            out_path = generate_presentation(payload)

        # ---- Build filename ----
        title = extract_title_from_payload(payload)
        safe_title = title.replace(" ", "_")[:50]
        timestamp = datetime.now().strftime("%d_%b_%H-%M")
        display_name = f"{safe_title}_{timestamp}.pptx"

        # ---- Store in session (LATEST FIRST) ----
        st.session_state["generated_ppts"].insert(
            0,
            {
                "path": out_path,
                "name": display_name,
                "created_at": datetime.now(),
                "payload_id": id(payload),  # 🔑 KEY FIX
            }
        )

        st.success("✅ PPT generated successfully!")

    except Exception as e:
        logger.exception("Generation failed")
        st.error(f"Failed to generate PPT: {e}")
        st.stop()

else:
    st.info("ℹ️ PPT already generated for this preview.")

st.markdown("---")

# ------------------------------------------------------------
# Display generated PPTs (SESSION ONLY)
# ------------------------------------------------------------
st.subheader("📂 Generated PPTs (This Session)")

if not st.session_state["generated_ppts"]:
    st.caption("No PPTs generated yet.")
else:
    for idx, item in enumerate(st.session_state["generated_ppts"]):
        col1, col2 = st.columns([4, 2])

        with col1:
            st.write(f"{idx + 1}. {item['name']}")

        with col2:
            try:
                with open(item["path"], "rb") as f:
                    st.download_button(
                        label="⬇️ Download",
                        data=f,
                        file_name=item["name"],
                        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                        key=f"download_{idx}",
                    )
            except Exception:
                st.caption("File not available")

st.markdown("---")

if st.button("⬅ Back to Home"):
    st.switch_page("pages/1_Home.py")