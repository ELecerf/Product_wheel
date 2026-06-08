# Configuration module for Product Wheel Simulator
"""
This module contains default configuration values and constants.
"""

# Default values for configuration parameters
DEFAULT_AVAILABLE_TIME_PER_WEEK_H = 168.0  # hours
DEFAULT_CYCLE_T_DAYS = 42  # days
DEFAULT_OPENED_WEEK_PER_YEAR = 52  # weeks
DEFAULT_OPENED_DAYS_PER_WEEK = 7  # days
DEFAULT_PLANNED_LOSS_PERCENT = 0.2  # %

# Default values for calculations
DEFAULT_PROCESSING_TIME_PER_UNIT = 1.0  # hours
DEFAULT_SAFETY_STOCK_Z_SCORE = 1.65  # Z-score for safety stock calculation
DEFAULT_DAYS_PER_MONTH = 30.25  # Average days per month for safety stock

# Color palette for visualizations
COLOR_PALETTE = [
    "#1f77b4",  # Blue
    "#ff7f0e",  # Orange
    "#2ca02c",  # Green
    "#d62728",  # Red
    "#9467bd",  # Purple
    "#8c564b",  # Brown
    "#e377c2",  # Pink
    "#7f7f7f",  # Gray
    "#bcbd22",  # Olive
    "#17becf",  # Cyan
]

# Required columns for each data type
REQUIRED_CONFIG_COLUMNS = [
    "Available Time per week (h)",
    "Cycle T (days)",
    "Opened Week per year",
    "Opened Days per week",
    "Planned Loss (%)",
]

REQUIRED_PRODUCT_COLUMNS = [
    "Product",
    "Annual Demand (unit)",
    "k",
    "Phase+",
    "Standard Dev Demand",
    "Throughput €",
    "C/O Time",
    "Processing_Time_per_Unit",
]

# Validation rules
K_MIN = 1
K_MAX = 4
PHASE_PLUS_MIN = 0
PLANNED_LOSS_MIN = 0.0
PLANNED_LOSS_MAX = 100.0
