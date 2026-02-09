from __future__ import annotations

import os
import random
from typing import Any

import requests
from bs4 import BeautifulSoup
from mcp.server.fastmcp import FastMCP

FUTUREPEDIA_SEARCH_API_URL = "https://www.futurepedia.io/api/search"
BASE_TOOL_URL = "https://www.futurepedia.io/tool/"

mcp = FastMCP("futurepedia-crawler")


def _session() -> requests.Session:
    s = requests.Session()
    proxy = os.getenv("PROXY_URL", "").strip()
    if proxy:
        s.proxies.update({"http": proxy, "https": proxy})
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (compatible; futurepedia-mcp/0.1)",
        "Accept": "application/json,text/html;q=0.9,*/*;q=0.8",
    })
    return s


def _fetch_random_meta(s: requests.Session) -> dict[str, str]:
    payload = {"query": "", "page": 1, "sort": "new"}
    r = s.post(FUTUREPEDIA_SEARCH_API_URL, json=payload, timeout=20)
    r.raise_for_status()
    data = r.json()
    items = data.get("data") or []
    if not items:
        raise RuntimeError("Futurepedia search returned no items")

    # Keep it simple and fast: random item from first page.
    tool = random.choice(items)

    slug_field = tool.get("slug")
    slug = ""
    if isinstance(slug_field, dict):
        slug = (slug_field.get("current") or "").strip()
    elif isinstance(slug_field, str):
        slug = slug_field.strip()

    if not slug:
        raise RuntimeError("Futurepedia item missing slug")

    return {
        "slug": slug,
        "name": (tool.get("toolName") or "").strip(),
        "short_description": (tool.get("toolShortDescription") or "").strip(),
        "website_url": (tool.get("websiteUrl") or "").strip(),
    }


def _extract_text(soup: BeautifulSoup, selector: str) -> str:
    el = soup.select_one(selector)
    return el.get_text(" ", strip=True) if el else ""


def _extract_meta(soup: BeautifulSoup, key: str, by: str = "property") -> str:
    el = soup.find("meta", attrs={by: key})
    if el and el.get("content"):
        return el["content"].strip()
    return ""


def _extract_section_list(soup: BeautifulSoup, title: str) -> list[str]:
    needle = title.strip().lower()
    for h in soup.find_all(["h2", "h3", "h4"]):
        htxt = h.get_text(" ", strip=True).lower()
        if not htxt.startswith(needle):
            continue
        for sib in h.find_next_siblings():
            if getattr(sib, "name", None) in {"h2", "h3", "h4"}:
                return []
            if getattr(sib, "name", None) in {"ul", "ol"}:
                return [
                    li.get_text(" ", strip=True)
                    for li in sib.find_all("li")
                    if li.get_text(" ", strip=True)
                ]
    return []


def _extract_section_text(soup: BeautifulSoup, title: str) -> str:
    needle = title.strip().lower()
    for h in soup.find_all(["h2", "h3", "h4"]):
        htxt = h.get_text(" ", strip=True).lower()
        if not htxt.startswith(needle):
            continue
        parts: list[str] = []
        for sib in h.find_next_siblings():
            if getattr(sib, "name", None) in {"h2", "h3", "h4"}:
                break
            if getattr(sib, "name", None) == "p":
                txt = sib.get_text(" ", strip=True)
                if txt:
                    parts.append(txt)
            if getattr(sib, "name", None) in {"ul", "ol"}:
                items = [li.get_text(" ", strip=True) for li in sib.find_all("li")]
                items = [i for i in items if i]
                if items:
                    parts.append("; ".join(items))
        return " ".join(parts).strip()
    return ""


def _extract_what_is(soup: BeautifulSoup) -> str:
    for h in soup.find_all(["h2", "h3", "h4"]):
        t = h.get_text(" ", strip=True)
        if not t.lower().startswith("what is"):
            continue
        parts: list[str] = []
        for sib in h.find_next_siblings():
            if getattr(sib, "name", None) in {"h2", "h3", "h4"}:
                break
            if getattr(sib, "name", None) == "p":
                txt = sib.get_text(" ", strip=True)
                if txt:
                    parts.append(txt)
        return " ".join(parts).strip()
    return ""


def _parse_tool_page(html: str, fallback: dict[str, str], url: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")

    name = _extract_text(soup, "h1") or _extract_meta(soup, "og:title") or fallback.get("name", "")
    description = (
        _extract_meta(soup, "og:description")
        or _extract_meta(soup, "description", by="name")
        or fallback.get("short_description", "")
    )
    if not description:
        raise RuntimeError("Tool page has no description")

    return {
        "name": name,
        "description": description,
        "url": url,
        "website_url": fallback.get("website_url", ""),
        "what_is": _extract_what_is(soup),
        "key_features": _extract_section_list(soup, "Key Features"),
        "pros": _extract_section_list(soup, "Pros"),
        "cons": _extract_section_list(soup, "Cons"),
        "who_uses": _extract_section_text(soup, "Who is Using"),
        "og_image": _extract_meta(soup, "og:image"),
    }


def _fetch_one() -> dict[str, Any]:
    s = _session()
    meta = _fetch_random_meta(s)
    url = f"{BASE_TOOL_URL}{meta['slug']}"

    r = s.get(url, timeout=20)
    r.raise_for_status()
    return _parse_tool_page(r.text, meta, url)


@mcp.tool()
def futurepedia_random_tool() -> dict[str, Any]:
    """Fetch one random Futurepedia tool with structured fields."""
    return _fetch_one()


@mcp.tool()
def futurepedia_tools(count: int = 3) -> list[dict[str, Any]]:
    """Fetch several random Futurepedia tools (1..10)."""
    count = max(1, min(10, int(count)))
    return [_fetch_one() for _ in range(count)]


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
