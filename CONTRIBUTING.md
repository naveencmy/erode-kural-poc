# Contributing to Erode Collectorate AI System

Thank you for considering contributing to the **Erode District Collectorate AI Administrative Assistant**. This document provides guidelines and best practices for contributing to this project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Development Environment](#development-environment)
- [Branch Strategy](#branch-strategy)
- [Commit Messages](#commit-messages)
- [Pull Request Process](#pull-request-process)
- [Code Style](#code-style)
- [Testing](#testing)

---

## Code of Conduct

This project adheres to the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

---

## Development Environment

### Prerequisites

| Tool | Version | Purpose |
|:---|:---|:---|
| Python | 3.11+ | Backend runtime |
| Node.js | 18+ | Frontend toolchain |
| Tesseract OCR | 5.x | Tamil + English OCR |
| Ollama | Latest | Local LLM inference (optional) |

### Backend Setup

```bash
cd backend
python -m venv .venv

# Windows
.\.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env  # Edit with your local configuration

python main.py --mode all
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

---

## Branch Strategy

We follow a **trunk-based development** model:

| Branch | Purpose |
|:---|:---|
| `main` | Production-ready, stable code |
| `feature/<name>` | New features (e.g., `feature/bulk-export-csv`) |
| `fix/<name>` | Bug fixes (e.g., `fix/ocr-deskew-angle`) |
| `docs/<name>` | Documentation changes |

### Rules

- All changes go through pull requests — no direct pushes to `main`.
- Feature branches should be short-lived (< 1 week).
- Rebase onto `main` before opening a PR to maintain a linear history.

---

## Commit Messages

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

[optional body]

[optional footer(s)]
```

### Types

| Type | Description |
|:---|:---|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `style` | Code formatting (no logic changes) |
| `refactor` | Refactoring without feature/fix |
| `test` | Adding or updating tests |
| `chore` | Build scripts, CI, tooling |
| `perf` | Performance improvement |

### Examples

```
feat(data-viz): add 1.5x IQR outlier detection for budget datasets
fix(ocr): correct Tamil deskew threshold from 2° to 1.5°
docs(readme): update quickstart for Windows 11 compatibility
test(mail): add Mailpit SMTP integration test
```

---

## Pull Request Process

1. **Create a feature branch** from `main`.
2. **Write or update tests** for your changes.
3. **Run the full test suite** and ensure all tests pass:
   ```bash
   cd backend && pytest tests/ -v
   cd frontend && npm run build
   ```
4. **Open a pull request** with:
   - A clear title following Conventional Commits format.
   - A description of *what* changed and *why*.
   - Screenshots for any UI changes.
5. **Request review** from at least one maintainer.
6. **Squash and merge** once approved.

---

## Code Style

### Python (Backend)

- Follow [PEP 8](https://peps.python.org/pep-0008/) with a line length of 120 characters.
- Use type hints for all public function signatures.
- Docstrings follow Google style:
  ```python
  def classify_petition(text: str, officer_id: str) -> dict:
      """Classify a Tamil grievance petition into a department.

      Args:
          text: Raw OCR-extracted Tamil text.
          officer_id: Identifier of the reviewing officer.

      Returns:
          Classification result with department, confidence, and method.
      """
  ```
- All Tamil string literals must use Unicode — no transliteration.

### JavaScript / React (Frontend)

- Use functional components with hooks.
- State management via Zustand stores.
- Component files use PascalCase (e.g., `DataModule.jsx`).
- Utility files use camelCase (e.g., `api.js`).

---

## Testing

### Backend

We use **pytest** with the following test modules:

| Test File | Coverage |
|:---|:---|
| `test_pipeline.py` | Core ingestion, OCR, and classification pipeline |
| `test_document_summary.py` | Module 1: Document summarization & dynamic suggestions |
| `test_data_viz.py` | Module 2: Data analytics & visualization |
| `test_mail_engine.py` | Module 5: Mail integration & dispatch |
| `test_official_content.py` | Module 3: Official content generation & export |

```bash
# Run all tests
pytest tests/ -v

# Run a specific module
pytest tests/test_data_viz.py -v
```

### Frontend

```bash
# Production build (catches import/type errors)
npm run build

# Lint check
npm run lint
```

---

## Questions?

If you have questions about contributing, please open a [GitHub Issue](../../issues) or reach out to the maintainers.
