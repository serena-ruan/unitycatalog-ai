from dataclasses import dataclass
from typing import Optional


@dataclass
class DocstringInfo:
    """Dataclass to store parsed docstring information."""

    description: str
    params: Optional[dict[str, str]]
    returns: Optional[str]


class State:
    DESCRIPTION = "DESCRIPTION"
    ARGS = "ARGS"
    RETURNS = "RETURNS"
    END = "END"


def parse_docstring(docstring: str) -> DocstringInfo:
    """
    Parses the docstring to extract the function description, parameter comments,
    and return value description.
    Handles both reStructuredText and Google-style docstrings.

    Args:
        docstring: The docstring to parse.

    Returns:
        DocstringInfo: A dataclass containing the parsed information.

    Raises:
        ValueError: If the docstring is empty or missing a function description.
    """

    if not docstring or not docstring.strip():
        raise ValueError(
            "Docstring is empty. Please provide a docstring with a function description."
        )

    description_lines = []
    parsed_params = {}
    returns = None
    current_param = None
    param_description_lines = []
    return_description_lines = []

    state = State.DESCRIPTION
    lines = docstring.strip().splitlines()
    lines.append("")  # Add an empty line to ensure the last param is processed

    param_indent = None
    return_indent = None

    for line in lines:
        if not line.strip():
            if state == State.ARGS and current_param and param_description_lines:
                description = " ".join(param_description_lines).strip()
                if description:
                    parsed_params[current_param] = description
                current_param = None
                param_description_lines = []
            elif state == State.RETURNS and return_description_lines:
                returns = " ".join(return_description_lines).strip()
            continue

        stripped_line = line.lstrip()
        indent = len(line) - len(stripped_line)

        if state == State.DESCRIPTION:
            if stripped_line in ("Args:", "Arguments:"):
                state = State.ARGS
                param_indent = None
                continue
            elif stripped_line == "Returns:":
                state = State.RETURNS
                return_indent = None
                continue
            else:
                description_lines.append(stripped_line)
        elif state == State.ARGS:
            if stripped_line in ("Returns:",):
                state = State.RETURNS
                if current_param and param_description_lines:
                    description = " ".join(param_description_lines).strip()
                    if description:
                        parsed_params[current_param] = description
                    current_param = None
                    param_description_lines = []
                continue

            if param_indent is None:
                # Set the base indentation for parameters
                param_indent = indent

            if indent < param_indent:
                # End of Args section
                state = State.END
                if current_param and param_description_lines:
                    description = " ".join(param_description_lines).strip()
                    if description:
                        parsed_params[current_param] = description
                    current_param = None
                    param_description_lines = []
                # Reprocess this line in the new state
                if stripped_line in ("Args:", "Arguments:"):
                    state = State.ARGS
                    param_indent = None
                elif stripped_line == "Returns:":
                    state = State.RETURNS
                    return_indent = None
                else:
                    state = State.END
                continue

            # Check if the section line is a new parameter
            if ":" in stripped_line:
                # Split only at the first colon
                param_part, desc_part = stripped_line.split(":", 1)
                param_part = param_part.strip()
                desc_part = desc_part.strip()

                # Handle Google-style type hints in parameters, e.g., "param (int)"
                if "(" in param_part and param_part.endswith(")"):
                    param_name = param_part.split("(", 1)[0].strip()
                else:
                    param_name = param_part

                # If indent is equal to base indent, it's a new parameter
                if indent == param_indent:
                    if current_param and param_description_lines:
                        description = " ".join(param_description_lines).strip()
                        if description:
                            parsed_params[current_param] = description

                    current_param = param_name
                    param_description_lines = [desc_part] if desc_part else []
                else:
                    # Handle continuations
                    if current_param:
                        param_description_lines.append(stripped_line)
            else:
                # Handle continuation lines for the parameter description
                if current_param:
                    param_description_lines.append(stripped_line)
        elif state == State.RETURNS:
            if return_indent is None:
                return_indent = indent

            if indent < return_indent:
                state = State.END
                if return_description_lines:
                    returns = " ".join(return_description_lines).strip()
                if stripped_line in ("Args:", "Arguments:"):
                    state = State.ARGS
                    param_indent = None
                elif stripped_line == "Returns:":
                    state = State.RETURNS
                    return_indent = None
                else:
                    state = State.END
                continue

            return_description_lines.append(stripped_line)

    if state == State.ARGS and current_param and param_description_lines:
        description = " ".join(param_description_lines).strip()
        if description:
            parsed_params[current_param] = description
    if state == State.RETURNS and return_description_lines:
        returns = " ".join(return_description_lines).strip()

    description = " ".join(description_lines).strip()

    if not description:
        raise ValueError(
            "Function description is missing in the docstring. Please provide a function description."
        )

    return DocstringInfo(description=description, params=parsed_params, returns=returns)
