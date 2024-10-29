from collections import defaultdict
from typing import Mapping, Sequence
from warnings import filterwarnings, warn

from .colors import color
from .constants import BOTTOM, LEFT, RIGHT, TOP

# Make sure deprecation warnings are shown by default
filterwarnings("default", category=DeprecationWarning)


class ImmutableList:
    def __init__(self, iterable):
        self._data = [*iterable]

    def __getitem__(self, index):
        return self._data[index]

    def __len__(self):
        return len(self._data)

    def __iter__(self):
        return iter(self._data)

    def __eq__(self, other):
        return self._data == other

    def __str__(self):
        return str(self._data)

    def __repr__(self):
        return repr(self._data)


class Choices:
    "A class to define allowable data types for a property"

    def __init__(
        self,
        *constants,
        default=None,  # DEPRECATED
        string=False,
        integer=False,
        number=False,
        color=False,
    ):
        if default is not None:
            warn(
                "The `default` argument to Choices.__init__ is deprecated. "
                "Providing no initial value to a property using it is sufficient.",
                DeprecationWarning,
                stacklevel=2,
            )

        self.constants = set(constants)

        self.string = string
        self.integer = integer
        self.number = number
        self.color = color

        self._options = sorted(str(c).lower().replace("_", "-") for c in self.constants)
        if self.string:
            self._options.append("<string>")
        if self.integer:
            self._options.append("<integer>")
        if self.number:
            self._options.append("<number>")
        if self.color:
            self._options.append("<color>")

    def validate(self, value):
        if self.string:
            try:
                return value.strip()
            except AttributeError:
                pass
        if self.integer:
            try:
                return int(value)
            except (ValueError, TypeError):
                pass
        if self.number:
            try:
                return float(value)
            except (ValueError, TypeError):
                pass
        if self.color:
            try:
                return color(value)
            except ValueError:
                pass
        for const in self.constants:
            if value == const:
                return const

        raise ValueError(f"{value!r} is not a valid value")

    def __str__(self):
        return ", ".join(self._options)


class validated_property:
    def __init__(self, choices, initial=None):
        """Define a simple validated property attribute.

        :param choices: The available choices.
        :param initial: The initial value for the property.
        """
        self.choices = choices
        self.initial = None

        try:
            # If an initial value has been provided, it must be consistent with
            # the choices specified.
            if initial is not None:
                self.initial = self.validate(initial)
        except ValueError:
            # Unfortunately, __set_name__ hasn't been called yet, so we don't know the
            # property's name.
            raise ValueError(
                f"Invalid initial value {initial!r}. Available choices: {choices}"
            )

    def __set_name__(self, owner, name):
        self.name = name
        owner._BASE_PROPERTIES[owner].add(name)
        owner._BASE_ALL_PROPERTIES[owner].add(name)

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self

        value = getattr(obj, f"_{self.name}", None)
        return self.initial if value is None else value

    def __set__(self, obj, value):
        if value is self:
            # This happens during autogenerated dataclass __init__ when no value is
            # supplied.
            return

        if value is None:
            raise ValueError(
                "Python `None` cannot be used as a style value; "
                f"to reset a property, use del `style.{self.name}`."
            )

        value = self.validate(value)

        if value != getattr(obj, f"_{self.name}", None):
            setattr(obj, f"_{self.name}", value)
            obj.apply(self.name, value)

    def __delete__(self, obj):
        try:
            delattr(obj, f"_{self.name}")
        except AttributeError:
            pass
        else:
            obj.apply(self.name, self.initial)

    @property
    def _name_if_set(self, default=""):
        return f" {self.name}" if hasattr(self, "name") else default

    def validate(self, value):
        try:
            return self.choices.validate(value)
        except ValueError:
            raise ValueError(
                f"Invalid value {value!r} for property{self._name_if_set}; "
                f"Valid values are: {self.choices}"
            )

    def is_set_on(self, obj):
        return hasattr(obj, f"_{self.name}")


class list_property(validated_property):
    def validate(self, value):
        if isinstance(value, str):
            value = [value]
        elif not isinstance(value, Sequence):
            raise TypeError(
                f"Value for list property{self._name_if_set} must be a sequence."
            )

        if not value:
            name = getattr(self, "name", "prop_name")
            raise ValueError(
                "List properties cannot be set to an empty sequence; "
                f"to reset a property, use del `style.{name}`."
            )

        # This could be a comprehension, but then the error couldn't specify which value
        # is at fault.
        result = []
        for item in value:
            try:
                item = self.choices.validate(item)
            except ValueError:
                raise ValueError(
                    f"Invalid item value {item!r} for list property{self._name_if_set}; "
                    f"Valid values are: {self.choices}"
                )
            result.append(item)

        return ImmutableList(result)


class directional_property:
    DIRECTIONS = [TOP, RIGHT, BOTTOM, LEFT]
    ASSIGNMENT_SCHEMES = {
        #   T  R  B  L
        1: [0, 0, 0, 0],
        2: [0, 1, 0, 1],
        3: [0, 1, 2, 1],
        4: [0, 1, 2, 3],
    }

    def __init__(self, name_format):
        """Define a property attribute that proxies for top/right/bottom/left alternatives.

        :param name_format: The format from which to generate subproperties. "{}" will
            be replaced with "_top", etc.
        """
        self.name_format = name_format

    def __set_name__(self, owner, name):
        self.name = name
        owner._BASE_ALL_PROPERTIES[owner].add(self.name)

    def format(self, direction):
        return self.name_format.format(f"_{direction}")

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self

        return tuple(obj[self.format(direction)] for direction in self.DIRECTIONS)

    def __set__(self, obj, value):
        if value is self:
            # This happens during autogenerated dataclass __init__ when no value is
            # supplied.
            return

        if not isinstance(value, tuple):
            value = (value,)

        if order := self.ASSIGNMENT_SCHEMES.get(len(value)):
            for direction, index in zip(self.DIRECTIONS, order):
                obj[self.format(direction)] = value[index]
        else:
            raise ValueError(
                f"Invalid value for '{self.name}'; value must be a number, or a 1-4 tuple."
            )

    def __delete__(self, obj):
        for direction in self.DIRECTIONS:
            del obj[self.format(direction)]

    def is_set_on(self, obj):
        return any(
            hasattr(obj, self.format(direction)) for direction in self.DIRECTIONS
        )


class BaseStyle:
    """A base class for style declarations.

    Exposes a dict-like interface. Designed for subclasses to be decorated
    with @dataclass(kw_only=True), which most IDEs should be able to interpret and
    provide autocompletion of argument names. On Python < 3.10, init=False can be used
    to still get the keyword-only behavior from the included __init__.
    """

    _BASE_PROPERTIES = defaultdict(set)
    _BASE_ALL_PROPERTIES = defaultdict(set)

    def __init_subclass__(cls):
        # Give the subclass a direct reference to its properties.
        cls._PROPERTIES = cls._BASE_PROPERTIES[cls]
        cls._ALL_PROPERTIES = cls._BASE_ALL_PROPERTIES[cls]

    # Fallback in case subclass isn't decorated as subclass (probably from using
    # previous API) or for pre-3.10, before kw_only argument existed.
    def __init__(self, **style):
        self.update(**style)

    @property
    def _applicator(self):
        return getattr(self, "_assigned_applicator", None)

    @_applicator.setter
    def _applicator(self, value):
        self._assigned_applicator = value

    ######################################################################
    # Interface that style declarations must define
    ######################################################################

    def apply(self, property, value):
        raise NotImplementedError(
            "Style must define an apply method"
        )  # pragma: no cover

    ######################################################################
    # Provide a dict-like interface
    ######################################################################

    def reapply(self):
        for name in self._PROPERTIES:
            self.apply(name, self[name])

    def update(self, **styles):
        "Set multiple styles on the style definition."
        for name, value in styles.items():
            name = name.replace("-", "_")
            if name not in self._ALL_PROPERTIES:
                raise NameError(f"Unknown style {name}")

            self[name] = value

    def copy(self, applicator=None):
        "Create a duplicate of this style declaration."
        dup = self.__class__()
        dup.update(**self)

        if applicator is not None:
            warn(
                "Providing an applicator to BaseStyle.copy() is deprecated. Set "
                "applicator afterward on the returned copy.",
                DeprecationWarning,
                stacklevel=2,
            )
            dup._applicator = applicator

        return dup

    def __getitem__(self, name):
        name = name.replace("-", "_")
        if name in self._ALL_PROPERTIES:
            return getattr(self, name)
        raise KeyError(name)

    def __setitem__(self, name, value):
        name = name.replace("-", "_")
        if name in self._ALL_PROPERTIES:
            setattr(self, name, value)
        else:
            raise KeyError(name)

    def __delitem__(self, name):
        name = name.replace("-", "_")
        if name in self._ALL_PROPERTIES:
            delattr(self, name)
        else:
            raise KeyError(name)

    def keys(self):
        return {name for name in self._PROPERTIES if name in self}

    def items(self):
        return [(name, self[name]) for name in self._PROPERTIES if name in self]

    def __len__(self):
        return sum(1 for name in self._PROPERTIES if name in self)

    def __contains__(self, name):
        return name in self._ALL_PROPERTIES and (
            getattr(self.__class__, name).is_set_on(self)
        )

    def __iter__(self):
        yield from (name for name in self._PROPERTIES if name in self)

    def __or__(self, other):
        if isinstance(other, BaseStyle):
            if self.__class__ is not other.__class__:
                return NotImplemented
        elif not isinstance(other, Mapping):
            return NotImplemented

        result = self.copy()
        result.update(**other)
        return result

    def __ior__(self, other):
        if isinstance(other, BaseStyle):
            if self.__class__ is not other.__class__:
                return NotImplemented
        elif not isinstance(other, Mapping):
            return NotImplemented

        self.update(**other)
        return self

    ######################################################################
    # Get the rendered form of the style declaration
    ######################################################################
    def __str__(self):
        return "; ".join(
            f"{name.replace('_', '-')}: {value}" for name, value in sorted(self.items())
        )

    ######################################################################
    # Backwards compatibility
    ######################################################################

    @classmethod
    def validated_property(cls, name, choices, initial=None):
        warn(
            "Defining style properties with class methods is deprecated; use class "
            "attributes instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        prop = validated_property(choices, initial)
        setattr(cls, name, prop)
        prop.__set_name__(cls, name)

    @classmethod
    def directional_property(cls, name):
        warn(
            "Defining style properties with class methods is deprecated; use class "
            "attributes instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        name_format = name % "{}"
        name = name_format.format("")
        prop = directional_property(name_format)
        setattr(cls, name, prop)
        prop.__set_name__(cls, name)
