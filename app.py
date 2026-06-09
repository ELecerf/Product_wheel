
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
    page_icon="ð¡",
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
    
    required_cols = ['Product', 'Annual Demand', 'Sequence', 'k', 'Phi']
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


def validate_changeover_matrix(df, products):
    """Validate changeover matrix."""
    errors = []
    if df is None or len(df) == 0:
        errors.append("Changeover matrix is required.")
        return errors
    
    product_names = products['Product'].tolist()
    
    # Check if matrix has correct dimensions
    if len(df.columns) != len(product_names) + 1:  # +1 for the From\To column
        errors.append(f"Changeover matrix must have {len(product_names)} product columns.")
    
    if len(df.index) != len(product_names):
        errors.append(f"Changeover matrix must have {len(product_names)} product rows.")
    
    # Check diagonal values
    for idx in df.index:
        if idx in df.columns:
            diag_val = df.loc[idx, idx]
            if pd.notna(diag_val) and diag_val != 0:
                errors.append(f"Changeover matrix diagonal at ({idx}, {idx}) should be 0.")
    
    # Check for negative values
    numeric_cols = [col for col in df.columns if col != 'From\\To']
    for col in numeric_cols:
        if (df[col] < 0).any():
            errors.append(f"Changeover matrix column {col} contains negative values.")
    
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


def allocate_products_to_cycles(products_df, super_cycle):
    """Allocate products to cycles based on k and Phi."""
    allocation_data = []
    
    for _, product in products_df.iterrows():
        k = int(product['k'])
        phi = int(product['Phi'])
        demand_per_cycle = product['Demand_per_Cycle']
        
        for cycle in range(1, super_cycle + 1):
            if (cycle - phi - 1) % k == 0:
                allocation_data.append({
                    'Product': product['Product'],
                    'Cycle': cycle,
                    'Quantity': demand_per_cycle * k,
                    'k': k,
                    'Phi': phi
                })
    
    return pd.DataFrame(allocation_data)


def calculate_load_per_cycle(allocation_df, products_df, changeover_df, config_df):
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
        changeover_load = 0
        if len(cycle_products) > 1:
            # Sort products by their sequence number
            sequence_dict = dict(zip(products_df['Product'], products_df['Sequence']))
            sorted_products = sorted(cycle_products, key=lambda x: sequence_dict.get(x, 0))
            
            for i in range(len(sorted_products) - 1):
                from_prod = sorted_products[i]
                to_prod = sorted_products[i + 1]
                
                if from_prod in changeover_df.index and to_prod in changeover_df.columns:
                    co_time = changeover_df.loc[from_prod, to_prod]
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


def calculate_throughput(products_df):
    """Calculate throughput per hour for each product."""
    products_df = products_df.copy()
    
    processing_time = products_df.get('Processing Time', 1.0)
    co_time = products_df.get('C/O Time', 0.0)
    throughput_euro = products_df.get('Throughput â¬', 0.0)
    
    products_df['Production_Load'] = products_df['Demand_per_Cycle'] * processing_time
    products_df['Throughput_per_Hour'] = throughput_euro / (products_df['Production_Load'] + co_time)
    
    return products_df


def run_simulation(config_df, products_df, changeover_df):
    """Run the complete Product Wheel simulation."""
    results = {}
    
    # Step 1: Calculate Super Cycle
    super_cycle = calculate_super_cycle(products_df)
    results['super_cycle'] = super_cycle
    
    # Step 2: Calculate demand per cycle
    products_with_demand = calculate_demand_per_cycle(config_df, products_df)
    results['products_with_demand'] = products_with_demand
    
    # Step 3: Calculate frequency
    products_with_freq = calculate_frequency(products_with_demand, super_cycle)
    results['products_with_freq'] = products_with_freq
    
    # Step 4: Calculate safety stock
    products_with_ss = calculate_safety_stock(products_with_freq, config_df)
    results['products_with_ss'] = products_with_ss
    
    # Step 5: Allocate products to cycles
    allocation_df = allocate_products_to_cycles(products_with_freq, super_cycle)
    results['allocation'] = allocation_df
    
    # Step 6: Calculate load per cycle
    load_df = calculate_load_per_cycle(allocation_df, products_with_ss, changeover_df, config_df)
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
            'Throughput â¬': [17500, 12500, 10000]
        })
    
    if 'changeover_df' not in st.session_state:
        product_names = st.session_state.products_df['Product'].tolist()
        # Create empty matrix
        matrix_data = {}
        matrix_data['From\\To'] = product_names
        for prod in product_names:
            matrix_data[prod] = [0] * len(product_names)
        st.session_state.changeover_df = pd.DataFrame(matrix_data).set_index('From\\To')
    
    if 'simulation_results' not in st.session_state:
        st.session_state.simulation_results = None
    
    # Header
    st.markdown('<p class="main-header">ð¡ Product Wheel Simulator - Simplified</p>', unsafe_allow_html=True)
    st.markdown("### Optimize production planning with Product Wheel methodology")
    
    # Sidebar
    with st.sidebar:
        st.header("Navigation")
        page = st.radio(
            "Select Page",
            ["Configuration", "Products & Matrix", "Simulation", "Results", "Visualizations"]
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
                'Throughput â¬': [17500, 12500, 10000]
            })
            product_names = st.session_state.products_df['Product'].tolist()
            matrix_data = {}
            matrix_data['From\\To'] = product_names
            for prod in product_names:
                matrix_data[prod] = [0] * len(product_names)
            st.session_state.changeover_df = pd.DataFrame(matrix_data).set_index('From\\To')
            st.session_state.simulation_results = None
            st.rerun()
    
    # Page routing
    if page == "Configuration":
        show_config_page()
    elif page == "Products & Matrix":
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
        use_container_width=True,
        num_rows="fixed"
    )
    
    if edited_config is not None:
        st.session_state.config_df = edited_config
    
    # Display current values
    st.markdown("**Current Configuration:**")
    st.dataframe(st.session_state.config_df, use_container_width=True)


def show_products_page():
    """Display the products and changeover matrix page."""
    st.header("2. Products & Changeover Matrix")
    
    # Products table
    st.markdown("### Product Data")
    st.markdown("Define your products with their parameters.")
    
    edited_products = st.data_editor(
        st.session_state.products_df,
        key="products_editor",
        use_container_width=True,
        num_rows="dynamic"
    )
    
    if edited_products is not None:
        st.session_state.products_df = edited_products
        # Update changeover matrix when products change
        product_names = edited_products['Product'].tolist()
        matrix_data = {}
        matrix_data['From\\To'] = product_names
        for prod in product_names:
            matrix_data[prod] = [0] * len(product_names)
        st.session_state.changeover_df = pd.DataFrame(matrix_data).set_index('From\\To')
    
    st.divider()
    
    # Changeover matrix
    st.markdown("### Changeover Matrix (From-To)")
    st.markdown("Define changeover times between products (in hours). Diagonal values should be 0.")
    
    edited_matrix = st.data_editor(
        st.session_state.changeover_df,
        key="matrix_editor",
        use_container_width=True,
        num_rows="fixed"
    )
    
    if edited_matrix is not None:
        st.session_state.changeover_df = edited_matrix


def show_simulation_page():
    """Display the simulation page."""
    st.header("3. Run Simulation")
    st.markdown("Validate inputs and execute the Product Wheel simulation.")
    
    # Validate all inputs
    config_errors = validate_config(st.session_state.config_df)
    product_errors = validate_products(st.session_state.products_df)
    matrix_errors = validate_changeover_matrix(st.session_state.changeover_df, st.session_state.products_df)
    
    all_errors = config_errors + product_errors + matrix_errors
    
    if all_errors:
        st.error("â Input validation errors:")
        for error in all_errors:
            st.error(f"- {error}")
        return
    
    # Run simulation button
    if st.button("Run Simulation", type="primary"):
        with st.spinner("Running Product Wheel simulation..."):
            results = run_simulation(
                st.session_state.config_df,
                st.session_state.products_df,
                st.session_state.changeover_df
            )
            
            st.session_state.simulation_results = results
            st.success("Simulation completed successfully!")
            
            # Show summary
            st.subheader("Simulation Summary")
            show_simulation_summary(results)


def show_simulation_summary(results):
    """Display a summary of the simulation results."""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Super Cycle", f"{results['super_cycle']} cycles")
    
    with col2:
        st.metric("Cycles per Year", f"{results['cycles_per_year']:.1f}")
    
    with col3:
        st.metric("Available Time/Cycle", f"{results['available_time_per_cycle']:.1f} hours")
    
    with col4:
        num_products = len(results['products_with_demand'])
        st.metric("Products", f"{num_products}")
    
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
    
    st.dataframe(
        products_df[display_cols],
        use_container_width=True,
        format={
            'Demand_per_Cycle': '{:.2f}',
            'Freq': '{:.1f}',
            'Throughput_per_Hour': '{:.2f} â¬/h',
            'Safety_Stock': '{:.1f}'
        }
    )


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
        'Demand per Cycle': products_df['Demand_per_Cycle'],
        'Frequency': products_df['Freq'],
    })
    
    if 'Throughput_per_Hour' in products_df.columns:
        metrics_df['Throughput (â¬/h)'] = products_df['Throughput_per_Hour']
    
    if 'Safety_Stock' in products_df.columns:
        metrics_df['Safety Stock'] = products_df['Safety_Stock']
    
    st.dataframe(
        metrics_df,
        use_container_width=True,
        format={
            'Demand per Cycle': '{:.2f}',
            'Frequency': '{:.1f}',
            'Throughput (â¬/h)': '{:.2f}',
            'Safety Stock': '{:.1f}'
        }
    )
    
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
    
    # Pivot the allocation for better display
    pivot_df = allocation_df.pivot_table(
        index='Product',
        columns='Cycle',
        values='Quantity',
        aggfunc='sum',
        fill_value=0
    )
    
    st.markdown("**Allocation Matrix (Quantity per Cycle)**")
    st.dataframe(pivot_df, use_container_width=True)
    
    st.markdown("**Detailed Allocation**")
    st.dataframe(
        allocation_df,
        use_container_width=True,
        format={'Quantity': '{:.2f}'}
    )


def show_load_analysis(results):
    """Display load analysis by cycle."""
    st.subheader("Load Analysis by Cycle")
    
    load_df = results['load_per_cycle'].copy()
    available_time = results['available_time_per_cycle']
    
    # Add capacity utilization
    load_df['Utilization (%)'] = (load_df['Total_Load'] / available_time) * 100
    load_df['Available Capacity'] = available_time
    
    st.dataframe(
        load_df,
        use_container_width=True,
        format={
            'Production_Load': '{:.2f} h',
            'Changeover_Load': '{:.2f} h',
            'Total_Load': '{:.2f} h',
            'Utilization (%)': '{:.1f}%',
            'Available Capacity': '{:.2f} h'
        }
    )
    
    # Highlight cycles with utilization issues
    high_utilization = load_df[load_df['Utilization (%)'] > 100]
    if len(high_utilization) > 0:
        st.warning(f"â ï¸ {len(high_utilization)} cycles exceed available capacity!")
        st.dataframe(high_utilization, use_container_width=True)


def show_throughput_results(results):
    """Display throughput analysis."""
    st.subheader("Throughput Analysis")
    
    products_df = results['products_with_throughput'].copy()
    
    if 'Throughput_per_Hour' in products_df.columns:
        throughput_df = products_df[['Product', 'Throughput_per_Hour']].copy()
        throughput_df = throughput_df.sort_values('Throughput_per_Hour', ascending=False)
        
        st.dataframe(
            throughput_df,
            use_container_width=True,
            format={
                'Throughput_per_Hour': '{:.2f} â¬/h'
            }
        )


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
        show_changeover_heatmap = st.checkbox("Changeover Matrix Heatmap", value=True)
    
    st.divider()
    
    if show_allocation_chart and results['allocation'] is not None:
        plot_allocation_chart(results)
        st.divider()
    
    if show_load_chart and results['load_per_cycle'] is not None:
        plot_load_distribution(results)
        st.divider()
    
    if show_throughput_chart and results['products_with_throughput'] is not None:
        plot_throughput_comparison(results)
        st.divider()
    
    if show_changeover_heatmap and st.session_state.changeover_df is not None:
        plot_changeover_heatmap()


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
        title="Product Allocation Across Cycles",
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
    st.plotly_chart(fig, use_container_width=True)


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
        title="Load Distribution by Cycle",
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
    st.plotly_chart(fig, use_container_width=True)


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
        labels={'Throughput_per_Hour': 'Throughput (â¬/h)', 'Product': 'Product'},
        text='Throughput_per_Hour'
    )
    
    fig.update_traces(texttemplate='%{text:.2f}', textposition='outside')
    fig.update_layout(height=500, showlegend=False)
    
    return fig


def plot_throughput_comparison(results):
    """Plot throughput comparison across products."""
    st.subheader("Throughput Comparison")
    fig = get_throughput_comparison_chart(results)
    st.plotly_chart(fig, use_container_width=True)


@st.cache_data
def get_changeover_heatmap() -> go.Figure:
    """Generate changeover matrix heatmap."""
    changeover_df = st.session_state.changeover_df.copy()
    
    fig = px.imshow(
        changeover_df,
        title="Changeover Times Between Products (hours)",
        labels=dict(x="To Product", y="From Product", color="Time (h)"),
        color_continuous_scale='YlOrRd',
        text_auto='.1f',
        aspect='auto'
    )
    
    fig.update_layout(height=600)
    
    return fig


def plot_changeover_heatmap():
    """Plot changeover matrix as a heatmap."""
    st.subheader("Changeover Matrix Heatmap")
    fig = get_changeover_heatmap()
    st.plotly_chart(fig, use_container_width=True)


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    main()

