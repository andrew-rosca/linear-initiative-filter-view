"""Client-side filtering for fields not supported by Linear's API."""
from typing import Dict, Any, List


class ClientSideFilter:
    """Evaluates filters client-side on initiative data."""
    
    # Fields that Linear's API supports natively in InitiativeFilter
    NATIVE_FIELDS = {
        "id",
        "name", 
        "status",
        "targetDate",
        "completedAt",
        "createdAt",
        "updatedAt",
        "archivedAt",
    }
    
    # Fields that require client-side filtering
    CLIENT_SIDE_FIELDS = {
        "description",
        "content",    # Markdown content field (what's shown in UI)
        "startedAt",  # Not in InitiativeFilter but we query it
    }
    
    @classmethod
    def requires_client_side_filtering(cls, filter_obj: Dict[str, Any]) -> bool:
        """Check if a filter requires client-side evaluation.
        
        Args:
            filter_obj: Parsed GraphQL filter object
            
        Returns:
            True if filter contains fields not supported by Linear's API
        """
        return cls._contains_client_side_fields(filter_obj)
    
    @classmethod
    def _contains_client_side_fields(cls, filter_obj: Dict[str, Any]) -> bool:
        """Recursively check if filter contains client-side fields.
        
        Args:
            filter_obj: Filter object or sub-object
            
        Returns:
            True if any client-side fields are found
        """
        if not isinstance(filter_obj, dict):
            return False
            
        for key, value in filter_obj.items():
            # Check if this key is a client-side field
            if key in cls.CLIENT_SIDE_FIELDS:
                return True
            
            # Check logical operators recursively
            if key in ("and", "or", "not"):
                if isinstance(value, list):
                    for item in value:
                        if cls._contains_client_side_fields(item):
                            return True
                elif cls._contains_client_side_fields(value):
                    return True
            
            # Recurse into nested dicts
            elif isinstance(value, dict):
                if cls._contains_client_side_fields(value):
                    return True
        
        return False
    
    @classmethod
    def apply_filter(cls, initiatives: List[Dict[str, Any]], filter_obj: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Apply filter to initiatives client-side.
        
        Args:
            initiatives: List of initiative objects with all fields
            filter_obj: Parsed filter object
            
        Returns:
            Filtered list of initiatives
        """
        return [init for init in initiatives if cls._evaluate_filter(init, filter_obj)]
    
    @classmethod
    def _evaluate_filter(cls, initiative: Dict[str, Any], filter_obj: Dict[str, Any]) -> bool:
        """Evaluate if an initiative matches a filter.
        
        Args:
            initiative: Initiative object
            filter_obj: Filter object or sub-object
            
        Returns:
            True if initiative matches the filter
        """
        if not isinstance(filter_obj, dict):
            return True
        
        # Handle logical operators
        if "and" in filter_obj:
            conditions = filter_obj["and"]
            return all(cls._evaluate_filter(initiative, cond) for cond in conditions)
        
        if "or" in filter_obj:
            conditions = filter_obj["or"]
            return any(cls._evaluate_filter(initiative, cond) for cond in conditions)
        
        if "not" in filter_obj:
            return not cls._evaluate_filter(initiative, filter_obj["not"])
        
        # Handle field comparisons
        for field, operators in filter_obj.items():
            if not isinstance(operators, dict):
                continue
                
            field_value = initiative.get(field)
            
            for op, compare_value in operators.items():
                if not cls._evaluate_comparison(field_value, op, compare_value):
                    return False
        
        return True
    
    @classmethod
    def _evaluate_comparison(cls, field_value: Any, operator: str, compare_value: Any) -> bool:
        """Evaluate a single comparison operation.
        
        Args:
            field_value: Value from the initiative
            operator: Comparison operator (eq, neq, gt, gte, lt, lte, contains, etc.)
            compare_value: Value to compare against
            
        Returns:
            True if comparison is true
        """
        # Handle None values
        if field_value is None:
            if operator == "eq":
                return compare_value is None
            elif operator == "neq":
                return compare_value is not None
            else:
                return False
        
        # Convert to string for string operations
        if operator in ("contains", "startsWith", "endsWith"):
            field_str = str(field_value) if field_value is not None else ""
            compare_str = str(compare_value)
            
            if operator == "contains":
                return compare_str.lower() in field_str.lower()
            elif operator == "startsWith":
                return field_str.lower().startswith(compare_str.lower())
            elif operator == "endsWith":
                return field_str.lower().endswith(compare_str.lower())
        
        # Equality operators
        if operator == "eq":
            return field_value == compare_value
        elif operator == "neq":
            return field_value != compare_value
        
        # Comparison operators (for numbers, dates, etc.)
        try:
            if operator == "gt":
                return field_value > compare_value
            elif operator == "gte":
                return field_value >= compare_value
            elif operator == "lt":
                return field_value < compare_value
            elif operator == "lte":
                return field_value <= compare_value
            elif operator == "in":
                return field_value in compare_value
            elif operator == "nin":
                return field_value not in compare_value
        except TypeError:
            # Can't compare these types
            return False
        
        return True
