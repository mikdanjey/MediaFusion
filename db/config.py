from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    mongo_uri: str
    git_rev: str = "beta"
    secret_key: str
    host_url: str = "https://media-fusion.vercel.app"
    logging_level: str = "INFO"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
