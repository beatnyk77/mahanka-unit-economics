import sys
import os
import pandas as pd
import numpy as np

# Add parent directory to path to import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import calculations

def test_returns_logic():
    print("🚀 Starting Logic Verification...")
    
    # 1. Generate Sample Data
    data = calculations.generate_sample_data()
    sales = data['Sales']
    inventory = data['Inventory']
    marketing = data['Marketing']
    logistics = data['Logistics']
    
    print(f"Generated {len(sales)} sales records.")
    
    # 2. Force specific test case: Ensure at least one return exists
    # Find a specific Order ID
    test_order_id = sales['Order_ID'].iloc[0]
    
    # Force this order to be a return in logistics
    logistics.loc[logistics['Order_ID'] == test_order_id, 'Is_Return'] = 1
    
    print(f"Forcing Order {test_order_id} to be a RETURN.")
    
    # 3. Process Data
    merged_df, channel_metrics, overall_kpis = calculations.process_data(sales, inventory, marketing, logistics)
    
    # 4. Verify Calculations for Test Order
    test_row = merged_df[merged_df['Order_ID'] == test_order_id].iloc[0]
    
    print("\n🔍 Verifying Test Order (Returned):")
    print(f"  Revenue (Gross): {test_row['Revenue']}")
    print(f"  Net Revenue: {test_row['Net_Revenue']}")
    print(f"  COGS: {test_row['Total_COGS']}")
    print(f"  Fulfillment: {test_row['Fulfillment_Cost']}")
    print(f"  Contribution 1: {test_row['Contribution_Profit_1']}")
    
    # ASSERTIONS
    
    # A. Net Revenue should be 0 for a return
    assert test_row['Net_Revenue'] == 0, f"Error: Net Revenue for return should be 0, got {test_row['Net_Revenue']}"
    
    # B. Stats: Gross > Net (assuming some returns exist in total)
    assert overall_kpis['Gross_Revenue'] > overall_kpis['Net_Revenue'], "Error: Gross Revenue should be greater than Net Revenue"
    
    # C. Sunk Costs Logic: Contribution should be negative (-COGS - Fulfillment)
    expected_contrib = 0 - test_row['Total_COGS'] - test_row['Fulfillment_Cost']
    # Start floats might be tricky, use almost_equal
    assert abs(test_row['Contribution_Profit_1'] - expected_contrib) < 0.01, \
        f"Error: Contribution calculation mismatch. Expected {expected_contrib}, got {test_row['Contribution_Profit_1']}"
        
    print("\n✅ Test Passed: Returns correctly reduce Net Revenue to 0 and treat COGS/Fulfillment as sunk costs.")
    
    # 5. Verify Aggregates
    print("\n📊 Overall Metrics Check:")
    print(f"  Gross Revenue: {overall_kpis['Gross_Revenue']}")
    print(f"  Net Revenue:   {overall_kpis['Net_Revenue']}")
    print(f"  Return Rate:   {overall_kpis['Return_Rate']:.1%}")
    
    if overall_kpis['Return_Rate'] > 0:
        print("✅ Return Rate detected.")
    else:
        print("⚠️ Warning: Return Rate is 0% (unlikely with this sample logic).")

if __name__ == "__main__":
    try:
        test_returns_logic()
        print("\n🎉 ALL TESTS PASSED")
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        sys.exit(1)
