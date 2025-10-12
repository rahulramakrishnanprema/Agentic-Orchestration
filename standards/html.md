# HTML Coding Standards

## General Guidelines
- Use HTML5 semantic elements
- Write valid, well-structured HTML
- Use consistent indentation and formatting
- Include proper DOCTYPE declaration
- Ensure accessibility compliance

## Document Structure
- Always include DOCTYPE declaration: `<!DOCTYPE html>`
- Use proper HTML5 document structure
- Include meta tags for character encoding and viewport
- Use meaningful title tags

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Descriptive Page Title</title>
</head>
<body>
    <!-- Page content -->
</body>
</html>
```

## Semantic Elements
- Use appropriate semantic HTML5 elements
- `<header>`, `<nav>`, `<main>`, `<section>`, `<article>`, `<aside>`, `<footer>`
- Use `<h1>` through `<h6>` for proper heading hierarchy
- Use `<p>` for paragraphs, not `<div>` or `<br>` tags

## Accessibility
- Include `alt` attributes for all images
- Use proper form labels and input associations
- Ensure proper heading hierarchy
- Include `lang` attribute on html element
- Use ARIA attributes when necessary
- Ensure keyboard navigation support

```html
<!-- Good accessibility practices -->
<img src="logo.png" alt="Company Logo">

<label for="email">Email Address:</label>
<input type="email" id="email" name="email" required>

<button aria-label="Close dialog">×</button>
```

## Forms
- Always associate labels with form controls
- Use appropriate input types (email, tel, date, etc.)
- Include required attributes where applicable
- Group related form elements with fieldset
- Provide clear error messages and validation

## Attributes and Values
- Use lowercase for element names and attributes
- Always quote attribute values
- Use meaningful class and id names
- Avoid inline styles and JavaScript
- Use data attributes for custom data

## Best Practices
- Keep HTML clean and semantic
- Separate content, presentation, and behavior
- Use external CSS and JavaScript files
- Optimize for performance (minimize HTTP requests)
- Validate HTML markup
- Use consistent naming conventions

## Performance
- Minimize HTTP requests
- Optimize images (size, format, lazy loading)
- Use efficient CSS and JavaScript loading
- Implement proper caching strategies
- Consider Progressive Web App features

## SEO Considerations
- Use descriptive title tags
- Include meta descriptions
- Use proper heading hierarchy
- Implement structured data markup
- Create user-friendly URLs
- Optimize page loading speed

## Code Organization
- Use consistent indentation (2 or 4 spaces)
- Group related elements together
- Add comments for complex sections
- Keep line length reasonable
- Use meaningful element organization

## Validation
- Validate HTML markup regularly
- Fix validation errors and warnings
- Test across different browsers
- Ensure responsive design
- Test accessibility compliance