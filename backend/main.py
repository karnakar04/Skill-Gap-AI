from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from datetime import datetime
import PyPDF2
import io
import os
import json
import re
from dotenv import load_dotenv

import requests
# ---------------------------
# LOAD ENV
# ---------------------------
import os
from dotenv import load_dotenv

# 🔥 FORCE correct path loading
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, ".env")

load_dotenv(ENV_PATH)

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

print("API KEY:", MISTRAL_API_KEY)





# ---------------------------
# MISTRAL CLIENT
# ---------------------------


# ---------------------------
# APP INIT
# ---------------------------
app = FastAPI(title="Skill Gap AI Evaluator Pro")
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------
# MongoDB
# ---------------------------
client = MongoClient("mongodb+srv://karnakar5511_db_user:dCbU95XaxKalCj4Y@skillgapai.sbhsuiu.mongodb.net/")
db = client["skillgap_db"]
analytics_collection = db["analytics"]

# ---------------------------
# Extract PDF Text
# ---------------------------
def extract_text(file_bytes):
    reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text

# ---------------------------
# AI Resume Evaluation
# ---------------------------


import json
import re

def ai_evaluate_resume(resume_text, target_role):

    prompt = f"""
You are an AI Resume Evaluator.

Target Role: {target_role}

Return ONLY JSON:

{{
"resume_accuracy": number,
"extracted_skills": [],
"missing_skills": [],
"recommendations": [],
"learning_roadmap": [],
"experience_level": "Basic/Intermediate/Strong"
}}

Resume:
{resume_text}
"""

    url = "https://api.mistral.ai/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {MISTRAL_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "mistral-small-latest",
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }

    response = requests.post(url, headers=headers, json=payload)

    data = response.json()

    content = data["choices"][0]["message"]["content"]

    cleaned = re.sub(r"```json|```", "", content).strip()

    try:
        return json.loads(cleaned)
    except:
        return {"raw_response": cleaned}



# ---------------------------
# Analytics Counter
# ---------------------------
def update_daily_queries():
    today = datetime.now().strftime("%Y-%m-%d")

    analytics_collection.update_one(
        {"date": today},
        {"$inc": {"queries": 1}},
        upsert=True
    )

# ---------------------------
# Upload Resume + Target Role
# ---------------------------
@app.post("/evaluate-resume")
async def evaluate_resume(file: UploadFile = File(...), target_role: str = ""):

    try:
        file_bytes = await file.read()
        resume_text = extract_text(file_bytes)

        ai_result = ai_evaluate_resume(resume_text, target_role)

        update_daily_queries()

        return {
            "target_role": target_role,
            "ai_analysis": ai_result
        }

    except Exception as e:
        print("ERROR:", e)   # 👈 shows error in terminal
        return {"error": str(e)}


# ---------------------------
# ANALYTICS DASHBOARD
# ---------------------------
@app.get("/analytics-dashboard")
def analytics_dashboard():

    data = list(analytics_collection.find({}, {"_id":0}))
    total_queries = sum(d.get("queries",0) for d in data)

    return {
        "total_queries": total_queries,
        "daily_usage": data
    }





# ---------------------------
# HOME
# ---------------------------
@app.get("/")
def home():
    return {"message": "Skill Gap AI Evaluator Running"}
