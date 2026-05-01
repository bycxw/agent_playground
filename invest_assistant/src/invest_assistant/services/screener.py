"""Stock screener service - wraps zvt factors."""
from typing import List, Dict, Optional
import pandas as pd

from ..data import query_all_financial_metrics


class StockScreener:
    """Stock screener using zvt."""

    def __init__(self, market: str = "A股"):
        self.market = market

    def screen(
        self,
        pe_max: Optional[float] = None,
        pe_min: Optional[float] = None,
        pb_max: Optional[float] = None,
        roe_min: Optional[float] = None,
        revenue_yoy_min: Optional[float] = None,
        net_income_yoy_min: Optional[float] = None,
        gross_margin_min: Optional[float] = None,
        debt_to_asset_max: Optional[float] = None,
        max_results: int = 100,
    ) -> List[Dict]:
        """Screen stocks by multiple criteria.

        All filter parameters are optional. Only specified filters will be applied.
        """
        df = query_all_financial_metrics(market=self.market)

        if df.empty:
            return []

        # Apply filters
        if pe_max is not None:
            df = df[df["pe_ttm"] <= pe_max]

        if pe_min is not None:
            df = df[df["pe_ttm"] >= pe_min]

        if pb_max is not None:
            df = df[df["pb"] <= pb_max]

        if roe_min is not None:
            df = df[df["roe"] >= roe_min]

        if revenue_yoy_min is not None:
            df = df[df["revenue_yoy"] >= revenue_yoy_min]

        if net_income_yoy_min is not None:
            df = df[df["net_income_yoy"] >= net_income_yoy_min]

        if gross_margin_min is not None:
            df = df[df["gross_margin"] >= gross_margin_min]

        if debt_to_asset_max is not None:
            df = df[df["debt_to_asset_ratio"] <= debt_to_asset_max]

        # Sort by ROE descending and limit
        df = df.sort_values("roe", ascending=False).head(max_results)

        # Convert to list of dicts
        results = []
        for _, row in df.iterrows():
            stock = {
                "symbol": row.get("symbol", ""),
                "name": row.get("name", ""),
                "pe_ttm": row.get("pe_ttm"),
                "pb": row.get("pb"),
                "roe": row.get("roe"),
                "revenue_yoy": row.get("revenue_yoy"),
                "net_income_yoy": row.get("net_income_yoy"),
                "gross_margin": row.get("gross_margin"),
                "debt_to_asset_ratio": row.get("debt_to_asset_ratio"),
            }
            results.append(stock)

        return results

    def screen_by_value(
        self,
        pe_max: float = 15,
        pb_max: float = 1.5,
        roe_min: float = 10,
    ) -> List[Dict]:
        """Screen by classic value investing criteria."""
        return self.screen(pe_max=pe_max, pb_max=pb_max, roe_min=roe_min)

    def screen_by_growth(
        self,
        revenue_yoy_min: float = 20,
        net_income_yoy_min: float = 20,
        roe_min: float = 10,
    ) -> List[Dict]:
        """Screen by growth criteria."""
        return self.screen(
            revenue_yoy_min=revenue_yoy_min,
            net_income_yoy_min=net_income_yoy_min,
            roe_min=roe_min,
        )