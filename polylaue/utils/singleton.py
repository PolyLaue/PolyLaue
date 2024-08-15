# Copyright © 2024, UChicago Argonne, LLC. See "LICENSE" for full details.


class SingletonMetaclass(type):
    """A metaclass used to make a class into a singleton"""

    _instance = None

    def __call__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__call__(*args, **kwargs)

        return cls._instance


class Singleton(metaclass=SingletonMetaclass):
    """Inherit from this class to be a singleton"""

    pass
