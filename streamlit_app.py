import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils import calculations
import io

# --- Page Config & Styling ---
st.set_page_config(
    page_title="Mahanka Unit Economics Calculator",
    page_icon="🇮🇳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for concise, professional look
st.markdown("""
<style>
    .main .block-container { padding-top: 2rem; }
    .stMetric { background-color: #f8f9fa; padding: 15px; border-radius: 8px; border: 1px solid #e9ecef; }
    .stMetric .css-1wivap2 { font-size: 1.2rem; }
    h1, h2, h3 { color: #0F172A; font-family: 'Inter', sans-serif; }
    .upsell-box { background-color: #e3f2fd; padding: 20px; border-radius: 10px; border-left: 5px solid #1e88e5; margin-top: 40px; }
    .footer-text { font-size: 0.85rem; color: #64748b; text-align: center; margin-top: 50px; }
</style>
""", unsafe_allow_html=True)

# --- Header ---
st.title("Mahanka Unit Economics Calculator")
st.markdown("**Discover Your True Profitability Per SKU & Channel – Free Tool for Indian D2C Brands 🇮🇳**")
st.markdown("---")

# --- Sidebar: Data Inputs ---
with st.sidebar:
    st.header("📊 Data Input")
    
    # Session State for Data
    if 'data_source' not in st.session_state:
        st.session_state['data_source'] = None
    
    # 1. Option: Load Sample Data
    st.caption("New here? Try with realistic data:")
    if st.button("🚀 Load D2C Sample Data", type="primary", use_container_width=True):
        sample_data = calculations.generate_sample_data()
        st.session_state['sales_df'] = sample_data['Sales']
        st.session_state['inventory_df'] = sample_data['Inventory']
        st.session_state['marketing_df'] = sample_data['Marketing']
        st.session_state['logistics_df'] = sample_data['Logistics']
        st.session_state['data_source'] = 'sample'
        st.success("Sample data loaded!")

    st.markdown("---")
    st.caption("OR Upload your own CSVs:")
    
    # 2. File Uploaders
    sales_file = st.file_uploader("1. Sales Data (Required)", type=['csv'], help="Columns: Order_Date, SKU, Channel, Revenue, Units_Sold")
    inventory_file = st.file_uploader("2. Inventory/COGS (Optional)", type=['csv'], help="Columns: SKU, Cost_Price")
    marketing_file = st.file_uploader("3. Marketing Spend (Optional)", type=['csv'], help="Columns: Date, Channel, Spend")
    logistics_file = st.file_uploader("4. Logistics/Other (Optional)", type=['csv'], help="Columns: Order_ID, Fulfillment_Cost")

    if sales_file:
        st.session_state['sales_df'] = pd.read_csv(sales_file)
        st.session_state['data_source'] = 'upload'
        if inventory_file: st.session_state['inventory_df'] = pd.read_csv(inventory_file)
        if marketing_file: st.session_state['marketing_df'] = pd.read_csv(marketing_file)
        if logistics_file: st.session_state['logistics_df'] = pd.read_csv(logistics_file)

# --- Main Logic ---
if 'sales_df' in st.session_state and st.session_state['sales_df'] is not None:
    # Get DataFrames from session state
    sales = st.session_state.get('sales_df')
    inventory = st.session_state.get('inventory_df')
    marketing = st.session_state.get('marketing_df')
    logistics = st.session_state.get('logistics_df')
    
    # Process Data
    try:
        merged_df, channel_metrics, overall_kpis = calculations.process_data(sales, inventory, marketing, logistics)
        
        # --- Top Summary Cards ---
        c1, c2, c3, c4, c5 = st.columns(5)
        
        c1.metric("Net Revenue", f"₹{overall_kpis['Net_Revenue']:,.0f}", help=f"Gross: ₹{overall_kpis['Gross_Revenue']:,.0f}")
        
        # Real Gross Margin based on Net Revenue
        real_gm = overall_kpis['Gross_Revenue'] - overall_kpis['Total_Spend'] # Placeholder logic if needed, but let's use the DF
        # Actually overall_kpis has calculated Net Profit (Contribution 2). 
        # Let's show Return Rate instead of generic GM here if space is tight, or stick to CM.
        
        c2.metric("Return Rate", f"{overall_kpis['Return_Rate']:.1%}", help="Percent of Orders Returned")
        
        c3.metric("Contribution Margin (CM2)", f"{overall_kpis['Blended_CM_Pct']:.1%}", delta_color="normal", help="Net Revenue - COGS - Logistics - Marketing")
        c4.metric("Blended CAC", f"₹{overall_kpis['Blended_CAC']:.0f}")
        c5.metric("Blended ROAS", f"{overall_kpis['Blended_ROAS']:.2f}x")

        # --- Unit Economics Health Score ---
        # Heuristic: (CM% * 60) + (ROAS * 10) - (Return Rate * 20)
        score = min(100, max(0, (overall_kpis['Blended_CM_Pct'] * 100 * 1.5) + (overall_kpis['Blended_ROAS'] * 5) - (overall_kpis['Return_Rate']*100)))
        st.progress(min(score/100, 1.0), text=f"**Unit Economics Health Score: {int(score)}/100**")
        
        # --- Tabs ---
        tab1, tab2, tab3 = st.tabs(["📈 Profitability Waterfall", "📢 Channel Mix", "📦 SKU Analysis"])
        
        with tab1:
            st.subheader("Profitability Waterfall: Where is money going?")
            # Waterfall Calculation
            rev = overall_kpis['Gross_Revenue']
            returns_val = -(overall_kpis['Gross_Revenue'] - overall_kpis['Net_Revenue'])
            cogs = -merged_df['Total_COGS'].sum()
            logistics_cost = -merged_df['Fulfillment_Cost'].sum()
            mkt_spend = -overall_kpis['Total_Spend']
            
            fig_waterfall = go.Figure(go.Waterfall(
                measure = ["relative", "relative", "subtotal", "relative", "relative", "relative", "total"],
                x = ["Gross Revenue", "Returns", "Net Sales", "COGS", "Fulfillment", "Marketing", "Contribution Profit"],
                y = [rev, returns_val, 0, cogs, logistics_cost, mkt_spend, 0],
                connector = {"line":{"color":"rgb(63, 63, 63)"}},
                decreasing = {"marker":{"color":"#EF553B"}},
                increasing = {"marker":{"color":"#00CC96"}},
                totals = {"marker":{"color":"#636EFA"}}
            ))
            st.plotly_chart(fig_waterfall, use_container_width=True)
            
            st.markdown("#### Monthly Profit Trend")
            # Group merged_df by Month
            monthly = merged_df.groupby('Month')[['Revenue', 'Contribution_Profit_1']].sum().reset_index()
            # If marketing spend exists, need to subtract it month-wise. Complicated if not perfectly aligned, but we have channel_metrics
            m_trend = channel_metrics.groupby('Month')[['Revenue', 'Spend', 'Contribution_Profit_2']].sum().reset_index()
            
            fig_trend = px.line(m_trend, x='Month', y=['Revenue', 'Contribution_Profit_2', 'Spend'], 
                                title="Revenue vs Contribution Profit vs Spend",
                                color_discrete_map={"Revenue": "#636EFA", "Contribution_Profit_2": "#00CC96", "Spend": "#EF553B"})
            st.plotly_chart(fig_trend, use_container_width=True)

        with tab2:
            c_col1, c_col2 = st.columns(2)
            with c_col1:
                st.subheader("Contribution Margin % by Channel")
                fig_bar = px.bar(channel_metrics, x='Channel', y='CM_Pct', color='Channel', 
                                 title="Higher is Better", text_auto='.1%')
                st.plotly_chart(fig_bar, use_container_width=True)
            
            with c_col2:
                st.subheader("ROAS vs Scale")
                fig_scat = px.scatter(channel_metrics, x='Spend', y='ROAS', size='Revenue', color='Channel',
                                      hover_name='Channel', title="Bubble Size = Revenue")
                st.plotly_chart(fig_scat, use_container_width=True)
                
            st.dataframe(channel_metrics.style.format({
                'Revenue': '₹{:,.0f}', 'Net_Revenue': '₹{:,.0f}', 'Spend': '₹{:,.0f}', 'CAC': '₹{:.0f}', 
                'ROAS': '{:.2f}x', 'CM_Pct': '{:.1%}', 'Gross_Margin_Pct': '{:.1%}', 'Return_Rate_Pct': '{:.1%}'
            }), use_container_width=True)

        with tab3:
            st.subheader("Top Performers & Bleeders")
            # Group by SKU
            sku_group = merged_df.groupby('SKU').agg({
                'Net_Revenue': 'sum',
                'Units_Sold': 'sum',
                'Gross_Profit': 'sum',
                'Contribution_Profit_1': 'sum' # Pre-marketing
            }).reset_index()
            sku_group['Gross_Margin_%'] = np.where(sku_group['Net_Revenue']>0, sku_group['Gross_Profit'] / sku_group['Net_Revenue'], 0)
            
            col_sku1, col_sku2 = st.columns(2)
            with col_sku1:
                st.markdown("**Top 5 SKUs by Net Revenue**")
                st.dataframe(sku_group.sort_values('Net_Revenue', ascending=False).head(5).style.format({'Net_Revenue': '₹{:,.0f}', 'Gross_Margin_%': '{:.1%}'}), hide_index=True)
            with col_sku2:
                st.markdown("**Bottom 5 SKUs by Margin %**")
                st.dataframe(sku_group.sort_values('Gross_Margin_%', ascending=True).head(5).style.format({'Net_Revenue': '₹{:,.0f}', 'Gross_Margin_%': '{:.1%}'}), hide_index=True)

        # --- Upsell / Footer ---
        st.markdown("<div class='upsell-box'>", unsafe_allow_html=True)
        u_c1, u_c2 = st.columns([0.7, 0.3])
        with u_c1:
            st.markdown("### 🚀 Ready to Improve These Numbers?")
            st.markdown("Mahanka helps Indian D2C brands optimize pricing, channel mix, and reduce CAC. Don't just track metrics—fix them.")
        with u_c2:
            st.button("Book Free Consultation ↗", type="primary")
        st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown("<div class='footer-text'>🔒 Privacy Note: Your data is processed in-memory and never stored. <br> © 2024 Mahanka Analytics</div>", unsafe_allow_html=True)

        # --- Report Generation ---
        st.markdown("---")
        st.markdown("### 📥 Export Analysis")
        from utils import reporting
        
        col_export1, col_export2 = st.columns(2)
        
        with col_export1:
            # Generate HTML report
            report_html = reporting.generate_html_report(
                overall_kpis, 
                channel_metrics, 
                fig_waterfall, 
                fig_trend, 
                fig_bar, 
                fig_scat
            )
            st.download_button(
                label="📄 Download Full Report (HTML/PDF)",
                data=report_html,
                file_name="Mahanka_Unit_Economics_Report.html",
                mime="text/html",
                use_container_width=True
            )
            
        with col_export2:
            # CSV Download
            csv_data = merged_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📊 Download Detailed Data (CSV)",
                data=csv_data,
                file_name="Mahanka_Processed_Data.csv",
                mime="text/csv",
                use_container_width=True,
                help="Export the row-level data with calculated COGS, Logistics, and Net Revenue."
            )

    except Exception as e:
        st.error(f"Error processing data: {str(e)}")
        st.warning("Please ensure your CSV columns match the required format (Order_Date, SKU, Channel...).")

else:
    # Empty State
    st.info("👈 Please upload your Sales CSV or click 'Load Sample Data' in the sidebar to begin.")
