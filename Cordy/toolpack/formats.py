import string
from random import sample
import zlib

def code_text(text: str) -> bytes:
    return zlib.compress(text.encode())

def decode_text(text: bytes) -> str:
    return zlib.decompress(text).decode()

def generate_random_string(length: int):
    return ''.join(sample(string.ascii_lowercase+string.digits+string.ascii_uppercase, length))

def format_millis_to_time(time: int):
    class dateFormat():
        days = 0
        hours = 0
        minutes = 0
        seconds = 0

        def __str__(self) -> str:
            if self.days == 0:
                return f'{self.hours if len(str(self.hours)) == 2 else f"0{self.hours}"}:{self.minutes if len(str(self.minutes)) == 2 else f"0{self.minutes}"}:{self.seconds if len(str(self.seconds)) == 2 else f"0{self.seconds}"}'
            else:
                return f'{self.days if len(str(self.days)) == 2 else f"0{self.days}"}:{self.hours if len(str(self.hours)) == 2 else f"0{self.hours}"}:{self.minutes if len(str(self.minutes)) == 2 else f"0{self.minutes}"}:{self.seconds if len(str(self.seconds)) == 2 else f"0{self.seconds}"}'
    
    date_in_format = dateFormat()

    count_cache = time // 86400000
    if count_cache != 0:
        date_in_format.days = count_cache
        time -= 86400000 * count_cache

    count_cache = time // 3600000
    if count_cache != 0:
        date_in_format.hours = count_cache
        time -= 3600000 * count_cache

    count_cache = time // 60000
    if count_cache != 0:
        date_in_format.minutes = count_cache
        time -= 60000 * count_cache

    count_cache = time // 1000
    if count_cache != 0:
        date_in_format.seconds = count_cache
        time -= 1000 * count_cache

    return date_in_format

def format_time_to_millis(d: int = 0, h: int = 0, m: int = 0, s: int = 0):
    return int(d) * 86400000 + int(h) * 3600000 + int(m) * 60000 + int(s) * 1000