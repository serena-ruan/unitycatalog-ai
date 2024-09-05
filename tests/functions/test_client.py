from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import pytest
from typing_extensions import override

from unitycatalog.functions.client import (
    BaseFunctionClient,
    get_uc_function_client,
    set_uc_function_client,
)

MOCK_FUNCTION_INFO = {}

@dataclass
class MockParamInfo:
    name: str
    type_name: str
    parameter_default: Optional[Any] = None

@dataclass
class MockInputParams:
    parameters: List[MockParamInfo]

class MockClient(BaseFunctionClient):
    def __init__(self, client=None, id=None):  # noqa: ARG002
        self.id = id
        super().__init__()
    
    @override
    def create_function(self, function_info: Any) -> Any:
        return function_info
    
    @override
    def retrieve_function(self, function_name: str, **kwargs: Any) -> Any:
        return MOCK_FUNCTION_INFO
    
    @override
    def _validate_param_type(self, value: Any, param_info: MockParamInfo) -> None:
        if type(value).__name__ != param_info.type_name:
            raise ValueError(f"Expected type {param_info.type_name}, but got {type(value).__name__}")
    
    @override
    def _execute_uc_function(
        self, function_info: Any, parameters: Dict[str, Any], **kwargs: Any
    ) -> Any:
        pass


@pytest.fixture
def client():
    return MockClient()

def test_validate_input_params(client):
    input_params = MockInputParams(parameters=[
        MockParamInfo(name="param1", type_name="int"),
        MockParamInfo(name="param2", type_name="str", parameter_default="default"),
    ])
    client.validate_input_params(input_params, {"param1": 1, "param2": "value"})
    
    with pytest.raises(ValueError, match="Parameter param1 is required but not provided."):
        client.validate_input_params(input_params, {"param2": "value"})
    
    with pytest.raises(ValueError, match="Invalid parameters provided: {'param1': 'Expected type int, but got str'}."):
        client.validate_input_params(input_params, {"param1": "value", "param2": "value"})
    
    with pytest.raises(ValueError, match="Extra parameters provided that are not defined in the function's input parameters: {'param3': 'value'}."):
        client.validate_input_params(input_params, {"param1": 1, "param2": "value", "param3": "value"})
    
    with pytest.raises(ValueError, match="Function does not have input parameters, but parameters {'param1': 1, 'param2': 'value'} were provided."):
        client.validate_input_params(None, {"param1": 1, "param2": "value"})


def test_set_function_info(client):
    set_uc_function_client(client)
    assert get_uc_function_client() == client
    
    set_uc_function_client(None)
    assert get_uc_function_client() == None
    
    def client_check(client):
        set_uc_function_client(client)
        assert get_uc_function_client() == client
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(client_check, MockClient(id=i)) for i in range(5)]
        for future in as_completed(futures):
            future.result()
    
    
