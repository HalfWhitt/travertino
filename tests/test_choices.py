from __future__ import annotations

import sys
from dataclasses import dataclass
from unittest.mock import Mock
from warnings import catch_warnings, filterwarnings

import pytest

from travertino.colors import NAMED_COLOR, rgb
from travertino.constants import GOLDENROD, NONE, REBECCAPURPLE, TOP
from travertino.declaration import BaseStyle, Choices, validated_property

if sys.version_info < (3, 10):
    _DATACLASS_KWARGS = {"init": False}
else:
    _DATACLASS_KWARGS = {"kw_only": True}


def prep_style_class(cls):
    """Decorator to apply dataclass and mock a style class's apply method."""
    return dataclass(**_DATACLASS_KWARGS)(mock_apply(cls))


def mock_apply(cls):
    """Only mock apply, without applying dataclass. For testing deprecated API."""
    orig_init = cls.__init__

    def __init__(self, *args, **kwargs):
        self.apply = Mock()
        orig_init(self, *args, **kwargs)

    cls.__init__ = __init__
    return cls


@prep_style_class
class Style(BaseStyle):
    none: str = validated_property(choices=Choices(NONE, REBECCAPURPLE), initial=NONE)
    allow_string: str = validated_property(
        choices=Choices(string=True), initial="start"
    )
    allow_integer: int = validated_property(choices=Choices(integer=True), initial=0)
    allow_number: float = validated_property(choices=Choices(number=True), initial=0)
    allow_color: str = validated_property(
        choices=Choices(color=True), initial="goldenrod"
    )
    values: str = validated_property(choices=Choices("a", "b", NONE), initial="a")
    multiple_choices: str | float = validated_property(
        choices=Choices("a", "b", NONE, number=True, color=True),
        initial=None,
    )
    string_symbol: str = validated_property(choices=Choices(TOP, NONE))


with catch_warnings():
    filterwarnings("ignore", category=DeprecationWarning)

    @mock_apply
    class DeprecatedStyle(BaseStyle):
        pass

    DeprecatedStyle.validated_property(
        "none", choices=Choices(NONE, REBECCAPURPLE), initial=NONE
    )
    DeprecatedStyle.validated_property(
        "allow_string", choices=Choices(string=True), initial="start"
    )
    DeprecatedStyle.validated_property(
        "allow_integer", choices=Choices(integer=True), initial=0
    )
    DeprecatedStyle.validated_property(
        "allow_number", choices=Choices(number=True), initial=0
    )
    DeprecatedStyle.validated_property(
        "allow_color", choices=Choices(color=True), initial="goldenrod"
    )
    DeprecatedStyle.validated_property(
        "values", choices=Choices("a", "b", NONE), initial="a"
    )
    DeprecatedStyle.validated_property(
        "multiple_choices",
        choices=Choices("a", "b", NONE, number=True, color=True),
        initial=None,
    )
    DeprecatedStyle.validated_property("string_symbol", choices=Choices(TOP, NONE))


@pytest.mark.parametrize("StyleClass", [Style, DeprecatedStyle])
def test_none(StyleClass):
    style = StyleClass()
    assert style.none == NONE

    with pytest.raises(ValueError):
        style.none = 10

    with pytest.raises(ValueError):
        style.none = 3.14159

    with pytest.raises(ValueError):
        style.none = "#112233"

    with pytest.raises(ValueError):
        style.none = "a"

    with pytest.raises(ValueError):
        style.none = "b"

    # Set the property to a different explicit value
    style.none = REBECCAPURPLE
    assert style.none == REBECCAPURPLE

    # A Travertino NONE is an explicit value
    style.none = NONE
    assert style.none == NONE

    # Set the property to a different explicit value
    style.none = REBECCAPURPLE
    assert style.none == REBECCAPURPLE

    # A Python None is invalid
    with pytest.raises(ValueError):
        style.none = None

    # The property can be reset
    del style.none
    assert style.none == NONE

    with pytest.raises(
        ValueError,
        match=r"Invalid value 'invalid' for property none; Valid values are: "
        r"none, rebeccapurple",
    ):
        style.none = "invalid"


@pytest.mark.parametrize("StyleClass", [Style, DeprecatedStyle])
def test_allow_string(StyleClass):
    style = StyleClass()
    assert style.allow_string == "start"

    with pytest.raises(ValueError):
        style.allow_string = 10

    with pytest.raises(ValueError):
        style.allow_string = 3.14159

    style.allow_string = REBECCAPURPLE
    assert style.allow_string == "rebeccapurple"

    style.allow_string = "#112233"
    assert style.allow_string == "#112233"

    style.allow_string = "a"
    assert style.allow_string == "a"

    style.allow_string = "b"
    assert style.allow_string == "b"

    # A Travertino NONE is an explicit string value
    style.allow_string = NONE
    assert style.allow_string == NONE

    # A Python None is invalid
    with pytest.raises(ValueError):
        style.allow_string = None

    # The property can be reset
    del style.allow_string
    assert style.allow_string == "start"

    with pytest.raises(
        ValueError,
        match=r"Invalid value 99 for property allow_string; Valid values are: <string>",
    ):
        style.allow_string = 99


@pytest.mark.parametrize("StyleClass", [Style, DeprecatedStyle])
def test_allow_integer(StyleClass):
    style = StyleClass()
    assert style.allow_integer == 0

    style.allow_integer = 10
    assert style.allow_integer == 10

    # This is an odd case; Python happily rounds floats to integers.
    # It's more trouble than it's worth to correct this.
    style.allow_integer = 3.14159
    assert style.allow_integer == 3

    with pytest.raises(ValueError):
        style.allow_integer = REBECCAPURPLE

    with pytest.raises(ValueError):
        style.allow_integer = "#112233"

    with pytest.raises(ValueError):
        style.allow_integer = "a"

    with pytest.raises(ValueError):
        style.allow_integer = "b"

    # A Travertino NONE is an explicit string value
    with pytest.raises(ValueError):
        style.allow_integer = NONE

    # A Python None is invalid
    with pytest.raises(ValueError):
        style.allow_integer = None

    # The property can be reset
    del style.allow_integer
    assert style.allow_integer == 0

    # Check the error message
    with pytest.raises(
        ValueError,
        match=r"Invalid value 'invalid' for property allow_integer; Valid values are: <integer>",
    ):
        style.allow_integer = "invalid"


@pytest.mark.parametrize("StyleClass", [Style, DeprecatedStyle])
def test_allow_number(StyleClass):
    style = StyleClass()
    assert style.allow_number == 0

    style.allow_number = 10
    assert style.allow_number == 10.0

    style.allow_number = 3.14159
    assert style.allow_number == 3.14159

    with pytest.raises(ValueError):
        style.allow_number = REBECCAPURPLE

    with pytest.raises(ValueError):
        style.allow_number = "#112233"

    with pytest.raises(ValueError):
        style.allow_number = "a"

    with pytest.raises(ValueError):
        style.allow_number = "b"

    # A Travertino NONE is an explicit string value
    with pytest.raises(ValueError):
        style.allow_number = NONE

    # A Python None is invalid
    with pytest.raises(ValueError):
        style.allow_number = None

    # The property can be reset
    del style.allow_number
    assert style.allow_number == 0

    with pytest.raises(
        ValueError,
        match=r"Invalid value 'invalid' for property allow_number; Valid values are: <number>",
    ):
        style.allow_number = "invalid"


@pytest.mark.parametrize("StyleClass", [Style, DeprecatedStyle])
def test_allow_color(StyleClass):
    style = StyleClass()
    assert style.allow_color == NAMED_COLOR[GOLDENROD]

    with pytest.raises(ValueError):
        style.allow_color = 10

    with pytest.raises(ValueError):
        style.allow_color = 3.14159

    style.allow_color = REBECCAPURPLE
    assert style.allow_color == NAMED_COLOR[REBECCAPURPLE]

    style.allow_color = "#112233"
    assert style.allow_color == rgb(0x11, 0x22, 0x33)

    with pytest.raises(ValueError):
        style.allow_color = "a"

    with pytest.raises(ValueError):
        style.allow_color = "b"

    # A Travertino NONE is an explicit string value
    with pytest.raises(ValueError):
        style.allow_color = NONE

    # A Python None is invalid
    with pytest.raises(ValueError):
        style.allow_color = None

    # The property can be reset
    del style.allow_color
    assert style.allow_color == NAMED_COLOR["goldenrod"]

    with pytest.raises(
        ValueError,
        match=r"Invalid value 'invalid' for property allow_color; Valid values are: <color>",
    ):
        style.allow_color = "invalid"


@pytest.mark.parametrize("StyleClass", [Style, DeprecatedStyle])
def test_values(StyleClass):
    style = StyleClass()
    assert style.values == "a"

    with pytest.raises(ValueError):
        style.values = 10

    with pytest.raises(ValueError):
        style.values = 3.14159

    with pytest.raises(ValueError):
        style.values = REBECCAPURPLE

    with pytest.raises(ValueError):
        style.values = "#112233"

    style.values = NONE
    assert style.values == NONE

    style.values = "b"
    assert style.values == "b"

    # A Python None is invalid
    with pytest.raises(ValueError):
        style.values = None

    # The property can be reset
    del style.values
    assert style.values == "a"

    with pytest.raises(
        ValueError,
        match=r"Invalid value 'invalid' for property values; Valid values are: a, b, none",
    ):
        style.values = "invalid"


@pytest.mark.parametrize("StyleClass", [Style, DeprecatedStyle])
def test_multiple_choices(StyleClass):
    style = StyleClass()

    style.multiple_choices = 10
    assert style.multiple_choices == 10.0

    style.multiple_choices = 3.14159
    assert style.multiple_choices == 3.14159

    style.multiple_choices = REBECCAPURPLE
    assert style.multiple_choices == NAMED_COLOR[REBECCAPURPLE]

    style.multiple_choices = "#112233"
    assert style.multiple_choices == rgb(0x11, 0x22, 0x33)

    style.multiple_choices = "a"
    assert style.multiple_choices == "a"

    style.multiple_choices = NONE
    assert style.multiple_choices == NONE

    style.multiple_choices = "b"
    assert style.multiple_choices == "b"

    # A Python None is invalid
    with pytest.raises(ValueError):
        style.multiple_choices = None

    # The property can be reset
    # There's no initial value, so the property is None
    del style.multiple_choices
    assert style.multiple_choices is None

    # Check the error message
    with pytest.raises(
        ValueError,
        match=r"Invalid value 'invalid' for property multiple_choices; Valid values are: "
        r"a, b, none, <number>, <color>",
    ):
        style.multiple_choices = "invalid"


@pytest.mark.parametrize("StyleClass", [Style, DeprecatedStyle])
def test_string_symbol(StyleClass):
    style = StyleClass()

    # Set a symbolic value using the string value of the symbol
    # We can't just use the string directly, though - that would
    # get optimized by the compiler. So we create a string and
    # transform it into the value we want.
    val = "TOP"
    style.string_symbol = val.lower()

    # Both equality and instance checking should work.
    assert style.string_symbol == TOP
    assert style.string_symbol is TOP
