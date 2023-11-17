# -*- coding: utf-8 -*-

import asyncio
import requests

from aiohttp import ClientSession

from apscheduler.schedulers.background import BackgroundScheduler

import settings


class Translator:
    __IAM_DATA = {'yandexPassportOauthToken': settings.YANDEX_OAUTH_TOKEN}
    __IAM_URL = 'https://iam.api.cloud.yandex.net/iam/v1/tokens'
    __URL = 'https://translate.api.cloud.yandex.net/translate/v2/translate'

    def __init__(self):
        self.__headers = {'Content-Type': 'application/json'}
        self.__body = {'folderId': settings.YANDEX_CLOUD_FOLDER_ID}

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
        self.__body['targetLanguageCode'] = lang
        self.__body['texts'] = words
        parameters = {'json': self.__body, 'headers': self.__headers}

        async with ClientSession() as session:
            async with session.post(url=Translator.__URL, **parameters) as resp:
                data = await resp.json()
        return [x.get('text', '') for x in data.get('translations', [])]


class Geocoder:
    __URL = 'https://graphhopper.com/api/1/geocode'

    def __init__(self):
        self.__params = {'key': settings.GRAPHHOPPER_API_KEY}

    async def search(self, query, lang='ru', limit=10):
        self.__params['q'] = str(query)
        self.__params['locale'] = str(lang)
        self.__params['limit'] = str(limit)
        params = {'params': self.__params}

        async with ClientSession() as session:
            async with session.get(url=Geocoder.__URL, **params) as response:
                data = await response.json()
                hits = data.get('hits', [])
        return hits


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


class Meteorologist:
    def __init__(self):
        pass

    async def weather(self, lat : float, lon : float):
        pass
