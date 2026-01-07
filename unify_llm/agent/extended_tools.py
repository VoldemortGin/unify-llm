"""Extended built-in tools for AI agents."""

from unify_llm.agent.tools import Tool, ToolParameter, ToolParameterType, ToolResult
from typing import List, Dict, Any
import json
import os
import re
from datetime import datetime, timedelta


def create_datetime_tools() -> List[Tool]:
    """Create date and time related tools.

    Returns:
        List of datetime tools
    """
    tools = []

    def get_current_datetime(format: str = "%Y-%m-%d %H:%M:%S") -> ToolResult:
        """Get current date and time."""
        try:
            now = datetime.now()
            formatted = now.strftime(format)
            return ToolResult(
                success=True,
                output=formatted,
                metadata={
                    "timestamp": now.timestamp(),
                    "format": format
                }
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def calculate_date_diff(date1: str, date2: str, unit: str = "days") -> ToolResult:
        """Calculate difference between two dates."""
        try:
            d1 = datetime.fromisoformat(date1)
            d2 = datetime.fromisoformat(date2)
            diff = d2 - d1

            if unit == "days":
                result = diff.days
            elif unit == "hours":
                result = diff.total_seconds() / 3600
            elif unit == "minutes":
                result = diff.total_seconds() / 60
            elif unit == "seconds":
                result = diff.total_seconds()
            else:
                return ToolResult(success=False, error=f"Unknown unit: {unit}")

            return ToolResult(
                success=True,
                output=result,
                metadata={"unit": unit, "date1": date1, "date2": date2}
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def add_time_to_date(date: str, amount: int, unit: str = "days") -> ToolResult:
        """Add time to a date."""
        try:
            dt = datetime.fromisoformat(date)

            if unit == "days":
                result = dt + timedelta(days=amount)
            elif unit == "hours":
                result = dt + timedelta(hours=amount)
            elif unit == "minutes":
                result = dt + timedelta(minutes=amount)
            elif unit == "weeks":
                result = dt + timedelta(weeks=amount)
            else:
                return ToolResult(success=False, error=f"Unknown unit: {unit}")

            return ToolResult(
                success=True,
                output=result.isoformat(),
                metadata={"original": date, "amount": amount, "unit": unit}
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    # Current datetime tool
    tools.append(Tool(
        name="get_current_datetime",
        description="Get current date and time in specified format",
        parameters={
            "format": ToolParameter(
                type=ToolParameterType.STRING,
                description="Date format string (default: %Y-%m-%d %H:%M:%S)",
                required=False,
                default="%Y-%m-%d %H:%M:%S"
            )
        },
        function=get_current_datetime
    ))

    # Date diff tool
    tools.append(Tool(
        name="calculate_date_diff",
        description="Calculate difference between two dates",
        parameters={
            "date1": ToolParameter(
                type=ToolParameterType.STRING,
                description="First date in ISO format (YYYY-MM-DD)",
                required=True
            ),
            "date2": ToolParameter(
                type=ToolParameterType.STRING,
                description="Second date in ISO format (YYYY-MM-DD)",
                required=True
            ),
            "unit": ToolParameter(
                type=ToolParameterType.STRING,
                description="Unit for result: days, hours, minutes, seconds",
                required=False,
                enum=["days", "hours", "minutes", "seconds"],
                default="days"
            )
        },
        function=calculate_date_diff
    ))

    # Add time tool
    tools.append(Tool(
        name="add_time_to_date",
        description="Add or subtract time from a date",
        parameters={
            "date": ToolParameter(
                type=ToolParameterType.STRING,
                description="Date in ISO format (YYYY-MM-DD)",
                required=True
            ),
            "amount": ToolParameter(
                type=ToolParameterType.INTEGER,
                description="Amount to add (negative to subtract)",
                required=True
            ),
            "unit": ToolParameter(
                type=ToolParameterType.STRING,
                description="Time unit: days, hours, minutes, weeks",
                required=False,
                enum=["days", "hours", "minutes", "weeks"],
                default="days"
            )
        },
        function=add_time_to_date
    ))

    return tools


def create_text_analysis_tools() -> List[Tool]:
    """Create text analysis tools.

    Returns:
        List of text analysis tools
    """
    tools = []

    def extract_emails(text: str) -> ToolResult:
        """Extract email addresses from text."""
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)

        return ToolResult(
            success=True,
            output=emails,
            metadata={"count": len(emails)}
        )

    def extract_urls(text: str) -> ToolResult:
        """Extract URLs from text."""
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        urls = re.findall(url_pattern, text)

        return ToolResult(
            success=True,
            output=urls,
            metadata={"count": len(urls)}
        )

    def extract_numbers(text: str) -> ToolResult:
        """Extract numbers from text."""
        # Match integers and decimals
        number_pattern = r'-?\d+\.?\d*'
        numbers = [float(n) if '.' in n else int(n) for n in re.findall(number_pattern, text)]

        return ToolResult(
            success=True,
            output=numbers,
            metadata={"count": len(numbers)}
        )

    def analyze_text_stats(text: str) -> ToolResult:
        """Analyze text statistics."""
        words = text.split()
        sentences = re.split(r'[.!?]+', text)
        paragraphs = text.split('\n\n')

        stats = {
            "characters": len(text),
            "characters_no_spaces": len(text.replace(" ", "")),
            "words": len(words),
            "sentences": len([s for s in sentences if s.strip()]),
            "paragraphs": len([p for p in paragraphs if p.strip()]),
            "avg_word_length": sum(len(w) for w in words) / len(words) if words else 0,
            "avg_sentence_length": len(words) / len([s for s in sentences if s.strip()]) if sentences else 0
        }

        return ToolResult(success=True, output=stats)

    # Email extraction
    tools.append(Tool(
        name="extract_emails",
        description="Extract email addresses from text",
        parameters={
            "text": ToolParameter(
                type=ToolParameterType.STRING,
                description="Text to extract emails from",
                required=True
            )
        },
        function=extract_emails
    ))

    # URL extraction
    tools.append(Tool(
        name="extract_urls",
        description="Extract URLs from text",
        parameters={
            "text": ToolParameter(
                type=ToolParameterType.STRING,
                description="Text to extract URLs from",
                required=True
            )
        },
        function=extract_urls
    ))

    # Number extraction
    tools.append(Tool(
        name="extract_numbers",
        description="Extract numbers from text",
        parameters={
            "text": ToolParameter(
                type=ToolParameterType.STRING,
                description="Text to extract numbers from",
                required=True
            )
        },
        function=extract_numbers
    ))

    # Text statistics
    tools.append(Tool(
        name="analyze_text_stats",
        description="Analyze text statistics (word count, sentence count, etc.)",
        parameters={
            "text": ToolParameter(
                type=ToolParameterType.STRING,
                description="Text to analyze",
                required=True
            )
        },
        function=analyze_text_stats
    ))

    return tools


def create_file_tools() -> List[Tool]:
    """Create file operation tools.

    Returns:
        List of file operation tools
    """
    tools = []

    def read_text_file(file_path: str, encoding: str = "utf-8") -> ToolResult:
        """Read a text file."""
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                content = f.read()

            return ToolResult(
                success=True,
                output=content,
                metadata={
                    "file_path": file_path,
                    "size": len(content),
                    "encoding": encoding
                }
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def write_text_file(file_path: str, content: str, encoding: str = "utf-8") -> ToolResult:
        """Write content to a text file."""
        try:
            with open(file_path, 'w', encoding=encoding) as f:
                f.write(content)

            return ToolResult(
                success=True,
                output=f"File written: {file_path}",
                metadata={
                    "file_path": file_path,
                    "size": len(content)
                }
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def list_directory(directory: str, pattern: str = "*") -> ToolResult:
        """List files in a directory."""
        try:
            import glob
            files = glob.glob(os.path.join(directory, pattern))

            return ToolResult(
                success=True,
                output=files,
                metadata={
                    "directory": directory,
                    "pattern": pattern,
                    "count": len(files)
                }
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    # Read file tool
    tools.append(Tool(
        name="read_text_file",
        description="Read content from a text file",
        parameters={
            "file_path": ToolParameter(
                type=ToolParameterType.STRING,
                description="Path to the file to read",
                required=True
            ),
            "encoding": ToolParameter(
                type=ToolParameterType.STRING,
                description="File encoding (default: utf-8)",
                required=False,
                default="utf-8"
            )
        },
        function=read_text_file
    ))

    # Write file tool
    tools.append(Tool(
        name="write_text_file",
        description="Write content to a text file",
        parameters={
            "file_path": ToolParameter(
                type=ToolParameterType.STRING,
                description="Path to the file to write",
                required=True
            ),
            "content": ToolParameter(
                type=ToolParameterType.STRING,
                description="Content to write",
                required=True
            ),
            "encoding": ToolParameter(
                type=ToolParameterType.STRING,
                description="File encoding (default: utf-8)",
                required=False,
                default="utf-8"
            )
        },
        function=write_text_file
    ))

    # List directory tool
    tools.append(Tool(
        name="list_directory",
        description="List files in a directory",
        parameters={
            "directory": ToolParameter(
                type=ToolParameterType.STRING,
                description="Directory path to list",
                required=True
            ),
            "pattern": ToolParameter(
                type=ToolParameterType.STRING,
                description="File pattern to match (e.g., *.txt)",
                required=False,
                default="*"
            )
        },
        function=list_directory
    ))

    return tools


def create_json_tools() -> List[Tool]:
    """Create JSON manipulation tools.

    Returns:
        List of JSON tools
    """
    tools = []

    def parse_json(json_string: str) -> ToolResult:
        """Parse JSON string."""
        try:
            data = json.loads(json_string)
            return ToolResult(success=True, output=data)
        except Exception as e:
            return ToolResult(success=False, error=f"JSON parse error: {str(e)}")

    def stringify_json(data: dict, indent: int = 2) -> ToolResult:
        """Convert data to JSON string."""
        try:
            json_string = json.dumps(data, indent=indent)
            return ToolResult(success=True, output=json_string)
        except Exception as e:
            return ToolResult(success=False, error=f"JSON stringify error: {str(e)}")

    def extract_json_field(json_string: str, field_path: str) -> ToolResult:
        """Extract a field from JSON using dot notation."""
        try:
            data = json.loads(json_string)
            fields = field_path.split('.')

            result = data
            for field in fields:
                if isinstance(result, dict):
                    result = result.get(field)
                elif isinstance(result, list) and field.isdigit():
                    result = result[int(field)]
                else:
                    return ToolResult(
                        success=False,
                        error=f"Cannot access field '{field}' in {type(result)}"
                    )

            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    # Parse JSON
    tools.append(Tool(
        name="parse_json",
        description="Parse JSON string into data structure",
        parameters={
            "json_string": ToolParameter(
                type=ToolParameterType.STRING,
                description="JSON string to parse",
                required=True
            )
        },
        function=parse_json
    ))

    # Stringify JSON
    tools.append(Tool(
        name="stringify_json",
        description="Convert data to JSON string",
        parameters={
            "data": ToolParameter(
                type=ToolParameterType.OBJECT,
                description="Data to convert to JSON",
                required=True
            ),
            "indent": ToolParameter(
                type=ToolParameterType.INTEGER,
                description="Indentation spaces (default: 2)",
                required=False,
                default=2
            )
        },
        function=stringify_json
    ))

    # Extract JSON field
    tools.append(Tool(
        name="extract_json_field",
        description="Extract a field from JSON using dot notation (e.g., 'user.name')",
        parameters={
            "json_string": ToolParameter(
                type=ToolParameterType.STRING,
                description="JSON string",
                required=True
            ),
            "field_path": ToolParameter(
                type=ToolParameterType.STRING,
                description="Field path in dot notation (e.g., 'user.address.city')",
                required=True
            )
        },
        function=extract_json_field
    ))

    return tools
