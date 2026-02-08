"""Guide for writing and running tests in the GitHub Webhook Bot project.

## Testing Structure

The project uses pytest as the testing framework with the following structure:

```
src/tests/
├── __init__.py
├── conftest.py           # Pytest configuration and fixtures
├── test_config.py        # Tests for settings
├── test_logger.py        # Tests for logging
├── unit/                 # Unit tests
│   ├── __init__.py
│   ├── test_enums.py
│   ├── test_decorators.py
│   ├── test_command_validator.py
│   └── test_github_utils.py
└── integration/          # Integration tests
    ├── __init__.py
    ├── test_server.py
    └── test_bot_init.py
```

## Running Tests

### Run all tests
```bash
pytest src/tests
```

### Run with coverage
```bash
pytest src/tests --cov=src --cov-report=html
```

### Run only unit tests
```bash
pytest src/tests/unit -m unit
```

### Run only integration tests
```bash
pytest src/tests/integration -m integration
```

### Run async tests
```bash
pytest src/tests -m async_
```

### Run with verbose output
```bash
pytest src/tests -v
```

### Run a specific test file
```bash
pytest src/tests/test_config.py
```

### Run a specific test
```bash
pytest src/tests/test_config.py::TestSettings::test_settings_instance
```

## Writing Tests

### Unit Test Example

```python
import pytest

class TestMyFeature:
    @pytest.mark.unit
    def test_something(self):
        \"\"\"Test description.\"\"\"
        assert True
```

### Async Test Example

```python
import pytest

class TestAsync:
    @pytest.mark.async_
    async def test_async_operation(self):
        \"\"\"Test async operation.\"\"\"
        result = await some_async_function()
        assert result == expected
```

### Integration Test Example

```python
import pytest
from fastapi.testclient import TestClient

class TestEndpoint:
    @pytest.fixture
    def client(self):
        from core.server import app
        return TestClient(app)
    
    @pytest.mark.integration
    def test_endpoint(self, client):
        response = client.get('/health')
        assert response.status_code == 200
```

### Using Fixtures

Use the provided fixtures in `conftest.py`:

```python
@pytest.mark.unit
def test_with_settings(mock_settings):
    \"\"\"Test using mock settings.\"\"\"
    assert mock_settings.BOT_TOKEN == "test-token"

@pytest.mark.async_
async def test_with_bot(mock_bot):
    \"\"\"Test using mock bot.\"\"\"
    await mock_bot.send_message(chat_id=1, text="test")
    mock_bot.send_message.assert_called_once()
```

## Pre-commit Hooks

The project uses pre-commit hooks to automatically:
1. Format code with Ruff
2. Run pytest before each commit

### Install pre-commit

```bash
pre-commit install
```

### Run pre-commit manually

```bash
pre-commit run --all-files
```

### Skip pre-commit hooks (not recommended)

```bash
git commit --no-verify
```

## Test Markers

Available markers:
- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.async_` - Async tests

## Coverage

View coverage report in HTML:

```bash
pytest src/tests --cov=src --cov-report=html
open htmlcov/index.html
```

## Best Practices

1. **Use descriptive names**: Test names should describe what is being tested
2. **One assertion per test**: Keep tests focused on a single behavior
3. **Use fixtures**: Share common setup code with fixtures
4. **Mock external dependencies**: Use unittest.mock for external services
5. **Test both happy and sad paths**: Include tests for error cases
6. **Keep tests fast**: Avoid unnecessary I/O and sleep calls
7. **Clean up**: Ensure tests clean up after themselves

## Continuous Integration

Pre-commit automatically runs:
- **Ruff**: Code linting and formatting
- **Pytest**: All test suite

Make sure all tests pass before committing code!
"""

