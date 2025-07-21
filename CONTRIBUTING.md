# Contributing to ServeML

First off, thank you for considering contributing to ServeML! It's people like you that make ServeML such a great tool for the ML community.

## 🤝 Code of Conduct

This project and everyone participating in it is governed by the [ServeML Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## 🚀 How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check existing issues to avoid duplicates. When creating a bug report, please include:

- A clear and descriptive title
- Steps to reproduce the behavior
- Expected behavior
- Screenshots (if applicable)
- Your environment details (OS, Python version, etc.)

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, please include:

- A clear and descriptive title
- A detailed description of the proposed enhancement
- Why this enhancement would be useful to most ServeML users
- Possible implementation approach (if you have ideas)

### Your First Code Contribution

Unsure where to begin? Look for these tags:

- `good first issue` - Simple issues perfect for beginners
- `help wanted` - Issues where we need community help
- `documentation` - Help improve our docs

## 📝 Development Process

1. **Fork the Repository**
   ```bash
   git clone https://github.com/yourusername/serveml.git
   cd serveml
   ```

2. **Create a Branch**
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/issue-description
   ```

3. **Set Up Development Environment**
   
   **Backend:**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements-dev.txt
   ```
   
   **Frontend:**
   ```bash
   cd frontend
   npm install
   ```

4. **Make Your Changes**
   - Write clean, readable code
   - Follow existing code style
   - Add tests for new functionality
   - Update documentation as needed

5. **Test Your Changes**
   
   **Backend:**
   ```bash
   pytest tests/
   flake8 app/
   black app/ --check
   ```
   
   **Frontend:**
   ```bash
   npm run test
   npm run lint
   ```

6. **Commit Your Changes**
   ```bash
   git add .
   git commit -m "feat: add new feature" # or "fix: resolve issue"
   ```
   
   We follow [Conventional Commits](https://www.conventionalcommits.org/):
   - `feat:` New feature
   - `fix:` Bug fix
   - `docs:` Documentation changes
   - `style:` Code style changes
   - `refactor:` Code refactoring
   - `test:` Test additions/changes
   - `chore:` Maintenance tasks

7. **Push and Create Pull Request**
   ```bash
   git push origin feature/your-feature-name
   ```
   Then create a PR on GitHub!

## 🏗️ Project Structure

```
serveml/
├── backend/           # FastAPI backend
│   ├── app/          # Application code
│   ├── tests/        # Backend tests
│   └── templates/    # Docker/app templates
├── frontend/         # React frontend
│   ├── src/         # React source code
│   └── tests/       # Frontend tests
├── infrastructure/   # Terraform configs
└── docs/            # Documentation
```

## 🎯 Areas We Need Help

### Backend (Python/FastAPI)
- Model serving optimization
- Support for new ML frameworks
- API performance improvements
- Security enhancements

### Frontend (React/TypeScript)
- Dashboard UI improvements
- Real-time monitoring features
- Mobile responsiveness
- Accessibility (a11y)

### Infrastructure (AWS/Terraform)
- Cost optimization
- Multi-region support
- Deployment automation
- Monitoring and alerting

### Documentation
- Tutorials and guides
- API documentation
- Video tutorials
- Translation to other languages

## 💅 Style Guidelines

### Python Code Style
- Follow PEP 8
- Use Black for formatting
- Type hints are encouraged
- Docstrings for all public functions

### JavaScript/TypeScript Code Style
- Use ESLint and Prettier
- Functional components with hooks
- TypeScript for type safety
- Clear component documentation

### Commit Messages
- Keep the first line under 50 characters
- Use present tense ("Add feature" not "Added feature")
- Reference issues and PRs liberally

## 🔍 Pull Request Process

1. **Before Submitting**
   - Ensure all tests pass
   - Update documentation
   - Add your changes to CHANGELOG.md
   - Ensure no merge conflicts

2. **PR Description Template**
   ```markdown
   ## Description
   Brief description of changes
   
   ## Type of Change
   - [ ] Bug fix
   - [ ] New feature
   - [ ] Breaking change
   - [ ] Documentation update
   
   ## Testing
   - [ ] Tests pass locally
   - [ ] Added new tests
   
   ## Checklist
   - [ ] Code follows style guidelines
   - [ ] Self-reviewed code
   - [ ] Updated documentation
   ```

3. **Review Process**
   - PRs require at least one approving review
   - Address all feedback
   - Keep discussions focused and professional

## 🎁 Recognition

Contributors are recognized in our:
- README.md contributors section
- Release notes
- Monthly community highlights

## ❓ Questions?

Feel free to:
- Open a [Discussion](https://github.com/yourusername/serveml/discussions)
- Join our [Discord](https://discord.gg/serveml)
- Email us at contributors@serveml.com

## 🙏 Thank You!

Every contribution, no matter how small, helps make ServeML better for everyone. We're excited to see what you'll build!

---

<div align="center">
  <b>Happy Contributing! 🎉</b>
</div>