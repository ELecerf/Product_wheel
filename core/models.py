# Models module for Product Wheel Simulator
"""
This module contains data models for the Product Wheel simulation.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
import pandas as pd
from .config import (
    K_MIN, K_MAX, PHASE_PLUS_MIN,
    DEFAULT_PROCESSING_TIME_PER_UNIT
)


@dataclass
class Config:
    """
    Configuration data for the Product Wheel simulation.
    
    Attributes:
        available_time_per_week_h: Available production time per week in hours.
        cycle_t_days: Cycle time in days.
        opened_week_per_year: Number of opened weeks per year.
        opened_days_per_week: Number of opened days per week.
        planned_loss_percent: Planned loss percentage.
    """
    available_time_per_week_h: float = 168.0
    cycle_t_days: int = 42
    opened_week_per_year: int = 52
    opened_days_per_week: int = 7
    planned_loss_percent: float = 0.2
    
    def __post_init__(self):
        """Validate configuration parameters."""
        if self.available_time_per_week_h <= 0:
            raise ValueError("Available Time per week must be greater than 0.")
        if self.cycle_t_days <= 0:
            raise ValueError("Cycle T must be greater than 0.")
        if self.opened_week_per_year < 1 or self.opened_week_per_year > 52:
            raise ValueError("Opened Week per year must be between 1 and 52.")
        if self.opened_days_per_week < 1 or self.opened_days_per_week > 7:
            raise ValueError("Opened Days per week must be between 1 and 7.")
        if self.planned_loss_percent < 0 or self.planned_loss_percent >= 100:
            raise ValueError("Planned Loss must be between 0 and 100.")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {
            "Available Time per week (h)": self.available_time_per_week_h,
            "Cycle T (days)": self.cycle_t_days,
            "Opened Week per year": self.opened_week_per_year,
            "Opened Days per week": self.opened_days_per_week,
            "Planned Loss (%)": self.planned_loss_percent,
        }
    
    @classmethod
    def from_dataframe(cls, df: pd.DataFrame) -> "Config":
        """Create Config from a pandas DataFrame."""
        return cls(
            available_time_per_week_h=df["Available Time per week (h)"].iloc[0],
            cycle_t_days=int(df["Cycle T (days)"].iloc[0]),
            opened_week_per_year=int(df["Opened Week per year"].iloc[0]),
            opened_days_per_week=int(df["Opened Days per week"].iloc[0]),
            planned_loss_percent=float(df["Planned Loss (%)"].iloc[0]),
        )
    
    def to_dataframe(self) -> pd.DataFrame:
        """Convert config to a pandas DataFrame."""
        return pd.DataFrame([self.to_dict()])


@dataclass
class Product:
    """
    Product data for the Product Wheel simulation.
    
    Attributes:
        name: Product name.
        annual_demand: Annual demand in units.
        k: Frequency parameter (1-4).
        phase_plus: Phase offset (0 <= Phase+ < k).
        standard_dev_demand: Standard deviation of demand.
        throughput_euro: Throughput in euros.
        co_time: Changeover time in hours.
        processing_time_per_unit: Processing time per unit in hours.
        sequence: Sequence number for ordering (optional).
        line: Production line (optional).
        strategy: Production strategy (optional).
        qcode: Quality code (optional).
    """
    name: str
    annual_demand: float
    k: int
    phase_plus: int
    standard_dev_demand: float
    throughput_euro: float
    co_time: float
    processing_time_per_unit: float = DEFAULT_PROCESSING_TIME_PER_UNIT
    sequence: Optional[int] = None
    line: Optional[str] = None
    strategy: Optional[str] = None
    qcode: Optional[str] = None
    
    def __post_init__(self):
        """Validate product parameters."""
        if self.annual_demand <= 0:
            raise ValueError(f"Annual demand for product {self.name} must be greater than 0.")
        if not (K_MIN <= self.k <= K_MAX):
            raise ValueError(f"k for product {self.name} must be between {K_MIN} and {K_MAX}.")
        if self.phase_plus < PHASE_PLUS_MIN or self.phase_plus >= self.k:
            raise ValueError(
                f"Phase+ for product {self.name} must be between {PHASE_PLUS_MIN} and k-1 (k={self.k})."
            )
        if self.standard_dev_demand < 0:
            raise ValueError(f"Standard Dev Demand for product {self.name} cannot be negative.")
        if self.throughput_euro < 0:
            raise ValueError(f"Throughput for product {self.name} cannot be negative.")
        if self.co_time < 0:
            raise ValueError(f"C/O Time for product {self.name} cannot be negative.")
        if self.processing_time_per_unit <= 0:
            raise ValueError(f"Processing Time per Unit for product {self.name} must be greater than 0.")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert product to dictionary."""
        return {
            "Product": self.name,
            "Annual Demand (unit)": self.annual_demand,
            "k": self.k,
            "Phase+": self.phase_plus,
            "Standard Dev Demand": self.standard_dev_demand,
            "Throughput €": self.throughput_euro,
            "C/O Time": self.co_time,
            "Processing_Time_per_Unit": self.processing_time_per_unit,
            "Sequence": self.sequence,
            "Line": self.line,
            "Strategy": self.strategy,
            "Qcode": self.qcode,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Product":
        """Create Product from a dictionary."""
        return cls(
            name=data.get("Product"),
            annual_demand=data.get("Annual Demand (unit)"),
            k=data.get("k"),
            phase_plus=data.get("Phase+"),
            standard_dev_demand=data.get("Standard Dev Demand"),
            throughput_euro=data.get("Throughput €"),
            co_time=data.get("C/O Time"),
            processing_time_per_unit=data.get("Processing_Time_per_Unit", DEFAULT_PROCESSING_TIME_PER_UNIT),
            sequence=data.get("Sequence"),
            line=data.get("Line"),
            strategy=data.get("Strategy"),
            qcode=data.get("Qcode"),
        )


@dataclass
class SimulationResults:
    """
    Container for simulation results.
    
    Attributes:
        super_cycle: The calculated super cycle (LCM of all k values).
        cycles_per_year: Number of cycles per year.
        available_time_per_cycle: Available time per cycle in hours.
        products_with_demand: Products with demand per cycle calculated.
        products_with_freq: Products with frequency calculated.
        products_with_ss: Products with safety stock calculated.
        allocation: Product allocation by cycle.
        load_per_cycle: Load analysis by cycle.
        products_with_throughput: Products with throughput calculated.
    """
    super_cycle: int = 0
    cycles_per_year: float = 0.0
    available_time_per_cycle: float = 0.0
    products_with_demand: Optional[pd.DataFrame] = None
    products_with_freq: Optional[pd.DataFrame] = None
    products_with_ss: Optional[pd.DataFrame] = None
    allocation: Optional[pd.DataFrame] = None
    load_per_cycle: Optional[pd.DataFrame] = None
    products_with_throughput: Optional[pd.DataFrame] = None
