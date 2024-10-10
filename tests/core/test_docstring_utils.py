import pytest

from ucai.core.utils.docstring_utils import DocstringInfo, parse_docstring


def test_parse_docstring_empty():
    """
    Test that an empty docstring raises a ValueError.
    """
    with pytest.raises(ValueError, match="Docstring is empty"):
        parse_docstring("")


def test_parse_docstring_missing_description():
    """
    Test that a docstring without a description raises a ValueError.
    """
    docstring = """
    Args:
        x: The input value.
    Returns:
        int: The input value incremented by one.
    """
    with pytest.raises(ValueError, match="Function description is missing"):
        parse_docstring(docstring)


def test_parse_docstring_single_line_single_param():
    """
    Test parsing a simple docstring with a single-line description and one parameter.
    """
    docstring = """
    Add one to the input.

    Args:
        x: The input value.
    Returns:
        int: The input value incremented by one.
    """
    expected = DocstringInfo(
        description="Add one to the input.",
        params={"x": "The input value."},
        returns="int: The input value incremented by one.",
    )
    result = parse_docstring(docstring)
    assert result == expected


def test_parse_docstring_multiple_params():
    """
    Test parsing a docstring with multiple parameters.
    """
    docstring = """
    Calculate the area of a rectangle.

    Args:
        width: The width of the rectangle.
        height: The height of the rectangle.
    Returns:
        float: The area of the rectangle.
    """
    expected = DocstringInfo(
        description="Calculate the area of a rectangle.",
        params={"width": "The width of the rectangle.", "height": "The height of the rectangle."},
        returns="float: The area of the rectangle.",
    )
    result = parse_docstring(docstring)
    assert result == expected


def test_parse_docstring_multi_line_param_description_with_colon():
    """
    Test parsing a docstring where a parameter description spans multiple lines and includes a colon.
    """
    docstring = """
    Add one to the input.

    Args:
        x: The input value.
            For example: 4
    Returns:
        int: The input value incremented by one.
    """
    expected = DocstringInfo(
        description="Add one to the input.",
        params={"x": "The input value. For example: 4"},
        returns="int: The input value incremented by one.",
    )
    result = parse_docstring(docstring)
    assert result == expected


def test_parse_docstring_no_params():
    """
    Test parsing a docstring with no parameters.
    """
    docstring = """
    Get the current timestamp.

    Returns:
        str: The current timestamp in ISO format.
    """
    expected = DocstringInfo(
        description="Get the current timestamp.",
        params={},
        returns="str: The current timestamp in ISO format.",
    )
    result = parse_docstring(docstring)
    assert result == expected


def test_parse_docstring_google_style():
    """
    Test parsing a Google-style docstring.
    """
    docstring = """
    Calculate the sum of two numbers.

    Args:
        a (int): The first number.
        b (int): The second number.

    Returns:
        int: The sum of a and b.
    """
    expected = DocstringInfo(
        description="Calculate the sum of two numbers.",
        params={"a": "The first number.", "b": "The second number."},
        returns="int: The sum of a and b.",
    )
    result = parse_docstring(docstring)
    assert result == expected


def test_parse_docstring_malformed_missing_sections():
    """
    Test parsing a malformed docstring missing Args and Returns sections.
    """
    docstring = """
    Just a simple description without parameters or return information.
    """
    expected = DocstringInfo(
        description="Just a simple description without parameters or return information.",
        params={},
        returns=None,
    )
    result = parse_docstring(docstring)
    assert result == expected


def test_parse_docstring_parameters_without_descriptions():
    """
    Test parsing a docstring where parameters are listed without descriptions.
    """
    docstring = """
    Process data.

    Args:
        data:
        config:
    Returns:
        bool: Success status.
    """
    expected = DocstringInfo(
        description="Process data.", params={}, returns="bool: Success status."
    )
    result = parse_docstring(docstring)
    assert result == expected


def test_parse_docstring_returns_without_description():
    """
    Test parsing a docstring where the Returns section is present without a description.
    """
    docstring = """
    Check if the user is active.

    Args:
        user_id: The ID of the user.

    Returns:
        bool:
    """
    expected = DocstringInfo(
        description="Check if the user is active.",
        params={"user_id": "The ID of the user."},
        returns="bool:",
    )
    result = parse_docstring(docstring)
    assert result == expected


def test_parse_docstring_extra_colons_in_description():
    """
    Test parsing a docstring with extra colons in the parameter description.
    """
    docstring = """
    Add one to the input.

    Args:
        x: The input value.
            Note: This should be an integer.
    Returns:
        int: The input value incremented by one.
    """
    expected = DocstringInfo(
        description="Add one to the input.",
        params={"x": "The input value. Note: This should be an integer."},
        returns="int: The input value incremented by one.",
    )
    result = parse_docstring(docstring)
    assert result == expected


def test_parse_docstring_multiple_colons_in_description():
    """
    Test parsing a docstring with multiple colons in a single parameter description.
    """
    docstring = """
    Configure the server.

    Args:
        config: Server configuration.
            Details: Should include IP, port, and protocol.
            Example: ip=127.0.0.1, port=8080, protocol=http
    Returns:
        None:
    """
    expected = DocstringInfo(
        description="Configure the server.",
        params={
            "config": "Server configuration. Details: Should include IP, port, and protocol. Example: ip=127.0.0.1, port=8080, protocol=http"
        },
        returns="None:",
    )
    result = parse_docstring(docstring)
    assert result == expected
