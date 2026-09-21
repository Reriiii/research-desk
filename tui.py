from app.observability import init_agentops


init_agentops()

from app.tui import main


if __name__ == "__main__":
    main()
