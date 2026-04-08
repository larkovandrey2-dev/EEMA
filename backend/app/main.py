from fastapi import FastAPI

from app.api import router_user,router_courses, router_auth

app = FastAPI(
    title="EEMA RecSys",
    version="1.0",
)
app.include_router(router_user.router)
app.include_router(router_courses.router)
app.include_router(router_auth.router)
@app.get("/")
def read_root():
    return {"status": "ok"}

