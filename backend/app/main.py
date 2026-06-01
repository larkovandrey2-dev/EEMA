import sys
import os

current_path = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_path, '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import router_user, router_courses, router_auth
from app.core.config import get_cors_origins

app = FastAPI(
    title="EEMA RecSys",
    version="1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router_user.router)
app.include_router(router_courses.router)
app.include_router(router_auth.router)


@app.get("/")
def read_root():
    return {"status": "ok"}
