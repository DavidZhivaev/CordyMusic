from motor.motor_asyncio import AsyncIOMotorClient


class Config:
    # Discord emojis
    OTHER_EMOJI = '<::>'
    SOUNDCLOUD_EMOJI = '<::>'
    YANDEXMUSIC_EMOJI = '<::>'

    SOURCE_EMOJIS = {
        'soundcloud': SOUNDCLOUD_EMOJI,
        'sc': SOUNDCLOUD_EMOJI,
        'yandexmusic': YANDEXMUSIC_EMOJI,
        'ym': YANDEXMUSIC_EMOJI
    }

    # Tokens of discord bots
    TEST_TOKEN = ''
    MAIN_TOKEN = ''

    TOKEN = TEST_TOKEN

    DEFAULT_EMBED_COLOR = 0x04bf42

    MUSIC_NODES = {
        'main': {
            'host': '',
            'port': ,
            'password': ''
        }
    }

    MONGO_CLIENT = AsyncIOMotorClient('') 
    DB = MONGO_CLIENT.CordyNew

    SDC_TOKEN = ''
    BOTICORD_TOKEN = ''
