# Project: Aave V2 Wallet Credit Scoring

This project assigns a credit score between 0 and 1000 to each wallet that interacted with the Aave V2 protocol, using only on-chain transaction behavior.

## Objective

Using a sample of raw transaction-level data from Aave V2, I:

- Engineer meaningful behavioral features for each wallet
- Normalize these features
- Score wallets using a heuristic-based approach
- Output scores and analyze behavior patterns

## Methodology

I used heuristic scoring based on engineered behavioral features. Each wallet is scored between 0 and 1000 based on how reliably and responsibly it interacted with Aave V2.

## Architecture

Raw JSON --> Feature Extraction --> Normalization --> Heuristic Weighting --> Scaled Score --> Output CSV + Histogram

## Project Structure

```bash
project-wallet-credit-score/
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
# requirements.txt
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

These are engineered by grouping the transaction data per wallet and calculating metrics that indicate responsible DeFi behavior.

### Scoring Model

I normalized all features using `MinMaxScaler` and apply a weighted sum based on domain intuition:

- Positive weights: repay ratio, diversity, consistency, deposit size
- Negative weights: liquidations, excessive borrowing, bot-like behavior

The raw score is scaled to a range of 0–1000.

## Processing Flow

1. **Load & Parse**: Read the raw transaction JSON file, convert timestamps, and extract the action and amount fields.
2. **Group by Wallet**: Aggregate transactions by `userWallet` to compute wallet-level features.
3. **Feature Engineering**: Extract behavioral metrics such as number of deposits, borrowing behavior, liquidations, action diversity, etc.
4. **Normalize Features**: Apply MinMaxScaler to ensure features are on the same scale.
5. **Score Computation**: Multiply normalized features by defined weights and scale to range [0, 1000].
6. **Export Results**: Save credit scores as a CSV and generate a score distribution plot.

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
