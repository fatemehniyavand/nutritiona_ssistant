import os
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()


def _to_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Settings(BaseModel):
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    openai_default_model: str = os.getenv("OPENAI_DEFAULT_MODEL", "gpt-5-nano")

    chroma_path: str = os.getenv("CHROMA_PATH", "storage/chroma")
    calorie_collection: str = os.getenv("CALORIE_COLLECTION", "nutrition_db")
    qna_collection: str = os.getenv("QNA_COLLECTION", "nutrition_qna")

    calorie_csv_path: str = os.getenv("CALORIE_CSV_PATH", "data/raw/calories.csv")
    qna_text_path: str = os.getenv("QNA_TEXT_PATH", "data/raw/questions_output.txt")

    top_k_calorie: int = int(os.getenv("TOP_K_CALORIE", "3"))
    top_k_qna: int = int(os.getenv("TOP_K_QNA", "4"))

    distance_threshold: float = float(os.getenv("DISTANCE_THRESHOLD", "0.35"))
    suggestion_limit: int = int(os.getenv("SUGGESTION_LIMIT", "3"))
    strict_match: bool = _to_bool(os.getenv("STRICT_MATCH"), default=False)


settings = Settings()