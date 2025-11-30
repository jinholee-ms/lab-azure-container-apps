from langchain.tools import tool
import investpy
from typing import List, Optional, Dict, Any
from datetime import datetime

DATE_FMT = "%d/%m/%Y"


def _format_date(d: str) -> str:
    """Normalize incoming date string to investpy's dd/mm/YYYY format.
    Accepts YYYY-MM-DD, YYYY/MM/DD, dd/mm/YYYY, dd-mm-YYYY.
    """
    d = d.strip()
    # Try multiple parse formats
    for fmt in ["%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%d-%m-%Y"]:
        try:
            return datetime.strptime(d, fmt).strftime(DATE_FMT)
        except ValueError:
            continue
    raise ValueError(f"Unrecognized date format: {d}")


def _validate_date_range(from_date: str, to_date: str) -> tuple[str, str]:
    fd = _format_date(from_date)
    td = _format_date(to_date)
    if datetime.strptime(fd, DATE_FMT) > datetime.strptime(td, DATE_FMT):
        raise ValueError("from_date must be earlier than to_date")
    return fd, td


@tool("stock_history", return_direct=False)
def stock_history(stock: str, country: str, from_date: str, to_date: str) -> str:
    """Retrieve historical daily OHLCV data for a stock.
    Args:
        stock: Ticker symbol (e.g. 'AAPL').
        country: Country where the stock is listed (e.g. 'United States').
        from_date: Start date (YYYY-MM-DD or dd/mm/YYYY).
        to_date: End date (YYYY-MM-DD or dd/mm/YYYY).
    Returns: Head of dataframe as string plus row count.
    """
    fd, td = _validate_date_range(from_date, to_date)
    df = investpy.get_stock_historical_data(stock=stock, country=country, from_date=fd, to_date=td)
    head = df.head().to_string()
    return f"Rows: {len(df)}\n{head}"


@tool("index_history", return_direct=False)
def index_history(index: str, country: str, from_date: str, to_date: str) -> str:
    """Retrieve historical data for a market index.
    Args:
        index: Index name (e.g. 'S&P 500').
        country: Country of the index (e.g. 'United States').
        from_date: Start date.
        to_date: End date.
    Returns: Summary string.
    """
    fd, td = _validate_date_range(from_date, to_date)
    df = investpy.get_index_historical_data(index=index, country=country, from_date=fd, to_date=td)
    return f"Rows: {len(df)}\n{df.head().to_string()}"


@tool("search_assets", return_direct=False)
def search_assets(query: str, products: Optional[List[str]] = None) -> str:
    """Search across multiple asset classes (stocks, etfs, funds, indices, currency_crosses, cryptos).
    Args:
        query: Free-text search term.
        products: List of product types to include. Default selects all.
    Returns: Aggregated matches as string tables.
    """
    if not products:
        products = ["stocks", "etfs", "funds", "indices", "currency_crosses", "cryptos"]
    output_parts = []
    for p in products:
        try:
            res = investpy.search_quotes(text=query, products=[p], n_results=5)
            if isinstance(res, list):
                table = "\n".join([str(r) for r in res])
            else:
                table = str(res)
            output_parts.append(f"## {p}\n{table}")
        except Exception as e:  # noqa: BLE001
            output_parts.append(f"## {p}\nError: {e}")
    return "\n\n".join(output_parts)


@tool("stock_overview", return_direct=False)
def stock_overview(stock: str, country: str) -> str:
    """Get recent data and company profile for a stock.
    Args:
        stock: Ticker symbol.
        country: Listing country.
    Returns: Combined overview string.
    """
    try:
        recent = investpy.get_stock_recent_data(stock=stock, country=country)
    except Exception as e:  # noqa: BLE001
        recent = f"Error fetching recent data: {e}"
    try:
        profile = investpy.get_stock_company_profile(stock=stock, country=country)
    except Exception as e:  # noqa: BLE001
        profile = {"error": str(e)}
    if isinstance(recent, str):
        recent_str = recent
    else:
        recent_str = recent.tail(5).to_string()
    profile_str = profile if isinstance(profile, str) else "\n".join(f"{k}: {v}" for k, v in profile.items())
    return f"Recent Data (last 5 rows):\n{recent_str}\n\nProfile:\n{profile_str}"


@tool("economic_calendar", return_direct=False)
def economic_calendar(from_date: str, to_date: str, countries: Optional[List[str]] = None, importance: Optional[List[str]] = None) -> str:
    """Retrieve economic calendar events.
    Args:
        from_date: Start date.
        to_date: End date.
        countries: Optional list of country names to filter.
        importance: Optional list of importance levels (e.g. ['low','medium','high']).
    Returns: First rows summary.
    """
    fd, td = _validate_date_range(from_date, to_date)
    df = investpy.economic_calendar(from_date=fd, to_date=td, countries=countries, importance=importance)
    return f"Rows: {len(df)}\n{df.head().to_string()}"


# Mapping dictionary for dynamic selection
TOOL_MAP: Dict[str, Any] = {
    "stock_history": stock_history,
    "index_history": index_history,
    "search_assets": search_assets,
    "stock_overview": stock_overview,
    "economic_calendar": economic_calendar,
}


__all__ = ["stock_history", "index_history", "search_assets", "stock_overview", "economic_calendar", "TOOL_MAP"]