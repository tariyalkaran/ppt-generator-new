import streamlit as st
import html
import json
import hashlib
from utils import logger

st.set_page_config(page_title="4 - Preview Slides", layout="wide")
st.title("Step 4 — Preview Your Presentation")

# ------------------------------------------------------------------
# Load payload from QnA (UNCHANGED STRUCTURE)
# ------------------------------------------------------------------
payload = st.session_state.get("generation_payload")

if not payload:
    st.error("No generation payload found. Please complete Q&A first.")
    st.stop()

slides = payload.get("slides", [])
answers_map = payload.get("answers_map", {})

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def _answers_signature(slides, answers_map):
    """
    Stable signature of slide selection + Q&A answers.
    If this changes, preview must regenerate.
    """
    data = []
    for s in slides:
        idx = str(s["slide_index"])
        data.append({
            "slide_index": idx,
            "answers": answers_map.get(idx, {})
        })
    raw = json.dumps(data, sort_keys=True)
    return hashlib.md5(raw.encode()).hexdigest()


current_signature = _answers_signature(slides, answers_map)

# 🔥 Invalidate preview when answers or slides change
if st.session_state.get("_preview_signature") != current_signature:
    st.session_state.pop("preview_slides", None)
    st.session_state["_preview_signature"] = current_signature

# ------------------------------------------------------------------
# Generate preview ONCE per payload (LLM logic UNCHANGED)
# ------------------------------------------------------------------
if "preview_slides" not in st.session_state:
    preview_slides = []

    from generate_ppt_llm import llm_synthesize_slide
    global_prompt = "professional business presentation"

    for slide in slides:
        idx = str(slide["slide_index"])
        slide_title = slide["slide_title"]
        user_answers = answers_map.get(idx, {})

        # --------------------------------------------------
        # CASE 1: Presentation title slide
        # --------------------------------------------------
        if "What should be the title of this presentation?" in user_answers:
            title = user_answers[
                "What should be the title of this presentation?"
            ].strip()
            bullets = []

        else:
            # --------------------------------------------------
            # CASE 2: No answers → TITLE ONLY
            # --------------------------------------------------
            has_valid_answers = any(
                v and v.strip() for v in user_answers.values()
            )

            if not has_valid_answers:
                title = slide_title
                bullets = []

            # --------------------------------------------------
            # CASE 3: Normal LLM preview generation
            # --------------------------------------------------
            else:
                try:
                    _, bullets = llm_synthesize_slide(
                        user_answers,
                        global_prompt
                    )
                    title = slide_title
                except Exception:
                    logger.exception("Preview generation failed")
                    title = slide_title
                    bullets = []

        preview_slides.append({
            "title": title,
            "bullets": bullets
        })

    st.session_state["preview_slides"] = preview_slides

# ------------------------------------------------------------------
# PREVIEW UI (PPT-LIKE CANVAS + EDIT UX)
# ------------------------------------------------------------------
st.subheader("🖥️ Slide Preview (Editable)")

for i, slide in enumerate(st.session_state["preview_slides"]):
    slide_dom_id = f"slide_{i}"

    bullets_html = "".join(
        f"<li contenteditable='true'>{html.escape(b)}</li>"
        for b in slide["bullets"]
    )

    st.components.v1.html(
        f"""
        <div style="
            width:1280px;
            height:720px;
            border:1px solid #d0d0d0;
            padding:60px;
            margin:40px auto;
            font-family:Segoe UI, Arial;
            background:white;
            box-shadow:0 4px 12px rgba(0,0,0,0.08);
        ">

            <!-- TITLE -->
            <div contenteditable="true"
                 id="{slide_dom_id}_title"
                 style="
                    font-size:40px;
                    font-weight:600;
                    margin-bottom:30px;
                    outline:none;
                 ">
                {html.escape(slide["title"])}
            </div>

            <!-- BULLETS -->
            <ul id="{slide_dom_id}_bullets"
                style="
                    font-size:22px;
                    line-height:1.6;
                    padding-left:30px;
                ">
                {bullets_html}
            </ul>
        </div>

        <script>
        const bulletsEl = document.getElementById("{slide_dom_id}_bullets");

        bulletsEl.addEventListener("keydown", (e) => {{
            const sel = window.getSelection();
            const li = sel?.anchorNode?.closest("li");
            if (!li) return;

            // ENTER → create new bullet (single press)
            if (e.key === "Enter") {{
                e.preventDefault();
                const newLi = document.createElement("li");
                newLi.contentEditable = "true";
                newLi.innerText = "";
                li.after(newLi);

                const range = document.createRange();
                range.setStart(newLi, 0);
                range.collapse(true);
                sel.removeAllRanges();
                sel.addRange(range);
            }}

            // BACKSPACE on empty → delete bullet
            if (e.key === "Backspace" && li.innerText.trim() === "") {{
                e.preventDefault();
                const prev = li.previousElementSibling;
                li.remove();
                if (prev) {{
                    const range = document.createRange();
                    range.selectNodeContents(prev);
                    range.collapse(false);
                    sel.removeAllRanges();
                    sel.addRange(range);
                }}
            }}
        }});

        const save = () => {{
            const title = document.getElementById("{slide_dom_id}_title").innerText;
            const bullets = [...document.querySelectorAll("#{slide_dom_id}_bullets li")]
                .map(li => li.innerText)
                .filter(t => t.trim().length > 0);

            window.parent.postMessage({{
                slideIndex: {i},
                title,
                bullets
            }}, "*");
        }};

        document.addEventListener("input", save);
        </script>
        """,
        height=800,
    )

# ------------------------------------------------------------------
# RECEIVE EDITS FROM JS
# ------------------------------------------------------------------
st.session_state.setdefault("preview_updates", {})

st.markdown(
    """
    <script>
    window.addEventListener("message", (event) => {
        const data = event.data;
        if (data && data.slideIndex !== undefined) {
            window.parent.streamlitSendMessage({
                type: "preview_update",
                data: data
            });
        }
    });
    </script>
    """,
    unsafe_allow_html=True
)

# ------------------------------------------------------------------
# APPLY EDITS TO SESSION STATE
# ------------------------------------------------------------------
for msg in st.session_state.get("_streamlit_messages", []):
    if msg.get("type") == "preview_update":
        data = msg.get("data", {})
        idx = data.get("slideIndex")
        if idx is not None and idx < len(st.session_state["preview_slides"]):
            st.session_state["preview_slides"][idx]["title"] = data.get("title", "")
            st.session_state["preview_slides"][idx]["bullets"] = data.get("bullets", [])

# ------------------------------------------------------------------
# NAVIGATION
# ------------------------------------------------------------------
st.markdown("---")
col1, col2 = st.columns(2)

with col1:
    if st.button("Previous:Q&A"):
        st.switch_page("pages/3_❓_QnA.py")

with col2:
    if st.button("Next:Generate PPT"):
        payload["slides"] = st.session_state["preview_slides"]
        st.session_state["generation_payload"] = payload
        st.switch_page("pages/5_Generate_PPT.py")