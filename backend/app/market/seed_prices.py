"""
Seed prices and GBM parameters for the market simulator.

Contains:
- SEED_PRICES: realistic starting prices for the default watchlist
- TICKER_PARAMS: per-ticker volatility (sigma) and drift (mu) for GBM
- DEFAULT_PARAMS: fallback parameters for dynamically added tickers
- CORRELATION_GROUPS: sector groupings for the Cholesky correlation matrix
- Correlation constants: INTRA_TECH_CORR, INTRA_FINANCE_CORR, CROSS_GROUP_CORR, TSLA_CORR
"""

from __future__ import annotations

# Realistic starting prices for the default watchlist (10 tickers)
# and extended set (~40 more popular tickers)
SEED_PRICES: dict[str, float] = {
    # Default watchlist
    "AAPL": 190.00,
    "GOOGL": 175.00,
    "MSFT": 420.00,
    "AMZN": 185.00,
    "TSLA": 250.00,
    "NVDA": 800.00,
    "META": 500.00,
    "JPM": 195.00,
    "V": 280.00,
    "NFLX": 600.00,
    # Extended tech
    "AVGO": 320.00,
    "AMD": 200.00,
    "CRM": 195.00,
    "ADBE": 262.00,
    "ORCL": 145.00,
    "INTC": 46.00,
    "CSCO": 79.00,
    "PLTR": 137.00,
    "SHOP": 121.00,
    "SNAP": 5.20,
    "UBER": 75.00,
    # Extended finance
    "GS": 860.00,
    "MS": 167.00,
    "BAC": 50.00,
    "WFC": 81.00,
    "PYPL": 46.00,
    "COIN": 176.00,
    "SOFI": 18.00,
    # Healthcare
    "JNJ": 248.00,
    "PFE": 28.00,
    "MRK": 124.00,
    "ABBV": 232.00,
    "LLY": 1052.00,
    "UNH": 293.00,
    "AMGN": 310.00,
    # Consumer
    "DIS": 106.00,
    "NKE": 62.00,
    "MCD": 341.00,
    "KO": 82.00,
    "PEP": 170.00,
    "COST": 1011.00,
    "WMT": 128.00,
    "HD": 381.00,
    "T": 28.00,
    # Energy
    "XOM": 153.00,
    "CVX": 187.00,
    # Industrial
    "BA": 228.00,
    "CAT": 743.00,
    "DE": 630.00,
}

# Per-ticker GBM parameters:
#   sigma: annualized volatility (controls how much price moves)
#   mu: annualized drift / expected return
TICKER_PARAMS: dict[str, dict[str, float]] = {
    # Default watchlist
    "AAPL":  {"sigma": 0.22, "mu": 0.05},
    "GOOGL": {"sigma": 0.25, "mu": 0.05},
    "MSFT":  {"sigma": 0.20, "mu": 0.05},
    "AMZN":  {"sigma": 0.28, "mu": 0.05},
    "TSLA":  {"sigma": 0.50, "mu": 0.03},  # High volatility
    "NVDA":  {"sigma": 0.40, "mu": 0.08},  # High volatility, strong drift
    "META":  {"sigma": 0.30, "mu": 0.05},
    "JPM":   {"sigma": 0.18, "mu": 0.04},  # Low volatility (bank)
    "V":     {"sigma": 0.17, "mu": 0.04},  # Low volatility (payments)
    "NFLX":  {"sigma": 0.35, "mu": 0.05},
    # Extended tech
    "AVGO":  {"sigma": 0.35, "mu": 0.08},
    "AMD":   {"sigma": 0.45, "mu": 0.08},
    "CRM":   {"sigma": 0.32, "mu": 0.05},
    "ADBE":  {"sigma": 0.30, "mu": 0.05},
    "ORCL":  {"sigma": 0.28, "mu": 0.04},
    "INTC":  {"sigma": 0.40, "mu": 0.02},
    "CSCO":  {"sigma": 0.22, "mu": 0.03},
    "PLTR":  {"sigma": 0.60, "mu": 0.06},
    "SHOP":  {"sigma": 0.50, "mu": 0.05},
    "SNAP":  {"sigma": 0.65, "mu": 0.02},
    "UBER":  {"sigma": 0.40, "mu": 0.05},
    # Extended finance
    "GS":    {"sigma": 0.25, "mu": 0.04},
    "MS":    {"sigma": 0.25, "mu": 0.04},
    "BAC":   {"sigma": 0.25, "mu": 0.03},
    "WFC":   {"sigma": 0.24, "mu": 0.03},
    "PYPL":  {"sigma": 0.38, "mu": 0.04},
    "COIN":  {"sigma": 0.65, "mu": 0.05},
    "SOFI":  {"sigma": 0.55, "mu": 0.04},
    # Healthcare
    "JNJ":   {"sigma": 0.18, "mu": 0.03},
    "PFE":   {"sigma": 0.28, "mu": 0.02},
    "MRK":   {"sigma": 0.22, "mu": 0.03},
    "ABBV":  {"sigma": 0.22, "mu": 0.04},
    "LLY":   {"sigma": 0.30, "mu": 0.06},
    "UNH":   {"sigma": 0.22, "mu": 0.04},
    "AMGN":  {"sigma": 0.22, "mu": 0.03},
    # Consumer
    "DIS":   {"sigma": 0.30, "mu": 0.03},
    "NKE":   {"sigma": 0.28, "mu": 0.03},
    "MCD":   {"sigma": 0.18, "mu": 0.04},
    "KO":    {"sigma": 0.15, "mu": 0.03},
    "PEP":   {"sigma": 0.16, "mu": 0.03},
    "COST":  {"sigma": 0.22, "mu": 0.05},
    "WMT":   {"sigma": 0.18, "mu": 0.04},
    "HD":    {"sigma": 0.22, "mu": 0.04},
    "T":     {"sigma": 0.20, "mu": 0.02},
    # Energy
    "XOM":   {"sigma": 0.25, "mu": 0.03},
    "CVX":   {"sigma": 0.24, "mu": 0.03},
    # Industrial
    "BA":    {"sigma": 0.35, "mu": 0.02},
    "CAT":   {"sigma": 0.25, "mu": 0.04},
    "DE":    {"sigma": 0.25, "mu": 0.04},
}

# Default parameters for tickers not in the list above (dynamically added)
DEFAULT_PARAMS: dict[str, float] = {"sigma": 0.25, "mu": 0.05}

# Sector groupings for the Cholesky correlation matrix
# Tickers within the same group tend to move together
CORRELATION_GROUPS: dict[str, set[str]] = {
    "tech": {
        "AAPL", "GOOGL", "MSFT", "AMZN", "META", "NVDA", "NFLX",
        "AVGO", "AMD", "CRM", "ADBE", "ORCL", "INTC", "CSCO",
        "PLTR", "SHOP", "SNAP", "UBER",
    },
    "finance": {
        "JPM", "V", "GS", "MS", "BAC", "WFC", "PYPL", "COIN", "SOFI",
    },
    "healthcare": {
        "JNJ", "PFE", "MRK", "ABBV", "LLY", "UNH", "AMGN",
    },
    "consumer": {
        "DIS", "NKE", "MCD", "KO", "PEP", "COST", "WMT", "HD", "T", "NFLX",
    },
    "energy": {
        "XOM", "CVX",
    },
    "industrial": {
        "BA", "CAT", "DE",
    },
}

# Correlation coefficients
INTRA_TECH_CORR: float = 0.6      # Tech stocks move together
INTRA_FINANCE_CORR: float = 0.5   # Finance stocks move together
INTRA_HEALTH_CORR: float = 0.4    # Healthcare stocks
INTRA_CONSUMER_CORR: float = 0.4  # Consumer stocks
INTRA_ENERGY_CORR: float = 0.6    # Energy stocks
INTRA_INDUSTRIAL_CORR: float = 0.5  # Industrial stocks
CROSS_GROUP_CORR: float = 0.3     # Between sectors / unknown tickers
TSLA_CORR: float = 0.3            # TSLA does its own thing

# Map from sector name to intra-sector correlation
SECTOR_INTRA_CORR: dict[str, float] = {
    "tech": INTRA_TECH_CORR,
    "finance": INTRA_FINANCE_CORR,
    "healthcare": INTRA_HEALTH_CORR,
    "consumer": INTRA_CONSUMER_CORR,
    "energy": INTRA_ENERGY_CORR,
    "industrial": INTRA_INDUSTRIAL_CORR,
}

# Default watchlist — the 10 tickers seeded in the database
DEFAULT_WATCHLIST: list[str] = [
    "AAPL", "GOOGL", "MSFT", "AMZN", "TSLA",
    "NVDA", "META", "JPM", "V", "NFLX",
]
