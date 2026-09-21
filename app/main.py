from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from app.api.routes import router
from app.logging_config import LOG_FILE, configure_logging, get_logger


configure_logging(console=True)
logger = get_logger("server")


app = FastAPI(title="LangGraph Research Agent")
app.include_router(router)


@app.on_event("startup")
def log_startup() -> None:
    logger.info("event=server_started log_file=%s", LOG_FILE)


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/docs")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
