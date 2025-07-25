# Compound V2 Wallet Credit Scoring

## Overview

This project aims to generate credit scores for Ethereum wallet addresses based on their on-chain activity, particularly focusing on interactions with Compound Finance protocol cTokens and related transactions. The credit score is designed to provide a risk assessment metric for wallets by analyzing their borrowing, repayment, and token transfer behaviors on the Ethereum blockchain.

## Data Collection Method

- **Source:** Ethereum blockchain data accessed via the [Etherscan API](https://etherscan.io/apis).
- **Data Types Collected:**
  - **ERC-20 Token Transfers:** Specifically filtered for cTokens (Compound protocol tokens) such as cUSDC, cDAI, cWBTC, cUNI, and others.
  - **Normal Transactions:** Contract calls involving functions like borrow, repay, liquidate, mint, redeem, etc.
- **Process:**
  - For each wallet address, the system fetches all ERC-20 token transfer events and normal transactions from Etherscan.
  - Transactions are filtered and labeled by type (e.g., deposit, withdraw, borrow, repay, liquidate).
  - Duplicate transactions are removed based on transaction hashes.
- **Rate Limiting:** The system respects Etherscan API rate limits by introducing delays between requests.

## Feature Selection Rationale

The features used to compute wallet credit scores are derived from transaction behaviors that reflect financial activity and risk on the Compound protocol:

- **Deposits and Withdrawals:** Indicate the wallet’s engagement with supplying collateral or withdrawing it.
- **Borrowing and Repayment:** Core indicators of credit usage and repayment behavior.
- **Liquidations:** Critical risk signals indicating failure to maintain collateralization.
- **Token Transfer Patterns:** Transfers of cTokens in and out can indicate collateral movements or other financial maneuvers.
- **Transaction Counts and Frequencies:** Reflect activity levels and possibly risk exposure.
- **Normalized Features:** MinMaxScaler is used to scale features to a comparable range, ensuring balanced contribution to the score.

These features collectively capture both positive behaviors (e.g., timely repayments, consistent deposits) and negative signals (e.g., liquidations, defaults).

## Scoring Method

- **Data Preparation:** Raw transaction data is aggregated per wallet to compute feature vectors representing their on-chain financial behavior.
- **Normalization:** Features are scaled using MinMaxScaler to normalize across different metrics.
- **Score Calculation:** A weighted scoring algorithm combines normalized features to produce a credit score between 0 and 1000.
  - Positive indicators (e.g., repayments, deposits) increase the score.
  - Negative indicators (e.g., liquidations, failed repayments) reduce the score.
- **Output:** The final credit score is stored alongside the wallet address in a CSV file (`wallet_credit_scores.csv`).

## Justification of Risk Indicators Used

- **Borrowing Behavior:** Frequent or large borrowings without corresponding repayments may indicate higher risk.
- **Repayment History:** Timely repayments reduce risk and increase creditworthiness.
- **Liquidations:** Occurrence of liquidations is a strong negative risk indicator, signaling inability to maintain collateral.
- **Collateral Movements:** Deposits and withdrawals of cTokens show engagement and liquidity management.
- **Token Transfer Types:** Differentiating between transfers in/out and deposits/withdrawals helps identify the intent and risk profile.
- **Transaction Volume and Diversity:** High activity can indicate sophistication or risk-taking behavior.

By combining these indicators, the model aims to reflect real-world credit risk dynamics adapted to decentralized finance (DeFi) on Ethereum.

## Usage

1. **Setup:**
    - Rename the `.env.example` file to `.env` and add your Etherscan API key:

    ```bash
    ETHERSCAN_API_KEY="your_api_key_here"
    ```

2. **Run the script:**
   - Use `wallet-score.py` to fetch transactions and compute scores for a list of wallet addresses.
3. **Results:**
   - The JSON output (`transformed_wallet_transactions.json`) contains raw but transformed wallet data, fetched using the Etherscan API. This file is then used as input data for scoring the wallets.
   - The output CSV (`wallet_credit_scores.csv`) contains wallet addresses and their computed credit scores.

## Dependencies

- Python 3.x
- pandas
- numpy
- scikit-learn
- requests
- python-dotenv

Install dependencies via:

```bash
pip install pandas numpy scikit-learn requests python-dotenv
```

## Notes

- The scoring model is heuristic and based on on-chain data only; it does not incorporate off-chain credit information.
- API rate limits and data completeness depend on Etherscan’s service availability.
- The model can be extended with more sophisticated machine learning techniques and additional data sources.
