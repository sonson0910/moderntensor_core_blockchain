# sdk/moderntensor_formulas/resource_allocation.py

def calculate_subnet_resource(
    subnet_performance: float,
    total_resources: float,
    total_performance: float
) -> float:
    """
    Tính tài nguyên phân bổ cho subnet dựa trên hiệu suất.

    Args:
        subnet_performance (float): Hiệu suất của subnet.
        total_resources (float): Tổng tài nguyên có sẵn.
        total_performance (float): Tổng hiệu suất của tất cả subnets.

    Returns:
        float: Số tài nguyên phân bổ cho subnet.
    """
    allocation = (subnet_performance / total_performance) * total_resources if total_performance != 0 else 0.0
    return max(0.0, allocation)