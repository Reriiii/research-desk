from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from app.api.routes import router


app = FastAPI(title="LangGraph Research Agent")
app.include_router(router)


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/docs")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
