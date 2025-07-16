import json
import pandas as pd
import numpy as np
# from datetime import datetime
from sklearn.preprocessing import MinMaxScaler
import matplotlib.pyplot as plt

# Load raw data
with open("user-wallet-transactions.json") as f:
    data = json.load(f)

# Step 1: Preprocess into DataFrame
df = pd.DataFrame(data)

# Step 1: Clean & prepare data
df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
df['amount'] = df['actionData'].apply(lambda x: float(x.get('amount', 0)) if isinstance(x, dict) else 0)
df['action'] = df['action'].str.lower()

# Step 2: Group by wallet & extract features
features = []

for wallet, group in df.groupby('userWallet'):
    group_sorted = group.sort_values('timestamp')
    time_deltas = group_sorted['timestamp'].diff().dt.total_seconds().dropna()
    
    deposits = group[group['action'] == 'deposit']
    borrows = group[group['action'] == 'borrow']
    repays = group[group['action'] == 'repay']
    redeems = group[group['action'] == 'redeemunderlying']
    liquidations = group[group['action'] == 'liquidationcall']

    total_borrowed = borrows['amount'].sum()
    total_deposited = deposits['amount'].sum()
    total_repaid = repays['amount'].sum()

    repay_ratio = total_repaid / total_borrowed if total_borrowed > 0 else 0
    borrow_to_deposit = total_borrowed / total_deposited if total_deposited > 0 else 0
    entropy = -np.sum((group['action'].value_counts(normalize=True) * 
                      np.log2(group['action'].value_counts(normalize=True) + 1e-9)))

    features.append({
        "wallet": wallet,
        "num_deposits": len(deposits),
        "total_deposited": total_deposited,
        "num_borrows": len(borrows),
        "total_borrowed": total_borrowed,
        "num_repays": len(repays),
        "total_repaid": total_repaid,
        "repay_ratio": repay_ratio,
        "num_liquidations": len(liquidations),
        "borrow_to_deposit_ratio": borrow_to_deposit,
        "num_actions": len(group),
        "avg_time_between_actions": time_deltas.mean() if not time_deltas.empty else 0,
        "distinct_days_active": group['timestamp'].dt.date.nunique(),
        "action_entropy": entropy
    })

features_df = pd.DataFrame(features).fillna(0)

# Step 3: Normalize features and compute weighted scores
scoring_features = features_df.drop(columns=['wallet'])
scaler = MinMaxScaler()
normalized = scaler.fit_transform(scoring_features)

# Define heuristic weights for each feature (same order as DataFrame columns)
weights = np.array([
    0.05,   # num_deposits
    0.10,   # total_deposited
    -0.05,  # num_borrows
    -0.10,  # total_borrowed
    0.15,   # num_repays
    0.15,   # total_repaid
    0.20,   # repay_ratio
    -0.25,  # num_liquidations
    -0.15,  # borrow_to_deposit_ratio
    -0.05,  # num_actions
    0.05,   # avg_time_between_actions
    0.10,   # distinct_days_active
    0.10    # action_entropy
])

# Compute raw score and scale to 0–1000
raw_scores = normalized.dot(weights)
scaled_scores = MinMaxScaler(feature_range=(0, 1000)).fit_transform(raw_scores.reshape(-1, 1)).flatten()
features_df["credit_score"] = scaled_scores.round().astype(int)

# Step 4: Save the final credit scores
output_csv = "wallet_credit_scores.csv"
features_df[["wallet", "credit_score"]].to_csv(output_csv, index=False)

# Step 5: Plot score distribution
bins = list(range(0, 1001, 100))
labels = [f"{bins[i]+1}-{bins[i+1]}" if i != 0 else f"{bins[i]}-{bins[i+1]}" for i in range(len(bins)-1)]

features_df["score_range"] = pd.cut(features_df["credit_score"], bins=bins, labels=labels, right=True, include_lowest=True)

score_distribution = features_df["score_range"].value_counts().sort_index()

print(score_distribution)


plt.figure(figsize=(10, 6))
score_distribution.plot(kind="bar", color="skyblue", edgecolor="black")
plt.title("Wallet Credit Score Distribution")
plt.xlabel("Credit Score Range")
plt.ylabel("Number of Wallets")
plt.xticks(rotation=45)
plt.tight_layout()

# Save the histogram
hist_path = "score_distribution.png"
plt.savefig(hist_path)