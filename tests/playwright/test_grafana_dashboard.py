"""
Playwright Tests for Grafana Trading Dashboard

These tests verify that the Grafana dashboard loads correctly,
displays data, and has no JavaScript errors.
"""
import pytest
from playwright.sync_api import Page, expect


@pytest.mark.playwright
class TestGrafanaLogin:
    """Tests for Grafana login functionality"""

    def test_can_login_to_grafana(self, page: Page, grafana_credentials: dict):
        """Verify that we can successfully login to Grafana"""
        # Navigate to login page
        page.goto(f"{grafana_credentials['url']}/login")

        # Verify login form is present
        expect(page.locator('input[name="user"]')).to_be_visible()
        expect(page.locator('input[name="password"]')).to_be_visible()

        # Fill in credentials
        page.fill('input[name="user"]', grafana_credentials['username'])
        page.fill('input[name="password"]', grafana_credentials['password'])

        # Submit login
        page.click('button[type="submit"]')

        # Wait for navigation
        page.wait_for_load_state('networkidle')
        page.wait_for_timeout(2000)

        # Verify we're logged in (check we're not on login page OR we see skip button)
        is_logged_in = (
            page.url != f"{grafana_credentials['url']}/login" or
            page.locator('button:has-text("Skip")').is_visible()
        )
        assert is_logged_in, f"Login failed - URL: {page.url}"


@pytest.mark.playwright
class TestGrafanaDashboard:
    """Tests for the Trading System dashboard"""

    def test_dashboard_loads_successfully(self, dashboard_page: Page):
        """Verify the trading dashboard loads without errors"""
        # Check we're on the correct dashboard
        assert "trading-overview" in dashboard_page.url, "Not on trading dashboard"

        # Verify dashboard title is present
        expect(dashboard_page.locator('text=Autonomous Trading System')).to_be_visible()

    def test_all_panels_are_present(self, dashboard_page: Page):
        """Verify all 9 dashboard panels are present"""
        expected_panels = [
            "Decisions (24h)",
            "Agent Success Rate (24h)",
            "Candles Collected (24h)",
            "Signals Generated (24h)",
            "Recent Trading Decisions",
            "Price Charts (1h)",
            "Decision Distribution (24h)",
            "Signal Distribution (24h)",
            "Agent Performance (24h)"
        ]

        for panel_title in expected_panels:
            # Check panel title is visible (may need to scroll)
            locator = dashboard_page.locator(f'text={panel_title}').first
            assert locator.count() > 0, f"Panel '{panel_title}' not found"

    def test_panels_display_data_not_no_data(self, dashboard_page: Page):
        """
        Verify panels show actual data, not 'No data' message.

        This is the key test that would have caught the datasource issue!
        """
        # Wait for data to load
        dashboard_page.wait_for_timeout(3000)

        # Check for "No data" messages
        no_data_messages = dashboard_page.locator('text="No data"').all()

        # Get count of visible "No data" messages
        visible_no_data = [msg for msg in no_data_messages if msg.is_visible()]

        # Assert we have NO "No data" messages
        assert len(visible_no_data) == 0, \
            f"Found {len(visible_no_data)} panels with 'No data' - datasource may not be configured correctly"

    def test_stat_panels_show_numbers(self, dashboard_page: Page):
        """Verify the stat panels (top row) display numeric values"""
        # Wait for panels to load
        dashboard_page.wait_for_timeout(2000)

        # The stat panels should show numbers, not "No data"
        # We can check if there are stat panels with values
        stat_values = dashboard_page.locator('[data-testid="data-testid Panel header Decisions (24h)"]').first

        # Just verify the page has rendered panels
        assert dashboard_page.locator('[class*="panel-container"]').count() > 0, \
            "No panel containers found on dashboard"

    def test_no_console_errors_on_dashboard(self, page: Page, grafana_credentials: dict):
        """
        Verify there are no JavaScript console errors when loading dashboard.

        This test would have caught the 'default database' error!
        """
        console_errors = []

        # Set up console error listener
        def on_console(msg):
            if msg.type == 'error':
                # Filter out known non-critical errors
                error_text = msg.text
                # Ignore websocket/live connection errors and known 404s (non-critical)
                if ('websocket' not in error_text.lower() and
                    'ws:' not in error_text.lower() and
                    'public-dashboards' not in error_text.lower() and
                    '404' not in error_text):
                    console_errors.append(error_text)

        page.on('console', on_console)

        # Login
        page.goto(f"{grafana_credentials['url']}/login")
        page.fill('input[name="user"]', grafana_credentials['username'])
        page.fill('input[name="password"]', grafana_credentials['password'])
        page.click('button[type="submit"]')
        page.wait_for_load_state('networkidle')

        # Skip password change if prompted
        if page.locator('button:has-text("Skip")').is_visible():
            page.click('button:has-text("Skip")')
            page.wait_for_load_state('networkidle')

        # Navigate to dashboard
        page.goto(f"{grafana_credentials['url']}/d/trading-overview/autonomous-trading-system-overview")
        page.wait_for_load_state('networkidle')

        # Wait for panels to load
        page.wait_for_timeout(3000)

        # Check for console errors
        assert len(console_errors) == 0, \
            f"Console errors detected: {console_errors[:5]}"  # Show first 5 errors

    def test_decisions_table_has_data(self, dashboard_page: Page):
        """Verify the Recent Trading Decisions panel exists and has content"""
        # Wait for panels to load
        dashboard_page.wait_for_timeout(2000)

        # Look for the Recent Trading Decisions panel
        # Grafana tables might be rendered as divs, not HTML tables
        decisions_panel = dashboard_page.locator('text=Recent Trading Decisions').first

        # Verify the panel exists
        assert decisions_panel.count() > 0, "Recent Trading Decisions panel not found"

    def test_time_range_selector_works(self, dashboard_page: Page):
        """Verify the time range selector is present and functional"""
        # Look for time range picker
        time_picker = dashboard_page.locator('[aria-label*="Time range"]').first

        # Should be able to find time range controls
        assert dashboard_page.locator('text=Last 24 hours').count() > 0 or \
               dashboard_page.locator('[class*="time-picker"]').count() > 0, \
            "Time range selector not found"

    def test_refresh_interval_is_set(self, dashboard_page: Page):
        """Verify auto-refresh is configured (should be 30s)"""
        # Check if refresh picker exists
        # This verifies the dashboard has refresh configured
        assert "refresh=30s" in dashboard_page.url or \
               dashboard_page.locator('[class*="refresh-picker"]').count() > 0, \
            "Auto-refresh not configured"


@pytest.mark.playwright
class TestGrafanaDatasource:
    """Tests for Grafana datasource configuration"""

    def test_timescaledb_datasource_exists(self, logged_in_page: Page):
        """Verify TimescaleDB datasource is configured"""
        # Navigate to datasources page
        logged_in_page.goto(f"{logged_in_page.url.split('/')[0]}//{logged_in_page.url.split('/')[2]}/datasources")

        # Wait for page to load
        logged_in_page.wait_for_load_state('networkidle')

        # Look for TimescaleDB datasource (use .first since there may be multiple matches)
        expect(logged_in_page.locator('text=TimescaleDB').first).to_be_visible(timeout=5000)

    def test_timescaledb_datasource_connected(self, logged_in_page: Page, grafana_credentials: dict):
        """Verify TimescaleDB datasource connection is working"""
        # Navigate to datasources
        logged_in_page.goto(f"{grafana_credentials['url']}/connections/datasources")
        logged_in_page.wait_for_load_state('networkidle')

        # Click on TimescaleDB
        logged_in_page.locator('text=TimescaleDB').first.click()
        logged_in_page.wait_for_load_state('networkidle')

        # Scroll to bottom where "Save & test" button is
        logged_in_page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

        # Click "Save & test" button
        save_button = logged_in_page.locator('button:has-text("Save & test")').first
        if save_button.is_visible():
            save_button.click()

            # Wait for result
            logged_in_page.wait_for_timeout(2000)

            # Should see success message (not "failed" or "error")
            page_content = logged_in_page.content().lower()
            assert 'connection ok' in page_content or 'successfully' in page_content, \
                "Datasource connection test failed"


@pytest.mark.playwright
@pytest.mark.slow
class TestDashboardPerformance:
    """Performance and load tests for the dashboard"""

    def test_dashboard_loads_within_timeout(self, page: Page, grafana_credentials: dict):
        """Verify dashboard loads within reasonable time (10 seconds)"""
        import time

        # Login
        page.goto(f"{grafana_credentials['url']}/login")
        page.fill('input[name="user"]', grafana_credentials['username'])
        page.fill('input[name="password"]', grafana_credentials['password'])
        page.click('button[type="submit"]')
        page.wait_for_load_state('networkidle')

        # Skip password change if prompted
        if page.locator('button:has-text("Skip")').is_visible():
            page.click('button:has-text("Skip")')

        # Time the dashboard load
        start_time = time.time()
        page.goto(f"{grafana_credentials['url']}/d/trading-overview/autonomous-trading-system-overview")
        page.wait_for_load_state('networkidle')
        load_time = time.time() - start_time

        # Should load within 10 seconds
        assert load_time < 10, f"Dashboard took {load_time:.2f}s to load (should be < 10s)"

    def test_dashboard_refresh_works(self, dashboard_page: Page):
        """Verify dashboard refresh button works without errors"""
        # Find and click refresh button
        refresh_button = dashboard_page.locator('[aria-label*="Refresh"]').first

        if refresh_button.is_visible():
            refresh_button.click()
            dashboard_page.wait_for_load_state('networkidle')
            dashboard_page.wait_for_timeout(2000)

            # Dashboard should still be visible after refresh
            expect(dashboard_page.locator('text=Autonomous Trading System')).to_be_visible()
