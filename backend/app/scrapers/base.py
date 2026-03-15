"""Base scraper for browser-based automation."""

from abc import ABC, abstractmethod
from playwright.async_api import async_playwright, Browser, Page
from app.core.config import get_settings

settings = get_settings()


class BaseScraper(ABC):
    """Base class for browser-based scrapers.

    Used when APIs aren't available and data must be scraped
    from web interfaces (e.g., brokerage portals, bank web apps).
    """

    def __init__(self):
        self.browser: Browser | None = None
        self.page: Page | None = None

    async def start(self):
        pw = await async_playwright().start()
        self.browser = await pw.chromium.launch(headless=settings.PLAYWRIGHT_HEADLESS)
        context = await self.browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        self.page = await context.new_page()

    async def stop(self):
        if self.browser:
            await self.browser.close()

    @abstractmethod
    async def login(self, credentials: dict) -> bool:
        """Login to the platform."""
        ...

    @abstractmethod
    async def fetch_data(self) -> dict:
        """Fetch account data after login."""
        ...

    async def run(self, credentials: dict) -> dict:
        """Full scraping workflow."""
        try:
            await self.start()
            success = await self.login(credentials)
            if not success:
                raise Exception("Login failed")
            return await self.fetch_data()
        finally:
            await self.stop()


class WebullScraper(BaseScraper):
    """Webull web scraper — placeholder for when API access is unavailable.

    Webull does not provide a public API. This scraper can be extended
    to automate data extraction from the Webull web platform.
    """

    async def login(self, credentials: dict) -> bool:
        if not self.page:
            return False
        # Navigate to Webull login
        # NOTE: This is a placeholder. Actual implementation would need
        # to handle Webull's specific login flow, 2FA, etc.
        return False

    async def fetch_data(self) -> dict:
        return {"holdings": [], "transactions": []}
