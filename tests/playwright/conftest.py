"""
Playwright Test Fixtures and Configuration
"""
import pytest
from playwright.sync_api import Page, expect


# Grafana credentials
GRAFANA_URL = "http://localhost:3000"
GRAFANA_USERNAME = "admin"
GRAFANA_PASSWORD = "admin"


@pytest.fixture(scope="session")
def grafana_credentials():
    """Provide Grafana login credentials"""
    return {
        "username": GRAFANA_USERNAME,
        "password": GRAFANA_PASSWORD,
        "url": GRAFANA_URL
    }


@pytest.fixture
def logged_in_page(page: Page, grafana_credentials: dict) -> Page:
    """
    Fixture that provides a Playwright page already logged into Grafana.

    This fixture:
    1. Navigates to Grafana login page
    2. Logs in with credentials
    3. Waits for successful login
    4. Returns the authenticated page

    Usage:
        def test_something(logged_in_page):
            logged_in_page.goto('/d/trading-overview')
            # ... test code
    """
    # Navigate to login page
    page.goto(f"{grafana_credentials['url']}/login")

    # Fill in login form
    page.fill('input[name="user"]', grafana_credentials['username'])
    page.fill('input[name="password"]', grafana_credentials['password'])

    # Click login button
    page.click('button[type="submit"]')

    # Wait for navigation to complete (login successful)
    # This waits for either the home page or skip password change
    page.wait_for_load_state('networkidle')

    # If we see "Skip" button (change password prompt), click it
    if page.locator('button:has-text("Skip")').is_visible():
        page.click('button:has-text("Skip")')
        page.wait_for_load_state('networkidle')

    return page


@pytest.fixture
def dashboard_page(logged_in_page: Page) -> Page:
    """
    Fixture that provides a page with the trading dashboard loaded.

    Returns:
        Page object with trading dashboard loaded and ready
    """
    # Navigate to trading dashboard
    logged_in_page.goto(f"{GRAFANA_URL}/d/trading-overview/autonomous-trading-system-overview")

    # Wait for dashboard to load
    logged_in_page.wait_for_load_state('networkidle')

    # Wait a bit for panels to render
    logged_in_page.wait_for_timeout(2000)

    return logged_in_page


@pytest.fixture
def console_errors(page: Page) -> list:
    """
    Fixture that captures console errors from the page.

    Usage:
        def test_no_errors(dashboard_page, console_errors):
            # Do some actions
            assert len(console_errors) == 0, f"Console errors: {console_errors}"
    """
    errors = []

    def on_console(msg):
        if msg.type == 'error':
            errors.append(msg.text)

    page.on('console', on_console)

    return errors
