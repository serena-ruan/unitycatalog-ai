# Unity Catalog AI Core library

The Unity Catalog AI Core library provides convenient APIs to interact with Unity Catalog functions, including functions creation, retrieval and execution.
The library includes clients for interacting with both the Open-Source Unity Catalog server and the Databricks-managed Unity Catalog service.

## Installation

```sh
# install from the source
pip install git+ssh://git@github.com/serena-ruan/unitycatalog-ai.git
```

> [!NOTE]
> Once this package is published to PyPI, users can install via `pip install ucai-core`

## Get started

### Databricks-managed UC

To use Databricks-managed Unity Catalog with this package, follow the [instructions](https://docs.databricks.com/en/dev-tools/cli/authentication.html#authentication-for-the-databricks-cli) to authenticate to your workspace and ensure that your access token has workspace-level privilege for managing UC functions.

#### Prerequisites

- **[Highly recommended]** Use python>=3.10 for accessing all functionalities including function creation and function execution.
- Install databricks-sdk package with `pip install databricks-sdk`.
- For creating UC functions with SQL body, **only [serverless compute](https://docs.databricks.com/en/compute/use-compute.html#use-serverless-compute) is supported**.
  Install databricks-connect package with `pip install databricks-connect==15.1.0`, **python>=3.10** is a requirement to install this version.
- For executing the UC functions in Databricks, use either SQL warehouse or Databricks Connect with serverless:
  - SQL warehouse: create a SQL warehouse following [this instruction](https://docs.databricks.com/en/compute/sql-warehouse/create.html), and use the warehouse id when initializing the client.
    NOTE: **only `serverless` [SQL warehouse type](https://docs.databricks.com/en/admin/sql/warehouse-types.html#sql-warehouse-types) is supported** because of performance concerns.
  - Databricks connect with serverless: Install databricks-connect package with `pip install databricks-connect==15.1.0`. No config needs to be passed when initializing the client.

#### Client initialization

In this example, we use serverless compute as an example.

```python
from ucai.core.databricks import DatabricksFunctionClient

client = DatabricksFunctionClient()
```

#### Create a UC function

Create a UC function with SQL string should follow [this syntax](https://docs.databricks.com/en/sql/language-manual/sql-ref-syntax-ddl-create-sql-function.html#create-function-sql-and-python).

```python
# make sure you have privilege in the corresponding catalog and schema for function creation
CATALOG = "..."
SCHEMA = "..."
func_name = "test"
sql_body = f"""CREATE FUNCTION {CATALOG}.{SCHEMA}.{func_name}(s string)
RETURNS STRING
LANGUAGE PYTHON
AS $$
  return s
$$
"""

function_info = client.create_function(sql_function_body=sql_body)
```

#### Create a Unity Catalog Python Function

The `create_python_function` API allows you to directly convert a Python function into a Unity Catalog (UC) User-Defined Function (UDF). It automates the creation of UC functions, while ensuring the Python function meets certain criteria and adheres to best practices.

##### Requirements and Guidelines

**Type Annotations**:

- **Mandatory**: The Python function must use argument and return type annotations. These annotations are used to generate the SQL signature of the UC function.
- **Supported Types**: The following Python types are supported and mapped to their corresponding Unity Catalog SQL types:

    | Python Type          | Unity Catalog Type       |
    |----------------------|--------------------------|
    | `int`                | `LONG`                   |
    | `float`              | `DOUBLE`                 |
    | `str`                | `STRING`                 |
    | `bool`               | `BOOLEAN`                |
    | `Decimal`            | `DECIMAL`                |
    | `datetime.date`      | `DATE`                   |
    | `datetime.timedelta` | `INTERVAL DAY TO SECOND` |
    | `datetime.datetime`  | `TIMESTAMP`              |
    | `list`               | `ARRAY`                  |
    | `tuple`              | `ARRAY`                  |
    | `dict`               | `MAP`                    |
    | `bytes`              | `BINARY`                 |

- **Collection Types**: If you use collection types like `list`, `tuple`, or `dict`, you **must specify the inner types** explicitly. Unity Catalog does not support ambiguous types like `List` or `Dict`. For example:

```python
def process_data(ids: List[int], details: Dict[str, float]) -> List[str]:
    return [f"{id_}: {details.get(id_)}" for id_ in ids]
```

Failing to define the collection types will result in an Exception.

- **Disallowed Types**: Union types (e.g., `Union[str, int]`) and `Any` are **not supported**. You will receive an error if the return type or argument types include `Union` or `Any`.

```python
def my_func(a: Union[int, str]) -> str:  # This is not allowed.
    return str(a)
```

- **Example of a valid function**:

```python
def calculate_total(a: int, b: List[int]) -> float:
    return a + sum(b)
```

- **Invalid Function** (missing type annotations):

```python
def calculate_total(a, b):
    return a + sum(b)
```

This will raise an error as type annotations are required to generate the UC function’s signature.

- **No var args (`*args`, `**kwargs`)**: These argument types are not supported. All parameters must be explicitly declared with type hints.

---

**Google-Style Docstrings**:

- It is recommended to include detailed **Google-style docstrings** in your Python function. These docstrings will be automatically parsed to generate descriptions for the function and its parameters in Unity Catalog.
- If Google-style docstrings are provided, the function metadata will contain detailed descriptions. If not, default descriptions (`"Parameter <name>"`) will be used for function parameters.
- **Example of a Google-style docstring**:

```python
def add_integers(a: int, b: int) -> int:
    """
    Adds two integers and returns the result.
    
    Args:
        a (int): The first integer.
        b (int): The second integer.
    
    Returns:
        int: The sum of the two integers.
    """
    return a + b
```

- The docstring must conform to [Google-style](https://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_google.html) guidelines. Docstrings that do not follow this format will be parsed with default comments that refer to the name of the parameter only, reducing the effectiveness of GenAI tooling to understand the purpose of each argument.

---

**Type Validation**:

- **Strict Type Checking**: Unity Catalog requires strict type definitions. For example, a function returning a list must specify the type of the elements within the list. The following would raise an error due to a missing element type:

```python
def invalid_func(a: int) -> List:
    return [a]  # List type without specifying the element type is invalid.
```

- **Valid Example**:

```python
def valid_func(a: int) -> List[int]:
    return [a]  # Here, List[int] is valid.
```

- **Dict Types**: For dictionary types, both the key and value types must be specified. The following example is valid:

```python
def create_dict() -> Dict[str, int]:
    return {"a": 1, "b": 2}
```

- **Optional Values**: If you define an optional value, you must specify a default for your argument type hint to be converted to the correct SQL syntax. The assigned default, whether using `Optional[<type>]` or directly defining the type will be used as the default value when calling your function if it is not defined within the request dictionary when calling the function.

- **Valid Examples**:

```python
from typing import Optional

def func_with_optional_param(a: Optional[int] = None, b: str = "default") -> str:
    """
    A function that demonstrates the use of optional parameters with default values.

    Args:
        a: Optional integer parameter, default None.
        b: Optional string parameter, default "default".

    Returns:
        str: A concatenated string representation of the parameters.
    """
    return f"{a}-{b}"

# This will be converted into the following SQL function:
# CREATE OR REPLACE FUNCTION test_catalog.test_schema.func_with_optional_param(
#     a LONG DEFAULT NULL COMMENT 'Optional integer parameter, default None.',
#     b STRING DEFAULT 'default' COMMENT 'Optional string parameter, default "default".'
# )
# RETURNS STRING
# LANGUAGE PYTHON
# COMMENT 'A function that demonstrates the use of optional parameters with default values.'
# AS $$
# return f"{a}-{b}"
# $$;

```

In this valid example, both 'a' and 'b' have default values. 'a' is declared as `Optional[int]`, meaning it can either be an `int` or `None`. The default value of 'a' is `None`, which is converted to `NULL` in SQL. The string parameter 'b' has a default value of `"default"`.

```python
def func_with_direct_default(a: int = 10, b: str = "hello") -> str:
    """
    A function that demonstrates direct type hint with default values.

    Args:
        a: Optional integer parameter with default 10.
        b: Optional string parameter with default 'hello'.  # single quotes are cast to double quotes

    Returns:
        str: A concatenated string of the inputs.
    """
    return f"{a}-{b}"

# This will be converted into the following SQL function:
# CREATE OR REPLACE FUNCTION test_catalog.test_schema.func_with_direct_default(
#     a LONG DEFAULT 10 COMMENT 'Optional integer parameter with default 10.',
#     b STRING DEFAULT 'hello' COMMENT 'Optional string parameter with default "hello".'
# )
# RETURNS STRING
# LANGUAGE PYTHON
# COMMENT 'A function that demonstrates direct type hint with default values.'
# AS $$
# return f"{a}-{b}"
# $$;
```

In this example, the parameters are not wrapped in `Optional`, but defaults are still provided. The function is correctly converted, with the defaults for 'a' and 'b' being included in the SQL.

- **Invalid Example**

```python
from typing import Optional

def invalid_func(a: Optional[int], b: str = "default") -> str:
    """
    A function with an optional parameter that does not specify a default.

    Args:
        a: Optional integer parameter without default.
        b: Optional string parameter, default "default".

    Returns:
        str: A concatenated string representation of the parameters.
    """
    return f"{a}-{b}"

# Error: Optional values must have default values assigned.
# The absence of a default value for `a` will cause the function conversion to fail.
```

Why this is invalid: In this case, 'a' is declared as `Optional[int]` but does not have a default value assigned. The SQL function conversion will fail because `Optional` implies that the parameter can be omitted, but without a default value, there is no fallback for SQL to use. To fix this, you must assign a default value (e.g., `a: Optional[int] = None`).

**Note**: Collection types (`tuple`, `list`, `dict`) do not support defining default values. Only scalar defaults are supported.

---

**Handling External Dependencies**:

- **Standard Libraries Only**: Unity Catalog UDFs are restricted to Python standard libraries and Databricks-provided libraries. Functions that rely on unsupported external dependencies may fail when executed.
- **Testing is recommended**: Always test the created function to ensure that it runs correctly before using it in GenAI or other tool integrations.

---

**Creating a Function**:

- **Function Example**:

```python
def example_function(x: int, y: str) -> str:
    """
    Combines an integer with the length of a string and returns the result.

    Args:
        x (int): The integer to be combined.
        y (str): The string whose length will be used.
    
    Returns:
        str: A string showing the integer combined with the length of the string.
    """
    return f"{x + len(y)} characters"

function_info = client.create_python_function(
    func=example_function,
    catalog="my_catalog",
    schema="my_schema"
)
```

- **Overriding an existing function**:

The `create_python_function` API has the `replace` argument (default value `False`) that will replace a function within Unity Catalog if set to `True`.
Ensure that you are targeting the correct catalog, schema, and function name prior to setting this argument to ensure that you are not inadvertantly
overwriting the wrong function within UC.

```python
function_info = client.create_python_function(
  func=example_function,
  catalog="my_catalog",
  schema="my_schema",
  replace=True
)
```

---

**Function Metadata and Validation**:

- **Metadata**: Generated from the function’s docstrings (description and argument comments). Failure to provide a function description will cause a ValueError to be raised.
- **Validation**: If the function or any of its components (e.g., types) are invalid, an exception will be raised.
- **Strict Return Types**: If a function’s return type is not supported or improperly defined, an exception will be raised. For instance, return types such as `Union[int, str]` will cause an error.

---

##### Example Usage

```python
from typing import Dict, List
# Define the function to be registered
def process_orders(orders: Dict[str, List[int]]) -> str:
    """
    Processes a dictionary of orders and returns a summary.

    Args:
        orders (Dict[str, List[int]]): A dictionary where keys are customer names and values are lists of order totals.

    Returns:
        str: A summary of the orders.
    """
    return ", ".join(f"{k}: {sum(v)}" for k, v in orders.items())

# Create the function in Unity Catalog
function_info = client.create_python_function(
    func=process_orders,
    catalog="sales_catalog",
    schema="order_schema"
)
```

#### Retrieve a UC function

The client also provides API to get the UC function information details. Note that the function name passed in must be the full name in the format of `<catalog>.<schema>.<function_name>`.

```python
full_func_name = f"{CATALOG}.{SCHEMA}.{func_name}"
client.get_function(full_func_name)
```

#### List UC functions

To get a list of functions stored in a catalog and schema, you can use list API with wildcards to do so.

```python
client.list_functions(catalog=CATALOG, schema=SCHEMA, max_results=5)
```

#### Execute a UC function

Parameters passed into execute_function must be a dictionary that maps to the input params defined by the UC function.

```python
result = client.execute_function(full_func_name, {"s": "some_string"})
assert result.value == "some_string"
```

##### Function execution arguments configuration

To manage the function execution behavior using Databricks client under different configurations, we offer the following environment variables:

| Configuration Type                                | Environment Variable                                                | Description                                                                                                                                                                                                                                               | Default Value |
|---------------------------------------------------|---------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------|
| **Warehouse Execution**                           | `UCAI_DATABRICKS_WAREHOUSE_EXECUTE_FUNCTION_WAIT_TIMEOUT`            | Time in seconds the call will wait for the function to execute. Set as `Ns` where `N` can be 0 or between 5 and 50.                                                                                                                                         | `30s`         |
|                                                   | `UCAI_DATABRICKS_WAREHOUSE_EXECUTE_FUNCTION_ROW_LIMIT`               | Maximum number of rows in the function execution result. Also sets the `truncated` field in the response to indicate if the result was trimmed due to the limit.                                                                                            | 100           |
|                                                   | `UCAI_DATABRICKS_WAREHOUSE_EXECUTE_FUNCTION_BYTE_LIMIT`              | Maximum byte size of the function execution result. If truncated due to this limit, the `truncated` field in the response is set to `true`.                                                                                                                | 4096          |
|                                                   | `UCAI_DATABRICKS_WAREHOUSE_RETRY_TIMEOUT`                            | Client-side retry timeout for function execution. If execution doesn't complete within `UCAI_DATABRICKS_WAREHOUSE_EXECUTE_FUNCTION_WAIT_TIMEOUT`, client retries with exponential wait times until this timeout is reached.                                  | 120           |
| **Serverless Compute Execution**                  | `UCAI_DATABRICKS_SERVERLESS_EXECUTION_RESULT_ROW_LIMIT`              | Maximum number of rows in the function execution result.                                                                                                                                                                                                  | 100           |

#### Reminders

- If the function contains a `DECIMAL` type parameter, it is converted to python `float` for execution, and this conversion may lose precision.
