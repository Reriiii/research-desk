import uvicorn

from app.observability import init_agentops


def main() -> None:
    init_agentops()
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":
    main()
