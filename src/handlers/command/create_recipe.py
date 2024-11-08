import aio_pika
import msgpack
from aio_pika import ExchangeType
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup

from src.handlers.command.router import router
from aiogram import F

from src.handlers.state.recipe import RecipeGroup
from src.storage.rabbit import channel_pool


@router.callback_query(F.data == 'new_receipt')
async def create_recipe(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.answer('Введите пожалуйста название рецепта')
    await state.set_state(RecipeGroup.recipe_title)

@router.message(F.text, RecipeGroup.recipe_title)
async def create_recipe(message: Message, state: FSMContext):
    await state.update_data(recipe_title=message.text)
    await message.answer('Спасибо! А теперь какие ингредиенты нам нужны')
    await state.set_state(RecipeGroup.ingredients)

@router.message(F.text, RecipeGroup.ingredients)
async def create_recipe(message: Message, state: FSMContext):
    await state.update_data(ingredients=message.text)
    await message.answer('Потрясающе! Опишите процесс готовки')
    await state.set_state(RecipeGroup.description_recipe)

@router.message(F.text, RecipeGroup.description_recipe)
async def create_recipe(message: Message, state: FSMContext):
    await state.update_data(description_recipe=message.text)

    data = await state.get_data()
    caption = f'Пожалуйста, проверьте все ли верно: \n\n' \
              f'Название рецепта: {data.get("recipe_title")}\n' \
              f'Ингридиенты: {data.get("ingredients")}\n' \
              f'Процесс готовки: {data.get("description_recipe")}\n'

    kb_list = [
        [InlineKeyboardButton(text="✅Все верно", callback_data='correct')],
        [InlineKeyboardButton(text="❌Заполнить сначала", callback_data='incorrect')]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=kb_list)
    await message.answer(caption, reply_markup=keyboard)
    await state.set_state(RecipeGroup.check_state)

@router.callback_query(F.data == 'correct', RecipeGroup.check_state)
async def create_recipe(call: CallbackQuery, state: FSMContext):
    async with channel_pool.acquire() as channel: # type: aio_pika.Channel
        exchange = await channel.declare_exchange('user_receipts', ExchangeType.TOPIC, durable=True)
        user_queue = await channel.declare_queue(
            'user_messages',
            durable=True
        )

        await user_queue.bind(exchange, 'user_messages')

        data = await state.get_data()
        ingredients = data.get('ingredients').split(' ')

        body = {
            'user_id': call.from_user.id,
            'recipe_title': data.get('recipe_title'),
            'ingredients': ingredients,
            'description_recipe': data.get('description_recipe'),
            'action': 'create_recipe'
        }


        await exchange.publish(
            aio_pika.Message(msgpack.packb(body)),
            'user_messages'
        )

    await call.answer('Данные сохранены')
    await call.message.edit_reply_markup(reply_markup=None)
    await call.message.answer('Благодарю за регистрацию. Ваши данные успешно сохранены!')
    await state.clear()

@router.callback_query(F.data == 'incorrect', RecipeGroup.check_state)
async def create_recipe(call: CallbackQuery, state: FSMContext):
    await call.answer('Запускаем сценарий с начала')
    await call.message.edit_reply_markup(reply_markup=None)
    await call.message.answer('Введите пожалуйста название рецепта')
    await state.set_state(RecipeGroup.recipe_title)


