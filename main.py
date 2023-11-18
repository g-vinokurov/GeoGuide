# -*- coding: utf-8 -*-

import asyncio
import json
import time

from aiogram import F
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.media_group import MediaGroupBuilder
from aiogram.enums import ParseMode

from utils import Geocoder, Meteorologist, GeoGuide
from utils import YandexTranslator, Representer

import settings


bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

translator = YandexTranslator(settings.YANDEX_TOKEN, settings.YANDEX_FOLDER)

geocoder = Geocoder(token=settings.GRAPHHOPPER_API_KEY)
meteorologist = Meteorologist(token=settings.OPENWEATHERMAP_API_KEY)
geoguide = GeoGuide(token=settings.OPENTRIPMAP_API_KEY)


@dp.message(Command('start'))
async def cmd_start(message: types.Message):
    await message.answer('Привет! Давай найдём какую-нибудь интерсную локацию!')


@dp.message()
async def msg_handler(message: types.Message):
    locations = await geocoder.search(message.text)
    represented = await Representer.repr_locations(locations, translator)

    if not locations:
        return await message.answer('Странно... ничего не нашёл :(')

    points = [Geocoder.get_point(location) for location in locations]

    keyboard = []
    for point, represented_location in zip(points, represented):
        btn_text, btn_data = represented_location, f'point+@{json.dumps(point)}'
        button = InlineKeyboardButton(text=btn_text, callback_data=btn_data)
        keyboard.append([button])

    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await message.answer('Смотри, что я нашёл:', reply_markup=keyboard)


@dp.callback_query(F.data.startswith('point+@'))
async def geolocation_point_handler(callback: types.CallbackQuery):
    point = json.loads(callback.data.lstrip('point+@'))
    lat, lon = point.get('lat', 0.0), point.get('lng', 0.0)

    weather = asyncio.create_task(meteorologist.weather(lat, lon))
    places = asyncio.create_task(geoguide.places(lat, lon, rad=10000))

    weather = await weather
    places = await places

    if not places:
        return await callback.message.answer('Ничего интересного :(')

    weather = Representer.repr_weather(weather)
    places = Representer.repr_places(places)

    images = [place['img'] for place in places if place['img']]
    await callback.message.answer(weather)
    if images:
        album_builder = MediaGroupBuilder()
        for image in images:
            img_url, img_caption = image['url'], image['caption']
            album_builder.add_photo(media=img_url, caption=img_caption)
        await callback.message.answer_media_group(media=album_builder.build())
    representation = '\n\n'.join(x['text'] for x in places)
    await callback.message.answer(representation, parse_mode=ParseMode.HTML)


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    print('---------- STARTED ----------')
    asyncio.run(main())
