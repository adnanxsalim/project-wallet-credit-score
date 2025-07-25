import os
import time
import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
import requests
from dotenv import load_dotenv
import json
import uuid

load_dotenv()
ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY")
if not ETHERSCAN_API_KEY:
    raise ValueError("ETHERSCAN_API_KEY not found. Please set it in your .env file.")

ETHERSCAN_API_URL = "https://api.etherscan.io/api"

# A set of cToken symbols we are interested in for filtering token transfers
CTOKEN_SYMBOLS = {"cUSDC", "cDAI", "cWBTC", "cUNI", "cCOMP", "cUSDT", "cSAI", "cZRX", "cETH", "cAAVE", "cBAT", "cCOMP", "cLINK", "cMKR", "cSUSHI", "cYFI"}

# Fetch all relevant transactions from Etherscan
def get_wallet_transactions(wallet_address: str):
    print(f"\n🔍 Fetching data for wallet: {wallet_address}")
    all_wallet_txs = []
    
    # Fetch ERC-20 cToken Supply/Withdraw
    erc20_params = {
        "module": "account",
        "action": "tokentx",
        "address": wallet_address,
        "startblock": 0,
        "endblock": 99999999,
        "sort": "asc",
        "apikey": ETHERSCAN_API_KEY
    }
    
    try:
        response = requests.get(ETHERSCAN_API_URL, params=erc20_params)
        response.raise_for_status() 
        data = response.json()

        if data["status"] == "1":
            for tx in data["result"]:
                # Filter for cToken transfers we are interested in
                if tx.get("tokenSymbol") in CTOKEN_SYMBOLS:
                    tx["etherscan_tx_type"] = "erc20_token_transfer" 
                    tx["queried_wallet_address"] = wallet_address
                    all_wallet_txs.append(tx)
        elif data["message"] != "No transactions found":
            print(f"  -> Error fetching ERC-20 data for {wallet_address}: {data.get('message', 'Unknown error')}")

    except requests.exceptions.RequestException as e:
        print(f"  -> Error fetching ERC-20 data for {wallet_address}: {e}")

    # Etherscan rate limit workaround
    time.sleep(0.25)

    # Fetch Normal Transactions like Borrow, Repay, Liquidate, etc
    normal_tx_params = {
        "module": "account",
        "action": "txlist",
        "address": wallet_address,
        "startblock": 0,
        "endblock": 99999999,
        "sort": "asc",
        "apikey": ETHERSCAN_API_KEY
    }

    try:
        response = requests.get(ETHERSCAN_API_URL, params=normal_tx_params)
        response.raise_for_status()
        data = response.json()

        if data["status"] == "1":
            for tx in data["result"]:
                if tx.get("functionName"):
                    tx["etherscan_tx_type"] = "normal_transaction_contract_call"
                    tx["queried_wallet_address"] = wallet_address
                    all_wallet_txs.append(tx)
        elif data["message"] != "No transactions found":
            print(f"  -> Error fetching Normal TX data for {wallet_address}: {data.get('message', 'Unknown error')}")

    except requests.exceptions.RequestException as e:
        print(f"  -> Error fetching Normal TX data for {wallet_address}: {e}")

    # Remove duplicates using transaction hash as a unique identifier
    unique_transactions = {tx["hash"]: tx for tx in all_wallet_txs}.values()

    return list(unique_transactions)

# Getting transaction data ready for transforming
def get_action_type(tx, queried_wallet_address):
    func_name = tx.get("functionName", "").lower()
    tx_from = tx.get("from", "").lower()
    tx_to = tx.get("to", "").lower()
    contract_address = tx.get("contractAddress", "").lower()
    input_data = tx.get("input", "").lower()

    queried_wallet_address_lower = queried_wallet_address.lower()

    if tx.get("etherscan_tx_type") == "erc20_token_transfer":
        if tx_to == queried_wallet_address_lower:
            if "mint" in func_name or "supply" in func_name: 
                return "deposit"
            else:
                return "cToken_transfer_in"
        elif tx_from == queried_wallet_address_lower:
            if "redeem" in func_name or "withdraw" in func_name:
                return "withdraw"
            else:
                return "cToken_transfer_out"
    
    elif tx.get("etherscan_tx_type") == "normal_transaction_contract_call":
        if "borrow" in func_name:
            return "borrow"
        elif "repay" in func_name:
            return "repay"
        elif "liquidate" in func_name:
            return "liquidate"
        elif "mint" in func_name:
            return "deposit"
        elif "redeem" in func_name:
            return "withdraw"
        return "contract_interaction"

    return "other"

# Transform transactions for better processing
def transform_transaction(tx: dict, queried_wallet_address: str) -> dict:
    action = get_action_type(tx, queried_wallet_address)
    
    value_wei = int(tx.get("value", "0"))
    token_decimal = int(tx.get("tokenDecimal", "0")) if tx.get("tokenDecimal") else 0
    if tx.get("etherscan_tx_type") == "normal_transaction_contract_call" and not token_decimal:
        normalized_amount = str(float(value_wei) / (10**18))
    else:
        normalized_amount = str(float(value_wei) / (10**token_decimal) if token_decimal else float(value_wei))

    asset_symbol = tx.get("tokenSymbol")
    if not asset_symbol:
        if tx.get("etherscan_tx_type") == "normal_transaction_contract_call":
            asset_symbol = "ETH" # Placeholder, actual asset needs deeper parsing
        else:
            asset_symbol = "UNKNOWN"

    transformed_tx = {
        "_id": {"$oid": uuid.uuid4().hex},
        "userWallet": queried_wallet_address.lower(),
        "network": "ethereum",
        "protocol": "compound",
        "txHash": tx.get("hash", ""),
        "logId": f"{tx.get('hash', '')}_{action}",
        "timestamp": int(tx.get("timeStamp", 0)),
        "blockNumber": int(tx.get("blockNumber", 0)),
        "action": action,
        "actionData": {
            "type": action,
            "amount": normalized_amount,
            "assetSymbol": asset_symbol,
            "assetPriceUSD": None, # Cannot fetch with current tools; placeholder
            "poolId": tx.get("contractAddress", tx.get("to", ""))
        }
    }
    
    if transformed_tx["actionData"]["poolId"] == queried_wallet_address.lower():
        transformed_tx["actionData"]["userId"] = transformed_tx["actionData"]["poolId"]
    else:
        transformed_tx["actionData"]["userId"] = queried_wallet_address.lower()

    return transformed_tx

# Main execution block to fetch and transform transactions
if __name__ == "__main__":
    try:
        wallets_df = pd.read_csv("wallet_id.csv")
        wallet_addresses = wallets_df.iloc[:, 0].tolist()
        print(f"Loaded {len(wallet_addresses)} addresses from wallet_id.csv")

        all_transformed_transactions = []
        for address in wallet_addresses:
            if not address.startswith("0x") or len(address) != 42:
                print(f"\n⚠️ Skipping invalid address format: {address}")
                continue
            
            # Fetch raw transactions for the wallet
            raw_user_txs = get_wallet_transactions(address) 
            
            if raw_user_txs:
                print(f"  -> Transforming {len(raw_user_txs)} raw transaction(s)")
                # Transform each raw transaction and add to the final list
                for raw_tx in raw_user_txs:
                    transformed_tx = transform_transaction(raw_tx, address)
                    all_transformed_transactions.append(transformed_tx)
            
            # Etherscan rate limit workaround
            time.sleep(0.5) 

        if all_transformed_transactions:
            # Save the transformed transactions to a JSON file
            json_filename = "transformed_wallet_transactions.json"
            with open(json_filename, "w") as f:
                json.dump(all_transformed_transactions, f, indent=2)
            print(f"\n✅ Transformed transaction details saved to {json_filename}")
        else:
            print("\n\n--- No relevant transactions found for the given wallets. ---")

        with open("transformed_wallet_transactions.json") as f:
            transactions = json.load(f)

        print(f"\n✅ Transformed transaction details saved to {json_filename}")

        df = pd.DataFrame(transactions)

        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
        df['amount'] = df['actionData'].apply(lambda x: float(x.get('amount', 0)) if isinstance(x, dict) else 0)
        df['action'] = df['action'].str.lower()

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

        print(f"\n✅ Feature extraction completed for {len(features)} wallets.")

        features_df = pd.DataFrame(features).fillna(0)

        scoring_features = features_df.drop(columns=['wallet'])
        scaler = MinMaxScaler()
        normalized = scaler.fit_transform(scoring_features)

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

        raw_scores = normalized.dot(weights)
        scaled_scores = MinMaxScaler(feature_range=(0, 1000)).fit_transform(raw_scores.reshape(-1, 1)).flatten()
        features_df["credit_score"] = scaled_scores.round().astype(int)

        print(f"\n✅ Normalization and Scaling completed.")

        output_csv = "wallet_credit_scores.csv"
        features_df[["wallet", "credit_score"]].to_csv(output_csv, index=False)

        print(f"\n✅ Wallet credit score details saved to {output_csv}")

    except FileNotFoundError:
        print("Error: 'wallet_id.csv' not found. Make sure it's in the same directory.")
    except Exception as e:
        print(f"An error occurred: {e}")