# sdk/moderntensor_formulas/tests/test_resource_allocation.py
import pytest
from sdk.formulas.resource_allocation import calculate_subnet_resource

def test_calculate_subnet_resource():
    # Input
    subnet_performance = 30.0
    total_resources = 1000.0
    total_performance = 100.0
    # Công thức: (subnet_performance / total_performance) * total_resources
    expected_allocation = (30 / 100) * 1000
    result = calculate_subnet_resource(subnet_performance, total_resources, total_performance)
    assert result == expected_allocation, "Phân bổ tài nguyên subnet không đúng"