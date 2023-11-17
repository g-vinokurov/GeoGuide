# -*- coding: utf-8 -*-

import asyncio
import requests
import time
from datetime import datetime, timezone, timedelta

from aiohttp import ClientSession

from apscheduler.schedulers.background import BackgroundScheduler

import settings


class Translator:
    __IAM_DATA = {'yandexPassportOauthToken': settings.YANDEX_OAUTH_TOKEN}
    __IAM_URL = 'https://iam.api.cloud.yandex.net/iam/v1/tokens'
    __URL = 'https://translate.api.cloud.yandex.net/translate/v2/translate'

    def __init__(self):
        self.__headers = {'Content-Type': 'application/json'}
        self.__folder_id = settings.YANDEX_CLOUD_FOLDER_ID

        self.__scheduler = BackgroundScheduler()
        self.__scheduler.add_job(self.__update_iam_token, 'interval', hours=4)
        self.__scheduler.start()

    def __update_iam_token(self):
        data, url = Translator.__IAM_DATA, Translator.__IAM_URL
        response = requests.post(data=str(data), url=url)
        iam_token = response.json().get('iamToken', '')
        self.__headers['Authorization'] = f'Bearer {iam_token}'

    def init(self):
        self.__update_iam_token()

    def quit(self):
        self.__scheduler.shutdown()
        self.__headers['Authorization'] = None

    async def translate(self, words: list[str], lang='ru'):
        parameters = {'json': {}, 'headers': self.__headers}
        parameters['json']['folderId'] = self.__folder_id
        parameters['json']['targetLanguageCode'] = lang
        parameters['json']['texts'] = words

        async with ClientSession() as session:
            async with session.post(url=Translator.__URL, **parameters) as resp:
                data = await resp.json()
        return [x.get('text', '') for x in data.get('translations', [])]


class Geocoder:
    __URL = 'https://graphhopper.com/api/1/geocode'

    def __init__(self):
        self.__key = settings.GRAPHHOPPER_API_KEY

    async def search(self, q: str, lang='ru', lim=10):
        params = {'key': self.__key, 'q': q, 'locale': lang, 'limit': str(lim)}

        async with ClientSession() as session:
            async with session.get(url=Geocoder.__URL, params=params) as resp:
                data = await resp.json()
        return data.get('hits', [])


class Meteorologist:
    __URL = 'https://api.openweathermap.org/data/2.5/weather'

    def __init__(self):
        self.__key = settings.OPENWEATHERMAP_API_KEY

    async def weather(self, lat: float, lon: float, lang='ru'):
        ps = {'appid': self.__key, 'lat': lat, 'lon': lon, 'lang': lang}

        ps['units'] = 'metric'

        async with ClientSession() as session:
            async with session.get(url=Meteorologist.__URL, params=ps) as resp:
                data = await resp.json()
        return data


class GeoGuide:
    def __init__(self):
        pass


class Representer:
    @staticmethod
    async def repr_location(location, translator: Translator):
        country = location.get('country', None)

        city = location.get('city', None)
        city = f'г. {city}' if city else None

        name = location.get('name', None)
        name = f'"{name}"' if name else name

        key = location.get('osm_key', None)
        value = location.get('osm_value', None)

        to_translate = [str(x) for x in (key, value) if x]
        translated = await translator.translate(to_translate)

        answer = [str(x) for x in [country, city, name, *translated] if x]
        return ', '.join(answer)

    @staticmethod
    async def repr_locations(locations, translator: Translator):
        tasks = []
        for x in locations:
            task = asyncio.create_task(Representer.repr_location(x, translator))
            tasks.append(task)
        locations = await asyncio.gather(*tasks)
        return locations

    @staticmethod
    def __repr_wind_direction(deg):
        directions = (
            'северный', 'северо-восточный', 'восточный', 'юго-восточный',
            'южный', 'юго-западный', 'западный', 'северо-западный'
        )
        return directions[int((deg + 22.5) // 45 % 8)]

    @staticmethod
    def repr_weather(weather_data: dict):
        description = weather_data.get('weather', {}).get('description', '')

        main_data = weather_data.get('main', {})
        temp = main_data.get('temp', 0.0)  # Celsius
        feels_like = main_data.get('feels_like', 0.0)  # Celsius
        pressure = main_data.get('pressure', 1000) * 0.75  # mmHg

        humidity = main_data.get('humidity', 0)  # %

        visibility = weather_data.get('visibility', 10000)  # meters

        wind_data = weather_data.get('wind', {})
        wind_speed = wind_data.get('speed', 0)  # meter/sec
        wind_deg = wind_data.get('deg', 0)  # degrees
        wind_direction = Representer.__repr_wind_direction(wind_deg)
        wind_gust = wind_data.get('gust', 0)  # meter/sec

        tz = timezone(timedelta(weather_data.get('timezone', 0)))

        sunrise = weather_data.get('sys', {}).get('sunrise', time.time())
        sunrise = datetime.fromtimestamp(sunrise, tz=tz)
        sunrise = f'{sunrise.hour}:{sunrise.minute}'

        sunset = weather_data.get('sys', {}).get('sunset', time.time())
        sunset = datetime.fromtimestamp(sunset, tz=tz)
        sunset = f'{sunset.hour}:{sunset.minute}'

        representation = f'Погода в выбранном месте: {description}\n'
        representation += f'Температура воздуха: {temp}°C\n'
        representation += f'Ощущается как: {feels_like}°C\n'
        representation += f'Атмосферное давление: {pressure} мм рт. ст.\n'
        representation += f'Влажность: {humidity}%\n'
        representation += f'Ветер: {wind_direction}, '
        representation += f'{wind_speed} м/с, порывы до {wind_gust} м/с\n'
        representation += f'Восход солнца: {sunrise}\nЗаход солнца: {sunset}\n'
        representation += f'Видимость: {visibility / 1000} км'
        return representation
