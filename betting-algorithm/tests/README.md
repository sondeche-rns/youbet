# Betting Algorithm Test Suite

Comprehensive tests for the bet4me betting algorithm.

## Running Tests

### Run all tests
```bash
cd betting-algorithm
pytest tests/ -v
```

### Run specific test file
```bash
pytest tests/test_jackpot_fetcher.py -v
```

### Run specific test class
```bash
pytest tests/test_jackpot_fetcher.py::TestSampleData -v
```

### Run specific test
```bash
pytest tests/test_jackpot_fetcher.py::TestSampleData::test_fetch_sportpesa_mega_without_selenium -v
```

### Run with coverage
```bash
pytest tests/ --cov=src --cov-report=html
```

## Test Structure

### test_jackpot_fetcher.py

Comprehensive tests for the JackpotFetcher class:

- **TestFetcherInitialization**: Tests for proper initialization
- **TestSampleData**: Tests for sample data fallback
- **TestMatchDataStructure**: Validates match data structure
- **TestSeleniumMocking**: Tests Selenium functionality with mocks
- **TestDataExtraction**: Tests data extraction methods
- **TestHistorySaving**: Tests history saving functionality
- **TestErrorHandling**: Tests error handling and recovery
- **TestDataSourceTracking**: Tests data source tracking
- **TestTimestamps**: Tests timestamp handling
- **TestSampleDataConsistency**: Tests sample data consistency

**Total: 30+ tests**

## Test Coverage

Current test coverage:
- ✅ Fetcher initialization
- ✅ Sample data fallback
- ✅ Selenium mocking
- ✅ Data extraction
- ✅ History saving
- ✅ Error handling
- ✅ All providers (SportPesa, Betika)

## Writing New Tests

### Fixtures

Use provided fixtures for common setup:

```python
def test_my_feature(fetcher_no_selenium):
    """Test my feature"""
    result = fetcher_no_selenium.fetch_sportpesa_mega_jackpot()
    assert result is not None
```

### Mocking Selenium

```python
@patch('jackpot_fetcher.SELENIUM_AVAILABLE', True)
@patch('jackpot_fetcher.JackpotFetcher._create_driver')
def test_with_selenium(mock_driver, fetcher_with_selenium):
    # Your test here
    pass
```

## Continuous Integration

Tests are designed to run in CI/CD environments:
- No external dependencies (mocked)
- Temporary directories for data
- Fast execution (< 1 minute)

## Contributing

When adding new features:
1. Write tests first (TDD)
2. Ensure all tests pass
3. Maintain test coverage above 80%
4. Update this README if needed
