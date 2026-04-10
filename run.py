"""
Foxyz — Quick Launch
Chạy bằng lệnh: python3 run.py
"""
import asyncio
from foxyz.async_api import AsyncFoxyz

async def main():
    print("Đang mở Foxyz Browser...")
    async with AsyncFoxyz(headless=False, window=(1280, 800)) as browser:
        page = await browser.new_page()
        await page.goto("https://pixelscan.net/fingerprint-check")
        print("Browser đang mở. Đóng cửa sổ browser để thoát.")
        # Giữ browser mở cho đến khi user đóng
        try:
            await asyncio.Event().wait()
        except (KeyboardInterrupt, asyncio.CancelledError):
            pass

asyncio.run(main())
