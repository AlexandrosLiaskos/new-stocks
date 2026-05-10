"""
Map EODHD exchange codes / country names to our high-level Region enum.

Region is purely for UI filtering. When in doubt we return OTHER rather
than guessing wrong; the user-facing `country` field is always exact.
"""
from __future__ import annotations
from .schema import Region

_EXCHANGE_REGION: dict[str, Region] = {
    # US
    "US": Region.US, "NASDAQ": Region.US, "NYSE": Region.US, "AMEX": Region.US,
    "BATS": Region.US, "OTC": Region.US, "OTCBB": Region.US, "PINK": Region.US,
    "NYSE ARCA": Region.US, "ARCA": Region.US, "NYSE MKT": Region.US,
    # UK
    "LSE": Region.UK, "LON": Region.UK, "AIM": Region.UK,
    # EU
    "XETRA": Region.EU, "F": Region.EU, "FRANKFURT": Region.EU, "DE": Region.EU,
    "PA": Region.EU, "EURONEXT": Region.EU, "AS": Region.EU, "BR": Region.EU,
    "LS": Region.EU, "MI": Region.EU, "MC": Region.EU, "SW": Region.EU,
    "VI": Region.EU, "OL": Region.EU, "ST": Region.EU, "HE": Region.EU,
    "CO": Region.EU, "IC": Region.EU, "IR": Region.EU, "AT": Region.EU,
    "WAR": Region.EU, "BUD": Region.EU, "PR": Region.EU,
    # Asia
    "HK": Region.ASIA, "HKEX": Region.ASIA, "SHG": Region.ASIA, "SHE": Region.ASIA,
    "SS": Region.ASIA, "SZ": Region.ASIA, "TSE": Region.ASIA, "JPX": Region.ASIA,
    "T": Region.ASIA, "KO": Region.ASIA, "KQ": Region.ASIA, "KOSPI": Region.ASIA,
    "TW": Region.ASIA, "TWO": Region.ASIA, "SG": Region.ASIA, "SGX": Region.ASIA,
    "BK": Region.ASIA, "SET": Region.ASIA, "JK": Region.ASIA, "KLSE": Region.ASIA,
    # India
    "NSE": Region.INDIA, "BSE": Region.INDIA, "NS": Region.INDIA, "BO": Region.INDIA,
    # Oceania
    "AU": Region.OCEANIA, "ASX": Region.OCEANIA, "AX": Region.OCEANIA,
    "NZ": Region.OCEANIA, "NZE": Region.OCEANIA,
    # Latam
    "MX": Region.LATAM, "SA": Region.LATAM, "BVMF": Region.LATAM,
    "BUE": Region.LATAM, "SN": Region.LATAM, "LIM": Region.LATAM,
    # Africa / ME
    "JSE": Region.AFRICA, "JO": Region.AFRICA, "EGX": Region.AFRICA,
    "TA": Region.AFRICA, "TASE": Region.AFRICA, "DFM": Region.AFRICA,
    "ADX": Region.AFRICA, "QE": Region.AFRICA, "KSE": Region.AFRICA,
    # Canada
    "TO": Region.US, "V": Region.US, "TSX": Region.US, "TSXV": Region.US,
}


def region_for(exchange_code: str | None, country: str | None = None) -> Region:
    if exchange_code:
        ex = exchange_code.upper().strip()
        if ex in _EXCHANGE_REGION:
            return _EXCHANGE_REGION[ex]
    if country:
        c = country.lower()
        if "united states" in c or c == "usa" or c == "us":
            return Region.US
        if "united kingdom" in c or "britain" in c or c == "uk":
            return Region.UK
        if c in ("india",):
            return Region.INDIA
        if c in ("australia", "new zealand"):
            return Region.OCEANIA
        if c in ("japan", "china", "hong kong", "south korea", "singapore",
                 "taiwan", "thailand", "indonesia", "malaysia", "philippines",
                 "vietnam"):
            return Region.ASIA
        if c in ("canada",):
            return Region.US
    return Region.OTHER
