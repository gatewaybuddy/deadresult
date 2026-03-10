from fastapi import FastAPI

from deadresult.api.routes import router

app = FastAPI(
    title="DeadResult",
    description="Searchable catalog of failed AI research experiments — stop repeating dead ends.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(router)
