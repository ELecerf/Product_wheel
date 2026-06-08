# IO module for Product Wheel Simulator
"""
This module handles data input/output operations (CSV, Excel, JSON).
"""

import json
import pandas as pd
from typing import Optional, Dict, Any, Tuple
from io import BytesIO
from datetime import datetime
from core.models import Config, SimulationResults


def save_to_csv(df: pd.DataFrame, filename: Optional[str] = None) -> bytes:
    """
    Save a DataFrame to CSV format.
    
    Args:
        df: DataFrame to save.
        filename: Optional filename (without extension).
        
    Returns:
        CSV data as bytes.
    """
    if filename is None:
        filename = f"data_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    return df.to_csv(index=False).encode('utf-8')


def save_to_excel(
    data: Dict[str, pd.DataFrame],
    filename: Optional[str] = None
) -> bytes:
    """
    Save multiple DataFrames to an Excel file with multiple sheets.
    
    Args:
        data: Dictionary of {sheet_name: DataFrame}.
        filename: Optional filename (without extension).
        
    Returns:
        Excel data as bytes.
    """
    if filename is None:
        filename = f"data_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        for sheet_name, df in data.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)
    
    return output.getvalue()


def save_to_json(data: Dict[str, Any], filename: Optional[str] = None) -> str:
    """
    Save data to JSON format.
    
    Args:
        data: Dictionary to save.
        filename: Optional filename (without extension).
        
    Returns:
        JSON data as string.
    """
    if filename is None:
        filename = f"data_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    return json.dumps(data, indent=2, default=str)


def export_simulation_results(results: SimulationResults) -> bytes:
    """
    Export simulation results to Excel format.
    
    Args:
        results: SimulationResults object.
        
    Returns:
        Excel data as bytes.
    """
    data = {}
    
    # Add configuration if available
    if hasattr(results, 'config'):
        data['Configuration'] = results.config.to_dataframe()
    
    # Add products data
    if results.products_with_throughput is not None:
        data['Products'] = results.products_with_throughput
    
    # Add allocation data
    if results.allocation is not None:
        data['Allocation'] = results.allocation
    
    # Add load analysis
    if results.load_per_cycle is not None:
        data['Load_Per_Cycle'] = results.load_per_cycle
    
    # Add summary sheet
    summary_data = {
        'Metric': [
            'Super Cycle',
            'Cycles per Year',
            'Available Time per Cycle',
            'Number of Products'
        ],
        'Value': [
            results.super_cycle,
            f"{results.cycles_per_year:.1f}",
            f"{results.available_time_per_cycle:.2f}",
            len(results.products_with_throughput) if results.products_with_throughput is not None else 0
        ]
    }
    data['Summary'] = pd.DataFrame(summary_data)
    
    return save_to_excel(data, f"product_wheel_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}")


def export_summary_report(results: SimulationResults) -> bytes:
    """
    Export a summary report to Excel format.
    
    Args:
        results: SimulationResults object.
        
    Returns:
        Excel data as bytes.
    """
    data = {}
    
    # Summary metrics
    summary_data = {
        'Metric': [
            'Super Cycle',
            'Cycles per Year',
            'Available Time per Cycle (hours)',
            'Total Products',
            'Total Annual Demand'
        ],
        'Value': [
            results.super_cycle,
            f"{results.cycles_per_year:.1f}",
            f"{results.available_time_per_cycle:.2f}",
            len(results.products_with_throughput) if results.products_with_throughput is not None else 0,
            f"{results.products_with_throughput['Annual Demand (unit)'].sum():.0f}" 
            if results.products_with_throughput is not None else "0"
        ]
    }
    data['Summary'] = pd.DataFrame(summary_data)
    
    # Product metrics
    if results.products_with_throughput is not None:
        data['Products'] = results.products_with_throughput
    
    # Load analysis
    if results.load_per_cycle is not None:
        data['Load_Analysis'] = results.load_per_cycle
    
    return save_to_excel(data, f"summary_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}")


def export_configuration(
    config: pd.DataFrame,
    products: pd.DataFrame,
    changeover_matrix: pd.DataFrame
) -> str:
    """
    Export configuration data to JSON format.
    
    Args:
        config: Configuration DataFrame.
        products: Products DataFrame.
        changeover_matrix: Changeover matrix DataFrame.
        
    Returns:
        JSON data as string.
    """
    export_data = {
        'configuration': config.to_dict(),
        'products': products.to_dict(),
        'changeover_matrix': changeover_matrix.to_dict()
    }
    return save_to_json(export_data, f"configuration_{datetime.now().strftime('%Y%m%d_%H%M%S')}")


def read_csv(file_path: str) -> pd.DataFrame:
    """
    Read a CSV file and return as DataFrame.
    
    Args:
        file_path: Path to the CSV file.
        
    Returns:
        DataFrame loaded from the CSV file.
    """
    return pd.read_csv(file_path)


def read_excel(file_path: str, sheet_name: Optional[str] = None) -> pd.DataFrame:
    """
    Read an Excel file and return as DataFrame.
    
    Args:
        file_path: Path to the Excel file.
        sheet_name: Optional sheet name to read.
        
    Returns:
        DataFrame loaded from the Excel file.
    """
    if sheet_name:
        return pd.read_excel(file_path, sheet_name=sheet_name)
    return pd.read_excel(file_path)
