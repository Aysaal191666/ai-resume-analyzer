# 📄 AI Resume Analyzer

A web app that compares your resume with a job description and tells you how well they match, what skills are missing, and how to improve.

🔗 **Live demo:** https://ai-resume-analyzer-takyip5zqctp7egswrwaus.streamlit.app/
 

## What it does
- Upload a resume (PDF) or paste the text
- Paste a job description
- Get a **match score out of 100**, matched and missing skills, specific suggestions, and rewritten resume bullet points

## How to use it
1. Get a free Gemini API key at [aistudio.google.com](https://aistudio.google.com)
2. Open the app and paste the key in the sidebar (it is used only for your session and is never saved)
3. Add your resume and a job description, then click **Analyze my resume**

## How it works
1. `pypdf` extracts the text from the uploaded PDF
2. A carefully designed prompt sends the resume and job description to the **Gemini API** and asks for a reply in a fixed **JSON** format
3. The JSON is parsed and displayed with **Streamlit** (score, skills, suggestions, rewritten bullets)

## Challenges I solved
- **Retired models:** Gemini model names change over time, so the app tries several models in order and discovers other available ones automatically
- **Server overload (503 errors):** added automatic retry with waiting, plus friendly error messages for invalid keys, rate limits and busy servers
- **AI making up facts:** early versions invented numbers in the rewritten bullets. I fixed it by adding strict prompt rules: use only facts from the resume, and show `[add number]` where a metric is missing

## Tech stack
Python · Streamlit · Google Gemini API · pypdf

## Run it locally
```
pip install -r requirements.txt
streamlit run app.py
```

## Privacy
Your resume is sent to Google's Gemini API for analysis and is not stored by this app.

## Ideas for the next version
- Download the report as a PDF
- Keyword match chart
- Cover letter generator
