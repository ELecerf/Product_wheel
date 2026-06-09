import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import math
from io import BytesIO
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="Product Wheel Simulator - Simplified",
    page_icon="🎡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .stDataFrame, .stTable {
        font-size: 0.9rem;
    }
    </style>
""", unsafe_allow_html=True)


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def calculate_lcm(numbers):
    """Calculate the Least Common Multiple (PPCM) of a list of integers."""
    def lcm(a, b):
        return a * b // math.gcd(a, b)
    current_lcm = numbers[0]
    for num in numbers[1:]:
        current_lcm = lcm(current_lcm, num)
    return current_lcm


def validate_products(df):
    """Validate product data."""
    errors = []
    if df is None or len(df) == 0:
        errors.append("At least one product is required.")
        return errors
    
    required_cols = ['Product', 'Annual Demand', 'Sequence', 'k', 'Phi', 'C/O Time']
    for col in required_cols:
        if col not in df.columns:
            errors.append(f"Missing required column: {col}")
    
    for idx, row in df.iterrows():
        k_val = row.get('k')
        phi_val = row.get('Phi')
        
        if pd.isna(k_val) or k_val < 1 or k_val > 4:
            errors.append(f"Product {row.get('Product')}: k must be an integer between 1 and 4.")
        
        if pd.isna(phi_val) or phi_val < 0 or (pd.notna(k_val) and phi_val >= k_val):
            errors.append(f"Product {row.get('Product')}: Phi must be an integer such that 0 <= Phi < k.")
    
    return errors


def validate_config(df):
    """Validate configuration data."""
    errors = []
    if df is None or len(df) == 0:
        errors.append("Configuration data is required.")
        return errors
    
    required_cols = ['Available Time per week (h)', 'Cycle T (days)', 
                     'Opened Week per year', 'Opened Days per week', 'Planned Loss (%)']
    for col in required_cols:
        if col not in df.columns:
            errors.append(f"Missing required configuration: {col}")
    
    if 'Available Time per week (h)' in df.columns:
        if df['Available Time per week (h)'].iloc[0] <= 0:
            errors.append("Available Time per week must be greater than 0.")
    
    if 'Cycle T (days)' in df.columns:
        if df['Cycle T (days)'].iloc[0] <= 0:
            errors.append("Cycle T must be greater than 0.")
    
    if 'Planned Loss (%)' in df.columns:
        loss = df['Planned Loss (%)'].iloc[0]
        if loss < 0 or loss >= 100:
            errors.append("Planned Loss must be between 0 and 100.")
    
    return errors


# ============================================================================
# CALCULATION FUNCTIONS
# ============================================================================

def calculate_super_cycle(products_df):
    """Calculate the Super Cycle as the LCM of all k values."""
    k_values = products_df['k'].dropna().astype(int).tolist()
    if not k_values:
        return 0
    return calculate_lcm(k_values)


def calculate_super_cycle_months(config_df, super_cycle_days):
    """Calculate the Super Cycle duration in months."""
    opened_days_per_week = config_df['Opened Days per week'].iloc[0]
    opened_week_per_year = config_df['Opened Week per year'].iloc[0]
    
    # Calculate days per month
    days_per_year = opened_week_per_year * opened_days_per_week
    days_per_month = days_per_year / 12
    
    # Super cycle in months
    super_cycle_months = super_cycle_days / days_per_month
    return super_cycle_months


def calculate_demand_per_cycle(config_df, products_df):
    """Calculate demand per cycle for each product."""
    opened_week_per_year = config_df['Opened Week per year'].iloc[0]
    opened_days_per_week = config_df['Opened Days per week'].iloc[0]
    cycle_t = config_df['Cycle T (days)'].iloc[0]
    
    cycles_per_year = (opened_week_per_year * opened_days_per_week) / cycle_t
    
    products_df = products_df.copy()
    products_df['Demand_per_Cycle'] = products_df['Annual Demand'] / cycles_per_year
    return products_df


def calculate_frequency(products_df, super_cycle):
    """Calculate frequency for each product."""
    products_df = products_df.copy()
    products_df['Freq'] = super_cycle / products_df['k']
    return products_df


def calculate_safety_stock(products_df, config_df):
    """Calculate safety stock for each product."""
    cycle_t = config_df['Cycle T (days)'].iloc[0]
    
    products_df = products_df.copy()
    # Use standard deviation if available, otherwise use 10% of annual demand
    if 'Standard Dev Demand' in products_df.columns:
        std_dev = products_df['Standard Dev Demand']
    else:
        std_dev = products_df['Annual Demand'] * 0.1
    
    products_df['Safety_Stock'] = 1.65 * std_dev * np.sqrt(cycle_t / 30.25)
    return products_df


def format_dataframe_for_display(df, format_dict=None):
    """Format dataframe columns for display."""
    if format_dict:
        for col, fmt in format_dict.items():
            if col in df.columns:
                df[col] = df[col].apply(lambda x: fmt.format(x) if pd.notna(x) else x)
    return df


def allocate_products_to_cycles(products_df, super_cycle, num_cycles=None):
    """Allocate products to cycles based on k and Phi."""
    allocation_data = []
    
    # If num_cycles is not specified, use super_cycle
    if num_cycles is None:
        num_cycles = super_cycle
    
    for _, product in products_df.iterrows():
        k = int(product['k'])
        phi = int(product['Phi'])
        demand_per_cycle = product['Demand_per_Cycle']
        
        for cycle in range(1, num_cycles + 1):
            if (cycle - phi - 1) % k == 0:
                allocation_data.append({
                    'Product': product['Product'],
                    'Cycle': cycle,
                    'Quantity': demand_per_cycle * k,
                    'k': k,
                    'Phi': phi
                })
    
    return pd.DataFrame(allocation_data)


def calculate_load_per_cycle(allocation_df, products_df, config_df):
    """Calculate production load and changeover load for each cycle."""
    # Group allocation by cycle
    cycle_groups = allocation_df.groupby('Cycle')
    
    load_data = []
    
    for cycle, group in cycle_groups:
        cycle_products = group['Product'].tolist()
        
        # Calculate production load
        production_load = 0
        for _, row in group.iterrows():
            product_data = products_df[products_df['Product'] == row['Product']].iloc[0]
            processing_time = product_data.get('Processing Time', 1.0)
            production_load += row['Quantity'] * processing_time
        
        # Calculate changeover load based on sequence
        # Use C/O Time from products table
        changeover_load = 0
        if len(cycle_products) > 1:
            # Sort products by their sequence number
            sequence_dict = dict(zip(products_df['Product'], products_df['Sequence']))
            sorted_products = sorted(cycle_products, key=lambda x: sequence_dict.get(x, 0))
            
            for i in range(len(sorted_products) - 1):
                from_prod = sorted_products[i]
                to_prod = sorted_products[i + 1]
                
                # Get C/O Time from products table
                from_co = products_df[products_df['Product'] == from_prod]['C/O Time'].iloc[0]
                changeover_load += from_co
        
        load_data.append({
            'Cycle': cycle,
            'Production_Load': production_load,
            'Changeover_Load': changeover_load,
            'Total_Load': production_load + changeover_load,
            'Products': ', '.join(cycle_products)
        })
    
    return pd.DataFrame(load_data)


def calculate_throughput(products_df):
    """Calculate throughput per hour for each product."""
    products_df = products_df.copy()
    
    processing_time = products_df.get('Processing Time', 1.0)
    co_time = products_df.get('C/O Time', 0.0)
    throughput_euro = products_df.get('Throughput €', 0.0)
    
    products_df['Production_Load'] = products_df['Demand_per_Cycle'] * processing_time
    products_df['Throughput_per_Hour'] = throughput_euro / (products_df['Production_Load'] + co_time)
    
    return products_df


def run_simulation(config_df, products_df):
    """Run the complete Product Wheel simulation."""
    results = {}
    
    # Step 1: Calculate Super Cycle
    super_cycle = calculate_super_cycle(products_df)
    results['super_cycle'] = super_cycle
    
    # Step 1.5: Calculate Super Cycle in months
    cycle_t_days = config_df['Cycle T (days)'].iloc[0]
    super_cycle_months = calculate_super_cycle_months(config_df, super_cycle * cycle_t_days)
    results['super_cycle_months'] = super_cycle_months
    
    # Determine number of cycles to display
    # If super cycle is less than 6 months, display 2 super cycles
    cycles_to_display = super_cycle * 2 if super_cycle_months < 6 else super_cycle
    results['cycles_to_display'] = cycles_to_display
    
    # Step 2: Calculate demand per cycle
    products_with_demand = calculate_demand_per_cycle(config_df, products_df)
    results['products_with_demand'] = products_with_demand
    
    # Step 3: Calculate frequency
    products_with_freq = calculate_frequency(products_with_demand, super_cycle)
    results['products_with_freq'] = products_with_freq
    
    # Step 4: Calculate safety stock
    products_with_ss = calculate_safety_stock(products_with_freq, config_df)
    results['products_with_ss'] = products_with_ss
    
    # Step 5: Allocate products to cycles (for display)
    allocation_df = allocate_products_to_cycles(products_with_freq, cycles_to_display)
    results['allocation'] = allocation_df
    
    # Step 6: Calculate load per cycle
    load_df = calculate_load_per_cycle(allocation_df, products_with_ss, config_df)
    results['load_per_cycle'] = load_df
    
    # Step 7: Calculate throughput
    products_with_throughput = calculate_throughput(products_with_ss)
    results['products_with_throughput'] = products_with_throughput
    
    # Step 8: Calculate available capacity
    available_time = config_df['Available Time per week (h)'].iloc[0]
    opened_week_per_year = config_df['Opened Week per year'].iloc[0]
    opened_days_per_week = config_df['Opened Days per week'].iloc[0]
    cycle_t = config_df['Cycle T (days)'].iloc[0]
    planned_loss = config_df['Planned Loss (%)'].iloc[0]
    
    weeks_per_cycle = cycle_t / opened_days_per_week
    available_time_per_cycle = available_time * weeks_per_cycle * (1 - planned_loss / 100)
    results['available_time_per_cycle'] = available_time_per_cycle
    
    cycles_per_year = (opened_week_per_year * opened_days_per_week) / cycle_t
    results['cycles_per_year'] = cycles_per_year
    
    return results


# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main():
    # Initialize session state
    if 'config_df' not in st.session_state:
        st.session_state.config_df = pd.DataFrame({
            'Available Time per week (h)': [168.0],
            'Cycle T (days)': [42],
            'Opened Week per year': [52],
            'Opened Days per week': [7],
            'Planned Loss (%)': [0.2]
        })
    
    if 'products_df' not in st.session_state:
        st.session_state.products_df = pd.DataFrame({
            'Product': ['NA1020', 'NA1030', 'NA1034'],
            'Annual Demand': [7000, 5000, 3000],
            'Sequence': [1, 2, 3],
            'k': [2, 3, 2],
            'Phi': [1, 0, 1],
            'Processing Time': [0.1, 0.15, 0.12],
            'C/O Time': [1.5, 2.0, 1.0],
            'Throughput €': [17500, 12500, 10000]
        })
    
    if 'simulation_results' not in st.session_state:
        st.session_state.simulation_results = None
    
    # Header
    st.markdown('<p class="main-header">🎡 Product Wheel Simulator - Simplified</p>', unsafe_allow_html=True)
    st.markdown("### Optimize production planning with Product Wheel methodology")
    
    # Sidebar
    with st.sidebar:
        st.header("Navigation")
        page = st.radio(
            "Select Page",
            ["Configuration", "Products", "Simulation", "Results", "Visualizations"]
        )
        
        st.divider()
        st.header("Actions")
        if st.button("Reset to Defaults"):
            st.session_state.config_df = pd.DataFrame({
                'Available Time per week (h)': [168.0],
                'Cycle T (days)': [42],
                'Opened Week per year': [52],
                'Opened Days per week': [7],
                'Planned Loss (%)': [0.2]
            })
            st.session_state.products_df = pd.DataFrame({
                'Product': ['NA1020', 'NA1030', 'NA1034'],
                'Annual Demand': [7000, 5000, 3000],
                'Sequence': [1, 2, 3],
                'k': [2, 3, 2],
                'Phi': [1, 0, 1],
                'Processing Time': [0.1, 0.15, 0.12],
                'C/O Time': [1.5, 2.0, 1.0],
                'Throughput €': [17500, 12500, 10000]
            })
            st.session_state.simulation_results = None
            st.rerun()
    
    # Page routing
    if page == "Configuration":
        show_config_page()
    elif page == "Products":
        show_products_page()
    elif page == "Simulation":
        show_simulation_page()
    elif page == "Results":
        show_results_page()
    elif page == "Visualizations":
        show_visualizations_page()


def show_config_page():
    """Display the configuration page."""
    st.header("1. Configuration")
    st.markdown("Define global production parameters.")
    
    # Edit config as a table
    st.markdown("### Global Configuration")
    edited_config = st.data_editor(
        st.session_state.config_df,
        key="config_editor",
        width='stretch',
        num_rows="fixed"
    )
    
    if edited_config is not None:
        st.session_state.config_df = edited_config
    
    # Display current values
    st.markdown("**Current Configuration:**")
    st.dataframe(st.session_state.config_df, width='stretch')


def show_products_page():
    """Display the products page."""
    st.header("2. Products")
    st.markdown("Define your products with their parameters.")
    
    # Products table
    st.markdown("### Product Data")
    st.markdown("""
    Required columns:
    - **Product**: Name of the product
    - **Annual Demand**: Annual demand in units
    - **Sequence**: Production sequence number (for changeover optimization)
    - **k**: Multiplicateur de cycle (1-4)
    - **Phi**: Phase+ value (0 <= Phi < k)
    - **C/O Time**: Changeover time in hours (used for load calculations)
    - **Processing Time**: Processing time per unit in hours (optional, defaults to 1.0)
    - **Throughput €**: Throughput value in euros (optional, defaults to 0)
    """)
    
    edited_products = st.data_editor(
        st.session_state.products_df,
        key="products_editor",
        width='stretch',
        num_rows="dynamic"
    )
    
    if edited_products is not None:
        st.session_state.products_df = edited_products


def show_simulation_page():
    """Display the simulation page."""
    st.header("3. Run Simulation")
    st.markdown("Validate inputs and execute the Product Wheel simulation.")
    
    # Validate all inputs
    config_errors = validate_config(st.session_state.config_df)
    product_errors = validate_products(st.session_state.products_df)
    
    all_errors = config_errors + product_errors
    
    if all_errors:
        st.error("❌ Input validation errors:")
        for error in all_errors:
            st.error(f"- {error}")
        return
    
    # Run simulation button
    if st.button("Run Simulation", type="primary"):
        with st.spinner("Running Product Wheel simulation..."):
            results = run_simulation(
                st.session_state.config_df,
                st.session_state.products_df
            )
            
            st.session_state.simulation_results = results
            st.success("Simulation completed successfully!")
            
            # Show summary
            st.subheader("Simulation Summary")
            show_simulation_summary(results)


def show_simulation_summary(results):
    """Display a summary of the simulation results."""
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Super Cycle", f"{results['super_cycle']} cycles")
    
    with col2:
        st.metric("Super Cycle Duration", f"{results['super_cycle_months']:.1f} months")
    
    with col3:
        st.metric("Cycles per Year", f"{results['cycles_per_year']:.1f}")
    
    with col4:
        st.metric("Available Time/Cycle", f"{results['available_time_per_cycle']:.1f} hours")
    
    with col5:
        num_products = len(results['products_with_demand'])
        st.metric("Products", f"{num_products}")
    
    st.divider()
    
    # Display super cycle information
    if results['super_cycle_months'] < 6:
        st.info(f"✓ Displaying 2 super cycles ({results['super_cycle'] * 2} cycles total) since super cycle duration ({results['super_cycle_months']:.1f} months) is less than 6 months.")
    else:
        st.info(f"Displaying 1 super cycle ({results['super_cycle']} cycles) since super cycle duration ({results['super_cycle_months']:.1f} months) is 6 months or more.")
    
    st.divider()
    
    # Show product metrics
    st.subheader("Product Metrics")
    products_df = results['products_with_throughput'].copy()
    
    display_cols = [
        'Product', 'Annual Demand', 'k', 'Phi', 
        'Demand_per_Cycle', 'Freq'
    ]
    
    if 'Throughput_per_Hour' in products_df.columns:
        display_cols.append('Throughput_per_Hour')
    if 'Safety_Stock' in products_df.columns:
        display_cols.append('Safety_Stock')
    
    # Format the dataframe for display
    display_df = products_df[display_cols].copy()
    if 'Demand_per_Cycle' in display_df.columns:
        display_df['Demand_per_Cycle'] = display_df['Demand_per_Cycle'].apply(lambda x: f"{x:.2f}")
    if 'Freq' in display_df.columns:
        display_df['Freq'] = display_df['Freq'].apply(lambda x: f"{x:.1f}")
    if 'Throughput_per_Hour' in display_df.columns:
        display_df['Throughput_per_Hour'] = display_df['Throughput_per_Hour'].apply(lambda x: f"{x:.2f} €/h")
    if 'Safety_Stock' in display_df.columns:
        display_df['Safety_Stock'] = display_df['Safety_Stock'].apply(lambda x: f"{x:.1f}")
    
    st.dataframe(display_df, width='stretch')


def show_results_page():
    """Display the detailed results page."""
    st.header("4. Simulation Results")
    
    if st.session_state.simulation_results is None:
        st.warning("No simulation results available. Please run a simulation first.")
        return
    
    results = st.session_state.simulation_results
    
    # Tabs for different result views
    tab1, tab2, tab3, tab4 = st.tabs([
        "Product Metrics", 
        "Cycle Allocation", 
        "Load Analysis", 
        "Throughput"
    ])
    
    with tab1:
        show_product_metrics(results)
    
    with tab2:
        show_cycle_allocation(results)
    
    with tab3:
        show_load_analysis(results)
    
    with tab4:
        show_throughput_results(results)


def show_product_metrics(results):
    """Display product-level metrics."""
    st.subheader("Product-Level Metrics")
    
    products_df = results['products_with_throughput'].copy()
    
    metrics_df = pd.DataFrame({
        'Product': products_df['Product'],
        'Annual Demand': products_df['Annual Demand'],
        'k': products_df['k'],
        'Phi': products_df['Phi'],
        'C/O Time': products_df['C/O Time'],
        'Demand per Cycle': products_df['Demand_per_Cycle'],
        'Frequency': products_df['Freq'],
    })
    
    if 'Throughput_per_Hour' in products_df.columns:
        metrics_df['Throughput (€/h)'] = products_df['Throughput_per_Hour']
    
    if 'Safety_Stock' in products_df.columns:
        metrics_df['Safety Stock'] = products_df['Safety_Stock']
    
    # Format the dataframe for display
    if 'Demand per Cycle' in metrics_df.columns:
        metrics_df['Demand per Cycle'] = metrics_df['Demand per Cycle'].apply(lambda x: f"{x:.2f}")
    if 'Frequency' in metrics_df.columns:
        metrics_df['Frequency'] = metrics_df['Frequency'].apply(lambda x: f"{x:.1f}")
    if 'Throughput (€/h)' in metrics_df.columns:
        metrics_df['Throughput (€/h)'] = metrics_df['Throughput (€/h)'].apply(lambda x: f"{x:.2f}")
    if 'Safety Stock' in metrics_df.columns:
        metrics_df['Safety Stock'] = metrics_df['Safety Stock'].apply(lambda x: f"{x:.1f}")
    
    st.dataframe(metrics_df, width='stretch')
    
    # Download button
    csv = metrics_df.to_csv(index=False)
    st.download_button(
        label="Download Product Metrics CSV",
        data=csv,
        file_name=f"product_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )


def show_cycle_allocation(results):
    """Display cycle allocation details."""
    st.subheader("Product Allocation by Cycle")
    
    allocation_df = results['allocation'].copy()
    
    # Display number of cycles being shown
    num_cycles_shown = results['cycles_to_display']
    st.info(f"Showing allocation for {num_cycles_shown} cycles")
    
    # Pivot the allocation for better display
    pivot_df = allocation_df.pivot_table(
        index='Product',
        columns='Cycle',
        values='Quantity',
        aggfunc='sum',
        fill_value=0
    )
    
    # Format pivot dataframe
    pivot_df = pivot_df.apply(lambda col: col.map(lambda x: f"{x:.2f}" if pd.notna(x) else ""))
    
    st.markdown("**Allocation Matrix (Quantity per Cycle)**")
    st.dataframe(pivot_df, width='stretch')
    
    st.markdown("**Detailed Allocation**")
    # Format detailed allocation
    alloc_display = allocation_df.copy()
    if 'Quantity' in alloc_display.columns:
        alloc_display['Quantity'] = alloc_display['Quantity'].apply(lambda x: f"{x:.2f}")
    st.dataframe(alloc_display, width='stretch')


def show_load_analysis(results):
    """Display load analysis by cycle."""
    st.subheader("Load Analysis by Cycle")
    
    load_df = results['load_per_cycle'].copy()
    available_time = results['available_time_per_cycle']
    
    # Add capacity utilization
    load_df['Utilization (%)'] = (load_df['Total_Load'] / available_time) * 100
    load_df['Available Capacity'] = available_time
    
    # Format the dataframe for display
    load_df['Production_Load'] = load_df['Production_Load'].apply(lambda x: f"{x:.2f} h")
    load_df['Changeover_Load'] = load_df['Changeover_Load'].apply(lambda x: f"{x:.2f} h")
    load_df['Total_Load'] = load_df['Total_Load'].apply(lambda x: f"{x:.2f} h")
    load_df['Utilization (%)'] = load_df['Utilization (%)'].apply(lambda x: f"{x:.1f}%")
    load_df['Available Capacity'] = load_df['Available Capacity'].apply(lambda x: f"{x:.2f} h")
    
    st.dataframe(load_df, width='stretch')
    
    # Highlight cycles with utilization issues
    high_utilization = load_df[load_df['Utilization (%)'] > 100]
    if len(high_utilization) > 0:
        st.warning(f"⚠️ {len(high_utilization)} cycles exceed available capacity!")
        st.dataframe(high_utilization, width='stretch')


def show_throughput_results(results):
    """Display throughput analysis."""
    st.subheader("Throughput Analysis")
    
    products_df = results['products_with_throughput'].copy()
    
    if 'Throughput_per_Hour' in products_df.columns:
        throughput_df = products_df[['Product', 'Throughput_per_Hour']].copy()
        throughput_df = throughput_df.sort_values('Throughput_per_Hour', ascending=False)
        
        # Format the dataframe for display
        throughput_df['Throughput_per_Hour'] = throughput_df['Throughput_per_Hour'].apply(lambda x: f"{x:.2f} €/h")
        
        st.dataframe(throughput_df, width='stretch')


def show_visualizations_page():
    """Display visualizations of the simulation results."""
    st.header("5. Visualizations")
    
    if st.session_state.simulation_results is None:
        st.warning("No simulation results available. Please run a simulation first.")
        return
    
    results = st.session_state.simulation_results
    
    # Visualization options
    st.subheader("Select Visualizations")
    
    col1, col2 = st.columns(2)
    with col1:
        show_allocation_chart = st.checkbox("Product Allocation by Cycle", value=True)
        show_load_chart = st.checkbox("Load Distribution by Cycle", value=True)
    
    with col2:
        show_throughput_chart = st.checkbox("Throughput Comparison", value=True)
    
    st.divider()
    
    if show_allocation_chart and results['allocation'] is not None:
        plot_allocation_chart(results)
        st.divider()
    
    if show_load_chart and results['load_per_cycle'] is not None:
        plot_load_distribution(results)
        st.divider()
    
    if show_throughput_chart and results['products_with_throughput'] is not None:
        plot_throughput_comparison(results)


@st.cache_data
def get_allocation_chart(results) -> go.Figure:
    """Generate allocation chart."""
    allocation_df = results['allocation'].copy()
    
    pivot_df = allocation_df.pivot_table(
        index='Cycle',
        columns='Product',
        values='Quantity',
        aggfunc='sum',
        fill_value=0
    )
    
    fig = go.Figure()
    
    for product in pivot_df.columns:
        fig.add_trace(go.Bar(
            name=product,
            x=pivot_df.index,
            y=pivot_df[product],
            text=pivot_df[product].round(1),
            textposition='inside',
            texttemplate='%{text}'
        ))
    
    fig.update_layout(
        title=f"Product Allocation Across {results['cycles_to_display']} Cycles",
        xaxis_title="Cycle",
        yaxis_title="Quantity",
        barmode='stack',
        height=500,
        hovermode='x unified'
    )
    
    return fig


def plot_allocation_chart(results):
    """Plot product allocation across cycles."""
    st.subheader("Product Allocation by Cycle")
    fig = get_allocation_chart(results)
    st.plotly_chart(fig, width='stretch')


@st.cache_data
def get_load_distribution_chart(results) -> go.Figure:
    """Generate load distribution chart."""
    load_df = results['load_per_cycle'].copy()
    available_time = results['available_time_per_cycle']
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name='Production Load',
        x=load_df['Cycle'],
        y=load_df['Production_Load'],
        marker_color='lightblue'
    ))
    
    fig.add_trace(go.Bar(
        name='Changeover Load',
        x=load_df['Cycle'],
        y=load_df['Changeover_Load'],
        marker_color='lightcoral'
    ))
    
    fig.add_hline(
        y=available_time,
        line_dash="dash",
        line_color="red",
        annotation_text="Available Capacity",
        annotation_position="right"
    )
    
    fig.update_layout(
        title=f"Load Distribution Across {results['cycles_to_display']} Cycles",
        xaxis_title="Cycle",
        yaxis_title="Load (hours)",
        barmode='group',
        height=500,
        hovermode='x unified'
    )
    
    return fig


def plot_load_distribution(results):
    """Plot load distribution across cycles."""
    st.subheader("Load Distribution by Cycle")
    fig = get_load_distribution_chart(results)
    st.plotly_chart(fig, width='stretch')


@st.cache_data
def get_throughput_comparison_chart(results) -> go.Figure:
    """Generate throughput comparison chart."""
    products_df = results['products_with_throughput'].copy()
    
    fig = px.bar(
        products_df,
        x='Product',
        y='Throughput_per_Hour',
        color='Product',
        title="Throughput per Hour by Product",
        labels={'Throughput_per_Hour': 'Throughput (€/h)', 'Product': 'Product'},
        text='Throughput_per_Hour'
    )
    
    fig.update_traces(texttemplate='%{text:.2f}', textposition='outside')
    fig.update_layout(height=500, showlegend=False)
    
    return fig


def plot_throughput_comparison(results):
    """Plot throughput comparison across products."""
    st.subheader("Throughput Comparison")
    fig = get_throughput_comparison_chart(results)
    st.plotly_chart(fig, width='stretch')


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    main()
