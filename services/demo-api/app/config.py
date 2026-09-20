from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    data_dir: str = "data"
    tesseract_lang: str = "fra+eng"
    spacy_model: str = "fr_core_news_sm"
    model_path: str = "/app/models/classifier.joblib"
    port: int = 8000
    log_level: str = "INFO"
    cors_origin: str = (
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://localhost:5174,http://127.0.0.1:5174"
    )
    nuxeo_url: str = ""
    nuxeo_username: str = ""
    nuxeo_password: str = ""
    nuxeo_document_id: str = ""
    nuxeo_timeout_seconds: float = 15

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
