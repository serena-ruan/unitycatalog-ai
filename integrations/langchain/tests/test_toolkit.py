import json
from unittest import mock

import pytest
from databricks.sdk.service.catalog import (
    FunctionInfo,
    FunctionParameterInfo,
    FunctionParameterInfos,
)
from ucai.core.client import (
    FunctionExecutionResult,
)
from ucai.core.utils.function_processing_utils import get_tool_name
from ucai.test_utils.client_utils import (
    USE_SERVERLESS,
    get_client,
    requires_databricks,
    set_default_client,
)
from ucai.test_utils.function_utils import (
    CATALOG,
    SCHEMA,
    create_function_and_cleanup,
)

from ucai_langchain.toolkit import UCFunctionToolkit


@requires_databricks
@pytest.mark.parametrize("use_serverless", [True, False])
def test_toolkit_e2e(use_serverless, monkeypatch):
    monkeypatch.setenv(USE_SERVERLESS, str(use_serverless))
    client = get_client()
    with set_default_client(client):
        with create_function_and_cleanup(client) as func_obj:
            toolkit = UCFunctionToolkit(function_names=[func_obj.full_function_name])
            tools = toolkit.tools
            assert len(tools) == 1
            tool = tools[0]
            assert tool.name == func_obj.tool_name
            assert tool.description == func_obj.comment
            assert tool.client_config == client.to_dict()
            tool.args_schema(**{"code": "print(1)"})
            result = json.loads(tool.func(code="print(1)"))["value"]
            assert result == "1\n"

            toolkit = UCFunctionToolkit(function_names=[f"{CATALOG}.{SCHEMA}.*"])
            assert len(toolkit.tools) >= 1
            assert func_obj.tool_name in [t.name for t in toolkit.tools]


@requires_databricks
@pytest.mark.parametrize("use_serverless", [True, False])
def test_toolkit_e2e_manually_passing_client(use_serverless, monkeypatch):
    monkeypatch.setenv(USE_SERVERLESS, str(use_serverless))
    client = get_client()
    with set_default_client(client), create_function_and_cleanup(client) as func_obj:
        toolkit = UCFunctionToolkit(function_names=[func_obj.full_function_name], client=client)
        tools = toolkit.tools
        assert len(tools) == 1
        tool = tools[0]
        assert tool.name == func_obj.tool_name
        assert tool.description == func_obj.comment
        assert tool.client_config == client.to_dict()
        tool.args_schema(**{"code": "print(1)"})
        result = json.loads(tool.func(code="print(1)"))["value"]
        assert result == "1\n"

        toolkit = UCFunctionToolkit(function_names=[f"{CATALOG}.{SCHEMA}.*"], client=client)
        assert len(toolkit.tools) >= 1
        assert func_obj.tool_name in [t.name for t in toolkit.tools]


@requires_databricks
@pytest.mark.parametrize("use_serverless", [True, False])
def test_toolkit_e2e_manually_passing_client(use_serverless, monkeypatch):
    monkeypatch.setenv(USE_SERVERLESS, str(use_serverless))
    client = get_client()
    with set_default_client(client), create_function_and_cleanup(client) as func_obj:
        toolkit = UCFunctionToolkit(function_names=[func_obj.full_function_name], client=client)
        tools = toolkit.tools
        assert len(tools) == 1
        tool = tools[0]
        assert tool.name == func_obj.tool_name
        assert tool.description == func_obj.comment
        assert tool.client_config == client.to_dict()
        tool.args_schema(**{"code": "print(1)"})
        result = json.loads(tool.func(code="print(1)"))["value"]
        assert result == "1\n"

        toolkit = UCFunctionToolkit(function_names=[f"{CATALOG}.{SCHEMA}.*"], client=client)
        assert len(toolkit.tools) >= 1
        assert func_obj.tool_name in [t.name for t in toolkit.tools]


@requires_databricks
@pytest.mark.parametrize("use_serverless", [True, False])
def test_multiple_toolkits(use_serverless, monkeypatch):
    monkeypatch.setenv(USE_SERVERLESS, str(use_serverless))
    client = get_client()
    with set_default_client(client), create_function_and_cleanup(client) as func_obj:
        toolkit1 = UCFunctionToolkit(function_names=[func_obj.full_function_name])
        toolkit2 = UCFunctionToolkit(function_names=[f"{CATALOG}.{SCHEMA}.*"])
        tool1 = toolkit1.tools[0]
        tool2 = [t for t in toolkit2.tools if t.name == func_obj.tool_name][0]
        input_args = {"code": "print(1)"}
        assert tool1.func(**input_args) == tool2.func(**input_args)


def test_toolkit_creation_errors():
    with pytest.raises(ValueError, match=r"No client provided"):
        UCFunctionToolkit(function_names=[])

    with pytest.raises(ValueError, match=r"instance of BaseFunctionClient expected"):
        UCFunctionToolkit(function_names=[], client="client")


def generate_function_info():
    parameters = [
        {
            "name": "x",
            "type_text": "string",
            "type_json": '{"name":"x","type":"string","nullable":true,"metadata":{"EXISTS_DEFAULT":"\\"123\\"","default":"\\"123\\"","CURRENT_DEFAULT":"\\"123\\""}}',
            "type_name": "STRING",
            "type_precision": 0,
            "type_scale": 0,
            "position": 17,
            "parameter_type": "PARAM",
            "parameter_default": '"123"',
        }
    ]
    return FunctionInfo(
        catalog_name="catalog",
        schema_name="schema",
        name="test",
        input_params=FunctionParameterInfos(
            parameters=[FunctionParameterInfo(**param) for param in parameters]
        ),
    )


def test_uc_function_to_langchain_tool():
    client = get_client()
    mock_function_info = generate_function_info()
    with (
        mock.patch(
            "ucai.core.databricks.DatabricksFunctionClient.get_function",
            return_value=mock_function_info,
        ),
        mock.patch(
            "ucai.core.databricks.DatabricksFunctionClient.execute_function",
            return_value=FunctionExecutionResult(format="SCALAR", value="some_string"),
        ),
    ):
        tool = UCFunctionToolkit.uc_function_to_langchain_tool(
            client=client, function_name=f"{CATALOG}.{SCHEMA}.test"
        )
        assert tool.name == get_tool_name(f"{CATALOG}.{SCHEMA}.test")
        assert json.loads(tool.func(x="some_string"))["value"] == "some_string"
