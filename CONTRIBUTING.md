# Contributing to Tintri OpenTelemetry Receiver

Thank you for your interest in contributing to the Tintri OpenTelemetry Receiver!

## Getting Started

### Development Setup

1. Clone the repository:
```bash
git clone https://github.com/IntegrationPlumbers/ip-tintri-otel-receiver.git
cd ip-tintri-otel-receiver
```

2. Install [uv](https://docs.astral.sh/uv/) if you don't have it:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

3. Install development dependencies:
```bash
uv pip install -e ".[dev]"
```

## Development Workflow

### Running Tests

```bash
# Run all tests
make test

# Run with coverage
make test-coverage

# Run specific test file
pytest tests/test_vmstore_client.py -v
```

### Code Quality

We use several tools to maintain code quality:

```bash
# Format code
make format

# Run linting
make lint

# Type checking
make type-check
```

### Code Style

- Follow PEP 8 guidelines
- Use type hints for function signatures
- Write docstrings for all public functions and classes
- Keep functions focused and under 50 lines when possible
- Maximum line length: 88 characters (Black default)

### Testing Guidelines

- Write unit tests for all new functionality
- Aim for >80% code coverage
- Use meaningful test names that describe what is being tested
- Mock external dependencies (API calls, file I/O, etc.)
- Test both success and failure scenarios

Example test structure:
```python
def test_feature_success(self):
    """Test that feature works correctly under normal conditions."""
    # Arrange
    # Act
    # Assert
    
def test_feature_handles_error(self):
    """Test that feature handles errors gracefully."""
    # Arrange
    # Act
    # Assert
```

## Pull Request Process

1. **Fork the repository** and create a new branch:
```bash
git checkout -b feature/your-feature-name
```

2. **Make your changes** following the code style guidelines

3. **Write or update tests** for your changes

4. **Run the test suite** and ensure all tests pass:
```bash
make test
make lint
make type-check
```

5. **Update documentation** if needed (README, docstrings, etc.)

6. **Commit your changes** with clear, descriptive commit messages:
```bash
git commit -m "Add feature: brief description"
```

7. **Push to your fork** and submit a pull request:
```bash
git push origin feature/your-feature-name
```

8. **Wait for review** - maintainers will review your PR and may request changes

## Commit Message Guidelines

- Use present tense ("Add feature" not "Added feature")
- Use imperative mood ("Move cursor to..." not "Moves cursor to...")
- Limit first line to 72 characters
- Reference issues and pull requests when relevant

Examples:
- `Add support for VDISK capacity metrics`
- `Fix authentication error handling in VMstore client`
- `Update documentation for TGC configuration`

## Areas for Contribution

### High Priority

- Additional metric types (nice-to-have features from PRD)
- Performance optimizations
- Integration tests with mock Tintri API
- Enhanced error recovery mechanisms

### Documentation

- Improved setup guides
- Troubleshooting documentation
- Example configurations for different scenarios
- API mapping reference updates

### Testing

- Additional unit test coverage
- Integration test suite
- Performance benchmarks
- Load testing

### Features

- Support for additional Tintri API versions
- Metric sampling and filtering options
- Advanced caching strategies
- Grafana dashboard templates

## Reporting Issues

When reporting issues, please include:

1. **Description**: Clear description of the issue
2. **Environment**: Python version, OS, Tintri API version
3. **Steps to reproduce**: Detailed steps to reproduce the issue
4. **Expected behavior**: What you expected to happen
5. **Actual behavior**: What actually happened
6. **Logs**: Relevant log output (sanitize any sensitive information)
7. **Configuration**: Relevant parts of your config (sanitize credentials)

## Questions?

If you have questions about contributing:

- Open an issue with the "question" label
- Contact the maintainers
- Check existing issues and pull requests

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (MIT License).

## Code of Conduct

### Our Pledge

We pledge to make participation in our project a harassment-free experience for everyone, regardless of age, body size, disability, ethnicity, gender identity and expression, level of experience, nationality, personal appearance, race, religion, or sexual identity and orientation.

### Our Standards

Examples of behavior that contributes to creating a positive environment include:

- Using welcoming and inclusive language
- Being respectful of differing viewpoints
- Gracefully accepting constructive criticism
- Focusing on what is best for the community
- Showing empathy towards other community members

### Enforcement

Instances of unacceptable behavior may be reported to the project maintainers. All complaints will be reviewed and investigated promptly and fairly.

Thank you for contributing to Tintri OpenTelemetry Receiver!
