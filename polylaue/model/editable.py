# Copyright © 2025, UChicago Argonne, LLC. See "LICENSE" for full details.

from typing import (
    Any,
    Callable,
    Literal,
    NotRequired,
    Sequence,
    TypedDict,
    Union,
)

from pathlib import Path

from polylaue.model.serializable import Serializable, ValidationError

Number = Union[int, float]
ParameterType = Literal[
    'string', 'integer', 'float', 'boolean', 'file', 'folder', 'enum', 'tuple'
]
ParameterValue = Union[str, Number]
ParameterOptions = Sequence[ParameterValue]


# NotRequired requires python >=3.11
class ParameterDescription(TypedDict):
    type: ParameterType
    label: str
    required: NotRequired[bool]
    subtype: NotRequired[ParameterType]
    length: NotRequired[int]
    default: NotRequired[ParameterValue]
    options: NotRequired[ParameterOptions]
    min: NotRequired[Number]
    max: NotRequired[Number]
    extensions: NotRequired[list[str]]
    tooltip: NotRequired[str]


ParameterValidator = Callable[
    [str, Any, ParameterDescription, dict[str, ParameterValue], 'Editable'],
    None,
]


def default_string_validator(
    name: str, value, description: ParameterDescription, *args
):
    valid = isinstance(value, str)

    if not valid:
        raise ValidationError(
            f"{description['label']}:\nThe provided value is not a string."
        )

    stripped_value = value.strip()

    minimum = description.get('min')
    if minimum is not None and len(stripped_value) < minimum:
        raise ValidationError(
            f"{description['label']}:\nThe provided string is shorter than the min allowed ({minimum})."
        )

    maximum = description.get('max')
    if maximum is not None and len(stripped_value) > maximum:
        raise ValidationError(
            f"{description['label']}:\nThe provided string is longer than the max allowed ({maximum})."
        )


def default_number_validator(
    name: str, value, description: ParameterDescription, *args
):
    valid = isinstance(value, (int, float))

    if not valid:
        raise ValidationError(
            f"{description['label']}:\nThe provided value is not a number."
        )

    minimum = description.get('min')
    if minimum is not None and value < minimum:
        raise ValidationError(
            f"{description['label']}:\nThe provided value is below the min allowed."
        )

    maximum = description.get('max')
    if maximum is not None and value > maximum:
        raise ValidationError(
            f"{description['label']}:\nThe provided value is above the max allowed."
        )


def default_path_validator(
    name: str, value, description: ParameterDescription, *args
):
    required = description.get('required', True)

    if not required and (
        value is None or (isinstance(value, str) and len(value.strip()) == 0)
    ):
        return

    if not isinstance(value, str) or len(value.strip()) == 0:
        raise ValidationError(
            f"{description['label']}:\n{description['type'].capitalize()} must be specified."
        )

    path = Path(value).resolve()

    exists_fn = path.is_file if description['type'] == 'file' else path.is_dir

    if not exists_fn():
        raise ValidationError(
            f"{description['label']}:\n{description['type'].capitalize()}  does not exist: {path}"
        )


def noop_validator(name: str, value, description: ParameterDescription, *args):
    pass


DEFAULT_SCALAR_VALIDATORS: dict[ParameterType, ParameterValidator] = {
    'string': default_string_validator,
    'integer': default_number_validator,
    'float': default_number_validator,
    'folder': default_path_validator,
    'file': default_path_validator,
    'enum': noop_validator,
}


def default_tuple_validator(
    name: str, value, description: ParameterDescription, *args
):
    valid = isinstance(value, tuple)
    valid = valid and len(value) == description.get('length', 2)

    if not valid:
        raise ValidationError(
            f"{description['label']}:\nThe provided tuple value is not a {description.get('length', 2)} element tuple."
        )

    element_validator = DEFAULT_SCALAR_VALIDATORS.get(
        description.get('subtype', 'integer'), default_number_validator
    )

    for x in value:
        element_validator(name, x, description, *args)


DEFAULT_VALIDATORS: dict[ParameterType, ParameterValidator] = {
    **DEFAULT_SCALAR_VALIDATORS,
    'tuple': default_tuple_validator,
}


class Editable(Serializable):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.custom_validators: dict[str, ParameterValidator] = {}

    @classmethod
    def get_parameters_description(cls) -> dict[str, ParameterDescription]:
        raise NotImplementedError

    # default get parameters implementation, subclasses could implement their special version.
    def get_parameters(self) -> dict:
        return {k: getattr(self, k) for k in self.get_parameters_description()}

    # default set parameters implementation, subclasses could implement their special version.
    def set_parameters(self, params: dict, validate: bool = True):
        # No changes are committed unless all parameters are valid
        if validate:
            self.validate_parameters(params)

        for k, v in params.items():
            setattr(self, k, v)

    def validate_parameters(self, params):
        parameters_description = self.get_parameters_description()

        for k, description in parameters_description.items():
            if k not in params:
                raise ValidationError(
                    f'Parameter {k} is missing from the provided parameters dict.'
                )

            value = params[k]

            validator = self.custom_validators.get(k)

            if validator is None:
                validator = DEFAULT_VALIDATORS.get(
                    description['type'], noop_validator
                )

            validator(k, value, description, params, self)
