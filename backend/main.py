from typing import Optional

from fastapi import FastAPI, Query
from supabase import create_client, Client
from dotenv import load_dotenv
import os

load_dotenv()

supabase: Client = create_client(
    os.environ.get("SUPABASE_URL"),
    os.environ.get("SUPABASE_KEY"),
)

app = FastAPI(
    title="EEMA RecSys",
    version="1.0",
)
@app.get("/")
def read_root():
    return {"status": "ok"}

@app.get("/api/recommend/baseline")
def get_recommend_baseline(
        tag: Optional[str] = Query(None, description="Фильтр по тегу"),
        limit: int = Query(10, description="Кол-во курсов в рекомендации")):
    try:
        query = supabase.table("courses").select("id, title, summary, url, difficulty, learners_count, rating, tags")
        if tag:
            query = query.ilike("tags", f"%{tag}%")
        response = query.order("learners_count",desc=True).limit(limit).execute()
        return {"algorithm": "baseline",
                "results_count":len(response.data),
                "courses": response.data}
    except Exception as e:
        return {"error": str(e)}