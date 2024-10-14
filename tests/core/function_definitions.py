import base64
import datetime
from decimal import Decimal
from typing import Any, Callable, Dict, List, NamedTuple


class PythonFunctionInputOutput(NamedTuple):
    func: Callable
    inputs: List[Dict[str, Any]]
    output: str


def python_function_with_dict_input() -> PythonFunctionInputOutput:
    def function_with_dict_input(s: Dict[str, int]) -> int:
        """Python function that sums the values in a dictionary."""
        return sum(s.values())

    return PythonFunctionInputOutput(
        func=function_with_dict_input,
        inputs=[{"s": {"a": 1, "b": 3, "c": 4}}],
        output="8",
    )


def python_function_with_array_input() -> PythonFunctionInputOutput:
    def function_with_array_input(s: List[int]) -> str:
        """Python function with array input"""
        return ",".join(str(i) for i in s)

    return PythonFunctionInputOutput(
        func=function_with_array_input,
        inputs=[{"s": [1, 2, 3]}],
        output="1,2,3",
    )


def python_function_with_string_input() -> PythonFunctionInputOutput:
    def function_with_string_input(s: str) -> str:
        """Python function with string input"""
        return s

    return PythonFunctionInputOutput(
        func=function_with_string_input,
        inputs=[{"s": "abc"}],
        output="abc",
    )


def python_function_with_binary_input() -> PythonFunctionInputOutput:
    def function_with_binary_input(s: bytes) -> str:
        """Python function with binary input"""
        return s.decode("utf-8")

    return PythonFunctionInputOutput(
        func=function_with_binary_input,
        inputs=[
            {"s": base64.b64encode(b"Hello").decode("utf-8")},
            {"s": "SGVsbG8="},
        ],
        output="Hello",
    )


def python_function_with_interval_input() -> PythonFunctionInputOutput:
    def function_with_interval_input(s: datetime.timedelta) -> str:
        """Python function with interval input"""
        import datetime

        return (datetime.datetime(2024, 8, 19) - s).isoformat()

    return PythonFunctionInputOutput(
        func=function_with_interval_input,
        inputs=[
            {"s": datetime.timedelta(days=0, hours=0, minutes=16, seconds=40, microseconds=123456)},
            {"s": datetime.timedelta(days=0, seconds=1000, microseconds=123456)},
        ],
        output="2024-08-18T23:43:19.876544",
    )


def python_function_with_timestamp_input() -> PythonFunctionInputOutput:
    def function_with_timestamp_input(x: datetime.datetime, y: datetime.datetime) -> str:
        """Python function with timestamp input"""
        return str(x.isoformat()) + "; " + str(y.isoformat())

    return PythonFunctionInputOutput(
        func=function_with_timestamp_input,
        inputs=[
            {
                "x": datetime.datetime(2024, 8, 19, 11, 2, 3),
                "y": datetime.datetime(2024, 8, 19, 11, 2, 3),
            },
            {"x": "2024-08-19T11:02:03", "y": "2024-08-19T11:02:03"},
        ],
        output="2024-08-19T11:02:03+00:00; 2024-08-19T11:02:03+00:00",
    )


def python_function_with_date_input() -> PythonFunctionInputOutput:
    def function_with_date_input(s: datetime.date) -> str:
        """Python function with date input"""
        return s.isoformat()

    return PythonFunctionInputOutput(
        func=function_with_date_input,
        inputs=[{"s": datetime.date(2024, 8, 19)}, {"s": "2024-08-19"}],
        output="2024-08-19",
    )


def python_function_with_map_input() -> PythonFunctionInputOutput:
    def function_with_map_input(s: Dict[str, List[int]]) -> str:
        """Python function with map input"""
        result = []
        for key, value in s.items():
            result.append(str(key) + " => " + str(value))
        return ",".join(result)

    return PythonFunctionInputOutput(
        func=function_with_map_input,
        inputs=[{"s": {"a": [1, 2, 3], "b": [4, 5, 6]}}],
        output="a => [1, 2, 3],b => [4, 5, 6]",
    )


def python_function_with_decimal_input() -> PythonFunctionInputOutput:
    def function_with_decimal_input(s: Decimal) -> str:
        """Python function with decimal input."""
        return format(s, ".20g")

    return PythonFunctionInputOutput(
        func=function_with_decimal_input,
        inputs=[{"s": Decimal("123.45123456789457000")}],
        output="123.45123456789457000",
    )
