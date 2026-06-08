# Validation module for Product Wheel Simulator
"""
This module contains functions for validating input data.
"""

from typing import List, Optional, Dict, Any
import pandas as pd
from .config import (
    REQUIRED_CONFIG_COLUMNS,
    REQUIRED_PRODUCT_COLUMNS,
    K_MIN, K_MAX, PHASE_PLUS_MIN,
    PLANNED_LOSS_MIN, PLANNED_LOSS_MAX,
)


def validate_config(config: pd.DataFrame) -> List[str]:
    """
    Validate configuration data.
    
    Args:
        config: DataFrame containing configuration data.
        
    Returns:
        List of error messages. Empty list if validation passes.
    """
    errors = []
    
    if config is None or len(config) == 0:
        errors.append("Configuration data is missing.")
        return errors
    
    # Check for required columns
    for col in REQUIRED_CONFIG_COLUMNS:
        if col not in config.columns:
            errors.append(f"Missing required configuration parameter: {col}")
    
    if len(errors) > 0:
        return errors
    
    # Validate numeric values
    if 'Available Time per week (h)' in config.columns:
        if config['Available Time per week (h)'].iloc[0] <= 0:
            errors.append("Available Time per week must be greater than 0.")
    
    if 'Cycle T (days)' in config.columns:
        if config['Cycle T (days)'].iloc[0] <= 0:
            errors.append("Cycle T must be greater than 0.")
    
    if 'Planned Loss (%)' in config.columns:
        loss = config['Planned Loss (%)'].iloc[0]
        if loss < PLANNED_LOSS_MIN or loss >= PLANNED_LOSS_MAX:
            errors.append(f"Planned Loss must be between {PLANNED_LOSS_MIN} and {PLANNED_LOSS_MAX}.")
    
    return errors


def validate_products(products: pd.DataFrame) -> List[str]:
    """
    Validate product data.
    
    Args:
        products: DataFrame containing product data.
        
    Returns:
        List of error messages. Empty list if validation passes.
    """
    errors = []
    
    if products is None or len(products) == 0:
        errors.append("Product data is missing.")
        return errors
    
    # Check for required columns
    for col in REQUIRED_PRODUCT_COLUMNS:
        if col not in products.columns:
            errors.append(f"Missing required product column: {col}")
    
    if len(errors) > 0:
        return errors
    
    # Validate k and Phase+ for each product
    for idx, row in products.iterrows():
        product_name = row.get('Product', f"Product {idx}")
        k_val = row.get('k')
        phase_val = row.get('Phase+')
        
        # Validate k
        if pd.isna(k_val) or not (K_MIN <= k_val <= K_MAX):
            errors.append(
                f"Product {product_name}: k must be an integer between {K_MIN} and {K_MAX}."
            )
        
        # Validate Phase+
        if pd.isna(phase_val):
            errors.append(f"Product {product_name}: Phase+ is missing.")
        elif pd.notna(k_val) and (phase_val < PHASE_PLUS_MIN or phase_val >= k_val):
            errors.append(
                f"Product {product_name}: Phase+ must be an integer such that 0 <= Phase+ < k."
            )
        
        # Validate Annual Demand
        annual_demand = row.get('Annual Demand (unit)')
        if pd.isna(annual_demand) or annual_demand <= 0:
            errors.append(f"Product {product_name}: Annual Demand must be greater than 0.")
    
    return errors


def validate_changeover_matrix(changeover_matrix: pd.DataFrame) -> List[str]:
    """
    Validate changeover matrix data.
    
    Args:
        changeover_matrix: DataFrame containing changeover matrix data.
        
    Returns:
        List of error messages. Empty list if validation passes.
    """
    errors = []
    
    if changeover_matrix is None or len(changeover_matrix) == 0:
        return errors  # Changeover matrix is optional
    
    # Check if matrix is square
    if len(changeover_matrix.columns) != len(changeover_matrix.index):
        errors.append("Changeover matrix must be square (same number of rows and columns).")
    
    # Check diagonal values
    for idx in changeover_matrix.index:
        if idx in changeover_matrix.columns:
            diag_val = changeover_matrix.loc[idx, idx]
            if pd.notna(diag_val) and diag_val != 0:
                errors.append(f"Changeover matrix diagonal value at ({idx}, {idx}) should be 0.")
    
    # Check for negative values
    if (changeover_matrix < 0).any().any():
        errors.append("Changeover matrix cannot contain negative values.")
    
    return errors


def validate_inputs(
    config: Optional[pd.DataFrame],
    products: Optional[pd.DataFrame],
    changeover_matrix: Optional[pd.DataFrame]
) -> List[str]:
    """
    Validate all input data (configuration, products, changeover matrix).
    
    Args:
        config: DataFrame containing configuration data.
        products: DataFrame containing product data.
        changeover_matrix: DataFrame containing changeover matrix data.
        
    Returns:
        List of error messages. Empty list if all validations pass.
    """
    errors = []
    
    # Validate config
    if config is not None:
        errors.extend(validate_config(config))
    else:
        errors.append("Configuration data is missing.")
    
    # Validate products
    if products is not None:
        errors.extend(validate_products(products))
    else:
        errors.append("Product data is missing.")
    
    # Validate changeover matrix
    if changeover_matrix is not None:
        errors.extend(validate_changeover_matrix(changeover_matrix))
    
    return errors


def validate_uploaded_file(
    df: pd.DataFrame,
    required_columns: List[str],
    file_name: str
) -> Optional[pd.DataFrame]:
    """
    Validate an uploaded CSV file.
    
    Args:
        df: DataFrame loaded from the uploaded file.
        required_columns: List of required column names.
        file_name: Name of the file for error messages.
        
    Returns:
        The validated DataFrame if successful, None otherwise.
    """
    if df.empty:
        print(f"Error: Uploaded file '{file_name}' is empty.")
        return None
    
    missing_cols = [col for col in required_columns if col not in df.columns]
    if missing_cols:
        print(f"Error: Missing columns in '{file_name}': {', '.join(missing_cols)}")
        return None
    
    return df
