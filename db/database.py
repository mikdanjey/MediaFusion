import motor.motor_asyncio
from beanie import init_beanie

from db.config import settings
from db.models import MediaFusionSeriesMetaData, MediaFusionMovieMetaData, Streams


async def init():
    # Create Motor client
    client = motor.motor_asyncio.AsyncIOMotorClient(settings.mongo_uri)
    database = client[settings.database]
    # Init beanie with the Product document class
    await init_beanie(database, document_models=[MediaFusionMovieMetaData, MediaFusionSeriesMetaData, Streams])


