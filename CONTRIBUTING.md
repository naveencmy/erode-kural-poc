# 🤝 Contributing to Erode District Collectorate AI

Thank you for your interest in contributing to the **Erode District Collectorate AI Administrative Assistant** project! 

This repository is built to **Google Engineering Standards** and mission-critical government infrastructure specifications. We maintain strict standards for code hygiene, local-first privacy, mathematical anti-hallucination verification, deterministic slot-filling, and comprehensive automated test coverage.

---

## 📋 Table of Contents
- [Code of Conduct](#-code-of-conduct)
- [How Can I Contribute?](#-how-can-i-contribute)
- [Development Setup](#-development-setup)
- [Branching & Commit Guidelines](#-branching--commit-guidelines)
- [Architectural Principles](#-architectural-principles)
- [Testing Guidelines](#-testing-guidelines)
- [Pull Request Checklist](#-pull-request-checklist)
- [License](#-license)

---

## 📜 Code of Conduct

We are committed to providing a welcoming, inclusive, and harassment-free environment for all contributors. Please adhere to the following principles:
- Be respectful and considerate in communications and code reviews.
- Focus on constructive technical feedback.
- Maintain absolute data privacy — never commit real citizen PII, live Aadhaar numbers, or proprietary government keys.

---

## 💡 How Can I Contribute?

1. **Reporting Bugs:** Open an issue with full reproduction steps, OS/environment details, and terminal output.
2. **Suggesting Enhancements:** Open an issue detailing the administrative or algorithmic rationale for the feature.
3. **Submitting Pull Requests:** Implement bug fixes, performance optimizations, new SOP knowledge items, or bilingual prompt enhancements.

---

## 🛠️ Development Setup

### 1. Prerequisites
- **Python:** `3.11+`
- **Node.js:** `18.0+` & `npm 9.0+`
- **Tesseract OCR:** Configured with English (`eng`) and Tamil (`tam`) language packs
- **Ollama:** `v0.3+` with `qwen2.5:7b-instruct-q4_K_M` (or fallback models `qwen2.5:3b`, `phi4-mini`)

### 2. Backend Setup
```bash
# Clone the repository
git clone https://github.com/naveencmy/Erode_Kural-Poc-.git
cd Erode_Collectrate/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Seed sample administrative datasets
python data/seed_datasets.py

# Run development server
python main.py --mode all
```

### 3. Frontend Setup
```bash
cd ../frontend

# Install node dependencies
npm install

# Start Vite dev server
npm run dev
```

---

## 🌿 Branching & Commit Guidelines

### Branch Naming Conventions
- `feature/<module-name>-<short-description>` (e.g., `feature/data-viz-scatter-labels`)
- `fix/<issue-number>-<short-description>` (e.g., `fix/rag-timeout-fallback`)
- `refactor/<subsystem-name>` (e.g., `refactor/extractor-multi-format`)
- `docs/<topic>` (e.g., `docs/apache-license-update`)

### Conventional Commits
Please structure your commit messages as follows:
```text
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: A new feature for users or administrative workflows
- `fix`: A bug fix
- `docs`: Documentation updates
- `style`: Code style changes (formatting, missing semicolons)
- `refactor`: Code refactoring without behavioral alterations
- `perf`: Performance optimization
- `test`: Adding or updating test suites
- `chore`: Dependency updates, tooling, or build configuration

---

## 🏛️ Architectural Principles

When contributing code, you must uphold the following core system tenets:

1. **Local-First & Air-Gapped Compatibility:**
   - No feature may require external proprietary cloud APIs (e.g., OpenAI, Anthropic) for core operations. All models run on local Ollama / ONNX runtimes.
2. **Zero Hallucination Barrier:**
   - All AI claims, summary figures, and draft slots must be grounded with exact page, chunk, or cell provenance.
   - Any missing entity slot must resolve to `[தகவல் இல்லை — கைமுறையாக நிரப்பவும்]` rather than a generated guess.
3. **AST-Enforced Sandboxing:**
   - Any natural language query that generates executable code (e.g., Pandas or SQL transformations) must pass through `ast.parse` and whitelist validation. `exec()`, `eval()`, `__import__`, `os`, `sys`, and `subprocess` are strictly forbidden.
4. **Tamil-First Bilingualism:**
   - All UI elements, error messages, and administrative templates must provide authentic, high-register Tamil (நற்றமிழ்) alongside formal administrative English.

---

## 🧪 Testing Guidelines

Before opening a pull request, ensure all test suites pass with 100% success rate:

```bash
# Run complete backend pytest suite
cd backend
pytest tests/ -v

# Run frontend build check
cd ../frontend
npm run build
```

---

## ✅ Pull Request Checklist

Before submitting your PR, verify:
- [ ] Code follows PEP 8 (Python) and ESLint/Prettier (JavaScript/React).
- [ ] Added unit or integration tests for new functionality.
- [ ] All 23+ backend tests pass with `pytest`.
- [ ] Frontend builds cleanly with `npm run build` with zero compiler errors.
- [ ] Updated documentation or docstrings where applicable.
- [ ] Verified no sensitive tokens, passwords, or personal citizen data are committed.

---

## 📄 License

By contributing to this repository, you agree that your contributions will be licensed under the **Apache License 2.0**.
