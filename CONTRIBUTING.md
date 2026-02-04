## Contributing

### Setup Development Environment

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### Run Tests

```bash
pytest tests/ -v
```

### Code Style

- Use PEP 8
- Add type hints to functions
- Write docstrings for modules, classes, methods

### Commit Messages

Format: `type: description`

Examples:
- `feat: add new API endpoint`
- `fix: correct database connection timeout`
- `test: add unit tests for RFM calculation`
- `docs: update README with setup instructions`

### Before Submitting PR

- [ ] Tests passing (`pytest tests/`)
- [ ] Code follows PEP 8 (`python -m flake8 src/`)
- [ ] Type hints added (`python -m mypy src/`)
- [ ] Docstrings updated
- [ ] Commit messages are descriptive

### Pull Request Process

1. Create feature branch: `git checkout -b feature/description`
2. Make changes and commit
3. Push: `git push origin feature/description`
4. Open PR on GitHub with description
5. Address review comments
6. Merge when approved
