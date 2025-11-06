# Grafana Dashboard Playwright Tests

End-to-end browser tests for the Grafana Trading Dashboard using Playwright and pytest.

## Purpose

These tests validate the Grafana dashboard from a real browser perspective, catching issues that API-level tests might miss:

- JavaScript console errors
- Datasource configuration problems
- UI rendering issues
- Data display ("No data" messages)
- Panel visibility and functionality

**Critical Value:** These tests would have immediately caught the datasource configuration issue where the database field was missing from jsonData, which caused all panels to show "No data" in the browser despite API queries working correctly.

## Installation

The test dependencies are already installed. If you need to reinstall:

```bash
# Install Python dependencies
venv/bin/pip install playwright pytest-playwright

# Install Chromium browser
venv/bin/playwright install chromium
```

## Running Tests

### Run all Playwright tests:
```bash
venv/bin/pytest tests/playwright/ -v -m playwright
```

### Run specific test class:
```bash
# Login tests only
venv/bin/pytest tests/playwright/test_grafana_dashboard.py::TestGrafanaLogin -v

# Dashboard tests only
venv/bin/pytest tests/playwright/test_grafana_dashboard.py::TestGrafanaDashboard -v

# Datasource tests only
venv/bin/pytest tests/playwright/test_grafana_dashboard.py::TestGrafanaDatasource -v

# Performance tests only
venv/bin/pytest tests/playwright/test_grafana_dashboard.py::TestDashboardPerformance -v -m slow
```

### Run specific test:
```bash
venv/bin/pytest tests/playwright/test_grafana_dashboard.py::TestGrafanaDashboard::test_panels_display_data_not_no_data -v
```

### Run with visible browser (headed mode):
```bash
venv/bin/pytest tests/playwright/ -v --headed
```

### Exclude slow tests:
```bash
venv/bin/pytest tests/playwright/ -v -m "playwright and not slow"
```

## Test Structure

### Test Files

- **`test_grafana_dashboard.py`** - Main test suite with 13 comprehensive tests
- **`conftest.py`** - pytest fixtures for authentication and page setup

### Test Classes

#### 1. TestGrafanaLogin
Tests Grafana authentication functionality.

**Tests:**
- `test_can_login_to_grafana` - Verifies successful login

#### 2. TestGrafanaDashboard
Core dashboard functionality tests.

**Tests:**
- `test_dashboard_loads_successfully` - Dashboard loads without errors
- `test_all_panels_are_present` - All 9 expected panels exist
- `test_panels_display_data_not_no_data` - **CRITICAL:** Panels show data, not "No data" messages
- `test_stat_panels_show_numbers` - Stat panels display numeric values
- `test_no_console_errors_on_dashboard` - **CRITICAL:** No JavaScript console errors
- `test_decisions_table_has_data` - Recent Decisions panel exists
- `test_time_range_selector_works` - Time range controls are present
- `test_refresh_interval_is_set` - Auto-refresh is configured

#### 3. TestGrafanaDatasource
Datasource configuration validation.

**Tests:**
- `test_timescaledb_datasource_exists` - TimescaleDB datasource is configured
- `test_timescaledb_datasource_connected` - Datasource connection test passes

#### 4. TestDashboardPerformance
Performance and load tests (marked as `@pytest.mark.slow`).

**Tests:**
- `test_dashboard_loads_within_timeout` - Dashboard loads in < 10 seconds
- `test_dashboard_refresh_works` - Refresh button functions correctly

## Key Tests Explained

### test_panels_display_data_not_no_data

**Why Critical:** This test would have caught the datasource configuration bug immediately.

```python
def test_panels_display_data_not_no_data(self, dashboard_page: Page):
    """Verify panels show actual data, not 'No data' message"""
    # Checks for "No data" messages on the dashboard
    # Fails if any panels show "No data"
```

When the datasource database field was missing, this test would have failed with:
```
AssertionError: Found 9 panels with 'No data' - datasource may not be configured correctly
```

### test_no_console_errors_on_dashboard

**Why Critical:** Catches JavaScript errors that might not be visible in the UI.

```python
def test_no_console_errors_on_dashboard(self, page: Page, grafana_credentials: dict):
    """Verify there are no JavaScript console errors when loading dashboard"""
    # Listens to browser console and captures errors
    # Filters out known non-critical errors (websocket, 404s)
```

This test would have caught the database configuration error:
```
Console errors detected: ['You do not currently have a default database configured...']
```

## Fixtures

### grafana_credentials (session-scoped)
Provides Grafana login credentials.

```python
{
    "username": "admin",
    "password": "admin",
    "url": "http://localhost:3000"
}
```

### logged_in_page
Returns a Playwright Page object already authenticated with Grafana.
Handles login form, password change prompt, and navigation.

### dashboard_page
Returns a Page with the trading dashboard loaded and ready.
Built on top of `logged_in_page`, navigates to the dashboard.

### console_errors
Captures JavaScript console errors from the page during test execution.

## Configuration

Configuration is in `pytest.ini`:

```ini
[pytest]
markers =
    playwright: Playwright browser tests
    slow: Slow running tests

# Playwright options
base-url = http://localhost:3000
headed = False
browser = chromium
slow-mo = 0
```

## When to Run These Tests

### Run After:
- Infrastructure changes (Docker, Grafana, TimescaleDB)
- Grafana configuration updates (datasources, dashboards)
- Dashboard JSON modifications
- New panel additions or changes
- Datasource provisioning file updates

### Run Frequency:
- **After infrastructure changes:** ALWAYS
- **Daily/Weekly validation:** Recommended
- **NOT in every cron cycle:** Too slow (74 seconds)

## Troubleshooting

### Tests fail with "Login failed"
- Verify Grafana is running: `docker ps | grep grafana`
- Check Grafana is accessible: `curl http://localhost:3000/api/health`
- Verify credentials in `conftest.py` match your setup

### Tests fail with "Connection refused"
- Ensure Docker containers are running: `docker-compose up -d`
- Wait for Grafana to be fully ready (can take 10-20 seconds)

### Tests timeout
- Increase timeout in individual tests if your system is slow
- Run with `--headed` to see what's happening in the browser

### "No data" test fails
- **This is the key test!** It means panels are not displaying data
- Check datasource configuration in Grafana UI
- Verify database field is set in both root and jsonData sections
- Check Grafana logs: `docker logs grafana`

## Test Results

**Current Status:** ✅ All 13 tests passing

```
13 passed, 4 warnings in 74.31s
```

Test coverage:
- ✅ Login functionality
- ✅ Dashboard loading
- ✅ Data display validation
- ✅ Console error detection
- ✅ Datasource configuration
- ✅ Performance metrics

## Future Enhancements

Potential additions:
- Screenshot capture on failure
- Video recording of test runs
- Network traffic analysis
- Query performance monitoring
- Multi-browser testing (Firefox, WebKit)
- Mobile viewport testing

## Related Files

- `infrastructure/monitoring/grafana/datasources/datasources.yml` - Datasource configuration
- `infrastructure/monitoring/grafana/dashboards/trading-overview.json` - Dashboard definition
- `pytest.ini` - pytest configuration
