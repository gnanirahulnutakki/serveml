# Security Policy

## Supported Versions

Currently supporting security updates for:

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability within ServeML, please send an email to security@serveml.com. All security vulnerabilities will be promptly addressed.

Please include the following information:
- Type of issue (e.g., buffer overflow, SQL injection, cross-site scripting, etc.)
- Full paths of source file(s) related to the manifestation of the issue
- The location of the affected source code (tag/branch/commit or direct URL)
- Any special configuration required to reproduce the issue
- Step-by-step instructions to reproduce the issue
- Proof-of-concept or exploit code (if possible)
- Impact of the issue, including how an attacker might exploit it

## Security Update Process

1. Security patches are released as soon as possible after discovery
2. Critical vulnerabilities are patched within 24-48 hours
3. Dependencies are automatically monitored via GitHub Dependabot
4. Regular security audits are performed using:
   - Bandit for Python code analysis
   - Safety for dependency checking
   - Trivy for container scanning

## Security Best Practices

When deploying ServeML:
1. Always use HTTPS for API endpoints
2. Implement proper authentication and authorization
3. Regularly update all dependencies
4. Monitor security advisories for all components
5. Use least-privilege IAM policies in AWS
6. Enable AWS CloudTrail for audit logging
7. Encrypt sensitive data at rest and in transit