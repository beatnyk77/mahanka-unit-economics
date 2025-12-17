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

    # 4. Logistics/Other (Order Level)
    # Generate logistics for existing orders
    logistics_records = []
    for order_id in sales_df['Order_ID'].unique():
        # Random logic: Amazon FBA vs Self Ship
        shipping = np.random.choice([60, 80, 120])
        returns = 0
        if np.random.random() < 0.15: # 15% return rate
            returns = 1
        
        logistics_records.append({
            'Order_ID': order_id,
            'Fulfillment_Cost': shipping,
            'Is_Return': returns
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
        - channel_metrics: Agreggated by Channel/Month with Marketing info
        - overall_metrics: Dictionary of scalar KPIs
    """
    # 1. Pre-process Sales
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
        
    merged_df['Gross_Profit'] = merged_df['Revenue'] - merged_df['Total_COGS']
    
    # 3. Merge Logistics (Variable Costs)
    if logistics is not None:
        # Try merging on Order_ID
        if 'Order_ID' in logistics.columns and 'Order_ID' in merged_df.columns:
            merged_df = pd.merge(merged_df, logistics, on='Order_ID', how='left')
            merged_df['Fulfillment_Cost'] = merged_df['Fulfillment_Cost'].fillna(0)
            
            # Handle RTO/Returns if column exists
            # Convention: If Is_Return is 1, maybe Revenue is lost? 
            # For simplicity, we'll just treat fulfillment cost as a sunk cost for now.
            # And usually returns imply negative revenue, but let's assume 'Revenue' in input is Net Sales for MVP simplicity 
            # OR we subtract returns from revenue.
            # Let's subtract return revenue if 'Is_Return' exists
            if 'Is_Return' in merged_df.columns:
                 # If returned, revenue becomes 0 (simplified) or negative. 
                 # Let's just track it as a cost 'Return_Cost' or deduced from Gross.
                 # Actually, usually 'Revenue' input is Gross Sales. 
                 # We will calculate Net Revenue = Revenue * (1 - Return Rate). 
                 # But sticking to exact data:
                 pass
        else:
            merged_df['Fulfillment_Cost'] = 0
    else:
        merged_df['Fulfillment_Cost'] = 0
        
    # Calculate Contribution Margin 1 (Product + Fulfillment)
    merged_df['Contribution_Profit_1'] = merged_df['Gross_Profit'] - merged_df['Fulfillment_Cost']
    
    # 4. Aggregations for Marketing (CM2)
    # Group by Channel and Month
    channel_group = merged_df.groupby(['Channel', 'Month']).agg({
        'Revenue': 'sum',
        'Total_COGS': 'sum',
        'Fulfillment_Cost': 'sum',
        'Contribution_Profit_1': 'sum',
        'Units_Sold': 'sum',
        'Order_ID': 'nunique' # Order Count
    }).reset_index()
    
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
    # Note: CAC is ideally Spend / New Customers. Using Total Orders as proxy if Customer info missing.
    # We can refine if we have customer ID later.
    
    channel_metrics['ROAS'] = np.where(channel_metrics['Spend'] > 0, channel_metrics['Revenue'] / channel_metrics['Spend'], 0)
    channel_metrics['AOV'] = np.where(channel_metrics['Order_ID'] > 0, channel_metrics['Revenue'] / channel_metrics['Order_ID'], 0)
    channel_metrics['Gross_Margin_Pct'] = np.where(channel_metrics['Revenue'] > 0, (channel_metrics['Revenue'] - channel_metrics['Total_COGS']) / channel_metrics['Revenue'], 0)
    channel_metrics['CM_Pct'] = np.where(channel_metrics['Revenue'] > 0, channel_metrics['Contribution_Profit_2'] / channel_metrics['Revenue'], 0)
    
    # 7. Overall Summary
    total_rev = channel_metrics['Revenue'].sum()
    total_spend = channel_metrics['Spend'].sum()
    total_orders = channel_metrics['Order_ID'].sum()
    total_margin = channel_metrics['Contribution_Profit_2'].sum()
    
    overall = {
        'Gross_Revenue': total_rev,
        'Total_Spend': total_spend,
        'Total_Orders': total_orders,
        'Net_Profit': total_margin, # Pre-fixed costs
        'Blended_ROAS': total_rev / total_spend if total_spend > 0 else 0,
        'Blended_CAC': total_spend / total_orders if total_orders > 0 else 0,
        'Blended_CM_Pct': total_margin / total_rev if total_rev > 0 else 0
    }
    
    return merged_df, channel_metrics, overall

def calculate_ltv(merged_df):
    """
    Simple LTV calculation.
    If Customer_ID exists: LTV = Avg Revenue per Customer * Gross Margin Avg
    """
    if 'Customer_ID' not in merged_df.columns:
        return 0, 0 # Can't calc LTV without Customer ID
        
    # Group by Customer
    cust_group = merged_df.groupby('Customer_ID').agg({
        'Revenue': 'sum',
        'Gross_Profit': 'sum',
        'Order_ID': 'nunique'
    })
    
    avg_customer_revenue = cust_group['Revenue'].mean()
    avg_customer_profit = cust_group['Gross_Profit'].mean()
    avg_orders_per_cust = cust_group['Order_ID'].mean()
    
    return avg_customer_revenue, avg_customer_profit

def calculate_payback(cac, margin_per_order, orders_per_month_per_cust=1):
    """
    Simple Payback Period in Months.
    Payback = CAC / (Margin/Month)
    Margin/Month = Margin/Order * Frequency
    """
    if margin_per_order <= 0: return 999 # Never breaks even
    return cac / margin_per_order
