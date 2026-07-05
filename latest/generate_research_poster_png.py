from __future__ import annotations

import base64
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options


BASE = Path(r"C:\Users\mohdw\OneDrive\Desktop\geo\Latest")
HTML = BASE / "research_poster.html"
OUT = BASE / "research_poster.png"


def main() -> None:
    if not HTML.exists():
        raise FileNotFoundError(f"Missing poster HTML: {HTML}")

    opts = Options()
    opts.binary_location = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--hide-scrollbars")
    opts.add_argument("--window-size=1800,2600")

    driver = webdriver.Chrome(options=opts)
    try:
        driver.get(HTML.resolve().as_uri())
        time.sleep(2)

        metrics = driver.execute_cdp_cmd("Page.getLayoutMetrics", {})
        content = metrics["contentSize"]
        driver.execute_cdp_cmd(
            "Emulation.setDeviceMetricsOverride",
            {
                "mobile": False,
                "width": int(content["width"]),
                "height": int(content["height"]),
                "deviceScaleFactor": 1,
                "screenOrientation": {"type": "portraitPrimary", "angle": 0},
            },
        )

        screenshot = driver.execute_cdp_cmd(
            "Page.captureScreenshot",
            {"format": "png", "captureBeyondViewport": True, "fromSurface": True},
        )
        OUT.write_bytes(base64.b64decode(screenshot["data"]))
        print(OUT)
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
