# Copyright © 2024, UChicago Argonne, LLC. See "LICENSE" for full details.


class Serializable:
    """The Serializable class is a class that can be serialized to a dict

    Subclasses need to override `_attrs_to_serialize` in order to specify
    which attributes to serialize (and the proper order).

    Once this is specified, all subclasses should be serializable with
    the `serialize()` method, and deserializable with the `deserialize()`
    method.

    If any custom logic is needed, one can override the `serialize()`
    and `deserialize()` methods.
    """

    # A list of attributes to serialize and deserialize
    # Subclasses should override this.
    _attrs_to_serialize = []

    def serialize(self) -> dict:
        # Serialize the series into a dict that can be saved and loaded
        return {k: getattr(self, k) for k in self._attrs_to_serialize}

    def deserialize(self, d: dict):
        # Set all of the settings from the dict
        for k, v in d.items():
            if k not in self._attrs_to_serialize:
                msg = f'Unknown attribute provided to deserializer: {k}'
                raise Exception(msg)

            setattr(self, k, v)

    @classmethod
    def from_serialized(cls, d: dict, parent=None):
        obj = cls(parent=parent)
        obj.deserialize(d)
        return obj


class ValidationError(Exception):
    pass
