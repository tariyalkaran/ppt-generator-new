# # =============================================
# generate_ppt_llm.py   
# =============================================
import os
import uuid
from pptx import Presentation
from pptx.util import Pt
from utils import text_client, get_env, logger

def llm_synthesize_slide(user_answers, global_prompt):
   qa_text = "\n".join(
       f"Q: {q}\nA: {a}"
       for q, a in user_answers.items()
       if a.strip()
   )
   prompt = f"""
You are a senior consultant creating a professional PowerPoint slide.
GLOBAL CONTEXT:
{global_prompt}
USER INPUT (rewrite professionally):
{qa_text}
TASK:
- derive a slide title
- derive 4–6 bullets
- rewrite clearly
- professional business tone
FORMAT:
Title: <title>
- bullet
- bullet
"""
   resp = text_client.chat.completions.create(
       model=get_env("CHAT_MODEL", required=True),
       messages=[{"role": "user", "content": prompt}],
       max_tokens=500,
       temperature=0.7,
   )
   raw = resp.choices[0].message.content.strip()
   lines = [x.strip() for x in raw.split("\n") if x.strip()]
   title = "Slide"
   bullets = []
   for ln in lines:
       if ln.lower().startswith("title"):
           title = ln.split(":",1)[1].strip()
       elif ln.startswith("-"):
           bullets.append(ln[1:].strip())
   if not bullets:
       bullets = ["Content could not be generated"]
   return title, bullets

# ============================================================
#               MAIN PPT GENERATOR
# ============================================================
def generate_presentation(payload):
   slides = payload.get("slides", [])
   answers_map = payload.get("answers_map", {})
   if not slides:
       raise ValueError("No slides provided")
   prs = Presentation()
   
   global_prompt = "professional business presentation"

   # ---------------------------------------------------
   # LOOP THROUGH ALL USER SLIDES
   # ---------------------------------------------------
   for slide in slides:
       slide_idx = str(slide["slide_index"])
       slide_title = slide["slide_title"]
       user_answers = answers_map.get(slide_idx, {})
       ppt_slide = prs.slides.add_slide(prs.slide_layouts[1])

       # ---------------------------------------------------
       # Special Case: User answered "presentation title" Q
       # ---------------------------------------------------
       if user_answers.get("What should be the title of this presentation?"):
           user_title = user_answers["What should be the title of this presentation?"].strip()
           ppt_slide.shapes.title.text = user_title
           continue     # no bullets here

       # ---------------------------------------------------
       # Case 2 → Normal content slide
       # ---------------------------------------------------
       try:
           llm_title, bullets = llm_synthesize_slide(
               user_answers,
               global_prompt
           )
       except:
           logger.exception("LLM failed")
           llm_title = slide_title
           bullets = ["Content could not be generated"]

       ppt_slide.shapes.title.text = slide_title
       body = ppt_slide.placeholders[1].text_frame
       body.clear()
       for b in bullets:
           para = body.add_paragraph()
           para.text = b
           para.level = 0
           para.font.size = Pt(18)

   # closing slide
   thanks = prs.slides.add_slide(prs.slide_layouts[1])
   thanks.shapes.title.text = "Thank You"
   thanks.placeholders[1].text = "Questions?"

   os.makedirs("generated", exist_ok=True)
   out_path = f"generated/ppt_{uuid.uuid4().hex[:6]}.pptx"
   prs.save(out_path)
   return out_path