import os

from dotenv import load_dotenv

load_dotenv()


def get_model_name() -> str:
    model = os.getenv("MODEL")
    if not model:
        raise RuntimeError("MODEL is not configured")
    return model
