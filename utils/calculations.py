import pandas as pd
import numpy as np
import datetime

def generate_sample_data():
    """Generates realistic sample data for D2C unit economics analysis."""
    np.random.seed(42)
    
    # 1. SKUs and Inventory (COGS)
    skus = [f'TSHIRT_{c}_{sz}' for c in ['BLK', 'WHT', 'NVY'] for sz in ['S', 'M', 'L', 'XL']]
    inventory_data = {
        'SKU': skus,
        'Cost_Price': np.random.uniform(150, 450, len(skus)).round(2)  # INR
    }
    inventory_df = pd.DataFrame(inventory_data)
    
    # 2. Sales Data
    dates = pd.date_range(start='2024-01-01', end='2024-03-31', freq='D')
    channels = ['Website', 'Amazon', 'Instagram', 'Myntra']
    
    sales_records = []
    order_id_counter = 1000
    
    for d in dates:
        # Random daily orders
        num_orders = np.random.poisson(15 if d.month == 1 else 25) 
        for _ in range(num_orders):
            channel = np.random.choice(channels, p=[0.4, 0.3, 0.2, 0.1])
            sku = np.random.choice(skus)
            qty = np.random.choice([1, 1, 1, 2, 3])
            price_base = inventory_df.loc[inventory_df['SKU'] == sku, 'Cost_Price'].values[0] * np.random.uniform(2.5, 4.0)
            
            # Channel adjustments
            if channel == 'Amazon': price_base *= 0.9 # Competitive pricing
            
            sales_records.append({
                'Order_Date': d,
                'Order_ID': f'ORD-{order_id_counter}',
                'SKU': sku,
                'Channel': channel,
                'Units_Sold': qty,
                'Revenue': round(price_base * qty, 2),
                'Customer_ID': f'CUST-{np.random.randint(1, 500)}' # Some repeat customers
            })
            order_id_counter += 1
            
    sales_df = pd.DataFrame(sales_records)
    
    # 3. Marketing Spend (Monthly/Channel)
    marketing_records = []
    for m in [1, 2, 3]:
        for ch in channels:
            if ch == 'Myntra': continue # Assume organic/commission only
            
            base_spend = 50000 if ch == 'Website' else 30000
            if ch == 'Instagram': base_spend = 80000
            
            spend = base_spend * np.random.uniform(0.8, 1.2)
            marketing_records.append({
                'Date': pd.Timestamp(f'2024-{m:02d}-01'),
                'Channel': ch,
                'Spend': round(spend, 2)
            })
    marketing_df = pd.DataFrame(marketing_records)

    # 4. Logistics/Other (Order Level) with RETURNS
    logistics_records = []
    for _, row in sales_df.iterrows():
        order_id = row['Order_ID']
        channel = row['Channel']
        
        # Random logic: Amazon FBA vs Self Ship
        shipping = np.random.choice([60, 80, 120])
        
        # Returns Logic (Higher returns for marketplaces)
        return_prob = 0.15 # Base
        if channel == 'Myntra': return_prob = 0.30
        if channel == 'Amazon': return_prob = 0.25
        
        is_return = 1 if np.random.random() < return_prob else 0
        
        logistics_records.append({
            'Order_ID': order_id,
            'Fulfillment_Cost': shipping,
            'Is_Return': is_return,
            'Return_Reason': np.random.choice(['Size', 'Quality', 'Changed Mind']) if is_return else None
        })
    logistics_df = pd.DataFrame(logistics_records)
    
    return {
        'Sales': sales_df,
        'Inventory': inventory_df,
        'Marketing': marketing_df,
        'Logistics': logistics_df
    }

def clean_dataframe(df):
    """Standardize column names to lowercase/stripped for easier matching."""
    if df is None: return None
    df = df.copy()
    # Basic cleanup: strip whitespace from headers
    df.columns = df.columns.astype(str).str.strip()
    return df

def process_data(sales, inventory, marketing, logistics):
    """
    Core logic to merge and calculate unit economics.
    Returns:
        - merged_df: Granular Sales + COGS + Logistics
        - channel_metrics: Aggregated by Channel/Month with Marketing info
        - overall_metrics: Dictionary of scalar KPIs
    """
    # 1. Pre-process Sales
    sales = sales.copy()
    sales['Order_Date'] = pd.to_datetime(sales['Order_Date'])
    sales['Month'] = sales['Order_Date'].dt.to_period('M').dt.to_timestamp()
    
    # 2. Merge Inventory (COGS)
    # Try merging on SKU
    merged_df = pd.merge(sales, inventory, on='SKU', how='left')
    
    # Calculate Total COGS
    if 'Cost_Price' in merged_df.columns:
        merged_df['Total_COGS'] = merged_df['Cost_Price'] * merged_df['Units_Sold']
    elif 'COGS_per_Unit' in merged_df.columns:
        merged_df['Total_COGS'] = merged_df['COGS_per_Unit'] * merged_df['Units_Sold']
    else:
        # Fallback if no match
        merged_df['Total_COGS'] = 0
        
    merged_df['Gross_Sales_Value'] = merged_df['Revenue'] # Preserve original as Gross
    
    # 3. Merge Logistics and Handle RETURNS
    if logistics is not None:
        if 'Order_ID' in logistics.columns and 'Order_ID' in merged_df.columns:
            merged_df = pd.merge(merged_df, logistics, on='Order_ID', how='left')
            merged_df['Fulfillment_Cost'] = merged_df['Fulfillment_Cost'].fillna(0)
            
            # Normalize Return Columns
            if 'Is_Return' not in merged_df.columns:
                # check for alternate names or derive
                if 'Return_Status' in merged_df.columns:
                     merged_df['Is_Return'] = merged_df['Return_Status'].apply(lambda x: 1 if str(x).lower() in ['returned', 'rto', 'return'] else 0)
                else:
                     merged_df['Is_Return'] = 0
            
            merged_df['Is_Return'] = merged_df['Is_Return'].fillna(0).astype(int)
            
        else:
            merged_df['Fulfillment_Cost'] = 0
            merged_df['Is_Return'] = 0
    else:
        merged_df['Fulfillment_Cost'] = 0
        merged_df['Is_Return'] = 0
        
    # --- NET REVENUE CALCULATION ---
    # Net Revenue = Revenue * (1 - Is_Return) -> Assuming full refund
    # Also handle negative revenue inputs if any
    merged_df['Net_Revenue'] = np.where(merged_df['Is_Return'] == 1, 0, merged_df['Revenue'])
    
    # Gross Profit (Net) = Net_Revenue - COGS (Sunk)
    # Note: User requested COGS is sunk even on returns. 
    merged_df['Gross_Profit'] = merged_df['Net_Revenue'] - merged_df['Total_COGS']
    
    # Contribution Margin 1 (Net) = Gross Profit - Fulfillment (Sunk)
    merged_df['Contribution_Profit_1'] = merged_df['Gross_Profit'] - merged_df['Fulfillment_Cost']
    
    # 4. Aggregations for Marketing (CM2)
    # Group by Channel and Month
    channel_group = merged_df.groupby(['Channel', 'Month']).agg({
        'Revenue': 'sum', # Gross Revenue
        'Net_Revenue': 'sum',
        'Total_COGS': 'sum',
        'Fulfillment_Cost': 'sum',
        'Contribution_Profit_1': 'sum',
        'Units_Sold': 'sum',
        'Order_ID': 'nunique',
        'Is_Return': 'sum'
    }).rename(columns={'Is_Return': 'Return_Count'}).reset_index()
    
    # 5. Merge Marketing Spend
    if marketing is not None:
        marketing['Date'] = pd.to_datetime(marketing['Date'])
        marketing['Month'] = marketing['Date'].dt.to_period('M').dt.to_timestamp()
        
        # Aggregate marketing just in case multiple entries per month/channel
        mkt_agg = marketing.groupby(['Channel', 'Month'])['Spend'].sum().reset_index()
        
        channel_metrics = pd.merge(channel_group, mkt_agg, on=['Channel', 'Month'], how='outer').fillna(0)
    else:
        channel_metrics = channel_group.copy()
        channel_metrics['Spend'] = 0
        
    # 6. Calculate Unit Economics Support Metrics
    channel_metrics['Contribution_Profit_2'] = channel_metrics['Contribution_Profit_1'] - channel_metrics['Spend']
    
    # KPIs
    channel_metrics['CAC'] = np.where(channel_metrics['Order_ID'] > 0, channel_metrics['Spend'] / channel_metrics['Order_ID'], 0)
    
    # ROAS calculated on Gross Revenue usually, but can be Net. Standard is Gross Sales / Spend.
    channel_metrics['ROAS'] = np.where(channel_metrics['Spend'] > 0, channel_metrics['Revenue'] / channel_metrics['Spend'], 0)
    
    channel_metrics['AOV'] = np.where(channel_metrics['Order_ID'] > 0, channel_metrics['Revenue'] / channel_metrics['Order_ID'], 0)
    
    # Margins based on Net Revenue ideally, but often denomination is Gross. 
    # Let's use Net Revenue denomiator for "Real" margin, or Gross for standard accounting?
    # User asked for "True Profitability". 
    # CM % = Contribution Profit / Net Revenue is most accurate.
    # However, to avoid Div/0 if Net Rev is 0 (all returns), we handle carefully.
    channel_metrics['CM_Pct'] = np.where(channel_metrics['Net_Revenue'] > 0, channel_metrics['Contribution_Profit_2'] / channel_metrics['Net_Revenue'], 0)
    
    # Return Rate
    channel_metrics['Return_Rate_Pct'] = np.where(channel_metrics['Order_ID'] > 0, channel_metrics['Return_Count'] / channel_metrics['Order_ID'], 0)
    
    # 7. Overall Summary
    gross_rev = channel_metrics['Revenue'].sum()
    net_rev = channel_metrics['Net_Revenue'].sum()
    total_spend = channel_metrics['Spend'].sum()
    total_orders = channel_metrics['Order_ID'].sum()
    total_margin = channel_metrics['Contribution_Profit_2'].sum()
    
    overall = {
        'Gross_Revenue': gross_rev,
        'Net_Revenue': net_rev,
        'Total_Spend': total_spend,
        'Total_Orders': total_orders,
        'Net_Profit': total_margin, # Pre-fixed costs
        'Blended_ROAS': gross_rev / total_spend if total_spend > 0 else 0,
        'Blended_CAC': total_spend / total_orders if total_orders > 0 else 0,
        'Blended_CM_Pct': total_margin / net_rev if net_rev > 0 else 0,
        'Return_Rate': channel_metrics['Return_Count'].sum() / total_orders if total_orders > 0 else 0
    }
    
    return merged_df, channel_metrics, overall

def calculate_ltv(merged_df):
    """
    Simple LTV calculation.
    """
    if 'Customer_ID' not in merged_df.columns:
        return 0, 0 
        
    # Group by Customer (Use Net Revenue)
    cust_group = merged_df.groupby('Customer_ID').agg({
        'Net_Revenue': 'sum',
        'Contribution_Profit_1': 'sum', # Gross Profit post-fulfillment
        'Order_ID': 'nunique'
    })
    
    avg_customer_revenue = cust_group['Net_Revenue'].mean()
    avg_customer_profit = cust_group['Contribution_Profit_1'].mean()
    
    return avg_customer_revenue, avg_customer_profit

def calculate_payback(cac, margin_per_order, orders_per_month_per_cust=1):
    if margin_per_order <= 0: return 999
    return cac / margin_per_order

