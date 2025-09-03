import json
import re
import sys
from typing import Tuple

import requests
from bs4 import BeautifulSoup


def get_product_info(url: str) -> Tuple[int, bool]:
    """Fetch product price and stock availability from a Vestel product page.

    Args:
        url: Product URL from vestel.com.tr.

    Returns:
        A tuple of (price_in_try, in_stock). Price is an integer representing
        Turkish Lira. in_stock is True if the product is available.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36"
        )
    }
    resp = requests.get(url, headers=headers, timeout=10)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    script_tag = soup.find("script", type="application/ld+json")
    if script_tag is None:
        raise ValueError("Could not find product JSON-LD script")

    data = json.loads(script_tag.string)
    offers = data.get("offers", {})
    price_raw = offers.get("price", "")
    match = re.search(r"[\d.,]+", price_raw)
    if not match:
        raise ValueError("Price not found in offers data")
    price_numeric = int(match.group(0).replace(".", "").replace(",", ""))

    availability = offers.get("availability", "")
    in_stock = availability.endswith("InStock")

    return price_numeric, in_stock


if __name__ == "__main__":
    urls = sys.argv[1:]
    if not urls:
        print("Usage: python scrape_vestel.py <product_url> [<product_url> ...]")
        sys.exit(1)

    for url in urls:
        try:
            price, in_stock = get_product_info(url)
            print(f"{url}\n  price: {price} TL\n  in_stock: {in_stock}")
        except Exception as exc:
            print(f"Error processing {url}: {exc}")
