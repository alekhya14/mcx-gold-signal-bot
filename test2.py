inr_per_oz = 417948
mcx_approx = round((inr_per_oz / 31.1035) * 10 * 1.0522, -1)
print(f"Corrected price: ₹{mcx_approx:,.0f}")
print(f"Actual MCX     : ₹1,41,450")
print(f"Difference     : ₹{141450 - mcx_approx:,.0f}")