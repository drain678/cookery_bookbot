import msgpack
from sqlalchemy import select, desc
from sqlalchemy.exc import IntegrityError
from aio_pika import ExchangeType, Message
from consumer.storage.db import async_session
from src.model.model import User, Recipe
from src.storage.rabbit import channel_pool
from config.settings import settings


async def get_popular_recipe(body):
    user_id = body.get('user_id')
    async with async_session() as db:
        result = await db.execute(
            select(Recipe).order_by(desc(Recipe.likes)).limit(1)
        )

        popular_recipes = result.scalars().all()

        popular_recipes_data = [
            recipe.to_dict()
            for recipe in popular_recipes
        ]

    async with channel_pool.acquire() as channel:
        exchange = await channel.declare_exchange('user_receipts', ExchangeType.TOPIC, durable=True)
        user_queue = await channel.declare_queue(
            settings.USER_QUEUE.format(user_id=user_id),
            durable=True
        )

        await user_queue.bind(
            exchange,
            settings.USER_QUEUE.format(user_id=user_id),
        )

        response_body = {
            "action": 'admin',
            "user_id": user_id,
            "popular_recipes": popular_recipes_data
        }

        await exchange.publish(
            Message(msgpack.packb(response_body)),
            routing_key=settings.USER_QUEUE.format(user_id=user_id)
        )
