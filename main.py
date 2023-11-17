# -*- coding: utf-8 -*-
import asyncio
from aiohttp import ClientSession

from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram.filters.state import StatesGroup, State
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

import requests

import settings

iam_data = str({'yandexPassportOauthToken': settings.YANDEX_OAUTH_TOKEN})
iam_url = 'https://iam.api.cloud.yandex.net/iam/v1/tokens'
iam_token = requests.post(data=iam_data, url=iam_url).json().get('iamToken', '')
headers = {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer {0}'.format(iam_token)
}

bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

print('--STARTED--')


async def get_translation(*args):
    body = {
        'targetLanguageCode': 'ru',
        'texts': list(args),
        'folderId': settings.YANDEX_CLOUD_FOLDER_ID,
    }
    url = 'https://translate.api.cloud.yandex.net/translate/v2/translate'

    async with ClientSession() as session:
        async with session.post(url=url, json=body, headers=headers) as resp:
            data = await resp.json()
    return [x.get('text', '') for x in data.get('translations', [])]


async def repr_location(location):
    country = location.get("country", None)
    city = location.get("city", None)
    name = location.get("name", None)
    key = location.get("osm_key", None)
    value = location.get("osm_value", None)

    answer = [country, city, name]

    to_ts = [str(x).capitalize() for x in (key, value) if x is not None]
    ts = await get_translation(*to_ts)

    answer.extend(ts)

    answer = [x for x in answer if x is not None]
    return ', '.join(answer)


@dp.message(Command('start'))
async def cmd_start(message: types.Message):
    await message.answer('Привет! Я могу многое рассказать о географических объектах. Тебе стоит лишь написать мне название чего-либо, а я постараюсь найти это')


@dp.message()
async def msg_handler(message: types.Message):
    locations = await get_locations(message.text)

    tasks = [asyncio.create_task(repr_location(x)) for x in locations]

    keys = await asyncio.gather(*tasks)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=key, callback_data=str(location['point']))
        ] for key, location in zip(keys, locations)
    ])
    await message.answer("Я нашёл несколько локаций. Выберите, о чём ты хочешь узнать подробнее", reply_markup=keyboard)


async def get_locations(query):
    url = 'https://graphhopper.com/api/1/geocode'
    api_key = settings.GRAPHHOPPER_API_KEY
    params = {'q': f'{query}', 'locale': 'ru', 'limit': '10', 'key': api_key}

    async with ClientSession() as session:
        async with session.get(url=url, params=params) as response:
            data = await response.json()
            hits = data.get('hits', [])
    return hits


async def get_weather(lat, lon):
    url = 'https://api.openweathermap.org/data/2.5/weather'
    api_key = settings.OPENWEATHERMAP_API_KEY
    params = {'lat': f'{lat}', 'lon': f'{lon}', 'APPID': api_key}

    async with ClientSession() as session:
        async with session.get(url=url, params=params) as response:
            data = await response.json()
    return data


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())


