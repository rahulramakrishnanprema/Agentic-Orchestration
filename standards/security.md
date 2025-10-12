# Security Guidelines for All Languages

## OWASP Top 10 Security Guidelines

### 1. Injection Vulnerabilities
- **SQL Injection**: Always use parameterized queries or prepared statements
- **Code Injection**: Never use eval(), exec(), or similar functions with user input
- **Command Injection**: Validate and sanitize all system command inputs
- **LDAP/NoSQL Injection**: Use proper input validation and parameterized queries

**Prevention:**
```python
### 2. Broken Authentication
- Use strong password policies
- Implement proper session management
- Use multi-factor authentication where possible
- Secure password storage with proper hashing (bcrypt, Argon2)

### 3. Sensitive Data Exposure
- Encrypt sensitive data at rest and in transit
- Use HTTPS for all communications
- Never log sensitive information (passwords, tokens, keys)
- Implement proper access controls

### 4. XML External Entities (XXE)
- Disable XML external entity processing
- Use simple data formats like JSON when possible
- Validate and sanitize all XML input

### 5. Broken Access Control
- Implement principle of least privilege
- Verify user permissions on server-side
- Use proper authentication and authorization
- Regularly audit access controls

### 6. Security Misconfiguration
- Keep all software up to date
- Remove default accounts and passwords
- Disable unnecessary features and services
- Implement proper error handling (don't expose stack traces)

### 7. Cross-Site Scripting (XSS)
- Sanitize all user input before output
- Use Content Security Policy (CSP) headers
- Encode output based on context (HTML, JavaScript, CSS)
- Use frameworks that automatically escape XSS

### 8. Insecure Deserialization
- Validate serialized data integrity
- Use safe deserialization methods
- Implement proper input validation
- Monitor deserialization activities

### 9. Using Components with Known Vulnerabilities
- Keep all dependencies updated
- Use tools like npm audit, pip-audit
- Monitor security advisories
- Remove unused dependencies

### 10. Insufficient Logging & Monitoring
- Log all security-relevant events
- Monitor for suspicious activities
- Implement proper incident response
- Use centralized logging systems

## Language-Specific Security Guidelines

### Python Security
- Use `secrets` module for cryptographic randomness
- Avoid `pickle` for untrusted data
- Use `subprocess` with shell=False
- Validate all inputs with proper type checking

### JavaScript Security
- Use strict mode ('use strict')
- Avoid `innerHTML` with user data
- Use `textContent` instead of `innerHTML` when possible
- Implement proper CORS policies

### Java Security
- Use PreparedStatement for database queries
- Validate inputs with proper sanitization
- Use secure random number generation
- Implement proper exception handling

### Web Security (HTML/CSS)
- Implement Content Security Policy
- Use HTTPS for all resources
- Validate form inputs on both client and server
- Use secure cookie attributes (HttpOnly, Secure, SameSite)

## Security Testing Guidelines

### Code Review Checklist
- [ ] No hardcoded credentials or secrets
- [ ] Proper input validation implemented
- [ ] Error handling doesn't expose sensitive information
- [ ] Authentication and authorization properly implemented
- [ ] All user inputs are sanitized
- [ ] Database queries use parameterized statements
- [ ] Sensitive data is properly encrypted
- [ ] Logging doesn't include sensitive information
- [ ] Dependencies are up to date
- [ ] Security headers are implemented

### Security Testing Tools
- **Static Analysis**: SonarQube, Veracode, Checkmarx
- **Dependency Scanning**: OWASP Dependency Check, Snyk
- **Dynamic Testing**: OWASP ZAP, Burp Suite
- **Infrastructure**: Nessus, OpenVAS

## Compliance Requirements

### Data Protection
- Follow GDPR/CCPA requirements for data handling
- Implement data minimization principles
- Provide data deletion capabilities
- Maintain audit trails for data access

### Industry Standards
- **PCI DSS**: For payment card data
- **HIPAA**: For healthcare information
- **SOX**: For financial reporting
- **ISO 27001**: For information security management

## Incident Response

### Security Incident Handling
1. **Identification**: Detect and analyze security events
2. **Containment**: Limit the scope and impact
3. **Eradication**: Remove the threat from the environment
4. **Recovery**: Restore systems to normal operation
5. **Lessons Learned**: Document and improve processes

### Emergency Contacts
- Security team escalation procedures
- Legal team notification requirements
- Customer communication protocols
- Regulatory reporting obligations