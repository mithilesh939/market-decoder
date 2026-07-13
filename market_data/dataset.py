from pathlib import Path


class Dataset:

    def __init__(self, path: str):

        self.path = Path(path)

    @property
    def exists(self):

        return self.path.exists()

    @property
    def size(self):

        return self.path.stat().st_size

    @property
    def name(self):

        return self.path.name