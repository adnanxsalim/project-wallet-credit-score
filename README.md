# Project: Aave V2 Wallet Credit Scoring

This project assigns a credit score between 0 and 1000 to each wallet that interacted with the Aave V2 protocol, using only on-chain transaction behavior.

## Objective

Using a sample of raw transaction-level data from Aave V2, we:

- Engineer meaningful behavioral features for each wallet
- Normalize these features
- Score wallets using a heuristic-based approach
- Output scores and analyze behavior patterns

## Architecture

Raw JSON --> Feature Extraction --> Scoring --> Output CSV + Score Graph

## Project Structure

```bash
aave-credit-scoring/
|
├── user-wallet-transactions.json        # Raw input
|
├── wallet-score.py                      # Main script to process, score, and analyze wallets
|
├── wallet_credit_scores.csv             # CSV of wallet addresses with assigned scores
├── score_distribution.png               # Bar plot of score distribution
|
├── requirements.txt                     # Python dependencies
|
├── README.md                            # Project overview, architecture, and usage
└── analysis.md                          # Insights and score behavior analysis
```

## Requirements

```bash
pandas
numpy
scikit-learn
matplotlib
```

## Features Engineered

- `repay_ratio`: total repaid / total borrowed
- `borrow_to_deposit_ratio`: leverage measure
- `num_liquidations`: penalizes risky users
- `avg_time_between_actions`: irregularity suggests organic use
- `distinct_days_active`: higher = long-term user
- `action_entropy`: measures diversity of actions

## Usage

```bash
# Install dependencies
pip install -r requirements.txt

# Run the credit scoring pipeline
python wallet-score.py
```

## Input/Output

Input: `user-wallet-transactions.json`

Outputs:

- `wallet_credit_scores.csv`
- `score_distribution.png`

## Results

See [`analysis.md`](https://github.com/adnanxsalim/project-wallet-credit-score/blob/main/analysis.md) for full breakdown of:

- Score distribution
- Behavioral patterns in different score bands
