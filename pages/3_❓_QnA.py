# pages/3_❓_QnA.py

import os
import streamlit as st
from utils import text_client, get_env, logger
from search_utils import collection

st.set_page_config(page_title="3 - Q&A", layout="wide")
st.title("3 — Q&A (Slide-Specific Questions)")

# ------------------------------------------------------------------
# Load selected slides
# ------------------------------------------------------------------
slides = st.session_state.get("selected_slide_structs", [])
if not slides:
    st.error("No slides selected. Please go back to Slide Selection.")
    st.stop()

st.info(
    "Answer the questions below. Your answers will be used to generate "
    "a clean, new presentation."
)

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def detect_slide_type(slide):
    title = (slide.get("title") or "").lower()

    if "thank" in title:
        return "thankyou"
    if "agenda" in title:
        return "agenda"
    if slide.get("slide_index") == 0 or "title" in title:
        return "title"
    return "content"



def get_exact_slide_text(slide, max_chars=1200):
    """
    Fetch exact slide text using ppt_blob + slide_index
    (NO embeddings, NO semantic search)
    """

    ppt_name = slide.get("ppt_blob")
    slide_index = slide.get("slide_index")

    if ppt_name is None or slide_index is None:
        logger.warning("[QNA] Missing ppt_blob or slide_index")
        return ""

    try:
        logger.info(
            f"[QNA] Fetching slide from Chroma | ppt={ppt_name} | index={slide_index}"
        )

        res = collection.get(
            where={
                "$and": [
                    {"ppt_name": ppt_name},
                    {"slide_index": slide_index}
                ]
            }
        )

        docs = res.get("documents", [])
        logger.info(f"[QNA] Retrieved {len(docs)} docs from Chroma")

        if not docs:
            return ""

        return "\n".join(docs)[:max_chars]

    except Exception:
        logger.exception("[QNA] Chroma get() failed")
        return ""




def chroma_questions(slide, max_q=3):
    """
    Generate questions from EXACT slide text (no semantic search)
    """
    context = get_exact_slide_text(slide)

    if not context:
        logger.warning(
            f"No exact text found in Chroma for "
            f"{slide.get('ppt_name')} | slide {slide.get('slide_index')}"
        )
        return []

    prompt = f"""
You are analysing a PowerPoint slide.

SLIDE CONTENT:
{context}

TASK:
Generate up to {max_q} diverse, non-overlapping questions
to help customize this slide.

Rules:
- Each question must focus on a DIFFERENT aspect
- Avoid objectives or key-points phrasing
- No generic questions
- Plain numbered list only
"""
    try:
        resp = text_client.chat.completions.create(
            model=get_env("CHAT_MODEL", required=True),
            messages=[{"role": "user", "content": prompt}],
            max_completion_tokens=300
        )

        raw = resp.choices[0].message.content or ""
        lines = [l.strip() for l in raw.splitlines() if l.strip()]

        questions = []
        for ln in lines:
            if ln[0].isdigit():
                q = ln.split(".", 1)[-1].strip()
                if q:
                    questions.append(q)

        return questions[:max_q]

    except Exception as e:
        logger.exception("LLM failed while generating questions from exact slide text")
        return []
    

# ------------------------------------------------------------------
# State init (CRITICAL FIX)
# ------------------------------------------------------------------
st.session_state.setdefault("questions_by_slide", {})
st.session_state.setdefault("answers_by_slide", {})

# ------------------------------------------------------------------
# Generate questions per slide (ONCE)
# ------------------------------------------------------------------
for slide in slides:
    slide_id = slide["slide_id"]

    if slide_id in st.session_state["questions_by_slide"]:
        continue

    slide_type = detect_slide_type(slide)
    questions = []

    if slide_type == "title":
        questions = [
            "What should be the title of this presentation?"
        ]

    elif slide_type == "agenda":
        questions = [
            "What should be included in the agenda?"
        ]

    elif slide_type == "thankyou":
        questions = []

    else:
        questions.append("What is the objective of this slide?")

        try:
            llm_qs = chroma_questions(slide, max_q=3)
            questions.extend(llm_qs)
        except Exception:
            logger.exception("Chroma-based question generation failed")

        questions.append("What are the key points to be added to this slide?")

    st.session_state["questions_by_slide"][slide_id] = questions
    st.session_state["answers_by_slide"].setdefault(slide_id, {})

# ------------------------------------------------------------------
# UI Rendering
# ------------------------------------------------------------------
for idx, slide in enumerate(slides):
    slide_id = slide["slide_id"]
    slide_title = slide.get("title") or "Slide"

    questions = st.session_state["questions_by_slide"].get(slide_id, [])

    st.markdown("---")
    st.subheader(f"Slide {idx + 1}: {slide_title}")

    # 🔹 Thumbnail reduced to ~40%
    if slide.get("png_path") and os.path.exists(slide["png_path"]):
        st.image(slide["png_path"], width=400)

    # 🔹 SAFETY INIT (fix >3 slides crash)
    st.session_state["answers_by_slide"].setdefault(slide_id, {})

    for i, q in enumerate(questions):
        ans_key = f"{slide_id}_q{i}"

        val = st.text_area(
            label=q,
            value=st.session_state["answers_by_slide"][slide_id].get(q, ""),
            key=ans_key
        )

        st.session_state["answers_by_slide"][slide_id][q] = val

# ------------------------------------------------------------------
# Navigation
# ------------------------------------------------------------------
st.markdown("---")
col1, col2 = st.columns(2)

with col1:
    if st.button("⬅ Back to Slide Selection"):
        st.switch_page("pages/2_🖼️_Slide_Selection.py")

with col2:
    if st.button("➡ Generate PPT"):
        answers_for_generator = {}

        for slide in slides:
            idx = str(slide["slide_index"])
            answers_for_generator[idx] = st.session_state["answers_by_slide"].get(
                slide["slide_id"], {}
            )

        st.session_state["generation_payload"] = {
            "selected_slides": slides,
            "answers_map": answers_for_generator
        }

        st.switch_page("pages/4_Generate_PPT.py")