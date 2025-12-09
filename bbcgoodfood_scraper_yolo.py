"""bbcgoodfood_scraper.py

Scrape the ingredients list of the first BBC Good Food search result
for a given search term.

Usage:
    python bbcgoodfood_scraper.py "chicken curry"

Dependencies:
    pip install requests beautifulsoup4

This script is intentionally defensive: it tries multiple heuristics to
locate the ingredients list in the recipe page.
"""
from __future__ import annotations

import argparse
import re
import sys
from typing import List, Optional, Tuple

import requests
from bs4 import BeautifulSoup

BASE = "https://www.bbcgoodfood.com"
HEADERS = {
    "User-Agent": "bbcgoodfood-ingredients-scraper/1.0 (+https://github.com/)"
}


def get_first_recipe_url(query: str, session: Optional[requests.Session] = None) -> Optional[str]:
    """Search BBC Good Food and return the URL of the first recipe result.

    Returns the absolute URL or None if no recipe link was found.
    """
    s = session or requests.Session()
    # Use the public search endpoint which returns results like `/search?q=mushroom+risotto`
    resp = s.get(f"{BASE}/search", params={"q": query}, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    # First, prefer links that are annotated as result links
    def _normalize_and_validate(href: str) -> Optional[str]:
        href = href.split("#")[0].split("?")[0]
        if "/recipes/" not in href:
            return None
        # skip collection or non-recipe paths
        tail = href.split("/recipes/", 1)[1].lstrip('/')
        if not tail:
            return None
        first_seg = tail.split('/', 1)[0]
        if first_seg in ("collection", "tag", "category"):
            return None
        if href.startswith("http://") or href.startswith("https://"):
            return href
        if href.startswith("/"):
            return BASE + href
        return BASE + "/" + href

    for a in soup.find_all("a", href=True):
        if a.get("data-component") == "link":
            valid = _normalize_and_validate(a["href"])
            if valid:
                return valid

    # Fallback: any anchor whose href contains /recipes/
    for a in soup.find_all("a", href=True):
        valid = _normalize_and_validate(a["href"])
        if valid:
            return valid

    return None


def extract_ingredients(html: str) -> List[str]:
    """Extract a list of ingredient lines from a recipe HTML page.

    Uses several fallbacks so it works across variations of the page markup.
    """
    soup = BeautifulSoup(html, "html.parser")

    # 1) Microdata: itemprop="recipeIngredient"
    items = [el.get_text(strip=True) for el in soup.select("[itemprop=recipeIngredient]")]
    if items:
        return items

    # 2) Look for elements with class containing 'ingredient' (common on the site)
    ingredient_nodes = soup.find_all(class_=re.compile(r"ingredient", re.I))
    for node in ingredient_nodes:
        lis = node.find_all("li")
        if lis:
            return [li.get_text(strip=True) for li in lis]

    # 3) Search for ul with class containing 'ingredients'
    uls = soup.find_all("ul", class_=re.compile(r"ingredients", re.I))
    for ul in uls:
        lis = [li.get_text(strip=True) for li in ul.find_all("li")]
        if lis:
            return lis

    # 4) Sometimes ingredients are in divs or p tags inside an 'ingredients' section
    for section in soup.find_all(class_=re.compile(r"ingredients|ingredients-list", re.I)):
        texts = [t.get_text(strip=True) for t in section.find_all(["p", "li"]) if t.get_text(strip=True)]
        if texts:
            return texts

    # 5) Fallback: return reasonable <li> items from the main content, filtered
    main = soup.find("main") or soup
    lis = [li.get_text(strip=True) for li in main.find_all("li") if li.get_text(strip=True)]
    # Filter out long unrelated list items and duplicates, keep order
    out: List[str] = []
    seen = set()
    for t in lis:
        if t in seen:
            continue
        if len(t) > 200:
            continue
        seen.add(t)
        out.append(t)
    return out


def get_ingredients_by_class(url: str, class_selector: str = "ingredients-list list",
                            session: Optional[requests.Session] = None) -> List[str]:
    """Fetch `url` and return list items under `ul` elements matching `class_selector`.

    `class_selector` should be the space-separated class attribute (e.g. "ingredients-list list").
    This constructs a CSS selector like `ul.ingredients-list.list` to find the correct lists.
    """
    s = session or requests.Session()
    resp = s.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    # Build selector from space-separated classes
    selector = "ul." + ".".join(class_selector.split())
    uls = soup.select(selector)
    items: List[str] = []
    for ul in uls:
        for li in ul.find_all("li"):
            text = li.get_text(strip=True)
            if text:
                items.append(text)
    return items


def scrape_first_ingredients(query: str) -> Tuple[str, List[str]]:
    """Return (recipe_url, ingredients_list) for the first recipe matching query."""
    session = requests.Session()
    url = get_first_recipe_url(query, session=session)
    if not url:
        raise RuntimeError(f"No recipe found for query: {query!r}")
    # Use the class-specific extractor for more precise results
    ingredients = get_ingredients_by_class(url, session=session)
    return url, ingredients


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Scrape ingredients from BBC Good Food (first search result)")
    parser.add_argument("query", nargs="+", help="Search term (wrap in quotes if multi-word)")
    args = parser.parse_args(argv)
    q = " ".join(args.query)
    try:
        url, ingredients = scrape_first_ingredients(q)
    except Exception as exc:
        print("Error:", exc, file=sys.stderr)
        return 2

    print("Recipe URL:", url)
    print("\nIngredients:")
    if not ingredients:
        print("(No ingredients found)")
    else:
        for ing in ingredients:
            print("-", ing)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
