class InstanceRegistry(dict):
    def __init__(self, type: object, **kwargs):
        super().__init__(**kwargs)
        self.type = type

    def __setitem__(self, key, value):
        if (existing := super().get(key)) is not None and existing is not value:
            raise KeyError(
                f"{self.type.__name__} instance '{key}' is already registered."
            )
        if not isinstance(value, self.type):
            raise ValueError(
                f"Value for key '{key}' must be an instance of {self.type.__name__}."
            )
        return super().__setitem__(key, value)

    def __getitem__(self, key):
        if key not in self:
            raise KeyError(f"{self.type.__name__} instance '{key}' is not registered.")
        return super().__getitem__(key)


class SubclassRegistry(dict):
    def __init__(self, type: type, **kwargs):
        super().__init__(**kwargs)
        self.type = type

    def __setitem__(self, key, value):
        if (existing := super().get(key)) is not None and existing is not value:
            raise KeyError(f"{self.type.__name__} type '{key}' is already registered.")
        if not issubclass(value, self.type):
            raise ValueError(
                f"Value for key '{key}' must be a subclass of {self.type.__name__}."
            )
        return super().__setitem__(key, value)

    def __getitem__(self, key):
        if key not in self:
            raise KeyError(f"{self.type.__name__} type '{key}' is not registered.")
        return super().__getitem__(key)
