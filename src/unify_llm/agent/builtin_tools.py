"""Built-in tools for AI agents."""


from __future__ import annotations

import ast
import json
import math
import operator
from typing import List, Union

from unify_llm.agent.tools import Tool, ToolParameter, ToolParameterType, ToolResult


class SafeMathEvaluator(ast.NodeVisitor):
    """Safe mathematical expression evaluator using AST.

    SECURITY: This replaces eval() with a safe AST-based approach that only
    allows mathematical operations and whitelisted functions.
    """

    # Supported binary operators
    _operators = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    # Whitelisted functions and constants
    _functions = {
        "abs": abs,
        "round": round,
        "min": min,
        "max": max,
        "pow": pow,
        "sqrt": math.sqrt,
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "log": math.log,
        "log10": math.log10,
        "exp": math.exp,
        "floor": math.floor,
        "ceil": math.ceil,
    }

    _constants = {
        "pi": math.pi,
        "e": math.e,
    }

    def evaluate(self, expression: str) -> int | float:
        """Safely evaluate a mathematical expression.

        Args:
            expression: Mathematical expression string

        Returns:
            Numeric result

        Raises:
            ValueError: If expression contains unsafe operations
        """
        try:
            tree = ast.parse(expression, mode='eval')
            return self.visit(tree.body)
        except (SyntaxError, TypeError) as e:
            raise ValueError(f"Invalid expression: {e}")

    def visit_BinOp(self, node):
        left = self.visit(node.left)
        right = self.visit(node.right)
        op_type = type(node.op)
        if op_type not in self._operators:
            raise ValueError(f"Unsupported operator: {op_type.__name__}")
        return self._operators[op_type](left, right)

    def visit_UnaryOp(self, node):
        operand = self.visit(node.operand)
        op_type = type(node.op)
        if op_type not in self._operators:
            raise ValueError(f"Unsupported unary operator: {op_type.__name__}")
        return self._operators[op_type](operand)

    def visit_Num(self, node):  # Python 3.7
        return node.n

    def visit_Constant(self, node):  # Python 3.8+
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError(f"Unsupported constant type: {type(node.value)}")

    def visit_Name(self, node):
        name = node.id
        if name in self._constants:
            return self._constants[name]
        raise ValueError(f"Unknown variable: {name}")

    def visit_Call(self, node):
        if not isinstance(node.func, ast.Name):
            raise ValueError("Only simple function calls are supported")

        func_name = node.func.id
        if func_name not in self._functions:
            raise ValueError(f"Unknown function: {func_name}")

        args = [self.visit(arg) for arg in node.args]
        return self._functions[func_name](*args)

    def generic_visit(self, node):
        raise ValueError(f"Unsupported expression type: {type(node).__name__}")


def create_calculator_tool() -> Tool:
    """Create a calculator tool for mathematical operations.

    Returns:
        Calculator tool
    """
    evaluator = SafeMathEvaluator()

    def calculate(expression: str) -> ToolResult:
        """Evaluate a mathematical expression safely.

        Args:
            expression: Mathematical expression to evaluate

        Returns:
            Calculation result
        """
        try:
            # SECURITY: Use AST-based safe evaluation instead of eval()
            result = evaluator.evaluate(expression)

            return ToolResult(
                success=True,
                output=result,
                metadata={"expression": expression}
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Error evaluating expression: {str(e)}"
            )

    return Tool(
        name="calculator",
        description="Evaluate mathematical expressions. Supports basic operations (+, -, *, /), "
                    "functions (sqrt, sin, cos, tan), and constants (pi, e).",
        parameters={
            "expression": ToolParameter(
                type=ToolParameterType.STRING,
                description="Mathematical expression to evaluate (e.g., '2 + 2', 'sqrt(16)', 'pi * 2')",
                required=True
            )
        },
        function=calculate
    )


def create_string_tools() -> list[Tool]:
    """Create string manipulation tools.

    Returns:
        List of string manipulation tools
    """

    def to_uppercase(text: str) -> ToolResult:
        """Convert text to uppercase."""
        return ToolResult(success=True, output=text.upper())

    def to_lowercase(text: str) -> ToolResult:
        """Convert text to lowercase."""
        return ToolResult(success=True, output=text.lower())

    def reverse_string(text: str) -> ToolResult:
        """Reverse a string."""
        return ToolResult(success=True, output=text[::-1])

    def count_words(text: str) -> ToolResult:
        """Count words in text."""
        word_count = len(text.split())
        return ToolResult(
            success=True,
            output=word_count,
            metadata={"text_length": len(text)}
        )

    tools = []

    # Uppercase tool
    tools.append(Tool(
        name="to_uppercase",
        description="Convert text to uppercase",
        parameters={
            "text": ToolParameter(
                type=ToolParameterType.STRING,
                description="Text to convert",
                required=True
            )
        },
        function=to_uppercase
    ))

    # Lowercase tool
    tools.append(Tool(
        name="to_lowercase",
        description="Convert text to lowercase",
        parameters={
            "text": ToolParameter(
                type=ToolParameterType.STRING,
                description="Text to convert",
                required=True
            )
        },
        function=to_lowercase
    ))

    # Reverse string tool
    tools.append(Tool(
        name="reverse_string",
        description="Reverse a string",
        parameters={
            "text": ToolParameter(
                type=ToolParameterType.STRING,
                description="Text to reverse",
                required=True
            )
        },
        function=reverse_string
    ))

    # Word count tool
    tools.append(Tool(
        name="count_words",
        description="Count the number of words in text",
        parameters={
            "text": ToolParameter(
                type=ToolParameterType.STRING,
                description="Text to count words in",
                required=True
            )
        },
        function=count_words
    ))

    return tools


def create_data_formatter_tool() -> Tool:
    """Create a data formatting tool.

    Returns:
        Data formatter tool
    """

    def format_data(data: str, format_type: str) -> ToolResult:
        """Format data into different representations.

        Args:
            data: Data to format (JSON string)
            format_type: Target format (json, yaml, table)

        Returns:
            Formatted data
        """
        try:
            # Parse input data
            parsed_data = json.loads(data)

            if format_type == "json":
                output = json.dumps(parsed_data, indent=2)
            elif format_type == "yaml":
                # Simple YAML-like formatting
                def dict_to_yaml(d, indent=0):
                    lines = []
                    for key, value in d.items():
                        if isinstance(value, dict):
                            lines.append("  " * indent + f"{key}:")
                            lines.append(dict_to_yaml(value, indent + 1))
                        elif isinstance(value, list):
                            lines.append("  " * indent + f"{key}:")
                            for item in value:
                                lines.append("  " * (indent + 1) + f"- {item}")
                        else:
                            lines.append("  " * indent + f"{key}: {value}")
                    return "\n".join(lines)

                output = dict_to_yaml(parsed_data)
            elif format_type == "table":
                # Simple table formatting for list of dicts
                if isinstance(parsed_data, list) and parsed_data:
                    headers = list(parsed_data[0].keys())
                    rows = [[str(item.get(h, "")) for h in headers] for item in parsed_data]

                    # Calculate column widths
                    widths = [max(len(h), max(len(r[i]) for r in rows)) for i, h in enumerate(headers)]

                    # Format table
                    header_line = " | ".join(h.ljust(w) for h, w in zip(headers, widths))
                    separator = "-+-".join("-" * w for w in widths)
                    data_lines = [" | ".join(r[i].ljust(widths[i]) for i in range(len(headers))) for r in rows]

                    output = "\n".join([header_line, separator] + data_lines)
                else:
                    output = str(parsed_data)
            else:
                return ToolResult(
                    success=False,
                    error=f"Unknown format type: {format_type}"
                )

            return ToolResult(success=True, output=output)

        except json.JSONDecodeError as e:
            return ToolResult(
                success=False,
                error=f"Invalid JSON data: {str(e)}"
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Error formatting data: {str(e)}"
            )

    return Tool(
        name="format_data",
        description="Format data into different representations (JSON, YAML-like, or table)",
        parameters={
            "data": ToolParameter(
                type=ToolParameterType.STRING,
                description="JSON string data to format",
                required=True
            ),
            "format_type": ToolParameter(
                type=ToolParameterType.STRING,
                description="Target format: 'json', 'yaml', or 'table'",
                required=True,
                enum=["json", "yaml", "table"]
            )
        },
        function=format_data
    )
