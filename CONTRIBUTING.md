# Contributing to YamiBot

Thank you for your interest in contributing to YamiBot! This document provides guidelines and instructions for contributing.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Coding Standards](#coding-standards)

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment:
- Be respectful and constructive
- Welcome newcomers and help them learn
- Focus on what is best for the community
- Show empathy towards other community members

## Getting Started

### Prerequisites

- Python 3.10 or higher
- Git
- A Discord Developer account (for testing)

### Repository Overview

```
YamiBot/
├── src/                    # Source code
│   ├── providers/           # AI provider implementations
│   ├── integrations/        # Music API integrations
│   ├── formatting/          # Response formatting
│   └── utils/              # Utility modules
├── tests/                  # Test suite
├── docs/                   # Documentation
├── deployment/              # Deployment configuration
└── main.py                 # Application entry point
```

## Development Setup

### 1. Fork and Clone

```bash
# Fork the repository on GitHub
git clone https://github.com/YOUR_USERNAME/YamiBot.git
cd YamiBot
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

For development with testing tools:
```bash
pip install -r requirements.txt
pip install pytest pytest-asyncio black isort mypy
```

### 4. Configure Environment

```bash
cp .env.example .env
# Edit .env with your API keys and configuration
```

### 5. Verify Installation

```bash
python tests/test_basic.py
```

## Making Changes

### Branch Strategy

1. Create a new branch for your changes:
```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/issue-description
```

2. Make your changes with clear, descriptive commits:
```bash
git add .
git commit -m "feat: add new feature"          # new feature
git commit -m "fix: resolve bug description"   # bug fix
git commit -m "docs: update README"            # documentation
git commit -m "refactor: optimize function"     # code refactoring
```

### Coding Style

- Follow PEP 8 style guidelines
- Use meaningful variable and function names
- Add type hints to all functions
- Write docstrings for all functions and classes
- Keep functions focused and single-purpose

### Type Hints Example

```python
from typing import Optional, Dict, List

async def process_message(
    user_id: int,
    content: str,
    timeout: Optional[int] = None
) -> Dict[str, Any]:
    """Process user message with optional timeout."""
    pass
```

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_providers.py

# Run with coverage
pytest --cov=src --cov-report=html
```

### Writing Tests

1. Create test file in `tests/` directory
2. Name it `test_<module_name>.py`
3. Use pytest fixtures and async support
4. Test both success and failure cases
5. Add meaningful assertions

Example test:
```python
import pytest
from src.utils.input_validator import InputValidator

def test_validate_message_valid():
    """Test that valid messages pass validation."""
    validator = InputValidator()
    is_valid, error = validator.validate_message("Hello, world!")
    assert is_valid is True
    assert error is None

def test_validate_message_too_long():
    """Test that messages exceeding length limit are rejected."""
    validator = InputValidator()
    is_valid, error = validator.validate_message("A" * 2001)
    assert is_valid is False
    assert "too long" in error.lower()
```

### Security Testing

Before submitting, ensure your changes:
- ✅ Don't expose sensitive data in logs
- ✅ Properly validate all user input
- ✅ Handle errors gracefully
- ✅ Don't create resource leaks (unclosed sessions, etc.)
- ✅ Follow rate limiting guidelines

## Submitting Changes

### 1. Update Documentation

- Update README.md if you added new features
- Add/update documentation in `docs/` if needed
- Update CHANGELOG.md with your changes

### 2. Run Code Quality Checks

```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Type checking
mypy src/

# Run tests
pytest
```

### 3. Pull Request

1. Push your branch:
```bash
git push origin feature/your-feature-name
```

2. Open a Pull Request on GitHub with:
- Clear title describing the change
- Detailed description of what you did and why
- Reference any related issues
- Screenshots for UI changes (if applicable)

### Pull Request Checklist

- [ ] Code follows project style guidelines
- [ ] Tests added/updated and passing
- [ ] Documentation updated
- [ ] No new security vulnerabilities introduced
- [ ] Commit messages are clear and follow conventions
- [ ] Branch is up-to-date with main

## Coding Standards

### Error Handling

Always handle exceptions appropriately:

```python
# ✅ Good - specific exception handling
try:
    result = await api_call()
except aiohttp.ClientError as e:
    logger.error(f"API request failed: {e}")
    raise UserFriendlyError("Unable to complete request")

# ❌ Bad - bare except
try:
    result = await api_call()
except:
    pass
```

### Logging

Use appropriate log levels:

```python
logger.debug("Detailed debugging info")        # Debug info
logger.info("Normal operation info")          # Normal events
logger.warning("Something unusual happened")    # Recoverable issues
logger.error("Error occurred")                 # Errors that don't stop execution
logger.critical("Critical failure")           # Serious failures
```

**IMPORTANT:** Never log sensitive data (API keys, tokens, passwords)

### Async/Await

- Always use `async` and `await` correctly
- Don't block the event loop with synchronous operations
- Use `asyncio.create_task()` for concurrent operations when appropriate

### Security

- Always validate user input before processing
- Use parameterized queries (if using database)
- Never trust client-side data
- Sanitize all output before sending to users

## Getting Help

If you need help:
- Open an issue with your question
- Join our Discord community (link in README)
- Check existing issues and pull requests
- Read the documentation in `docs/` directory

## Recognition

Contributors will be recognized in:
- CONTRIBUTORS.md
- Release notes
- Project documentation

Thank you for contributing to YamiBot! 🎉
