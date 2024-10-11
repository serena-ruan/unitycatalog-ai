# Using Unity Catalog AI with CrewAI 

You can use functions defined within Unity Catalog (UC) directly as tools within [CrewAI](https://www.crewai.com/) with this package.

## Installation

### From PyPI

```sh
pip install ucai-crewai
```

### From source

To get started with the latest version, you can directly install this package from source via:

<!-- TODO: update this to the actual path where the repo's main branch will live -->
```sh
%pip install git+https://github.com/michael-berk/unitycatalog-ai.git@michaelberk/crewai-tool-integration#subdirectory=integrations/crewai
```

## Getting started

### Databricks managed UC

To use Databricks-managed UC with this package, follow the [instructions here](https://docs.databricks.com/en/dev-tools/cli/authentication.html#authentication-for-the-databricks-cli) to authenticate to your workspace and ensure that your access token has workspace-level privilege for managing UC functions.

#### Client setup

Initialize a client for managing UC functions in a Databricks workspace, and set it as the global client.

```python
from ucai.core.client import set_uc_function_client
from ucai.core.databricks import DatabricksFunctionClient

client = DatabricksFunctionClient(
    warehouse_id="..." # replace with the warehouse_id
)

# sets the default uc function client
set_uc_function_client(client)
```

#### Create a UC function

To provide an executable function for your tool to use, you need to define and create the function within UC. To do this,
create a Python function that is wrapped within the SQL body format for UC and then utilize the `DatabricksFunctionClient` to store this in UC:

```python
# Replace with your own catalog and schema for where your function will be stored
CATALOG = "catalog"
SCHEMA = "schema"

func_name = f"{CATALOG}.{SCHEMA}.python_exec"
# define the function body in UC SQL functions format
sql_body = f"""CREATE OR REPLACE FUNCTION {func_name}(code STRING COMMENT 'Python code to execute. Remember to print the final result to stdout.')
RETURNS STRING
LANGUAGE PYTHON
COMMENT 'Executes Python code and returns its stdout.'
AS $$
    import sys
    from io import StringIO
    stdout = StringIO()
    sys.stdout = stdout
    exec(code)
    return stdout.getvalue()
$$
"""

client.create_function(sql_function_body=sql_body)
```

Now that the function exists within the Catalog and Schema that we defined, we can interface with it from CrewAI using the ucai_crewai package.

#### Create an instance of a CrewAI compatible tool

[CrewAI Tools](https://docs.crewai.com/core-concepts/Tools/) are callable external functions that GenAI applications can use (called by
an LLM), which are exposed with a UC interface through the use of the ucai_crewai package via the `UCFunctionToolkit` API.

```python
from ucai_crewai.toolkit import UCFunctionToolkit

# Pass the UC function name that we created to the constructor
toolkit = UCFunctionToolkit(function_names=[func_name])

# Get the CrewAI-compatible tools definitions
tools = toolkit.tools
```

If you would like to validate that your tool is functional prior to integrating it with CrewAI, you can call the tool directly:

```python
my_tool = tools[0]

my_tool.fn(**{"code": "print(1)"})
```

#### Utilize our function as a tool within a CrewAI `Crew`

With our interface to our UC function defined as a CrewAI tool collection, we can directly use it within a CrewAI `Crew`. 

```python
import os
from crewai import Agent, Task, Crew

# Set up API keys
os.environ["OPENAI_API_KEY"] = "your key"

# Create agents
coder = Agent(
    role="Simple coder",
    goal= "Create a program that prints Hello Unity Catalog!",
    backstory="likes long walks on the beach",
    expected_output="string",
    tools=tools,
    verbose=True
)

reviewer = Agent(
    role="reviewer",
    goal="Ensure the researcher calls a function and shows the answer",
    backstory="allergic to cats",
    expected_output="string",
    verbose=True
)

# Define tasks
research = Task(
    description="Call a tool",
    expected_output="string",
    agent=coder
)

review = Task(
    description="Review the tool call output. Once complete, stop.",
    expected_output="string",
    agent=reviewer,
)

# Assemble a crew with planning enabled
crew = Crew(
    agents=[coder, reviewer],
    tasks=[research, review],
    verbose=True,
    planning=True,  # Enable planning feature
)

# Execute tasks
crew.kickoff()
```

Output
```text
[2024-10-08 14:29:25][INFO]: Planning the crew execution

# Agent: Simple coder
## Task: Call a tool1. **Identify the Objective**: The Simple Coder aims to create a program that prints "Hello Unity Catalog!" by utilizing the UnityCatalogTool.

2. **Preparation for Tool Call**:
   
   - Ensure that the Python environment is set and accessible to execute the code.
   - Prepare the code snippet that needs to be executed. In this case, the Python code is as follows:

     ```python
     print("Hello Unity Catalog!")
     ```

3. **Utilize the UnityCatalogTool**:
   
   - Call the `main__default__python_exec()` function from the UnityCatalogTool with the appropriate Python code as an argument.
   - This is done by structuring the call to the tool as follows:

     ```python
     result = UnityCatalogTool.main__default__python_exec(code="print('Hello Unity Catalog!')")
     ```

   - Ensure that the call captures the stdout that will print "Hello Unity Catalog!".

4. **Execute and Capture Output**:
   
   - Execute the code through the above function call in the specified environment.
   - The expected output is the string "Hello Unity Catalog!" which will be displayed on the console.

5. **Confirmation**:
   
   - Check the return value of the tool call to ensure it executed correctly.
   - Log or print the result confirming the tool invocation was successful.


# Agent: Simple coder
## Thought: I need to create a program that prints "Hello Unity Catalog!" using the available tool.
## Using tool: main__default__python_exec
## Tool Input: 
"{\"code\": \"print('Hello Unity Catalog!')\"}"
## Tool Output: 
{"format": "SCALAR", "value": "Hello Unity Catalog!\n", "truncated": false}


# Agent: Simple coder
## Final Answer: 
Hello Unity Catalog!


# Agent: reviewer
## Task: Review the tool call output. Once complete, stop.


# Agent: reviewer
## Final Answer: 
Hello Unity Catalog!
```
