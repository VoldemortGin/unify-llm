"""Tests for code injection prevention.

These tests verify that the calculator tool and other expression
evaluators are protected against code injection attacks.
"""

import pytest

from unify_llm.agent.builtin_tools import SafeMathEvaluator, create_calculator_tool


class TestSafeMathEvaluator:
    """Test the AST-based safe math evaluator."""

    @pytest.fixture
    def evaluator(self):
        return SafeMathEvaluator()

    def test_basic_arithmetic(self, evaluator):
        """Test basic arithmetic operations work."""
        assert evaluator.evaluate("2 + 2") == 4
        assert evaluator.evaluate("10 - 3") == 7
        assert evaluator.evaluate("3 * 4") == 12
        assert evaluator.evaluate("15 / 3") == 5.0
        assert evaluator.evaluate("2 ** 3") == 8

    def test_math_functions(self, evaluator):
        """Test whitelisted math functions work."""
        assert evaluator.evaluate("sqrt(16)") == 4.0
        assert evaluator.evaluate("abs(-5)") == 5
        assert evaluator.evaluate("round(3.7)") == 4
        assert evaluator.evaluate("max(1, 2, 3)") == 3
        assert evaluator.evaluate("min(1, 2, 3)") == 1

    def test_constants(self, evaluator):
        """Test math constants work."""
        import math
        assert evaluator.evaluate("pi") == math.pi
        assert evaluator.evaluate("e") == math.e

    def test_complex_expressions(self, evaluator):
        """Test complex expressions work."""
        assert evaluator.evaluate("2 + 3 * 4") == 14
        assert evaluator.evaluate("(2 + 3) * 4") == 20
        assert evaluator.evaluate("sqrt(16) + 2") == 6.0

    # SECURITY TESTS - These should all fail/raise exceptions

    def test_blocks_import(self, evaluator):
        """SECURITY: Block __import__ attempts."""
        with pytest.raises(ValueError):
            evaluator.evaluate("__import__('os')")

    def test_blocks_exec(self, evaluator):
        """SECURITY: Block exec() attempts."""
        with pytest.raises(ValueError):
            evaluator.evaluate("exec('print(1)')")

    def test_blocks_eval(self, evaluator):
        """SECURITY: Block nested eval() attempts."""
        with pytest.raises(ValueError):
            evaluator.evaluate("eval('1+1')")

    def test_blocks_open(self, evaluator):
        """SECURITY: Block open() attempts."""
        with pytest.raises(ValueError):
            evaluator.evaluate("open('/etc/passwd')")

    def test_blocks_os_system(self, evaluator):
        """SECURITY: Block os.system attempts."""
        with pytest.raises(ValueError):
            evaluator.evaluate("__import__('os').system('ls')")

    def test_blocks_attribute_access(self, evaluator):
        """SECURITY: Block attribute access on objects."""
        with pytest.raises(ValueError):
            evaluator.evaluate("().__class__")

    def test_blocks_subscript_access(self, evaluator):
        """SECURITY: Block subscript access."""
        with pytest.raises(ValueError):
            evaluator.evaluate("[].__class__.__bases__[0]")

    def test_blocks_lambda(self, evaluator):
        """SECURITY: Block lambda expressions."""
        with pytest.raises(ValueError):
            evaluator.evaluate("(lambda: 1)()")

    def test_blocks_comprehension(self, evaluator):
        """SECURITY: Block list comprehensions."""
        with pytest.raises(ValueError):
            evaluator.evaluate("[x for x in range(10)]")

    def test_blocks_builtin_bypass(self, evaluator):
        """SECURITY: Block builtins bypass attempts."""
        with pytest.raises(ValueError):
            evaluator.evaluate("().__class__.__bases__[0].__subclasses__()")

    def test_blocks_unknown_functions(self, evaluator):
        """SECURITY: Block calls to unknown functions."""
        with pytest.raises(ValueError):
            evaluator.evaluate("unknown_func()")

    def test_blocks_string_literals(self, evaluator):
        """SECURITY: Block string literals (could be used for injection)."""
        with pytest.raises(ValueError):
            evaluator.evaluate("'malicious'")


class TestCalculatorTool:
    """Test the calculator tool integration."""

    @pytest.fixture
    def calculator(self):
        return create_calculator_tool()

    def test_calculator_basic(self, calculator):
        """Test calculator handles basic math."""
        result = calculator.function(expression="2 + 2")
        assert result.success is True
        assert result.output == 4

    def test_calculator_blocks_injection(self, calculator):
        """SECURITY: Calculator blocks code injection."""
        result = calculator.function(expression="__import__('os').system('ls')")
        assert result.success is False
        assert "error" in result.error.lower()

    def test_calculator_blocks_file_access(self, calculator):
        """SECURITY: Calculator blocks file access attempts."""
        result = calculator.function(expression="open('/etc/passwd').read()")
        assert result.success is False

    def test_calculator_blocks_subclass_exploit(self, calculator):
        """SECURITY: Calculator blocks __subclasses__ exploit."""
        result = calculator.function(
            expression="().__class__.__bases__[0].__subclasses__()"
        )
        assert result.success is False
