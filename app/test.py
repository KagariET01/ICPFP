import asyncio

from libs.readHTML import read_html

URL = "http://example.com"


async def main() -> None:
    print(f"Reading HTML from URL: {URL}")
    print(await read_html(URL))


if __name__ == "__main__":
    asyncio.run(main())
