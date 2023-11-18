# -*- coding: utf-8 -*-

import asyncio
import requests

from aiohttp import ClientSession

import time
from datetime import datetime, timezone, timedelta

from apscheduler.schedulers.background import BackgroundScheduler


class YandexTranslator:
    __URL = 'https://translate.api.cloud.yandex.net/translate/v2/translate'
    __IAM_URL = 'https://iam.api.cloud.yandex.net/iam/v1/tokens'

    def __init__(self, yandex_oauth_token: str, yandex_cloud_folder_id: str):
        self.__oauth_token = yandex_oauth_token
        self.__folder_id = yandex_cloud_folder_id

        self.__scheduler = BackgroundScheduler()
        self.__scheduler.add_job(self.__update_iam_token, 'interval', hours=1)
        self.__scheduler.start()

        self.__update_iam_token()

    def __del__(self):
        self.__scheduler.shutdown()

    def __update_iam_token(self):
        iam_data = str({'yandexPassportOauthToken': self.__oauth_token})
        response = requests.post(data=iam_data, url=self.__class__.__IAM_URL)
        self.__iam_token = response.json().get('iamToken', '')

    async def translate(self, words: list[str], lang='ru'):
        params = {'json': {}, 'headers': {}}
        params['headers']['Content-Type'] = 'application/json'
        params['headers']['Authorization'] = f'Bearer {self.__iam_token}'
        params['json']['folderId'] = self.__folder_id
        params['json']['targetLanguageCode'] = lang
        params['json']['texts'] = words

        async with ClientSession() as session:
            async with session.post(url=self.__class__.__URL, **params) as resp:
                data = await resp.json()
        return [x.get('text', '') for x in data.get('translations', [])]


class Geocoder:
    __URL = 'https://graphhopper.com/api/1/geocode'

    def __init__(self, token: str):
        self.__api_key = token

    async def search(self, query: str, lang='ru', limit=10):
        params = {'params': {}}
        params['params']['key'] = self.__api_key,
        params['params']['q'] = query,
        params['params']['locale'] = lang
        params['params']['limit'] = limit

        async with ClientSession() as session:
            async with session.get(url=self.__class__.__URL, **params) as resp:
                data = await resp.json()
        return data.get('hits', [])

    @staticmethod
    def get_point(location: dict):
        return location.get('point', {'lat': 0.0, 'lng': 0.0})


class Meteorologist:
    __URL = 'https://api.openweathermap.org/data/2.5/weather'

    def __init__(self, token: str):
        self.__api_key = token

    async def weather(self, latitude: float, longitude: float, lang='ru'):
        params = {'params': {}}
        params['params']['appid'] = self.__api_key
        params['params']['lat'] = latitude
        params['params']['lon'] = longitude
        params['params']['lang'] = lang
        params['params']['units'] = 'metric'

        async with ClientSession() as session:
            async with session.get(url=self.__class__.__URL, **params) as resp:
                data = await resp.json()
        return data


class GeoGuide:
    __URL = 'https://api.opentripmap.com/0.1/{}/places/{}'

    def __init__(self, token: str):
        self.__api_key = token

    async def places(self, lat: float, lon: float, rad=10, limit=10, lang='ru'):
        places_around = await self.__places_around(lat, lon, rad, lang)
        features = places_around.get('features', [])
        features = features[:min(len(features), limit)]
        places_xids = [x.get('properties', {}).get('xid', '') for x in features]
        return await self.__places(places_xids)

    async def __places_around(self, lat: float, lon: float, rad=10, lang='ru'):
        url = self.__class__.__URL.format(lang, 'radius')
        params = {'params': {}}
        params['params']['apikey'] = self.__api_key
        params['params']['radius'] = rad
        params['params']['lat'] = lat
        params['params']['lon'] = lon
        params['params']['rate'] = 3  # minimum rating of the object popularity

        async with ClientSession() as session:
            async with session.get(url=url, **params) as resp:
                data = await resp.json()
        return data

    async def __place(self, xid: str, lang='ru'):
        url = self.__class__.__URL.format(lang, f'xid/{xid}')
        params = {'params': {'apikey': self.__api_key}}

        async with ClientSession() as session:
            async with session.get(url=url, **params) as resp:
                data = await resp.json()
        return data

    async def __places(self, xids: list[str], lang='ru'):
        tasks = [asyncio.create_task(self.__place(xid, lang)) for xid in xids]
        return await asyncio.gather(*tasks)


class Representer:
    @staticmethod
    async def repr_location(location: dict, translator: YandexTranslator):
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
    async def repr_locations(locations: list, translator: YandexTranslator):
        tasks = []
        for x in locations:
            task = asyncio.create_task(Representer.repr_location(x, translator))
            tasks.append(task)
        return await asyncio.gather(*tasks)

    @staticmethod
    def __repr_wind_direction(deg: float):
        directions = (
            'северный', 'северо-восточный', 'восточный', 'юго-восточный',
            'южный', 'юго-западный', 'западный', 'северо-западный'
        )
        return directions[int((deg + 22.5) // 45 % 8)]

    @staticmethod
    def repr_weather(weather_data: dict):
        weather = weather_data.get('weather', [{}])
        desc = weather[0].get('description', '') if weather else ''

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

        tz = timezone(timedelta(seconds=weather_data.get('timezone', 0)))

        sunrise = weather_data.get('sys', {}).get('sunrise', time.time())
        sunrise = datetime.fromtimestamp(sunrise, tz=tz)
        sunrise = f'{str(sunrise.hour).zfill(2)}:{str(sunrise.minute).zfill(2)}'

        sunset = weather_data.get('sys', {}).get('sunset', time.time())
        sunset = datetime.fromtimestamp(sunset, tz=tz)
        sunset = f'{str(sunset.hour).zfill(2)}:{str(sunset.minute).zfill(2)}'

        representation = f'Погода в выбранном месте: {desc}\n'
        representation += f'Температура воздуха: {temp}°C\n'
        representation += f'Ощущается как: {feels_like}°C\n'
        representation += f'Атмосферное давление: {pressure} мм рт. ст.\n'
        representation += f'Влажность: {humidity}%\n'
        representation += f'Ветер: {wind_direction}, '
        representation += f'{wind_speed} м/с, порывы до {wind_gust} м/с\n'
        representation += f'Восход солнца: {sunrise}\nЗаход солнца: {sunset}\n'
        representation += f'Видимость: {visibility / 1000} км'
        return representation

    @staticmethod
    def repr_place(place_data: dict):
        print(place_data)
        name = place_data.get('name', '')

        address = place_data.get('address', {})
        country = address.get('country', '')
        state = address.get('state', '')
        county = address.get('county', '')
        hamlet = address.get('hamlet', '')
        town = address.get('town', '')
        city = address.get('city', '')
        city_district = address.get('city_district', '')
        road = address.get('road', '')
        house = address.get('house', '')
        house_number = address.get('house_number', '')

        addr =[country, state, county, town, city]
        addr += [road, house, house_number]
        addr = ', '.join(x for x in addr if x)

        wikipedia_extracts = place_data.get('wikipedia_extracts', {})
        wikipedia_text = wikipedia_extracts.get('text', '')
        opentripmap_info = place_data.get('info', {}).get('descr', '')

        description = wikipedia_text if wikipedia_text else ''
        description = opentripmap_info if not description else description

        description = description[:min(len(description), 300)]

        representation = f'<b>{name[:min(len(name), 50)]}...</b>\n'
        if description:
            representation += f'{description}...\n'
        if addr:
            representation += f'<b>Адрес:</b> {addr[:min(len(addr), 50)]}'
        # representation = representation[:min(len(representation), 400)]

        image = place_data.get('image', '')
        image = {'url': image, 'caption': name} if image else {}

        return {'text': representation, 'img': image}

    @staticmethod
    def repr_places(places: list):
        return [Representer.repr_place(place) for place in places]
