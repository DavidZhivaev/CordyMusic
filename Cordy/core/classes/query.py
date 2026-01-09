class CordySong:
    def __init__(self, position: int, title: str, source: str, playing_now: bool = False):
        self.position = position
        self.title = title
        self.source = source
        self.playing_now = playing_now