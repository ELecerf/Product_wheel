# Unit tests for Product Wheel Simulator calculations
"""
Test suite for the calculation functions in the core module.
"""

import pytest
import pandas as pd
import numpy as np
from core.calculations import (
    calculate_lcm, calculate_super_cycle, calculate_demand_per_cycle,
    calculate_frequency, calculate_safety_stock, allocate_products_to_cycles,
    calculate_load_per_cycle, calculate_throughput, run_simulation
)
from core.models import Config, SimulationResults
from core.config import DEFAULT_SAFETY_STOCK_Z_SCORE, DEFAULT_DAYS_PER_MONTH


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def sample_config():
    """Sample configuration for testing."""
    return Config(
        available_time_per_week_h=168.0,
        cycle_t_days=42,
        opened_week_per_year=52,
        opened_days_per_week=7,
        planned_loss_percent=0.2
    )


@pytest.fixture
def sample_products():
    """Sample product data for testing."""
    return pd.DataFrame({
        'Product': ['A', 'B', 'C'],
        'Annual Demand (unit)': [7000, 5000, 3000],
        'k': [2, 3, 2],
        'Phase+': [1, 0, 1],
        'Standard Dev Demand': [500, 400, 300],
        'Throughput €': [17500, 12500, 10000],
        'C/O Time': [1.5, 2.0, 1.0],
        'Processing_Time_per_Unit': [0.1, 0.15, 0.12],
        'Sequence': [1, 2, 3]
    })


@pytest.fixture
def sample_changeover_matrix():
    """Sample changeover matrix for testing."""
    return pd.DataFrame({
        'A': [0, 2, 5],
        'B': [2, 0, 1],
        'C': [5, 1, 0]
    }, index=['A', 'B', 'C'])


# ============================================================================
# Test calculate_lcm
# ============================================================================

def test_calculate_lcm_basic():
    """Test LCM calculation with basic inputs."""
    assert calculate_lcm([2, 3, 4]) == 12
    assert calculate_lcm([5, 10]) == 10
    assert calculate_lcm([1]) == 1
    assert calculate_lcm([2, 4, 8]) == 8


def test_calculate_lcm_with_prime_numbers():
    """Test LCM calculation with prime numbers."""
    assert calculate_lcm([2, 3, 5, 7]) == 210
    assert calculate_lcm([11, 13]) == 143


def test_calculate_lcm_with_duplicates():
    """Test LCM calculation with duplicate numbers."""
    assert calculate_lcm([2, 2, 2]) == 2
    assert calculate_lcm([3, 3, 6]) == 6


def test_calculate_lcm_empty_list():
    """Test LCM calculation with empty list."""
    with pytest.raises(ValueError, match="Input list cannot be empty"):
        calculate_lcm([])


def test_calculate_lcm_negative_numbers():
    """Test LCM calculation with negative numbers."""
    with pytest.raises(ValueError, match="All numbers must be positive integers"):
        calculate_lcm([2, -3, 4])


def test_calculate_lcm_zero():
    """Test LCM calculation with zero."""
    with pytest.raises(ValueError, match="All numbers must be positive integers"):
        calculate_lcm([2, 0, 4])


# ============================================================================
# Test calculate_super_cycle
# ============================================================================

def test_calculate_super_cycle_basic(sample_products):
    """Test super cycle calculation with sample products."""
    # k values: [2, 3, 2] -> LCM(2, 3, 2) = 6
    assert calculate_super_cycle(sample_products) == 6


def test_calculate_super_cycle_single_product():
    """Test super cycle calculation with single product."""
    products = pd.DataFrame({
        'Product': ['A'],
        'k': [4]
    })
    assert calculate_super_cycle(products) == 4


def test_calculate_super_cycle_empty():
    """Test super cycle calculation with empty DataFrame."""
    products = pd.DataFrame({'Product': [], 'k': []})
    assert calculate_super_cycle(products) == 0


def test_calculate_super_cycle_with_nan():
    """Test super cycle calculation with NaN values."""
    products = pd.DataFrame({
        'Product': ['A', 'B', 'C'],
        'k': [2, np.nan, 4]
    })
    # Should ignore NaN values -> LCM(2, 4) = 4
    assert calculate_super_cycle(products) == 4


# ============================================================================
# Test calculate_demand_per_cycle
# ============================================================================

def test_calculate_demand_per_cycle(sample_config, sample_products):
    """Test demand per cycle calculation."""
    result = calculate_demand_per_cycle(sample_config, sample_products)
    
    # cycles_per_year = (52 * 7) / 42 = 8.857...
    # demand_per_cycle = annual_demand / cycles_per_year
    expected_cycles_per_year = (52 * 7) / 42
    
    assert 'Demand_per_Cycle' in result.columns
    
    # Check first product
    expected_demand_a = 7000 / expected_cycles_per_year
    assert np.isclose(result.loc[0, 'Demand_per_Cycle'], expected_demand_a)


def test_calculate_demand_per_cycle_preserves_data(sample_config, sample_products):
    """Test that demand per cycle calculation preserves original data."""
    result = calculate_demand_per_cycle(sample_config, sample_products)
    
    # Check that original columns are preserved
    for col in sample_products.columns:
        assert col in result.columns


# ============================================================================
# Test calculate_frequency
# ============================================================================

def test_calculate_frequency(sample_products):
    """Test frequency calculation."""
    super_cycle = 6  # LCM(2, 3, 2)
    result = calculate_frequency(sample_products, super_cycle)
    
    assert 'Freq' in result.columns
    
    # Check frequencies
    # Product A: k=2 -> Freq = 6/2 = 3
    assert result.loc[0, 'Freq'] == 3
    # Product B: k=3 -> Freq = 6/3 = 2
    assert result.loc[1, 'Freq'] == 2
    # Product C: k=2 -> Freq = 6/2 = 3
    assert result.loc[2, 'Freq'] == 3


# ============================================================================
# Test calculate_safety_stock
# ============================================================================

def test_calculate_safety_stock(sample_config, sample_products):
    """Test safety stock calculation."""
    result = calculate_safety_stock(sample_products, sample_config)
    
    assert 'Safety_Stock' in result.columns
    
    # Check formula: z_score * std_dev * sqrt(cycle_t / 30.25)
    # For product A: 1.65 * 500 * sqrt(42 / 30.25)
    expected_a = (
        DEFAULT_SAFETY_STOCK_Z_SCORE * 
        500 * 
        np.sqrt(42 / DEFAULT_DAYS_PER_MONTH)
    )
    assert np.isclose(result.loc[0, 'Safety_Stock'], expected_a)


def test_calculate_safety_stock_missing_column():
    """Test safety stock calculation with missing column."""
    config = Config()
    products = pd.DataFrame({
        'Product': ['A'],
        'Annual Demand (unit)': [1000],
        'k': [2],
        'Phase+': [1]
        # Missing 'Standard Dev Demand'
    })
    
    with pytest.raises(KeyError, match="Missing 'Standard Dev Demand' column"):
        calculate_safety_stock(products, config)


# ============================================================================
# Test allocate_products_to_cycles
# ============================================================================

def test_allocate_products_to_cycles_basic(sample_products):
    """Test product allocation to cycles."""
    super_cycle = 6  # LCM(2, 3, 2)
    
    # First add Demand_per_Cycle column
    sample_products = sample_products.copy()
    sample_products['Demand_per_Cycle'] = [100, 150, 200]
    
    result = allocate_products_to_cycles(sample_products, super_cycle)
    
    assert 'Product' in result.columns
    assert 'Cycle' in result.columns
    assert 'Quantity' in result.columns
    assert 'k' in result.columns
    assert 'Phase+' in result.columns
    
    # Check that all products are allocated
    assert len(result) > 0


def test_allocate_products_to_cycles_formula():
    """Test that allocation follows the correct formula."""
    products = pd.DataFrame({
        'Product': ['A'],
        'k': [2],
        'Phase+': [0],
        'Demand_per_Cycle': [100]
    })
    
    super_cycle = 4  # LCM(2) = 2, but we'll use 4 for testing
    result = allocate_products_to_cycles(products, super_cycle)
    
    # For product A: k=2, Phase+=0
    # Cycles: 0 + 1 + 0*2 = 1, 0 + 1 + 1*2 = 3
    # So should have cycles 1 and 3
    cycles = result['Cycle'].tolist()
    assert 1 in cycles
    assert 3 in cycles
    assert 2 not in cycles
    assert 4 not in cycles


def test_allocate_products_to_cycles_empty():
    """Test allocation with empty products."""
    products = pd.DataFrame({
        'Product': [],
        'k': [],
        'Phase+': [],
        'Demand_per_Cycle': []
    })
    
    result = allocate_products_to_cycles(products, 10)
    assert len(result) == 0


# ============================================================================
# Test calculate_load_per_cycle
# ============================================================================

def test_calculate_load_per_cycle(sample_products, sample_changeover_matrix):
    """Test load per cycle calculation."""
    # First create allocation data
    sample_products = sample_products.copy()
    sample_products['Demand_per_Cycle'] = [100, 150, 200]
    
    allocation = allocate_products_to_cycles(sample_products, 6)
    
    config = Config()
    result = calculate_load_per_cycle(allocation, sample_products, sample_changeover_matrix, config)
    
    assert 'Cycle' in result.columns
    assert 'Production_Load' in result.columns
    assert 'Changeover_Load' in result.columns
    assert 'Total_Load' in result.columns
    assert 'Products' in result.columns


# ============================================================================
# Test calculate_throughput
# ============================================================================

def test_calculate_throughput(sample_products):
    """Test throughput calculation."""
    sample_products = sample_products.copy()
    sample_products['Demand_per_Cycle'] = [100, 150, 200]
    
    result = calculate_throughput(sample_products)
    
    assert 'Production_Load' in result.columns
    assert 'Throughput_per_Hour' in result.columns
    
    # Check formula: Throughput € / (Production_Load + C/O Time)
    # For product A: 17500 / (100 * 0.1 + 1.5) = 17500 / (10 + 1.5) = 17500 / 11.5
    expected_a = 17500 / (100 * 0.1 + 1.5)
    assert np.isclose(result.loc[0, 'Throughput_per_Hour'], expected_a)


def test_calculate_throughput_missing_column():
    """Test throughput calculation with missing column."""
    products = pd.DataFrame({
        'Product': ['A'],
        'Annual Demand (unit)': [1000],
        'k': [2],
        'Phase+': [1],
        'Demand_per_Cycle': [100],
        'Processing_Time_per_Unit': [0.1]
        # Missing 'Throughput €' and 'C/O Time'
    })
    
    with pytest.raises(KeyError, match="Missing required column"):
        calculate_throughput(products)


# ============================================================================
# Test run_simulation
# ============================================================================

def test_run_simulation(sample_config, sample_products, sample_changeover_matrix):
    """Test complete simulation run."""
    results = run_simulation(
        sample_config,
        sample_products,
        sample_changeover_matrix,
        optimize_sequence=False,
        include_safety_stock=True
    )
    
    assert isinstance(results, SimulationResults)
    assert results.super_cycle == 6  # LCM(2, 3, 2)
    assert results.cycles_per_year > 0
    assert results.available_time_per_cycle > 0
    assert results.products_with_demand is not None
    assert results.products_with_freq is not None
    assert results.products_with_ss is not None
    assert results.allocation is not None
    assert results.load_per_cycle is not None
    assert results.products_with_throughput is not None


def test_run_simulation_without_safety_stock(sample_config, sample_products, sample_changeover_matrix):
    """Test simulation without safety stock calculation."""
    results = run_simulation(
        sample_config,
        sample_products,
        sample_changeover_matrix,
        optimize_sequence=False,
        include_safety_stock=False
    )
    
    # Safety stock should not be calculated
    # But the function should still complete
    assert results.products_with_ss is not None


# ============================================================================
# Edge Cases
# ============================================================================

def test_edge_case_single_product():
    """Test with a single product."""
    config = Config(
        available_time_per_week_h=168.0,
        cycle_t_days=7,
        opened_week_per_year=52,
        opened_days_per_week=7,
        planned_loss_percent=0.0
    )
    
    products = pd.DataFrame({
        'Product': ['A'],
        'Annual Demand (unit)': [1000],
        'k': [1],
        'Phase+': [0],
        'Standard Dev Demand': [100],
        'Throughput €': [5000],
        'C/O Time': [1.0],
        'Processing_Time_per_Unit': [0.1],
        'Sequence': [1]
    })
    
    changeover = pd.DataFrame({'A': [0]}, index=['A'])
    
    results = run_simulation(config, products, changeover)
    
    assert results.super_cycle == 1
    assert len(results.allocation) > 0


def test_edge_case_high_k_values():
    """Test with high k values."""
    products = pd.DataFrame({
        'Product': ['A', 'B', 'C', 'D'],
        'Annual Demand (unit)': [1000, 1000, 1000, 1000],
        'k': [2, 3, 4, 5],
        'Phase+': [0, 0, 0, 0],
        'Standard Dev Demand': [100, 100, 100, 100],
        'Throughput €': [5000, 5000, 5000, 5000],
        'C/O Time': [1.0, 1.0, 1.0, 1.0],
        'Processing_Time_per_Unit': [0.1, 0.1, 0.1, 0.1],
        'Sequence': [1, 2, 3, 4]
    })
    
    # LCM(2, 3, 4, 5) = 60
    assert calculate_super_cycle(products) == 60
