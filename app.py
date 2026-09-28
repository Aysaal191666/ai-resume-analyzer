import json
import os
import time

import streamlit as st
from google import genai
from google.genai import types
from pypdf import PdfReader

# Models are tried in order. If one is unavailable on your key, the next is used.
MODELS = ["gemini-3.8-flash", "gemini-3.5-flash"]

st.set_page_config(page_title="AI Resume Analyzer", page_icon="📄", layout="wide")
st.title("📄 AI Resume Analyzer")
st.write("Upload your resume, paste a job description, and see how well they match.")
st.caption("🔒 Privacy: your resume is sent to Google's Gemini API for analysis and is not stored by this app.")


# ---------- API key ----------
def get_api_key():
    # 1) Deployed app: key stored in Streamlit secrets
    try:
        if "GEMINI_API_KEY" in st.secrets:
            return st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass
    # 2) Environment variable
    if os.environ.get("GEMINI_API_KEY"):
        return os.environ["GEMINI_API_KEY"]
    # 3) Typed in the sidebar (used when running on your own computer)
    return st.session_state.get("typed_key", "")


with st.sidebar:
    st.header("Setup")
    st.text_input("Gemini API key", type="password", key="typed_key",
                  help="Get a free key at aistudio.google.com")
    st.caption("Your key is used only for this session and is never saved.")

api_key = get_api_key()


# ---------- Helpers ----------
def read_pdf(file):
    reader = PdfReader(file)
    return "\n".join((page.extract_text() or "") for page in reader.pages)


PROMPT = """You are an expert recruiter and ATS (applicant tracking system) specialist.
Compare the RESUME with the JOB DESCRIPTION and reply ONLY with valid JSON in this exact format:
{{
  "match_score": <integer 0-100>,
  "summary": "<2-3 sentence overall assessment>",
  "matched_skills": ["skill", "..."],
  "missing_skills": ["skill", "..."],
  "suggestions": ["specific, actionable improvement", "..."],
  "rewritten_bullets": [
    {{"original": "<a weak bullet from the resume>", "improved": "<stronger version with impact>"}}
  ]
}}
Rules: be honest, do not invent experience the candidate does not have, give 4-6 suggestions
and 2-3 rewritten bullets.
IMPORTANT for rewritten bullets: use ONLY facts and numbers that already appear in the resume.
Never invent metrics, dataset sizes, percentages, tools or features. If a bullet would be
stronger with a number that is missing, write a placeholder like [add number] instead of guessing.

RESUME:
{resume}

JOB DESCRIPTION:
{jd}
"""


def analyze(resume, jd, key):
    client = genai.Client(api_key=key)
    errors = []
    candidates = list(MODELS)
    try:  # ask Google which other flash models this key can use
        for m in client.models.list():
            name = m.name.replace("models/", "")
            actions = getattr(m, "supported_actions", None) or []
            skip = any(w in name for w in ["image", "tts", "live", "audio", "embed", "robotics"])
            if "flash" in name and "generateContent" in actions and not skip and name not in candidates:
                candidates.append(name)
    except Exception:
        pass
    candidates = candidates[:5]  # don't try too many
    for model in candidates:
        for attempt in range(4):  # up to 4 tries per model
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=PROMPT.format(resume=resume, jd=jd),
                    config=types.GenerateContentConfig(response_mime_type="application/json"),
                )
                text = response.text.replace("```json", "").replace("```", "").strip()
                return json.loads(text)
            except Exception as e:
                msg = str(e)
                busy = "503" in msg or "UNAVAILABLE" in msg or "429" in msg
                if busy and attempt < 3:
                    time.sleep(3 * (attempt + 1))  # wait 3s, 6s, 9s then retry
                    continue
                errors.append(f"{model}: {msg[:200]}")
                break  # move on to the next model
    raise Exception("\n\n".join(errors))


# ---------- Inputs ----------
col1, col2 = st.columns(2)
with col1:
    st.subheader("1. Your resume")
    uploaded = st.file_uploader("Upload PDF", type="pdf")
    pasted = st.text_area("...or paste resume text", height=200)
with col2:
    st.subheader("2. Job description")
    jd = st.text_area("Paste the job description", height=290)

if st.button("Analyze my resume", type="primary"):
    resume_text = read_pdf(uploaded) if uploaded else pasted

    if not api_key:
        st.error("Please enter your Gemini API key in the left sidebar.")
    elif not resume_text.strip() or not jd.strip():
        st.warning("Please provide both a resume and a job description.")
    else:
        with st.spinner("Analyzing..."):
            try:
                result = analyze(resume_text, jd, api_key)
            except Exception as e:
                msg = str(e)
                if "API_KEY_INVALID" in msg or "API key not valid" in msg or "400" in msg:
                    st.error("Your API key looks invalid. Please check it in the sidebar "
                             "(get a free key at aistudio.google.com).")
                elif "429" in msg or "RESOURCE_EXHAUSTED" in msg:
                    st.error("You've reached the free usage limit for now. "
                             "Please wait a few minutes and try again.")
                elif "503" in msg or "UNAVAILABLE" in msg:
                    st.error("Google's AI is very busy right now. "
                             "Please try again in a minute or two.")
                else:
                    st.error("Something went wrong. Please try again in a moment.")
                with st.expander("Technical details"):
                    st.code(msg)
                st.stop()

        # ---------- Results ----------
        score = int(result.get("match_score", 0))
        st.divider()
        st.subheader("Results")
        st.metric("Match score", f"{score}/100")
        st.progress(min(max(score, 0), 100) / 100)
        st.info(result.get("summary", ""))

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### ✅ Matched skills")
            for s in result.get("matched_skills", []):
                st.write(f"- {s}")
        with c2:
            st.markdown("### ❌ Missing skills")
            for s in result.get("missing_skills", []):
                st.write(f"- {s}")

        st.markdown("### 💡 Suggestions")
        for s in result.get("suggestions", []):
            st.write(f"- {s}")

        st.markdown("### ✍️ Rewritten bullet points")
        for b in result.get("rewritten_bullets", []):
            st.markdown(f"**Before:** {b.get('original', '')}")
            st.markdown(f"**After:** {b.get('improved', '')}")
            st.write("")
