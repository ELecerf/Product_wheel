# Sample Data module for Product Wheel Simulator
"""
This module provides sample data for demonstration and testing purposes.
"""

import pandas as pd
from typing import Tuple, Optional
from core.models import Config, Product
from core.config import REQUIRED_CONFIG_COLUMNS, REQUIRED_PRODUCT_COLUMNS


def get_sample_config() -> pd.DataFrame:
    """
    Generate sample configuration data.
    
    Returns:
        DataFrame with sample configuration data.
    """
    config_data = pd.DataFrame({
        'Parameter': REQUIRED_CONFIG_COLUMNS,
        'Value': [168, 42, 52, 7, 0.2]
    }).set_index('Parameter').T
    return config_data


def get_sample_products() -> pd.DataFrame:
    """
    Generate sample product data.
    
    Returns:
        DataFrame with sample product data.
    """
    products_data = pd.DataFrame({
        'Product': ['NA1020', 'NA1030', 'NA1034'],
        'Annual Demand (unit)': [7000, 5000, 3000],
        'Preferred LT (days)': [5, 5, 5],
        'Standard Dev Demand': [500, 400, 300],
        'RM Profit €/kg': [2.5, 1.8, 2.0],
        'Throughput €': [17500, 12500, 10000],
        'Sequence': [1, 2, 3],
        'k': [2, 3, 2],
        'Phase+': [1, 0, 1],
        'C/O Time': [1.5, 2.0, 1.0],
        'Line': ['Line 402', 'Line 402', 'Line 402'],
        'Processing_Time_per_Unit': [0.1, 0.15, 0.12],
        'Strategy': ['MTS', 'MTS', 'MTO'],
        'Qcode': ['Q123', 'Q124', 'Q125']
    })
    return products_data


def get_sample_changeover_matrix() -> pd.DataFrame:
    """
    Generate sample changeover matrix data.
    
    Returns:
        DataFrame with sample changeover matrix data.
    """
    changeover_data = pd.DataFrame({
        'From\To': ['NA1020', 'NA1030', 'NA1034'],
        'NA1020': [0, 2, 5],
        'NA1030': [2, 0, 1],
        'NA1034': [5, 1, 0]
    }).set_index('From\To')
    return changeover_data


def get_sample_demand_history() -> pd.DataFrame:
    """
    Generate sample demand history data.
    
    Returns:
        DataFrame with sample demand history data.
    """
    demand_data = pd.DataFrame({
        'Product': ['NA1020', 'NA1020', 'NA1020', 'NA1030', 'NA1030', 'NA1030'],
        'Month': ['Jan-2024', 'Feb-2024', 'Mar-2024', 'Jan-2024', 'Feb-2024', 'Mar-2024'],
        'Monthly Demand (units)': [600, 650, 580, 450, 420, 480]
    })
    return demand_data


def load_sample_data() -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Load all sample data for demonstration purposes.
    
    Returns:
        Tuple containing (config_data, products_data, changeover_data, demand_data).
    """
    config_data = get_sample_config()
    products_data = get_sample_products()
    changeover_data = get_sample_changeover_matrix()
    demand_data = get_sample_demand_history()
    
    return config_data, products_data, changeover_data, demand_data


def get_sample_config_object() -> Config:
    """
    Generate a sample Config object.
    
    Returns:
        Config object with sample values.
    """
    return Config(
        available_time_per_week_h=168.0,
        cycle_t_days=42,
        opened_week_per_year=52,
        opened_days_per_week=7,
        planned_loss_percent=0.2
    )


def get_sample_product_objects() -> list:
    """
    Generate sample Product objects.
    
    Returns:
        List of Product objects.
    """
    return [
        Product(
            name='NA1020',
            annual_demand=7000,
            k=2,
            phase_plus=1,
            standard_dev_demand=500,
            throughput_euro=17500,
            co_time=1.5,
            processing_time_per_unit=0.1,
            sequence=1,
            line='Line 402',
            strategy='MTS',
            qcode='Q123'
        ),
        Product(
            name='NA1030',
            annual_demand=5000,
            k=3,
            phase_plus=0,
            standard_dev_demand=400,
            throughput_euro=12500,
            co_time=2.0,
            processing_time_per_unit=0.15,
            sequence=2,
            line='Line 402',
            strategy='MTS',
            qcode='Q124'
        ),
        Product(
            name='NA1034',
            annual_demand=3000,
            k=2,
            phase_plus=1,
            standard_dev_demand=300,
            throughput_euro=10000,
            co_time=1.0,
            processing_time_per_unit=0.12,
            sequence=3,
            line='Line 402',
            strategy='MTO',
            qcode='Q125'
        )
    ]
