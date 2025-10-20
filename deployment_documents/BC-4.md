# Deployment Document for **CALC-001**

## Metadata
- **Issue Key:** CALC-001  
- **Summary:** Create the Calculator  
- **Created At:** 2025-10-20T12:00:00Z  
- **Version:** 1.0  

## Project Overview
- **Description:** A minimal web‑based arithmetic calculator that supports addition, subtraction, multiplication, division, clear, and equals operations. The UI consists of a display screen and a keypad. The app runs entirely in the browser with no backend.  
- **Project Type:** web app  
- **Architecture:** Simple client‑side MVC‑like separation (HTML view, CSS styling, JavaScript controller)  

## Implementation Plan  

### Subtasks
1. Subtask 1: Create project skeleton with essential files: `index.html`, `style.css`, `app.js` and a `README`  
2. Subtask 2: Design HTML layout: display screen, numeric keypad (0‑9), operation buttons (+, -, *, /), clear and equals  
3. Subtask 3: Add CSS styling for a clean, responsive layout (flex/grid, button sizing, display readability)  
4. Subtask 4: Implement core JavaScript logic in `app.js`: capture button clicks, build expression string, evaluate using safe parsing, update display  
5. Subtask 5: Add error handling: prevent invalid sequences, handle division by zero, display user‑friendly error messages  

### Execution Order
1. 1  
2. 2  
3. 3  
4. 4  
5. 5  

### Dependencies
- **2:** Prerequisite – 1  
- **3:** Prerequisite – 2  
- **4:** Prerequisite – 3  
- **5:** Prerequisite – 4  

### Parallel Groups
*None*  

### Critical Path
1 → 2 → 3 → 4 → 5  

## File Structure  

### Files
- **index.html** – *HTML* – Defines the calculator UI – display area and all buttons  
- **style.css** – *CSS* – Provides layout, sizing, colors and responsive behavior  
- **app.js** – *JavaScript* – Handles user interaction, expression parsing, evaluation and error handling  
- **README.md** – *Markdown* – Project description, setup, run instructions  

### Folder Structure
- **root**
  - `index.html`
  - `style.css`
  - `app.js`
  - `README.md`  

### File Types
- HTML  
- CSS  
- JavaScript  
- Markdown  

## Technical Specifications  

### index.html
- **Imports:** None  
- **Classes:** None  
- **Functions:** None  
- **Data Structures:** None  
- **Logic Flows:**  
  - Static markup defines a `<div id="display">` for showing the current expression/result.  
  - A `<div class="keypad">` contains button elements with `data-value` attributes for numbers and operators.  
  - Each button has a class `btn` and a unique id for potential future extensions.  
- **Error Handling:** None  
- **Connections:**  
  - `app.js` attaches event listeners to all elements with class `btn` using `document.querySelectorAll('.btn')`.  
  - When a button is clicked, `app.js` reads the button’s `data-value` attribute to determine the input.  
  - `app.js` updates the `innerText` of the `#display` element to reflect the current expression or result.  

### style.css
- **Imports:** None  
- **Classes:** None  
- **Functions:** None  
- **Data Structures:** None  
- **Logic Flows:**  
  - Root container uses `display: flex; flex-direction: column;` to stack display and keypad.  
  - Keypad uses grid layout with 4 columns for uniform button sizing.  
  - Responsive media query adjusts button font‑size for smaller viewports.  
- **Error Handling:** None  
- **Connections:**  
  - Linked in `index.html` via `<link rel="stylesheet" href="style.css">`.  
  - All class names referenced in the HTML (e.g., `.display`, `.keypad`, `.btn`) have corresponding style rules.  

### app.js
- **Imports:** None  
- **Classes:** None  
- **Functions:**  
  1. **initCalculator()** – Runs on `DOMContentLoaded`; registers click listeners for all calculator buttons.  
  2. **handleButtonClick(event)** – Extracts the button’s `data-value`, validates the input sequence, updates the expression string, and calls `updateDisplay`.  
  3. **updateDisplay(value)** – Sets the `innerText` of the `#display` element to the provided value.  
  4. **evaluateExpression(expr)** – Safely parses the arithmetic expression using the `Function` constructor with restricted characters, handles division by zero, and returns the result or throws an error.  
  5. **clearDisplay()** – Resets the internal expression string to empty and updates the display to `'0'`.  
  6. **showError(message)** – Displays a user‑friendly error message in the `#display` element and clears after 2 seconds.  
- **Data Structures:**  
  - `let currentExpression = ""; // holds the building arithmetic string`  
- **Logic Flows:**  
  - On page load, `initCalculator` registers click listeners.  
  - When a numeric or operator button is pressed, `handleButtonClick` validates the sequence (e.g., no two operators in a row).  
  - If the equals button (`=`) is pressed, `evaluateExpression` is called with `currentExpression`; result is shown via `updateDisplay`.  
  - If clear (`C`) is pressed, `clearDisplay` resets state.  
  - Any caught error (syntax error, division by zero) triggers `showError`.  
- **Error Handling:**  
  - Prevent multiple consecutive operators.  
  - Disallow starting expression with an operator except minus for negative numbers.  
  - Catch exceptions from `evaluateExpression` and display a friendly message.  
  - Specific check for division by zero inside `evaluateExpression`.  
- **Connections:**  
  - `initCalculator` is invoked from a `<script>` tag at the end of `index.html` after the DOM is ready.  
  - `handleButtonClick` reads `button.dataset.value` (defined in `index.html`) and manipulates `currentExpression`.  
  - `updateDisplay` directly modifies the DOM element with id `display` defined in `index.html`.  
  - `evaluateExpression` returns a numeric result which is passed to `updateDisplay`.  
  - `clearDisplay` and `showError` also interact with the `#display` element.  

### README.md
- **Imports:** None  
- **Classes:** None  
- **Functions:** None  
- **Data Structures:** None  
- **Logic Flows:** None  
- **Error Handling:** None  
- **Connections:** Provides instructions for developers to open `index.html` in a browser; no runtime connections.  

## Deployment Instructions  

### Setup
- Ensure a modern web browser is installed (Chrome, Firefox, Edge, Safari).  
- (Optional) Install a lightweight static server, e.g., `npm install -g serve`, if you prefer to serve files over HTTP.  

### Build
- No build step required – the project consists of static assets.  

### Run
- **Method 1 (quick):** Double‑click `index.html` in the file explorer to open it in the default browser.  
- **Method 2 (static server):**  

```bash
serve .
```

Then navigate to `http://localhost:3000` in a browser.  

### Environment Variables
*None*