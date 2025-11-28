"""
Security tests: NoSQL injection protection.

Tests MongoDB query sanitization.
"""

import pytest
from fastapi import HTTPException

from backend.security import sanitize_mongo_query


@pytest.mark.security
@pytest.mark.unit
class TestNoSQLInjection:
    """Test NoSQL injection protection."""
    
    def test_sanitize_valid_query(self):
        """Test that valid queries pass sanitization."""
        query = {"name": "test", "age": 25}
        sanitized = sanitize_mongo_query(query)
        assert sanitized == query
    
    def test_sanitize_operator_injection(self):
        """Test that operator injection attempts are blocked."""
        # $where injection
        with pytest.raises(HTTPException):
            sanitize_mongo_query({"$where": "this.password == 'admin'"})
        
        # $code injection
        with pytest.raises(HTTPException):
            sanitize_mongo_query({"$code": "malicious_code"})
        
        # $function injection
        with pytest.raises(HTTPException):
            sanitize_mongo_query({"$function": "malicious_function"})
    
    def test_sanitize_nested_query(self):
        """Test that nested queries are sanitized recursively."""
        query = {
            "name": "test",
            "metadata": {
                "$where": "malicious",
            },
        }
        
        with pytest.raises(HTTPException):
            sanitize_mongo_query(query)
    
    def test_sanitize_array_query(self):
        """Test that queries with arrays are sanitized."""
        query = {
            "tags": ["tag1", {"$where": "malicious"}],
        }
        
        with pytest.raises(HTTPException):
            sanitize_mongo_query(query)





