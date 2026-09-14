from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


from .api import graph
from .api.auth import router as auth_router
from .api.search import router as search_router
from .api.actors import router as actors_router
from .routers.export import router as export_router

from .db.session import engine, Base  # adjust import path to match your project



app = FastAPI(
    title="SIH Dark Web Attribution API",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_origin_regex=r"https://(darkweb-attribution.*\.vercel\.app|.*\.onrender\.com|localhost.*)",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)



app.include_router(graph.router)
app.include_router(auth_router)
app.include_router(search_router)
app.include_router(actors_router)
app.include_router(export_router, prefix="/api")
app.include_router(export_router)


@app.get("/health")
@app.get("/api/health")
def health():
    return {"status": "ok"}

    
