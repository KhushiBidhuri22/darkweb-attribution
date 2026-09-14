from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


from .api import graph
from .api.auth import router as auth_router
from .api.search import router as search_router
from .api.actors import router as actors_router


app = FastAPI(
    title="SIH Dark Web Attribution API",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://darkweb-attribution-eight.vercel.app",
        "https://darkweb-attribution-tzsq.vercel.app",  # keep both if both are live
        "http://localhost:5500",
        "http://127.0.0.1:5500",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(
    graph.router
)

app.include_router(
    auth_router
)

app.include_router(
    search_router
)

app.include_router(
    actors_router
)


@app.get("/health")
@app.get("/api/health")
def health():

    return {"status": "ok"}

    
