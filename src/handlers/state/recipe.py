from aiogram.fsm.state import State, StatesGroup


class RecipeGroup(StatesGroup):
    recipe_title = State()
    ingredients = State()
    description_recipe = State()
    check_state = State()


class RecipeForm(StatesGroup):
    waiting_for_ingredients = State()
    ingredients_collected = State()
