import os
# from pydantic_settings import BaseSettings

from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")

print(os.getenv("MONGO_URI"))

SECRET_KEY = os.getenv("SECRET_KEY")
HOST_URL = os.getenv("HOST_URL")

class Settings():
    mongo_uri = MONGO_URI
    git_rev = "beta"
    secret_key = SECRET_KEY
    host_url = "https://media-fusion.vercel.app" # "https://882b9915d0fe-mediafusion.baby-beamup.club"
    logging_level = "INFO"

    # class Config:
    #     env_file = ".env"
    #     extra = "ignore"


settings = Settings()
