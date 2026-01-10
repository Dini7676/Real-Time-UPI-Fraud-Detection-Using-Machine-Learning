import os
import pandas as pd
import numpy as np
from datetime import datetime

out_path = os.path.join(os.path.dirname(__file__), "..", "dataset", "transactions.csv")
os.makedirs(os.path.join(os.path.dirname(__file__), "..", "dataset"), exist_ok=True)

np.random.seed(42)
N = 1000
categories = ["Groceries","Bills","OnlineShopping","FoodDelivery","Travel","Utilities"]
states = ["Karnataka","Maharashtra","Delhi","Tamil Nadu","Gujarat"]
locations = ["Bangalore","Mumbai","Delhi","Chennai","Ahmedabad"]

rows = []
for i in range(N):
    d = {
        "transaction_hour": np.random.randint(0,24),
        "transaction_date": np.random.randint(1,28),
        "transaction_month": np.random.randint(1,12),
        "transaction_year": 2025,
        "transaction_amount": round(np.random.exponential(800), 2),
        "transaction_category": np.random.choice(categories),
        "mobile_number": f"9{np.random.randint(100000000,999999999)}",
        "upi_transaction_id": f"TXN{np.random.randint(10000000,99999999)}",
        "state": np.random.choice(states),
        "zip_code": str(np.random.randint(100000,999999)),
        "location": np.random.choice(locations),
        "user_age": np.random.randint(18,65),
        "merchant_age": np.random.randint(1,20),
        "fraud_or_not": np.random.choice([0,1], p=[0.9,0.1]),
    }
    rows.append(d)

pd.DataFrame(rows).to_csv(out_path, index=False)
print(f"Generated sample dataset at {out_path}")
