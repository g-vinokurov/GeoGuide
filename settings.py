from dotenv import dotenv_values

config = dotenv_values('.env')

TELEGRAM_BOT_TOKEN = config.get('TELEGRAM_BOT_TOKEN', '')
YANDEX_OAUTH_TOKEN = config.get('YANDEX_OAUTH_TOKEN', '')
YANDEX_CLOUD_FOLDER_ID = config.get('YANDEX_CLOUD_FOLDER_ID', '')
GRAPHHOPPER_API_KEY = config.get('GRAPHHOPPER_API_KEY', '')
OPENWEATHERMAP_API_KEY = config.get('OPENWEATHERMAP_API_KEY', '')
