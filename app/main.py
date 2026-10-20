from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.database import engine
from app.routers import audit, auth, sessions, sms, transactions, users

app = FastAPI(
    title="Passerelle USSD/SMS — API (simulation, Burundi)",
    version="1.0.0",
    description="API REST du prototype de laboratoire. Aucun argent réel, aucun PIN réel.",
)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000", "http://localhost:5173"],
                   allow_methods=["*"], allow_headers=["*"])

for r in (auth, users, sessions, transactions, sms, audit):
    app.include_router(r.router)


@app.get("/health", tags=["Health"])
def health():
    with engine.connect() as c:
        c.execute(text("SELECT 1"))
    return {"status": "ok", "database": "up"}
