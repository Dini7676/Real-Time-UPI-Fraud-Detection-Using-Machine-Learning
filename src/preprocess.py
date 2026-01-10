import os
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline

DATA_PATH = os.getenv("DATA_PATH", os.path.join(os.path.dirname(__file__), "..", "dataset", "transactions.csv"))
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "dataset")

EXPECTED_COLUMNS = [
    "transaction_hour",
    "transaction_date",
    "transaction_month",
    "transaction_year",
    "transaction_amount",
    "transaction_category",
    "mobile_number",
    "upi_transaction_id",
    "state",
    "zip_code",
    "location",
    "user_age",
    "merchant_age",
    "fraud_or_not",
]

CATEGORY_TABLE = {
    # Placeholder mapping; ensure it matches dataset PDF categories
    "Groceries": 0,
    "Bills": 1,
    "OnlineShopping": 2,
    "FoodDelivery": 3,
    "Travel": 4,
    "Utilities": 5,
}

STATE_REF = {
    # Minimal sample, extend per dataset PDF
    "KA": "Karnataka",
    "MH": "Maharashtra",
    "DL": "Delhi",
    "TN": "Tamil Nadu",
    "GJ": "Gujarat",
}


def load_dataset(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Dataset not found at {path}. Place 'transactions.csv' in dataset directory.")
    df = pd.read_csv(path)
    return df


def validate_columns(df: pd.DataFrame):
    missing = [c for c in EXPECTED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Dataset missing columns: {missing}")


def preprocess():
    df = load_dataset(DATA_PATH)
    validate_columns(df)

    # Clean and normalize
    df = df.copy()
    df["transaction_amount"] = pd.to_numeric(df["transaction_amount"], errors="coerce").fillna(0)
    df["transaction_hour"] = pd.to_numeric(df["transaction_hour"], errors="coerce").fillna(0).astype(int)
    df["zip_code"] = df["zip_code"].astype(str).str.replace(r"[^0-9]", "", regex=True)
    df["user_age"] = pd.to_numeric(df["user_age"], errors="coerce").fillna(0)
    df["merchant_age"] = pd.to_numeric(df["merchant_age"], errors="coerce").fillna(0)

    # Map state short codes to names if present
    df["state"] = df["state"].map(lambda s: STATE_REF.get(str(s), str(s)))

    # Hash mobile number and transaction id for numeric features (privacy-preserving)
    df["mobile_hash"] = df["mobile_number"].astype(str).apply(lambda x: abs(hash(x)) % 1000000)
    df["txn_hash"] = df["upi_transaction_id"].astype(str).apply(lambda x: abs(hash(x)) % 1000000)

    # Ensure category values are strings
    df["transaction_category"] = df["transaction_category"].astype(str)

    # Build a timestamp for behavior features
    # Fallback safely if month/date invalid
    def _safe_ts(row):
        try:
            return pd.Timestamp(int(row["transaction_year"]), int(row["transaction_month"]), int(row["transaction_date"]), int(row["transaction_hour"]))
        except Exception:
            return pd.NaT

    df["_ts"] = df.apply(_safe_ts, axis=1)
    df.sort_values(["mobile_number", "_ts"], inplace=True)

    # Group-wise rolling/cumulative features by sender mobile
    g = df.groupby("mobile_number", group_keys=False)
    # Total prior transactions
    df["sender_total_txn"] = g.cumcount()
    # Total prior frauds
    df["sender_fraud_txn"] = g["fraud_or_not"].apply(lambda s: s.shift().cumsum().fillna(0))
    # Prior fraud rate
    with pd.option_context('mode.use_inf_as_na', True):
        df["sender_fraud_rate"] = (df["sender_fraud_txn"] / df["sender_total_txn"].replace(0, pd.NA)).fillna(0).clip(0, 1)
    # Rolling average of last 5 amounts (prior only)
    df["sender_recent_amount_avg"] = g["transaction_amount"].apply(lambda s: s.shift().rolling(window=5, min_periods=1).mean()).fillna(0)
    # Time gap to previous txn in hours
    def _gap_hours(series_ts: pd.Series) -> pd.Series:
        prev = series_ts.shift()
        diff = (series_ts - prev).dt.total_seconds() / 3600.0
        return diff.fillna(24.0).clip(lower=0, upper=24*30)
    df["sender_recent_gap_hours"] = g["_ts"].apply(_gap_hours)

    X = df[[
        "transaction_hour",
        "transaction_date",
        "transaction_month",
        "transaction_year",
        "transaction_amount",
        "transaction_category",
        "state",
        "zip_code",
        "location",
        "user_age",
        "merchant_age",
        "mobile_hash",
        "txn_hash",
        # Behavior features
        "sender_total_txn",
        "sender_fraud_txn",
        "sender_fraud_rate",
        "sender_recent_amount_avg",
        "sender_recent_gap_hours",
    ]]

    y = df["fraud_or_not"].astype(int)

    numeric_features = [
        "transaction_hour",
        "transaction_date",
        "transaction_month",
        "transaction_year",
        "transaction_amount",
        "user_age",
        "merchant_age",
        "mobile_hash",
        "txn_hash",
        "sender_total_txn",
        "sender_fraud_txn",
        "sender_fraud_rate",
        "sender_recent_amount_avg",
        "sender_recent_gap_hours",
    ]
    categorical_features = ["transaction_category", "state", "zip_code", "location"]

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), numeric_features),
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), categorical_features),
        ]
    )

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    pipeline = Pipeline(steps=[("preprocessor", preprocessor)])
    X_train_t = pipeline.fit_transform(X_train)
    X_test_t = pipeline.transform(X_test)

    # Ensure dense numpy arrays for saving
    try:
        import scipy.sparse as sp  # type: ignore
        if sp.issparse(X_train_t):
            X_train_t = X_train_t.toarray()
        if sp.issparse(X_test_t):
            X_test_t = X_test_t.toarray()
    except Exception:
        pass

    # Save processed arrays for model training
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    np.save(os.path.join(OUTPUT_DIR, "X_train.npy"), X_train_t)
    np.save(os.path.join(OUTPUT_DIR, "X_test.npy"), X_test_t)
    np.save(os.path.join(OUTPUT_DIR, "y_train.npy"), y_train.to_numpy())
    np.save(os.path.join(OUTPUT_DIR, "y_test.npy"), y_test.to_numpy())

    # Persist preprocessor for inference
    import joblib
    joblib.dump(pipeline, os.path.join(OUTPUT_DIR, "preprocessor.joblib"))

    print("Preprocessing complete. Saved X_train/X_test/y_train/y_test and preprocessor.joblib in dataset/")


if __name__ == "__main__":
    preprocess()
