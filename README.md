# Product Wheel Simulator 🎡

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Streamlit](https://img.shields.io/badge/streamlit-1.28+-ff4b4b.svg)](https://streamlit.io/)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A **Streamlit-based application** for optimizing production planning using the **Product Wheel methodology**. This tool helps manufacturers minimize changeover times, balance production load across cycles, and calculate key performance indicators.

---

## ✨ Features

- **📊 Data Input**: Upload or manually enter configuration, product data, and changeover matrices
- **🔄 Simulation**: Run Product Wheel simulations with configurable parameters
- **📈 Results**: View detailed metrics, cycle allocations, load analysis, and throughput calculations
- **📊 Visualizations**: Interactive charts for product allocation, load distribution, and throughput comparison
- **💾 Export**: Download results in CSV, Excel, or JSON formats
- **🎯 Optimization**: Optimized calculations for better performance

---

## 🚀 Quick Start

### Prerequisites

- Python 3.9 or higher
- pip (Python package manager)

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/ELecerf/Product_wheel.git
   cd Product_wheel
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**:
   ```bash
   streamlit run app.py
   ```

4. **Open in browser**:
   The application will automatically open in your default browser at `http://localhost:8501`

---

## 📁 Project Structure

```
product_wheel/
├── app.py                          # Main Streamlit application
├── README.md                       # This file
├── requirements.txt                # Python dependencies
├── core/                           # Core logic modules
│   ├── __init__.py
│   ├── config.py                   # Configuration constants
│   ├── models.py                   # Data models (Config, Product, etc.)
│   ├── calculations.py             # Calculation functions
│   └── validation.py               # Input validation functions
├── data/                           # Data handling modules
│   ├── __init__.py
│   ├── sample_data.py              # Sample data for testing
│   └── io.py                       # Input/Output operations
├── utils/                          # Utility modules
│   └── __init__.py
├── tests/                          # Unit tests
│   ├── __init__.py
│   └── test_calculations.py        # Tests for calculation functions
├── pages/                          # Additional Streamlit pages (optional)
│   └── __init__.py
└── assets/                         # Static files (CSS, images)
    └── style.css
```

---

## 🎯 Usage

### 1. Data Input

- **Configuration**: Set global parameters like available time, cycle duration, and planned loss
- **Products**: Upload or enter product data including demand, k-values, and phase offsets
- **Changeover Matrix**: Define changeover times between products
- **Sample Data**: Click "Load Sample Data" to populate with example data

### 2. Run Simulation

- Validate your inputs
- Configure simulation parameters (safety stock, sequence optimization)
- Click "Run Simulation" to execute the Product Wheel algorithm

### 3. View Results

- **Product Metrics**: Detailed metrics for each product
- **Cycle Allocation**: How products are allocated across cycles
- **Load Analysis**: Production and changeover load per cycle
- **Throughput**: Throughput analysis and comparison

### 4. Visualizations

- Interactive charts powered by Plotly
- Product allocation across cycles
- Load distribution with capacity lines
- Throughput comparison
- Changeover matrix heatmap

### 5. Export

- Download individual tables as CSV
- Export all results as Excel
- Save configuration as JSON

---

## 🔧 Configuration

### Required Product Columns

| Column | Description | Example |
|--------|-------------|---------|
| Product | Product name | NA1020 |
| Annual Demand (unit) | Annual demand in units | 7000 |
| k | Frequency parameter (1-4) | 2 |
| Phase+ | Phase offset (0 <= Phase+ < k) | 1 |
| Standard Dev Demand | Standard deviation of demand | 500 |
| Throughput € | Throughput in euros | 17500 |
| C/O Time | Changeover time in hours | 1.5 |
| Processing_Time_per_Unit | Processing time per unit in hours | 0.1 |

### Configuration Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| Available Time per week (h) | Available production time per week | 168 |
| Cycle T (days) | Cycle time in days | 42 |
| Opened Week per year | Number of opened weeks per year | 52 |
| Opened Days per week | Number of opened days per week | 7 |
| Planned Loss (%) | Planned loss percentage | 0.2 |

---

## 🧪 Testing

Run unit tests with pytest:

```bash
pytest tests/
```

Or with coverage:

```bash
pytest --cov=core tests/
```

---

## 📊 Key Algorithms

### Super Cycle Calculation

The super cycle is calculated as the **Least Common Multiple (LCM)** of all k-values:

```python
super_cycle = LCM(k1, k2, k3, ...)
```

### Product Allocation

Products are allocated to cycles using the formula:

```python
cycle = phase_plus + 1 + m * k
where m >= 0 and cycle <= super_cycle
```

### Demand per Cycle

```python
demand_per_cycle = annual_demand / cycles_per_year
cycles_per_year = (opened_week_per_year * opened_days_per_week) / cycle_t
```

### Safety Stock

```python
safety_stock = z_score * standard_dev_demand * sqrt(cycle_t / 30.25)
```

---

## 🎨 Customization

### Styling

Custom CSS can be added in the `app.py` file or in `assets/style.css`.

### Theming

Streamlit theming can be configured by creating a `.streamlit/config.toml` file:

```toml
[theme]
primaryColor = "#1f77b4"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f0f2f6"
textColor = "#31333F"
font = "sans serif"
```

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📜 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [Streamlit](https://streamlit.io/) - The web framework used
- [Pandas](https://pandas.pydata.org/) - Data manipulation library
- [Plotly](https://plotly.com/python/) - Interactive visualization library
- [Product Wheel Methodology](https://www.productwheel.com/) - The optimization methodology

---

## 📞 Contact

For questions or support, please open an issue on GitHub or contact the maintainer.

**Maintainer**: [ELecerf](https://github.com/ELecerf)

**Repository**: [https://github.com/ELecerf/Product_wheel](https://github.com/ELecerf/Product_wheel)
