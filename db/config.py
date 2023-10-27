from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    mongo_uri
    git_rev = "beta"
    secret_key
    host_url = "https://media-fusion.vercel.app" # "https://882b9915d0fe-mediafusion.baby-beamup.club"
    logging_level = "INFO"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
