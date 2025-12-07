from __future__ import annotations

import re
import aiohttp
from bs4 import BeautifulSoup


async def read_html(url: str) -> str:
    """Fetch a page and extract visible text content with indentation."""
    # Validate URL format
    regex_url = r"^https?:\/\/[^\s/$?.#].[^\s]*$"
    if not re.match(regex_url, url, re.IGNORECASE):
        raise ValueError("Invalid URL format.")

    print(f"Reading HTML from URL: {url}")
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            response.raise_for_status()
            original_content = await response.text()

    print(original_content)
    soup = BeautifulSoup(original_content, "html.parser")

    def recursively_get_text(node) -> list[list]:
        """Recursively extract text from node with depth tracking."""
        print(node.get_text())
        res = []
        nwtext = ""

        for child in node.children if hasattr(node, "children") else []:
            # Check if element is visible
            if hasattr(child, "name") and child.name:
                style = child.attrs.get("style", "").lower() if hasattr(child, "attrs") else ""
                if "display:none" in style or "visibility:hidden" in style:
                    continue

            # Handle text nodes
            if isinstance(child, str):
                text = child.strip()
                if text:
                    nwtext += text
            elif hasattr(child, "name") and child.name == "br":
                if nwtext:
                    nwtext += "\r\n"
            else:
                # Push current text and recurse
                if nwtext:
                    res.append([0, nwtext])
                    nwtext = ""
                child_res = recursively_get_text(child)
                for item in child_res:
                    item[0] += 1
                    res.append(item)

        if nwtext:
            res.append([0, nwtext])
            nwtext = ""

        # Normalize indentation
        max_indent = float("inf")
        for item in res:
            if isinstance(item[0], int):
                max_indent = min(max_indent, item[0])
        if max_indent != float("inf"):
            for item in res:
                item[0] -= max_indent
        return res

    text_content_arr = recursively_get_text(soup)
    final_text = ""
    for indent, text in text_content_arr:
        final_text += " " * (indent * 2) + text + "\n"

    return final_text
