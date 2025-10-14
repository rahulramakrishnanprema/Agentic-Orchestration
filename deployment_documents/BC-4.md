# Deployment Document for JIRA-123

## Metadata
- **Issue Key:** JIRA-123  
- **Summary:** Create the Calculator  
- **Created At:** 2025-10-14T12:00:00Z  
- **Version:** 1.0  

## Project Overview
- **Description:** Build a basic arithmetic calculator web application  
- **Project Type:** web app  
- **Architecture:** MVC  

## Implementation Plan
### Subtasks
- Subtask 1: Initialize the project repository, install core dependencies, and build a responsive calculator UI.  
- Subtask 2: Create core arithmetic utilities, wire them to the UI, and implement comprehensive input validation and error handling.  
- Subtask 3: Write unit tests for arithmetic utilities and integration tests for UI interactions to achieve at least 80% coverage.  
- Subtask 4: Deploy the application to a staging environment, perform manual QA, and document any final bugs for resolution.  

### Execution Order
- 1, 2, 3, 4  

### Dependencies
- Subtask 1: None  
- Subtask 2: 1  
- Subtask 3: 2  
- Subtask 4: 3  

### Parallel Groups
- None  

### Critical Path
- 1, 2, 3, 4  

## File Structure
### Files
- **app.py** – python – Flask backend, arithmetic utilities, request handling, validation, error handling, and test suite  
- **templates/index.html** – html – Calculator UI with form, display, and buttons  
- **static/style.css** – css – Styling for the calculator UI  

### Folder Structure
- root  
  - app.py  
  - templates  
    - index.html  
  - static  
    - style.css  

### File Types
- python  
- html  
- css  

## Technical Specifications
### app.py
- **Imports:** flask, flask.render_template, flask.request, flask.jsonify, unittest  
- **Classes:**  
  - Calculator – Provides static methods for basic arithmetic operations and input validation.  
- **Functions:**  
  - add(a, b) – returns float – Returns the sum of a and b.  
  - subtract(a, b) – returns float – Returns the difference of a and b.  
  - multiply(a, b) – returns float – Returns the product of a and b.  
  - divide(a, b) – returns float – Returns the quotient of a divided by b; raises ZeroDivisionError if b is zero.  
  - validate_input(value) – returns float – Attempts to convert value to float; raises ValueError if conversion fails.  
  - calculate(operation, a, b) – returns float – Dispatches to the appropriate arithmetic method based on operation.  
  - handle_request() – returns flask.Response – Handles POST requests from the UI, validates inputs, performs calculation, and returns JSON.  
  - run_tests() – returns None – Executes unit tests for arithmetic utilities and integration tests using Flask test client.  
- **Data Structures:**  
  - OPERATIONS = { '+': Calculator.add, '-': Calculator.subtract, '*': Calculator.multiply, '/': Calculator.divide }  
- **Logic Flows:**  
  1. Receive POST request with operation, operand1, operand2.  
  2. Validate both operands using validate_input; if invalid, return error JSON.  
  3. Retrieve operation function from OPERATIONS; if unsupported, return error JSON.  
  4. Execute operation; catch ZeroDivisionError and return error JSON.  
  5. Return result JSON with success flag.  
  6. run_tests() creates unittest.TestCase subclasses for each arithmetic method and for Flask integration using test client.  
- **Error Handling:**  
  - Invalid numeric input results in 400 Bad Request with message 'Invalid input'.  
  - Unsupported operation results in 400 Bad Request with message 'Unsupported operation'.  
  - Division by zero results in 400 Bad Request with message 'Division by zero'.  
- **Connections:**  
  - Renders templates/index.html for GET requests.  
  - Serves static/style.css via Flask static route.  
  - Unit tests and integration tests are defined within the same file to keep the project to three files.  

### templates/index.html
- **Imports:** None  
- **Classes:** None  
- **Functions:** None  
- **Data Structures:** None  
- **Logic Flows:**  
  1. Display a simple calculator layout with a display area and buttons for digits, operations, clear, and equals.  
  2. On button press, update the display or send a POST request to /calculate with operation and operands.  
  3. Receive JSON response and update the display with result or error message.  
- **Error Handling:**  
  - If the server returns an error, display the error message in the display area.  
- **Connections:**  
  - Form action posts to /calculate handled by app.py.  
  - Links to static/style.css for styling.  

### static/style.css
- **Imports:** None  
- **Classes:**  
  - .calculator – Container for the calculator UI.  
  - .display – Display area for input and results.  
  - .button – Styling for calculator buttons.  
- **Functions:** None  
- **Data Structures:** None  
- **Logic Flows:**  
  1. Define layout grid for calculator.  
  2. Style buttons with hover and active states.  
  3. Ensure responsive design for mobile screens.  
- **Error Handling:** None  
- **Connections:**  
  - Linked from templates/index.html.  

## Deployment Instructions
### Setup
- Create a virtual environment: `python -m venv venv`  
- Activate the virtual environment: `source venv/bin/activate` (Linux/macOS) or `venv\Scripts\activate` (Windows)  
- Install dependencies: `pip install flask`  

### Build
- None  

### Run
- Set environment variables: `export FLASK_APP=app.py && export FLASK_ENV=development`  
- Start the server: `flask run`  
- Open a browser and navigate to `http://127.0.0.1:5000` to use the calculator.  

### Environment Variables
- **FLASK_APP:** Path to the Flask application module (app.py)  
- **FLASK_ENV:** Set to 'development' for debug mode  

### Testing
- Run unit and integration tests: `python app.py`  
- The script will execute the test suite and print results to the console.