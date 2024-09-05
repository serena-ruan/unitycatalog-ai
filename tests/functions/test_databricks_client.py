import base64
import datetime
import logging
import uuid
from contextlib import contextmanager
from decimal import Decimal
from importlib.metadata import version
from typing import Any, Callable, Dict, List, NamedTuple
from unittest import mock

import pytest
from databricks.sdk.service.catalog import (
    ColumnTypeName,
    CreateFunction,
    CreateFunctionParameterStyle,
    CreateFunctionRoutineBody,
    CreateFunctionSecurityType,
    CreateFunctionSqlDataAccess,
    DependencyList,
    FunctionInfo,
    FunctionParameterInfo,
    FunctionParameterInfos,
)

from unitycatalog.functions.databricks import (
    DEFAULT_EXECUTE_FUNCTION_ARGS,
    EXECUTE_FUNCTION_ARG_NAME,
    DatabricksFunctionClient,
    extract_function_name,
)

CATALOG = "ml"
SCHEMA = "serena_uc_test"

_logger = logging.getLogger(__name__)


@pytest.fixture
def client() -> DatabricksFunctionClient:
    return DatabricksFunctionClient(warehouse_id="fake_warehouse_id")


def random_func_name():
    return f"test_{uuid.uuid4().hex[:4]}"


@contextmanager
def generate_func_name_and_cleanup(client: DatabricksFunctionClient):
    func_name = random_func_name()
    try:
        yield func_name
    finally:
        try:
            client.client.functions.delete(f"{CATALOG}.{SCHEMA}.{func_name}")
        except Exception as e:
            _logger.warning(f"Fail to delete function: {e}")


class FunctionInputOutput(NamedTuple):
    sql_body: str
    func_name: str
    inputs: List[Dict[str, Any]]
    output: str


def function_with_struct_input(func_name: str) -> FunctionInputOutput:
    sql_body = f"""CREATE OR REPLACE FUNCTION {CATALOG}.{SCHEMA}.{func_name}(s STRUCT<a: SHORT NOT NULL COMMENT 'short field', b: MAP<STRING, FLOAT>, c: INT NOT NULL>)
RETURNS STRING
LANGUAGE PYTHON
AS $$
  result = str(s['a']) + ";"
  if s['b']:
    result += ",".join([str(k) + "=>" + str(v) for k, v in s['b'].items()])
  result += ";" + str(s['c'])
  return result
$$
"""
    return FunctionInputOutput(
        sql_body=sql_body,
        func_name=f"{CATALOG}.{SCHEMA}.{func_name}",
        inputs=[{"s": {"a": 1, "b": {"2": 2, "3.0": 3.0}, "c": 4}}],
        output="1;2=>2.0,3.0=>3.0;4",
    )


def function_with_array_input(func_name: str) -> FunctionInputOutput:
    sql_body = f"""CREATE FUNCTION {CATALOG}.{SCHEMA}.{func_name}(s ARRAY<BYTE>)
RETURNS ARRAY<STRING>
LANGUAGE PYTHON
AS $$
    return [str(i) for i in s]
$$
"""
    return FunctionInputOutput(
        sql_body=sql_body,
        func_name=f"{CATALOG}.{SCHEMA}.{func_name}",
        inputs=[{"s": [1, 2, 3]}],
        output='["1","2","3"]',
    )


def function_with_binary_input(func_name: str) -> FunctionInputOutput:
    sql_body = f"""CREATE FUNCTION {CATALOG}.{SCHEMA}.{func_name}(s BINARY)
RETURNS STRING
LANGUAGE PYTHON
AS $$
  return s.decode('utf-8')
$$
"""
    return FunctionInputOutput(
        sql_body=sql_body,
        func_name=f"{CATALOG}.{SCHEMA}.{func_name}",
        inputs=[{"s": base64.b64encode(b"Hello").decode("utf-8")}],
        output="Hello",
    )


def function_with_interval_input(func_name: str) -> FunctionInputOutput:
    sql_body = f"""CREATE FUNCTION {CATALOG}.{SCHEMA}.{func_name}(s INTERVAL DAY TO SECOND)
RETURNS STRING
LANGUAGE PYTHON
AS $$
  import datetime

  return (datetime.datetime(2024, 8, 19) - s).isoformat()
$$
"""
    return FunctionInputOutput(
        sql_body=sql_body,
        func_name=f"{CATALOG}.{SCHEMA}.{func_name}",
        inputs=[
            {"s": "INTERVAL '0 0:16:40.123456' DAY TO SECOND"},
            {"s": datetime.timedelta(days=0, hours=0, minutes=16, seconds=40, microseconds=123456)},
            {"s": datetime.timedelta(days=0, seconds=1000, microseconds=123456)},
        ],
        output="2024-08-18T23:43:19.876544",
    )


def function_with_timestamp_input(func_name: str) -> FunctionInputOutput:
    sql_body = f"""CREATE FUNCTION {CATALOG}.{SCHEMA}.{func_name}(x TIMESTAMP, y TIMESTAMP_NTZ)
RETURNS STRING
LANGUAGE PYTHON
AS $$
  return str(x.isoformat()) + "; " + str(y.isoformat())
$$
"""
    return FunctionInputOutput(
        sql_body=sql_body,
        func_name=f"{CATALOG}.{SCHEMA}.{func_name}",
        inputs=[
            {
                "x": datetime.datetime(2024, 8, 19, 11, 2, 3),
                "y": datetime.datetime(2024, 8, 19, 11, 2, 3),
            },
            {"x": "2024-08-19T11:02:03", "y": "2024-08-19T11:02:03"},
        ],
        output="2024-08-19T11:02:03+00:00; 2024-08-19T11:02:03",
    )


def function_with_date_input(func_name: str) -> FunctionInputOutput:
    sql_body = f"""CREATE FUNCTION {CATALOG}.{SCHEMA}.{func_name}(s DATE)
RETURNS STRING
LANGUAGE PYTHON
AS $$
  return s.isoformat()
$$
"""
    return FunctionInputOutput(
        sql_body=sql_body,
        func_name=f"{CATALOG}.{SCHEMA}.{func_name}",
        inputs=[{"s": datetime.date(2024, 8, 19)}, {"s": "2024-08-19"}],
        output="2024-08-19",
    )


def function_with_map_input(func_name: str) -> FunctionInputOutput:
    sql_body = f"""CREATE FUNCTION {CATALOG}.{SCHEMA}.{func_name}(s MAP<STRING, ARRAY<INT>>)
RETURNS STRING
LANGUAGE PYTHON
AS $$
  result = []
  for x, y in s.items():
     result.append(str(x) + " => " + str(y))
  return ",".join(result)
$$
"""
    return FunctionInputOutput(
        sql_body=sql_body,
        func_name=f"{CATALOG}.{SCHEMA}.{func_name}",
        inputs=[{"s": {"a": [1, 2, 3], "b": [4, 5, 6]}}],
        output="a => [1, 2, 3],b => [4, 5, 6]",
    )


def function_with_decimal_input(func_name: str) -> FunctionInputOutput:
    sql_body = f"""CREATE FUNCTION {CATALOG}.{SCHEMA}.{func_name}(s DECIMAL(10, 2))
RETURNS STRING
LANGUAGE PYTHON
AS $$
    return str(s)
$$
"""
    return FunctionInputOutput(
        sql_body=sql_body,
        func_name=f"{CATALOG}.{SCHEMA}.{func_name}",
        inputs=[{"s": 123.45}, {"s": Decimal("123.45")}],
        output="123.45",
    )


def function_with_table_output(func_name: str) -> FunctionInputOutput:
    sql_body = f"""CREATE FUNCTION {CATALOG}.{SCHEMA}.{func_name}(start DATE, end DATE)
RETURNS TABLE(day_of_week STRING, day DATE)
RETURN SELECT extract(DAYOFWEEK_ISO FROM day), day
            FROM (SELECT sequence({func_name}.start, {func_name}.end)) AS T(days)
                LATERAL VIEW explode(days) AS day
            WHERE extract(DAYOFWEEK_ISO FROM day) BETWEEN 1 AND 5;
"""
    return FunctionInputOutput(
        sql_body=sql_body,
        func_name=f"{CATALOG}.{SCHEMA}.{func_name}",
        inputs=[{"start": datetime.date(2024, 1, 1), "end": "2024-01-07"}],
        output="day_of_week,day\n1,2024-01-01\n2,2024-01-02\n3,2024-01-03\n4,2024-01-04\n5,2024-01-05\n",
    )


def test_create_function_with_function_info(client: DatabricksFunctionClient):
    catalog_name = "ml"
    schema_name = "serena_test"
    func_name = "test"
    create_function = CreateFunction(
        name=func_name,
        catalog_name=catalog_name,
        schema_name=schema_name,
        input_params=FunctionParameterInfos(
            [
                FunctionParameterInfo(
                    "x",
                    type_name=ColumnTypeName.STRING,
                    type_text="string",
                    position=0,
                    type_json='{"name":"x","type":"string","nullable":true,"metadata":{}}',
                )
            ]
        ),
        data_type=ColumnTypeName.STRING,
        external_language="Python",
        comment="test function",
        routine_body=CreateFunctionRoutineBody.EXTERNAL,
        routine_definition="return x",
        full_data_type="STRING",
        return_params=FunctionParameterInfos(),
        routine_dependencies=DependencyList(),
        parameter_style=CreateFunctionParameterStyle.S,  # list things that is broken
        is_deterministic=False,
        sql_data_access=CreateFunctionSqlDataAccess.NO_SQL,
        is_null_call=False,
        security_type=CreateFunctionSecurityType.DEFINER,
        specific_name="test",
    )
    create_func_info = client.create_function(function_info=create_function)
    function_info = client.retrieve_function(f"{catalog_name}.{schema_name}.{func_name}")
    assert create_func_info == function_info


@pytest.mark.skipif(
    version("databricks-connect") != "15.1.0",
    reason="Creating function with sql body relies on databricks connect using serverless, which is only available in 15.1.0",
)
@pytest.mark.parametrize(
    "create_function",
    [
        function_with_array_input,
        function_with_struct_input,
        function_with_binary_input,
        function_with_interval_input,
        function_with_timestamp_input,
        function_with_date_input,
        function_with_map_input,
        function_with_decimal_input,
        function_with_table_output,
    ],
)
def test_create_and_execute_function(
    client: DatabricksFunctionClient, create_function: Callable[[str], FunctionInputOutput]
):
    with generate_func_name_and_cleanup(client) as func_name:
        function_sample = create_function(func_name)
        client.create_function(sql_function_body=function_sample.sql_body)
        for input_example in function_sample.inputs:
            result = client.execute_function(function_sample.func_name, input_example)
            assert result.value == function_sample.output


@pytest.mark.skipif(
    version("databricks-connect") != "15.1.0",
    reason="Creating function with sql body relies on databricks connect using serverless, which is only available in 15.1.0",
)
def test_retrieve_function(client: DatabricksFunctionClient):
    function_infos = client.retrieve_function(f"{CATALOG}.{SCHEMA}.*")
    existing_function_num = len(function_infos)  # type: ignore

    with generate_func_name_and_cleanup(client) as func_name:
        full_func_name = f"{CATALOG}.{SCHEMA}.{func_name}"
        sql_body = f"""CREATE FUNCTION {full_func_name}(s STRING)
RETURNS STRING
LANGUAGE PYTHON
AS $$
    return s
    $$
"""
        create_func_info = client.create_function(sql_function_body=sql_body)
        function_info = client.retrieve_function(full_func_name)
        assert create_func_info == function_info

        function_infos = client.retrieve_function(f"{CATALOG}.{SCHEMA}.*")
        assert isinstance(function_infos, list) and len(function_infos) == existing_function_num + 1
        assert len([f for f in function_infos if f.full_name == full_func_name]) == 1


@pytest.mark.parametrize(
    ("sql_body", "function_name"),
    [
        (
            "CREATE OR REPLACE FUNCTION test(s STRING) RETURNS STRING LANGUAGE PYTHON AS $$ return s $$",
            "test",
        ),
        (
            "CREATE OR REPLACE FUNCTION a.b.test(s STRING) RETURNS STRING LANGUAGE PYTHON AS $$ return s $$",
            "a.b.test",
        ),
        (
            "CREATE FUNCTION a.test(s STRING) RETURNS STRING LANGUAGE PYTHON AS $$ return s $$",
            "a.test",
        ),
        (
            "CREATE TEMPORARY FUNCTION a.b.test(s STRING) RETURNS STRING LANGUAGE PYTHON AS $$ return s $$",
            "a.b.test",
        ),
        (
            "CREATE TEMPORARY FUNCTION IF NOT EXISTS test(s STRING) RETURNS STRING LANGUAGE PYTHON AS $$ return s $$",
            "test",
        ),
        ("CREATE FUNCTION IF NOT EXISTS a.b.test() RETURN 123", "a.b.test"),
    ],
)
def test_extract_function_name(sql_body, function_name):
    assert extract_function_name(sql_body) == function_name


@pytest.mark.parametrize(
    "sql_body",
    [
        "CREATE OR REPLACE FUNCTION (s STRING) RETURNS STRING LANGUAGE PYTHON AS $$ return s $$",
        "CREATE FUNCTION RETURNS STRING LANGUAGE PYTHON AS $$ return s $$",
        "CREATE FUNCTION a.b. RETURNS STRING LANGUAGE PYTHON AS $$ return s $$",
        "UPDATE FUNCTION a.b.test(s STRING) RETURNS STRING LANGUAGE PYTHON AS $$ return s $$",
    ],
)
def test_extract_function_name_error(sql_body):
    with pytest.raises(ValueError, match="Could not extract function name from the sql body."):
        extract_function_name(sql_body)


@pytest.mark.parametrize(
    ("param_value", "param_info"),
    [
        (
            [1, 2, 3],
            FunctionParameterInfo(
                "param", type_name=ColumnTypeName.ARRAY, type_text="array<int>", position=0
            ),
        ),
        (
            ("a", "b"),
            FunctionParameterInfo(
                "param", type_name=ColumnTypeName.ARRAY, type_text="array<string>", position=1
            ),
        ),
        (
            "SEVMTE8=",
            FunctionParameterInfo(
                "param", type_name=ColumnTypeName.BINARY, type_text="binary", position=2
            ),
        ),
        (
            True,
            FunctionParameterInfo(
                "param", type_name=ColumnTypeName.BOOLEAN, type_text="boolean", position=3
            ),
        ),
        (
            123456,
            FunctionParameterInfo(
                "param", type_name=ColumnTypeName.BYTE, type_text="byte", position=4
            ),
        ),
        (
            "some_char",
            FunctionParameterInfo(
                "param", type_name=ColumnTypeName.CHAR, type_text="char", position=5
            ),
        ),
        (
            datetime.date(2024, 8, 19),
            FunctionParameterInfo(
                "param", type_name=ColumnTypeName.DATE, type_text="date", position=6
            ),
        ),
        (
            "2024-08-19",
            FunctionParameterInfo(
                "param", type_name=ColumnTypeName.DATE, type_text="date", position=7
            ),
        ),
        (
            123.45,
            FunctionParameterInfo(
                "param", type_name=ColumnTypeName.DECIMAL, type_text="decimal", position=8
            ),
        ),
        (
            Decimal("123.45"),
            FunctionParameterInfo(
                "param", type_name=ColumnTypeName.DECIMAL, type_text="decimal", position=9
            ),
        ),
        (
            123.45,
            FunctionParameterInfo(
                "param", type_name=ColumnTypeName.DOUBLE, type_text="double", position=10
            ),
        ),
        (
            123.45,
            FunctionParameterInfo(
                "param", type_name=ColumnTypeName.FLOAT, type_text="float", position=11
            ),
        ),
        (
            123,
            FunctionParameterInfo(
                "param", type_name=ColumnTypeName.INT, type_text="int", position=12
            ),
        ),
        (
            datetime.timedelta(days=1, hours=3),
            FunctionParameterInfo(
                "param",
                type_name=ColumnTypeName.INTERVAL,
                type_text="interval day to second",
                position=13,
            ),
        ),
        (
            "INTERVAL '1 3:00:00' DAY TO SECOND",
            FunctionParameterInfo(
                "param",
                type_name=ColumnTypeName.INTERVAL,
                type_text="interval day to second",
                position=14,
            ),
        ),
        (
            123,
            FunctionParameterInfo(
                "param", type_name=ColumnTypeName.LONG, type_text="long", position=15
            ),
        ),
        (
            {"a": 1, "b": 2},
            FunctionParameterInfo(
                "param", type_name=ColumnTypeName.MAP, type_text="map<string, int>", position=16
            ),
        ),
        (
            {"a": [1, 2, 3], "b": [4, 5, 6]},
            FunctionParameterInfo(
                "param",
                type_name=ColumnTypeName.MAP,
                type_text="map<string, array<int>>",
                position=17,
            ),
        ),
        (
            123,
            FunctionParameterInfo(
                "param", type_name=ColumnTypeName.SHORT, type_text="short", position=18
            ),
        ),
        (
            "some_string",
            FunctionParameterInfo(
                "param", type_name=ColumnTypeName.STRING, type_text="string", position=19
            ),
        ),
        (
            {"spark": 123},
            FunctionParameterInfo(
                "param", type_name=ColumnTypeName.STRUCT, type_text="struct<spark:int>", position=20
            ),
        ),
        (
            datetime.datetime(2024, 8, 19, 11, 2, 3),
            FunctionParameterInfo(
                "param", type_name=ColumnTypeName.TIMESTAMP, type_text="timestamp", position=21
            ),
        ),
        (
            "2024-08-19T11:02:03",
            FunctionParameterInfo(
                "param", type_name=ColumnTypeName.TIMESTAMP, type_text="timestamp", position=22
            ),
        ),
        (
            datetime.datetime(2024, 8, 19, 11, 2, 3),
            FunctionParameterInfo(
                "param",
                type_name=ColumnTypeName.TIMESTAMP_NTZ,
                type_text="timestamp_ntz",
                position=23,
            ),
        ),
        (
            "2024-08-19T11:02:03",
            FunctionParameterInfo(
                "param",
                type_name=ColumnTypeName.TIMESTAMP_NTZ,
                type_text="timestamp_ntz",
                position=24,
            ),
        ),
    ],
)
def test_validate_param_type(client: DatabricksFunctionClient, param_value, param_info):
    client._validate_param_type(param_value, param_info)


def test_validate_param_type_errors(client: DatabricksFunctionClient):
    with pytest.raises(ValueError, match=r"Parameter a should be of type STRING"):
        client._validate_param_type(
            123,
            FunctionParameterInfo(
                "a", type_name=ColumnTypeName.STRING, type_text="string", position=0
            ),
        )

    with pytest.raises(ValueError, match=r"Invalid datetime string"):
        client._validate_param_type(
            "2024/08/19",
            FunctionParameterInfo(
                "param", type_name=ColumnTypeName.DATE, type_text="date", position=0
            ),
        )

    with pytest.raises(
        ValueError, match=r"python timedelta can only be used for day-time interval"
    ):
        client._validate_param_type(
            datetime.timedelta(days=1),
            FunctionParameterInfo(
                "param",
                type_name=ColumnTypeName.INTERVAL,
                type_text="interval year to month",
                position=0,
            ),
        )

    with pytest.raises(ValueError, match=r"Invalid interval string"):
        client._validate_param_type(
            "INTERVAL '10-0' YEAR TO MONTH",
            FunctionParameterInfo(
                "param",
                type_name=ColumnTypeName.INTERVAL,
                type_text="interval day to second",
                position=0,
            ),
        )


@pytest.fixture
def good_function_info():
    func_name = random_func_name()
    return FunctionInfo(
        catalog_name=CATALOG,
        schema_name=SCHEMA,
        name=func_name,
        input_params=FunctionParameterInfos(
            parameters=[
                FunctionParameterInfo(
                    "a", type_name=ColumnTypeName.INT, type_text="int", position=0
                ),
                FunctionParameterInfo(
                    "b", type_name=ColumnTypeName.STRING, type_text="string", position=1
                ),
            ]
        ),
        data_type=ColumnTypeName.STRING,
        external_language="Python",
        comment="test function",
        routine_body=CreateFunctionRoutineBody.EXTERNAL,
        routine_definition="return str(a) + b",
        full_data_type="STRING",
        return_params=FunctionParameterInfos(),
        routine_dependencies=DependencyList(),
        parameter_style=CreateFunctionParameterStyle.S,
        is_deterministic=False,
        sql_data_access=CreateFunctionSqlDataAccess.NO_SQL,
        is_null_call=False,
        security_type=CreateFunctionSecurityType.DEFINER,
        specific_name=func_name,
    )


@pytest.fixture
def bad_function_info():
    func_name = random_func_name()
    return FunctionInfo(
        catalog_name=CATALOG,
        schema_name=SCHEMA,
        name=func_name,
        input_params=FunctionParameterInfos(
            parameters=[
                FunctionParameterInfo(
                    EXECUTE_FUNCTION_ARG_NAME,
                    type_name=ColumnTypeName.STRING,
                    type_text="string",
                    position=0,
                ),
            ]
        ),
        data_type=ColumnTypeName.STRING,
        external_language="Python",
        comment="test function",
        routine_body=CreateFunctionRoutineBody.EXTERNAL,
        routine_definition=f"return {EXECUTE_FUNCTION_ARG_NAME}",
        full_data_type="STRING",
        return_params=FunctionParameterInfos(),
        routine_dependencies=DependencyList(),
        parameter_style=CreateFunctionParameterStyle.S,
        is_deterministic=False,
        sql_data_access=CreateFunctionSqlDataAccess.NO_SQL,
        is_null_call=False,
        security_type=CreateFunctionSecurityType.DEFINER,
        specific_name=func_name,
    )


@pytest.mark.parametrize(
    ("parameters", "execute_params"),
    [
        ({"a": 1, "b": "b"}, DEFAULT_EXECUTE_FUNCTION_ARGS),
        (
            {"a": 1, EXECUTE_FUNCTION_ARG_NAME: {"wait_timeout": "10s"}},
            {**DEFAULT_EXECUTE_FUNCTION_ARGS, "wait_timeout": "10s"},
        ),
        (
            {EXECUTE_FUNCTION_ARG_NAME: {"row_limit": "1000"}},
            {**DEFAULT_EXECUTE_FUNCTION_ARGS, "row_limit": "1000"},
        ),
    ],
)
def test_extra_params_when_executing_function(
    client: DatabricksFunctionClient, parameters, execute_params, good_function_info
):
    def mock_execute_statement(
        statement,
        warehouse_id,
        *,
        byte_limit=None,
        catalog=None,
        disposition=None,
        format=None,
        on_wait_timeout=None,
        parameters=None,
        row_limit=None,
        schema=None,
        wait_timeout=None,
    ):
        for key, value in execute_params.items():
            assert locals()[key] == value
        return mock.Mock()

    client.client.statement_execution.execute_statement = mock_execute_statement
    client._execute_uc_function(good_function_info, parameters)


def test_extra_params_when_executing_function_errors(
    client: DatabricksFunctionClient, good_function_info, bad_function_info
):
    def mock_execute_statement(
        statement,
        warehouse_id,
        *,
        byte_limit=None,
        catalog=None,
        disposition=None,
        format=None,
        on_wait_timeout=None,
        parameters=None,
        row_limit=None,
        schema=None,
        wait_timeout=None,
    ):
        return mock.Mock()

    client.client.statement_execution.execute_statement = mock_execute_statement

    with pytest.raises(
        ValueError,
        match=r"Parameter name conflicts with the reserved argument name for executing functions",
    ):
        client._execute_uc_function(bad_function_info, {EXECUTE_FUNCTION_ARG_NAME: "value"})

    with pytest.raises(ValueError, match=r"Invalid parameters for executing functions"):
        client._execute_uc_function(
            good_function_info, {EXECUTE_FUNCTION_ARG_NAME: {"invalid_param": "a"}}
        )
