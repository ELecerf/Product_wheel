# Product Wheel Simulator - Main Application
"""
Streamlit application for Product Wheel simulation.
This app optimizes production planning using the Product Wheel methodology.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from io import BytesIO

# Import local modules
from core.models import Config, Product, SimulationResults
from core.calculations import (
    calculate_lcm, calculate_super_cycle, calculate_demand_per_cycle,
    calculate_frequency, calculate_safety_stock, allocate_products_to_cycles,
    calculate_load_per_cycle, calculate_throughput, run_simulation
)
from core.validation import validate_inputs, validate_uploaded_file
from core.config import (
    DEFAULT_AVAILABLE_TIME_PER_WEEK_H, DEFAULT_CYCLE_T_DAYS,
    DEFAULT_OPENED_WEEK_PER_YEAR, DEFAULT_OPENED_DAYS_PER_WEEK,
    DEFAULT_PLANNED_LOSS_PERCENT, COLOR_PALETTE
)
from data.sample_data import (
    get_sample_config, get_sample_products, 
    get_sample_changeover_matrix, get_sample_demand_history
)
from data.io import (
    save_to_csv, save_to_excel, save_to_json,
    export_simulation_results, export_summary_report, export_configuration
)


# ============================================================================
# APP CONFIGURATION
# ============================================================================

# Page configuration
st.set_page_config(
    page_title="Product Wheel Simulator",
    page_icon="🎡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
    }
    </style>
""", unsafe_allow_html=True)


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def init_session_state():
    """Initialize session state variables."""
    if 'simulation_results' not in st.session_state:
        st.session_state.simulation_results = None
    if 'config_data' not in st.session_state:
        st.session_state.config_data = None
    if 'products_data' not in st.session_state:
        st.session_state.products_data = None
    if 'changeover_data' not in st.session_state:
        st.session_state.changeover_data = None
    if 'demand_data' not in st.session_state:
        st.session_state.demand_data = None


def load_sample_data():
    """Load sample data for demonstration purposes."""
    # Check if there's existing data
    if any([
        st.session_state.config_data is not None,
        st.session_state.products_data is not None,
        st.session_state.changeover_data is not None
    ]):
        # Use a session state variable to track confirmation
        if 'load_sample_confirmed' not in st.session_state:
            st.session_state.load_sample_confirmed = False
        
        st.warning("⚠️ This will overwrite existing data.")
        if st.button("Confirm Overwrite", key="confirm_overwrite"):
            st.session_state.load_sample_confirmed = True
        
        if not st.session_state.load_sample_confirmed:
            return
        
        # Reset confirmation after use
        st.session_state.load_sample_confirmed = False
    
    # Load sample data
    st.session_state.config_data = get_sample_config()
    st.session_state.products_data = get_sample_products()
    st.session_state.changeover_data = get_sample_changeover_matrix()
    st.session_state.demand_data = get_sample_demand_history()
    
    # Reset results
    st.session_state.simulation_results = None
    
    st.success("Sample data loaded successfully!")


def edit_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Simple dataframe editor using st.data_editor.
    
    Args:
        df: DataFrame to edit.
        
    Returns:
        Edited DataFrame.
    """
    st.markdown("### Edit DataFrame")
    edited_df = st.data_editor(df, use_container_width=True)
    return edited_df


# ============================================================================
# PAGE FUNCTIONS
# ============================================================================

def show_data_input_page():
    """Display the data input page."""
    st.header("1. Data Input")
    st.markdown("Upload or edit your production data.")
    
    # Configuration section
    with st.expander("📋 Global Configuration", expanded=True):
        st.markdown("### Configuration Parameters")
        
        col1, col2 = st.columns(2)
        
        with col1:
            available_time = st.number_input(
                "Available Time per week (hours)",
                min_value=0.0,
                value=DEFAULT_AVAILABLE_TIME_PER_WEEK_H if st.session_state.config_data is None else 
                st.session_state.config_data['Available Time per week (h)'].iloc[0]
            )
            opened_week_per_year = st.number_input(
                "Opened Week per year",
                min_value=1,
                max_value=52,
                value=DEFAULT_OPENED_WEEK_PER_YEAR if st.session_state.config_data is None else 
                st.session_state.config_data['Opened Week per year'].iloc[0]
            )
        
        with col2:
            cycle_t = st.number_input(
                "Cycle T (days)",
                min_value=1,
                value=DEFAULT_CYCLE_T_DAYS if st.session_state.config_data is None else 
                st.session_state.config_data['Cycle T (days)'].iloc[0]
            )
            opened_days_per_week = st.number_input(
                "Opened Days per week",
                min_value=1,
                max_value=7,
                value=DEFAULT_OPENED_DAYS_PER_WEEK if st.session_state.config_data is None else 
                st.session_state.config_data['Opened Days per week'].iloc[0]
            )
            planned_loss = st.number_input(
                "Planned Loss (%)",
                min_value=0.0,
                max_value=100.0,
                value=DEFAULT_PLANNED_LOSS_PERCENT if st.session_state.config_data is None else 
                st.session_state.config_data['Planned Loss (%)'].iloc[0]
            )
        
        if st.button("Save Configuration"):
            config_df = pd.DataFrame({
                'Available Time per week (h)': [available_time],
                'Cycle T (days)': [cycle_t],
                'Opened Week per year': [opened_week_per_year],
                'Opened Days per week': [opened_days_per_week],
                'Planned Loss (%)': [planned_loss]
            })
            st.session_state.config_data = config_df
            st.success("Configuration saved!")
    
    # Products section
    with st.expander("📦 Product Data", expanded=True):
        st.markdown("### Product Information")
        
        # File upload or manual entry
        col1, col2 = st.columns([1, 3])
        
        with col1:
            upload_method = st.radio("Input Method", ["Upload CSV", "Manual Entry"])
        
        with col2:
            if upload_method == "Upload CSV":
                uploaded_file = st.file_uploader(
                    "Upload Products CSV",
                    type=["csv"],
                    key="products_upload"
                )
                if uploaded_file:
                    try:
                        products_df = pd.read_csv(uploaded_file)
                        # Validate required columns
                        required_cols = ['Product', 'Annual Demand (unit)', 'k', 'Phase+']
                        missing_cols = [col for col in required_cols if col not in products_df.columns]
                        if missing_cols:
                            st.error(f"Missing required columns: {', '.join(missing_cols)}")
                        else:
                            st.session_state.products_data = products_df
                            st.success("Products data uploaded!")
                    except Exception as e:
                        st.error(f"Error uploading file: {e}")
            else:
                st.markdown("Enter product data manually")
        
        # Display current products data
        if st.session_state.products_data is not None:
            st.dataframe(st.session_state.products_data, use_container_width=True)
            
            if st.button("Edit Products Manually"):
                st.session_state.products_data = edit_dataframe(st.session_state.products_data)
        else:
            st.info("No product data loaded. Please upload a file or use sample data.")
    
    # Changeover matrix section
    with st.expander("🔄 Changeover Matrix", expanded=True):
        st.markdown("### From-To Changeover Times (hours)")
        
        col1, col2 = st.columns([1, 3])
        
        with col1:
            upload_method_co = st.radio("Input Method", ["Upload CSV", "Manual Entry"], key="co_method")
        
        with col2:
            if upload_method_co == "Upload CSV":
                uploaded_file_co = st.file_uploader(
                    "Upload Changeover Matrix CSV",
                    type=["csv"],
                    key="changeover_upload"
                )
                if uploaded_file_co:
                    try:
                        co_df = pd.read_csv(uploaded_file_co, index_col=0)
                        st.session_state.changeover_data = co_df
                        st.success("Changeover matrix uploaded!")
                    except Exception as e:
                        st.error(f"Error uploading file: {e}")
            else:
                st.markdown("Enter changeover matrix manually")
        
        # Display current changeover matrix
        if st.session_state.changeover_data is not None:
            st.dataframe(st.session_state.changeover_data, use_container_width=True)
        else:
            st.info("No changeover matrix loaded. Please upload a file or use sample data.")
    
    # Demand history section
    with st.expander("📈 Demand History", expanded=False):
        st.markdown("### Historical Demand Data")
        
        uploaded_demand = st.file_uploader(
            "Upload Demand History CSV",
            type=["csv"],
            key="demand_upload"
        )
        if uploaded_demand:
            try:
                demand_df = pd.read_csv(uploaded_demand)
                st.session_state.demand_data = demand_df
                st.success("Demand history uploaded!")
            except Exception as e:
                st.error(f"Error uploading file: {e}")
        
        if st.session_state.demand_data is not None:
            st.dataframe(st.session_state.demand_data, use_container_width=True)


def show_simulation_page():
    """Display the simulation page."""
    st.header("2. Run Simulation")
    st.markdown("Configure and execute the Product Wheel simulation.")
    
    # Check if all required data is available
    missing_data = []
    if st.session_state.config_data is None:
        missing_data.append("Global Configuration")
    if st.session_state.products_data is None:
        missing_data.append("Product Data")
    if st.session_state.changeover_data is None:
        missing_data.append("Changeover Matrix")
    
    if missing_data:
        st.warning(f"Missing required data: {', '.join(missing_data)}. Please provide all inputs before running simulation.")
        return
    
    # Validate inputs
    errors = validate_inputs(
        st.session_state.config_data,
        st.session_state.products_data,
        st.session_state.changeover_data
    )
    
    if errors:
        st.error("❌ Input validation errors:")
        for error in errors:
            st.error(f"- {error}")
        return
    
    # Simulation parameters
    st.subheader("Simulation Parameters")
    
    col1, col2 = st.columns(2)
    
    with col1:
        optimize_sequence = st.checkbox(
            "Optimize Product Sequence",
            value=False,
            help="Automatically optimize product sequence to minimize changeover times"
        )
    
    with col2:
        include_safety_stock = st.checkbox(
            "Calculate Safety Stock",
            value=True,
            help="Include safety stock calculations in the results"
        )
    
    # Run simulation button
    if st.button("Run Simulation", type="primary", disabled=len(errors) > 0):
        with st.spinner("Running Product Wheel simulation..."):
            # Convert config to Config object
            try:
                config_obj = Config.from_dataframe(st.session_state.config_data)
            except Exception as e:
                st.error(f"Error creating config: {e}")
                return
            
            # Perform calculations
            results = run_simulation(
                config_obj,
                st.session_state.products_data,
                st.session_state.changeover_data,
                optimize_sequence,
                include_safety_stock
            )
            
            st.session_state.simulation_results = results
            st.success("Simulation completed successfully!")
            
            # Show summary
            st.subheader("Simulation Summary")
            show_simulation_summary(results)


def show_simulation_summary(results: SimulationResults):
    """Display a summary of the simulation results."""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Super Cycle", f"{results.super_cycle} cycles")
    
    with col2:
        st.metric("Cycles per Year", f"{results.cycles_per_year:.1f}")
    
    with col3:
        st.metric("Available Time/Cycle", f"{results.available_time_per_cycle:.1f} hours")
    
    with col4:
        num_products = len(results.products_with_demand) if results.products_with_demand is not None else 0
        st.metric("Products", f"{num_products}")
    
    st.divider()
    
    # Show product metrics
    st.subheader("Product Metrics")
    if results.products_with_throughput is not None:
        products_df = results.products_with_throughput.copy()
        
        # Select relevant columns for display
        display_cols = [
            'Product', 'Annual Demand (unit)', 'k', 'Phase+', 
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
                'Throughput_per_Hour': '{:.2f} €/h',
                'Safety_Stock': '{:.1f}'
            }
        )


def show_results_page():
    """Display the detailed results page."""
    st.header("3. Simulation Results")
    
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


def show_product_metrics(results: SimulationResults):
    """Display product-level metrics."""
    st.subheader("Product-Level Metrics")
    
    if results.products_with_throughput is None:
        st.warning("No product metrics available.")
        return
    
    products_df = results.products_with_throughput.copy()
    
    # Create a comprehensive dataframe
    metrics_df = pd.DataFrame({
        'Product': products_df['Product'],
        'Annual Demand': products_df['Annual Demand (unit)'],
        'k': products_df['k'],
        'Phase+': products_df['Phase+'],
        'Demand per Cycle': products_df['Demand_per_Cycle'],
        'Frequency': products_df['Freq'],
    })
    
    if 'Throughput_per_Hour' in products_df.columns:
        metrics_df['Throughput (€/h)'] = products_df['Throughput_per_Hour']
    
    if 'Processing_Time_per_Unit' in products_df.columns:
        metrics_df['Processing Time/Unit (h)'] = products_df['Processing_Time_per_Unit']
    
    if 'C/O Time' in products_df.columns:
        metrics_df['C/O Time (h)'] = products_df['C/O Time']
    
    if 'Safety_Stock' in products_df.columns:
        metrics_df['Safety Stock'] = products_df['Safety_Stock']
    
    st.dataframe(
        metrics_df,
        use_container_width=True,
        format={
            'Demand per Cycle': '{:.2f}',
            'Frequency': '{:.1f}',
            'Throughput (€/h)': '{:.2f}',
            'Processing Time/Unit (h)': '{:.3f}',
            'C/O Time (h)': '{:.2f}',
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


def show_cycle_allocation(results: SimulationResults):
    """Display cycle allocation details."""
    st.subheader("Product Allocation by Cycle")
    
    if results.allocation is None:
        st.warning("No allocation data available.")
        return
    
    allocation_df = results.allocation.copy()
    
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


def show_load_analysis(results: SimulationResults):
    """Display load analysis by cycle."""
    st.subheader("Load Analysis by Cycle")
    
    if results.load_per_cycle is None:
        st.warning("No load analysis data available.")
        return
    
    load_df = results.load_per_cycle.copy()
    available_time = results.available_time_per_cycle
    
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
        st.warning(f"⚠️ {len(high_utilization)} cycles exceed available capacity!")
        st.dataframe(high_utilization, use_container_width=True)


def show_throughput_results(results: SimulationResults):
    """Display throughput analysis."""
    st.subheader("Throughput Analysis")
    
    if results.products_with_throughput is None:
        st.warning("No throughput data available.")
        return
    
    products_df = results.products_with_throughput.copy()
    
    # Create throughput comparison
    if 'Throughput_per_Hour' in products_df.columns and 'RM Profit €/kg' in products_df.columns:
        throughput_df = products_df[['Product', 'Throughput_per_Hour', 'RM Profit €/kg']].copy()
        throughput_df = throughput_df.sort_values('Throughput_per_Hour', ascending=False)
        
        st.dataframe(
            throughput_df,
            use_container_width=True,
            format={
                'Throughput_per_Hour': '{:.2f} €/h',
                'RM Profit €/kg': '{:.2f} €/kg'
            }
        )
    elif 'Throughput_per_Hour' in products_df.columns:
        throughput_df = products_df[['Product', 'Throughput_per_Hour']].copy()
        throughput_df = throughput_df.sort_values('Throughput_per_Hour', ascending=False)
        
        st.dataframe(
            throughput_df,
            use_container_width=True,
            format={
                'Throughput_per_Hour': '{:.2f} €/h'
            }
        )


def show_visualizations_page():
    """Display visualizations of the simulation results."""
    st.header("4. Visualizations")
    
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
    
    if show_allocation_chart and results.allocation is not None:
        plot_allocation_chart(results)
        st.divider()
    
    if show_load_chart and results.load_per_cycle is not None:
        plot_load_distribution(results)
        st.divider()
    
    if show_throughput_chart and results.products_with_throughput is not None:
        plot_throughput_comparison(results)
        st.divider()
    
    if show_changeover_heatmap and st.session_state.changeover_data is not None:
        plot_changeover_heatmap()


@st.cache_data
def get_allocation_chart(results: SimulationResults) -> go.Figure:
    """Generate allocation chart."""
    allocation_df = results.allocation.copy()
    
    # Create a pivot table for plotting
    pivot_df = allocation_df.pivot_table(
        index='Cycle',
        columns='Product',
        values='Quantity',
        aggfunc='sum',
        fill_value=0
    )
    
    # Plot stacked bar chart
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


def plot_allocation_chart(results: SimulationResults):
    """Plot product allocation across cycles."""
    st.subheader("Product Allocation by Cycle")
    fig = get_allocation_chart(results)
    st.plotly_chart(fig, use_container_width=True)


@st.cache_data
def get_load_distribution_chart(results: SimulationResults) -> go.Figure:
    """Generate load distribution chart."""
    load_df = results.load_per_cycle.copy()
    available_time = results.available_time_per_cycle
    
    # Create figure with production and changeover loads
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
    
    # Add capacity line
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


def plot_load_distribution(results: SimulationResults):
    """Plot load distribution across cycles."""
    st.subheader("Load Distribution by Cycle")
    fig = get_load_distribution_chart(results)
    st.plotly_chart(fig, use_container_width=True)


@st.cache_data
def get_throughput_comparison_chart(results: SimulationResults) -> go.Figure:
    """Generate throughput comparison chart."""
    products_df = results.products_with_throughput.copy()
    
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


def plot_throughput_comparison(results: SimulationResults):
    """Plot throughput comparison across products."""
    st.subheader("Throughput Comparison")
    fig = get_throughput_comparison_chart(results)
    st.plotly_chart(fig, use_container_width=True)


@st.cache_data
def get_changeover_heatmap() -> go.Figure:
    """Generate changeover matrix heatmap."""
    changeover_df = st.session_state.changeover_data.copy()
    
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


def show_export_page():
    """Display the export page."""
    st.header("5. Export Results")
    
    if st.session_state.simulation_results is None:
        st.warning("No simulation results available. Please run a simulation first.")
        return
    
    results = st.session_state.simulation_results
    
    st.markdown("Download simulation results in various formats.")
    
    # Export options
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Export All Results (Excel)"):
            excel_data = export_simulation_results(results)
            st.download_button(
                label="Download All Results (Excel)",
                data=excel_data,
                file_name=f"product_wheel_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    
    with col2:
        if st.button("Export Summary (Excel)"):
            excel_data = export_summary_report(results)
            st.download_button(
                label="Download Summary Report (Excel)",
                data=excel_data,
                file_name=f"summary_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    
    with col3:
        if st.button("Export Configuration"):
            json_data = export_configuration(
                st.session_state.config_data,
                st.session_state.products_data,
                st.session_state.changeover_data
            )
            st.download_button(
                label="Download Configuration (JSON)",
                data=json_data,
                file_name=f"configuration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
    
    st.divider()
    
    # Individual exports
    st.subheader("Individual Exports")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📥 Download Product Metrics"):
            if results.products_with_throughput is not None:
                csv = results.products_with_throughput.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=f"product_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
        
        if st.button("📥 Download Cycle Allocation"):
            if results.allocation is not None:
                csv = results.allocation.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=f"cycle_allocation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
    
    with col2:
        if st.button("📥 Download Load Analysis"):
            if results.load_per_cycle is not None:
                csv = results.load_per_cycle.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=f"load_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
        
        if st.button("📥 Download Throughput Analysis"):
            if results.products_with_throughput is not None:
                throughput_df = results.products_with_throughput[['Product', 'Throughput_per_Hour']].copy()
                csv = throughput_df.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=f"throughput_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )


# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main():
    """Main application function."""
    # Initialize session state
    init_session_state()
    
    # Header
    st.markdown('<p class="main-header">🎡 Product Wheel Simulation</p>', unsafe_allow_html=True)
    st.markdown("### Optimize production planning with Product Wheel methodology")
    
    # Sidebar
    with st.sidebar:
        st.header("Navigation")
        page = st.radio(
            "Select Page",
            ["Data Input", "Simulation", "Results", "Visualizations", "Export"]
        )
        
        st.divider()
        st.header("Sample Data")
        if st.button("Load Sample Data"):
            load_sample_data()
        
        st.divider()
        st.header("About")
        st.markdown("""
        This application implements the Product Wheel simulation methodology to:
        
        - Optimize production planning across multiple products
        - Minimize changeover times
        - Balance production load across cycles
        - Calculate key performance indicators
        
        **Version**: 2.0.0
        
        **Last Updated**: 2025
        
        **Improvements**:
        - Modular code structure
        - Better error handling
        - Optimized calculations
        - Type hints and documentation
        """)
    
    # Page routing
    if page == "Data Input":
        show_data_input_page()
    elif page == "Simulation":
        show_simulation_page()
    elif page == "Results":
        show_results_page()
    elif page == "Visualizations":
        show_visualizations_page()
    elif page == "Export":
        show_export_page()


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    main()
