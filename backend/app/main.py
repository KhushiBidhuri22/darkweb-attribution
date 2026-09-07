from fastapi import FastAPI

app = FastAPI(title="Darkweb Attribution API")

@app.get("/")
def read_root():
    return {"message": "Darkweb Attribution Backend"}

@app.get("/health")
def health():
    return {"status": "ok"}