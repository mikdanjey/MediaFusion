import os
# from pydantic_settings import BaseSettings

from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DATABASE_NAME = os.getenv("DATABASE_NAME")
SECRET_KEY = os.getenv("SECRET_KEY")
HOST_URL = os.getenv("HOST_URL")

class Settings():
    mongo_uri = MONGO_URI
    database = DATABASE_NAME
    git_rev = "beta"
    secret_key = SECRET_KEY
    host_url = HOST_URL
    logging_level = "INFO"

    # class Config:
    #     env_file = ".env"
    #     extra = "ignore"


settings = Settings()
