# pages/2_🖼️_Slide_Selection.py
import streamlit as st

st.set_page_config(page_title="2 - Slide Selection", layout="wide")
st.title("2 — Slide Selection (reference slides)")

# -----------------------
# Session init (REQUIRED)
# -----------------------
st.session_state.setdefault("slides_catalog", [])
st.session_state.setdefault("selected_slides", [])

slides = st.session_state["slides_catalog"]

if not slides:
    st.warning("No slides loaded. Go back to Home.")
    st.stop()

st.write(
    "Select reference slides. "
    "The number of slides selected = number of content slides generated."
)

cols = st.columns(3)

for i, s in enumerate(slides):
    col = cols[i % 3]
    with col:
        # ✅ REAL slide thumbnail
        st.image(s.get("png_path"), use_container_width=True)

        caption = f"{s.get('ppt_blob')} — slide {s.get('slide_index')}"
        st.caption(caption)

        key = f"sel_{s['slide_id']}"
        checked = st.checkbox(
            "Select",
            key=key,
            value=(s["slide_id"] in st.session_state["selected_slides"])
        )

        if checked and s["slide_id"] not in st.session_state["selected_slides"]:
            st.session_state["selected_slides"].append(s["slide_id"])
        if not checked and s["slide_id"] in st.session_state["selected_slides"]:
            st.session_state["selected_slides"].remove(s["slide_id"])

st.markdown("---")

col1, col2 = st.columns(2)

with col1:
    if st.button("Continue to Q&A"):
        if not st.session_state["selected_slides"]:
            st.error("Select at least one slide.")
        else:
            selected = [
                s for s in slides
                if s["slide_id"] in st.session_state["selected_slides"]
            ]
            st.session_state["selected_slide_structs"] = selected
            st.session_state["answers_by_slide"] = {}
            st.switch_page("pages/3_❓_QnA.py")

with col2:
    if st.button("Back to Home"):
        st.switch_page("pages/1_Home.py")