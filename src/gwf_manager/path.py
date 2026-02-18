from pathlib import Path


class HashablePath(Path):
    def __repr__(self):
        return str(self)

    def __hash__(self):
        return hash(str(self))


class TemporaryPath(HashablePath):
    pass
