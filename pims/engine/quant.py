from typing import Optional, List, Dict

class QuantEngine:
    """
    Handles all financial and risk calculations strictly in Python.
    Prevents LLMs from doing math, as specified in the system design.
    """

    @staticmethod
    def calculate_per(price: float, eps: float) -> Optional[float]:
        """
        Price to Earnings Ratio
        """
        if eps <= 0:
            return None
        return round(price / eps, 2)

    @staticmethod
    def calculate_pbr(price: float, bps: float) -> Optional[float]:
        """
        Price to Book Ratio
        """
        if bps <= 0:
            return None
        return round(price / bps, 2)

    @staticmethod
    def calculate_roe(net_income: float, shareholders_equity: float) -> Optional[float]:
        """
        Return on Equity
        """
        if shareholders_equity <= 0:
            return None
        return round((net_income / shareholders_equity) * 100, 2)

    @staticmethod
    def calculate_roic(nopat: float, invested_capital: float) -> Optional[float]:
        """
        Return on Invested Capital
        """
        if invested_capital <= 0:
            return None
        return round((nopat / invested_capital) * 100, 2)

    @staticmethod
    def calculate_fcf(operating_cash_flow: float, capital_expenditures: float) -> float:
        """
        Free Cash Flow
        CapEx is usually expressed as a negative number in financial statements,
        but typically FCF = OCF - CapEx (if CapEx is positive absolute value).
        Here we assume capital_expenditures is passed as an absolute positive value.
        """
        return operating_cash_flow - abs(capital_expenditures)

    @staticmethod
    def calculate_portfolio_weights(positions: Dict[str, float], cash: float) -> Dict[str, float]:
        """
        Calculates the percentage weight of each position in the portfolio.
        positions: Dict of ticker to market_value
        cash: Current cash balance
        """
        total_value = sum(positions.values()) + cash

        if total_value <= 0:
            return {ticker: 0.0 for ticker in positions}

        weights = {ticker: round(value / total_value, 4) for ticker, value in positions.items()}
        weights['CASH'] = round(cash / total_value, 4)

        return weights

    @staticmethod
    def calculate_drawdown(peak_value: float, current_value: float) -> float:
        """
        Calculates the current drawdown percentage from peak.
        Returns a positive percentage (e.g., 10.0 for a 10% drawdown).
        """
        if peak_value <= 0 or current_value >= peak_value:
            return 0.0

        return round(((peak_value - current_value) / peak_value) * 100, 2)
