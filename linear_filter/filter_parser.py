"""SQL-like filter syntax parser to Linear GraphQL filter converter."""
from typing import Dict, Any, List, Union
from pyparsing import (
    Word, alphas, alphanums, nums, QuotedString, CaselessKeyword,
    infixNotation, opAssoc, ParseException, Group, Suppress, oneOf
)


class FilterParser:
    """Parser for SQL-like filter expressions."""

    # Supported field mappings to Linear API
    # Note: These are for INITIATIVES, not issues
    FIELD_MAPPINGS = {
        "name": "name",
        "status": "status",
        "startedAt": "startedAt",
        "started_at": "startedAt",
        "targetDate": "targetDate",
        "target_date": "targetDate",
        "description": "description",
    }

    # Operator mappings to Linear GraphQL filter operators
    OPERATOR_MAPPINGS = {
        "=": "eq",
        "!=": "neq",
        ">": "gt",
        ">=": "gte",
        "<": "lt",
        "<=": "lte",
        "CONTAINS": "contains",
        "STARTS_WITH": "startsWith",
        "ENDS_WITH": "endsWith",
        "IN": "in",
        "NOT IN": "nin",
    }

    def __init__(self):
        """Initialize parser grammar."""
        # Define grammar
        identifier = Word(alphas + "_", alphanums + "_")
        string_value = QuotedString("'") | QuotedString('"')
        number_value = Word(nums + ".-")
        value = string_value | number_value

        # Operators
        comparison_op = oneOf("= != > >= < <=", caseless=True)
        string_op = CaselessKeyword("CONTAINS") | CaselessKeyword("STARTS_WITH") | CaselessKeyword("ENDS_WITH")
        list_op = CaselessKeyword("IN") | (CaselessKeyword("NOT") + CaselessKeyword("IN"))

        # Comparison expression
        comparison = Group(identifier + comparison_op + value)
        string_comparison = Group(identifier + string_op + value)

        # Combine all expressions
        condition = comparison | string_comparison

        # Logical operators
        and_ = CaselessKeyword("AND")
        or_ = CaselessKeyword("OR")
        not_ = CaselessKeyword("NOT")

        # Build expression with precedence
        self.expr = infixNotation(
            condition,
            [
                (not_, 1, opAssoc.RIGHT),
                (and_, 2, opAssoc.LEFT),
                (or_, 2, opAssoc.LEFT),
            ]
        )

    def parse(self, filter_string: str) -> Dict[str, Any]:
        """Parse SQL-like filter string to GraphQL filter object.

        Args:
            filter_string: SQL-like filter expression

        Returns:
            GraphQL filter object

        Example:
            "status = 'started' AND priority > 2"
            ->
            {
                "and": [
                    {"status": {"eq": "started"}},
                    {"priority": {"gt": 2}}
                ]
            }
        """
        try:
            parsed = self.expr.parseString(filter_string, parseAll=True)
            return self._convert_to_graphql(parsed[0])
        except ParseException as e:
            raise ValueError(f"Failed to parse filter: {e}")

    def _convert_to_graphql(self, parsed: Union[List, str]) -> Dict[str, Any]:
        """Convert parsed expression to GraphQL filter format.

        Args:
            parsed: Parsed expression tree

        Returns:
            GraphQL filter object
        """
        if isinstance(parsed, str):
            return parsed

        # Handle simple condition: ['field', 'op', 'value']
        if len(parsed) == 3 and isinstance(parsed[0], str):
            field, operator, value = parsed
            field = self.FIELD_MAPPINGS.get(field, field)

            # Convert operator to GraphQL format
            if operator.upper() in self.OPERATOR_MAPPINGS:
                op = self.OPERATOR_MAPPINGS[operator.upper()]
            else:
                op = self.OPERATOR_MAPPINGS.get(operator, operator.lower())

            # Convert value type
            converted_value = self._convert_value(value)

            # Build filter object
            return {field: {op: converted_value}}

        # Handle logical operators
        if len(parsed) >= 2:
            # Check for AND/OR operators
            if any(isinstance(item, str) and item.upper() in ["AND", "OR"] for item in parsed):
                logical_op = None
                conditions = []

                i = 0
                while i < len(parsed):
                    item = parsed[i]
                    if isinstance(item, str) and item.upper() in ["AND", "OR"]:
                        logical_op = item.lower()
                        i += 1
                    else:
                        conditions.append(self._convert_to_graphql(item))
                        i += 1

                if logical_op:
                    return {logical_op: conditions}

            # Handle NOT operator
            if parsed[0] == "NOT" or (isinstance(parsed[0], str) and parsed[0].upper() == "NOT"):
                return {"not": self._convert_to_graphql(parsed[1])}

        # Fallback: try to process as nested structure
        if len(parsed) == 1:
            return self._convert_to_graphql(parsed[0])

        # Multiple conditions without explicit operator - assume AND
        conditions = [self._convert_to_graphql(item) for item in parsed if not isinstance(item, str) or item.upper() not in ["AND", "OR"]]
        if len(conditions) > 1:
            return {"and": conditions}
        elif len(conditions) == 1:
            return conditions[0]

        raise ValueError(f"Unexpected parsed structure: {parsed}")

    def _convert_value(self, value: str) -> Union[str, int, float, bool]:
        """Convert string value to appropriate Python type.

        Args:
            value: String value from parsed expression

        Returns:
            Converted value
        """
        # Try to convert to number
        try:
            if "." in value:
                return float(value)
            return int(value)
        except ValueError:
            pass

        # Check for boolean
        if value.lower() == "true":
            return True
        if value.lower() == "false":
            return False

        # Return as string
        return value


def parse_filter(filter_string: str) -> Dict[str, Any]:
    """Parse SQL-like filter string to GraphQL filter.

    Args:
        filter_string: SQL-like filter expression

    Returns:
        GraphQL filter object
    """
    parser = FilterParser()
    return parser.parse(filter_string)
