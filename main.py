# -*- coding: utf-8 -*-

import asyncio
import json

from aiogram import F
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from utils import Translator, Geocoder, Meteorologist, Representer
import settings


bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

translator = Translator()
translator.init()

geocoder = Geocoder()
meteorologist = Meteorologist()


@dp.message(Command('start'))
async def cmd_start(message: types.Message):
    await message.answer('Привет! Давай найдём какую-нибудь интерсную локацию!')


@dp.message()
async def msg_handler(message: types.Message):
    locations = await geocoder.search(message.text)
    represented = await Representer.repr_locations(locations, translator)

    if not locations:
        return await message.answer('Странно... ничего не нашёл :(')

    kbd = []
    for location, represented_location in zip(locations, represented):
        btn_data = f'point+@{json.dumps(location["point"])}'
        btn_text = represented_location
        button = InlineKeyboardButton(text=btn_text, callback_data=btn_data)
        kbd.append([button])

    keyboard = InlineKeyboardMarkup(inline_keyboard=kbd)
    await message.answer('Смотри, что я нашёл:', reply_markup=keyboard)


@dp.callback_query(F.data.startswith('point+@'))
async def geolocation_point_handler(callback: types.CallbackQuery):
    point = json.loads(callback.data.lstrip('point+@'))
    latitude, longitude = point.get('lat', 0.0), point.get('lng', 0.0)

    weather = await meteorologist.weather(latitude, longitude)
    weather = Representer.repr_weather(weather)
    await callback.message.answer(f'{weather}')


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    print('---------- STARTED ----------')
    asyncio.run(main())
