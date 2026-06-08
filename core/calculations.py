# Calculations module for Product Wheel Simulator
"""
This module contains all calculation functions for the Product Wheel simulation.
"""

import math
from typing import List, Optional, Tuple
import pandas as pd
import numpy as np
from .config import (
    DEFAULT_SAFETY_STOCK_Z_SCORE,
    DEFAULT_DAYS_PER_MONTH,
    DEFAULT_PROCESSING_TIME_PER_UNIT,
)
from .models import Config, Product, SimulationResults


def calculate_lcm(numbers: List[int]) -> int:
    """
    Calculate the Least Common Multiple (LCM) of a list of integers.
    
    Args:
        numbers: List of positive integers.
        
    Returns:
        The LCM of the input numbers.
        
    Raises:
        ValueError: If the list is empty or contains non-positive integers.
    """
    if not numbers:
        raise ValueError("Input list cannot be empty.")
    if any(n <= 0 for n in numbers):
        raise ValueError("All numbers must be positive integers.")
    
    def lcm(a: int, b: int) -> int:
        return a * b // math.gcd(a, b)
    
    current_lcm = numbers[0]
    for num in numbers[1:]:
        current_lcm = lcm(current_lcm, num)
    return current_lcm


def calculate_super_cycle(products: pd.DataFrame) -> int:
    """
    Calculate the Super Cycle as the LCM of all k values.
    
    Args:
        products: DataFrame containing product data with 'k' column.
        
    Returns:
        The super cycle (LCM of all k values).
    """
    k_values = products['k'].dropna().astype(int).tolist()
    if not k_values:
        return 0
    return calculate_lcm(k_values)


def calculate_demand_per_cycle(config: Config, products: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate demand per cycle for each product.
    
    Args:
        config: Configuration object.
        products: DataFrame containing product data.
        
    Returns:
        DataFrame with added 'Demand_per_Cycle' column.
    """
    total_opened_days = config.opened_week_per_year * config.opened_days_per_week
    cycles_per_year = total_opened_days / config.cycle_t_days
    
    # Warn if cycles_per_year is not an integer
    if not cycles_per_year.is_integer():
        print(f"Warning: Cycles per year ({cycles_per_year:.2f}) is not an integer. Demand per cycle may be fractional.")
    
    products = products.copy()
    products['Demand_per_Cycle'] = products['Annual Demand (unit)'] / cycles_per_year
    return products


def calculate_frequency(products: pd.DataFrame, super_cycle: int) -> pd.DataFrame:
    """
    Calculate frequency for each product.
    
    Args:
        products: DataFrame containing product data with 'k' column.
        super_cycle: The super cycle value.
        
    Returns:
        DataFrame with added 'Freq' column.
    """
    products = products.copy()
    products['Freq'] = super_cycle / products['k']
    return products


def calculate_safety_stock(
    products: pd.DataFrame,
    config: Config,
    z_score: float = DEFAULT_SAFETY_STOCK_Z_SCORE
) -> pd.DataFrame:
    """
    Calculate safety stock for each product.
    
    Args:
        products: DataFrame containing product data with 'Standard Dev Demand' column.
        config: Configuration object.
        z_score: Z-score for safety stock calculation (default: 1.65).
        
    Returns:
        DataFrame with added 'Safety_Stock' column.
        
    Raises:
        KeyError: If 'Standard Dev Demand' column is missing.
    """
    if 'Standard Dev Demand' not in products.columns:
        raise KeyError("Missing 'Standard Dev Demand' column in products data.")
    
    products = products.copy()
    products['Safety_Stock'] = (
        z_score * 
        products['Standard Dev Demand'] * 
        np.sqrt(config.cycle_t_days / DEFAULT_DAYS_PER_MONTH)
    )
    return products


def allocate_products_to_cycles(products: pd.DataFrame, super_cycle: int) -> pd.DataFrame:
    """
    Allocate products to cycles based on k and Phase+.
    
    This function calculates the target cycles for each product using the formula:
    cycle = phase_plus + 1 + m * k, where m >= 0 and cycle <= super_cycle.
    
    Args:
        products: DataFrame containing product data with 'k' and 'Phase+' columns.
        super_cycle: The super cycle value.
        
    Returns:
        DataFrame with columns: Product, Cycle, Quantity, k, Phase+.
    """
    allocation_data = []
    
    for _, product in products.iterrows():
        k = int(product['k'])
        phase_plus = int(product['Phase+'])
        demand_per_cycle = product['Demand_per_Cycle']
        
        # Direct calculation of target cycles
        m = 0
        while True:
            cycle = phase_plus + 1 + m * k
            if cycle > super_cycle:
                break
            allocation_data.append({
                'Product': product['Product'],
                'Cycle': cycle,
                'Quantity': demand_per_cycle * k,
                'k': k,
                'Phase+': phase_plus
            })
            m += 1
    
    return pd.DataFrame(allocation_data)


def calculate_load_per_cycle(
    allocation_df: pd.DataFrame,
    products: pd.DataFrame,
    changeover_matrix: pd.DataFrame,
    config: Config
) -> pd.DataFrame:
    """
    Calculate production load and changeover load for each cycle.
    
    Args:
        allocation_df: DataFrame with product allocation by cycle.
        products: DataFrame containing product data.
        changeover_matrix: DataFrame with changeover times between products.
        config: Configuration object (unused but kept for compatibility).
        
    Returns:
        DataFrame with columns: Cycle, Production_Load, Changeover_Load, Total_Load, Products.
    """
    # Group allocation by cycle
    cycle_groups = allocation_df.groupby('Cycle')
    load_data = []
    
    for cycle, group in cycle_groups:
        cycle_products = group['Product'].tolist()
        
        # Calculate production load
        production_load = 0.0
        for _, row in group.iterrows():
            product_data = products[products['Product'] == row['Product']].iloc[0]
            processing_time = product_data.get('Processing_Time_per_Unit', DEFAULT_PROCESSING_TIME_PER_UNIT)
            production_load += row['Quantity'] * processing_time
        
        # Calculate changeover load
        changeover_load = 0.0
        if len(cycle_products) > 1:
            # Get sequence from products dataframe
            sequence_products = []
            for prod in cycle_products:
                if 'Sequence' in products.columns:
                    prod_seq = products[products['Product'] == prod]['Sequence'].iloc[0]
                else:
                    prod_seq = 0
                sequence_products.append((prod_seq, prod))
            
            sequence_products.sort(key=lambda x: x[0])
            sorted_products = [p[1] for p in sequence_products]
            
            for i in range(len(sorted_products) - 1):
                from_prod = sorted_products[i]
                to_prod = sorted_products[i + 1]
                
                if from_prod in changeover_matrix.index and to_prod in changeover_matrix.columns:
                    co_time = changeover_matrix.loc[from_prod, to_prod]
                    if pd.notna(co_time):
                        changeover_load += co_time
        
        load_data.append({
            'Cycle': cycle,
            'Production_Load': production_load,
            'Changeover_Load': changeover_load,
            'Total_Load': production_load + changeover_load,
            'Products': ', '.join(cycle_products)
        })
    
    return pd.DataFrame(load_data)


def calculate_throughput(products: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate throughput per hour for each product.
    
    Args:
        products: DataFrame containing product data with required columns.
        
    Returns:
        DataFrame with added 'Production_Load' and 'Throughput_per_Hour' columns.
        
    Raises:
        KeyError: If required columns are missing.
    """
    required_cols = ['Throughput €', 'C/O Time', 'Processing_Time_per_Unit']
    for col in required_cols:
        if col not in products.columns:
            raise KeyError(f"Missing required column for throughput calculation: {col}")
    
    products = products.copy()
    products['Production_Load'] = products['Demand_per_Cycle'] * products['Processing_Time_per_Unit']
    products['Throughput_per_Hour'] = products['Throughput €'] / (products['Production_Load'] + products['C/O Time'])
    return products


def run_simulation(
    config: Config,
    products: pd.DataFrame,
    changeover_matrix: pd.DataFrame,
    optimize_sequence: bool = False,
    include_safety_stock: bool = True
) -> SimulationResults:
    """
    Run the complete Product Wheel simulation.
    
    Args:
        config: Configuration object.
        products: DataFrame containing product data.
        changeover_matrix: DataFrame with changeover times between products.
        optimize_sequence: Whether to optimize product sequence (not implemented yet).
        include_safety_stock: Whether to calculate safety stock.
        
    Returns:
        SimulationResults object containing all simulation results.
    """
    results = SimulationResults()
    
    # Step 1: Calculate Super Cycle
    super_cycle = calculate_super_cycle(products)
    results.super_cycle = super_cycle
    
    # Step 2: Calculate demand per cycle
    products_with_demand = calculate_demand_per_cycle(config, products)
    results.products_with_demand = products_with_demand
    
    # Step 3: Calculate frequency
    products_with_freq = calculate_frequency(products_with_demand, super_cycle)
    results.products_with_freq = products_with_freq
    
    # Step 4: Calculate safety stock if requested
    if include_safety_stock:
        try:
            products_with_ss = calculate_safety_stock(products_with_freq, config)
            results.products_with_ss = products_with_ss
        except KeyError as e:
            print(f"Warning: {e}. Skipping safety stock calculation.")
            results.products_with_ss = products_with_freq
    else:
        results.products_with_ss = products_with_freq
    
    # Step 5: Allocate products to cycles
    allocation_df = allocate_products_to_cycles(products_with_freq, super_cycle)
    results.allocation = allocation_df
    
    # Step 6: Calculate load per cycle
    load_df = calculate_load_per_cycle(allocation_df, products_with_freq, changeover_matrix, config)
    results.load_per_cycle = load_df
    
    # Step 7: Calculate throughput
    try:
        products_with_throughput = calculate_throughput(products_with_freq)
        results.products_with_throughput = products_with_throughput
    except KeyError as e:
        print(f"Warning: {e}. Skipping throughput calculation.")
        results.products_with_throughput = products_with_freq
    
    # Step 8: Calculate available capacity
    weeks_per_cycle = config.cycle_t_days / config.opened_days_per_week
    available_time_per_cycle = (
        config.available_time_per_week_h * 
        weeks_per_cycle * 
        (1 - config.planned_loss_percent / 100)
    )
    results.available_time_per_cycle = available_time_per_cycle
    
    # Calculate number of cycles per year
    total_opened_days = config.opened_week_per_year * config.opened_days_per_week
    cycles_per_year = total_opened_days / config.cycle_t_days
    results.cycles_per_year = cycles_per_year
    
    return results
