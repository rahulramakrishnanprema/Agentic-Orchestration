# Deployment Document for CALC-1

## Metadata
- Issue Key: CALC-1
- Summary: Create the Calculator
- Created At: 2023-10-27T10:00:00Z
- Version: 1.0

## Project Overview
- Description: Build a basic arithmetic calculator web application. This application will allow users to input two numbers and select an arithmetic operation (+, -, *, /) to get a result. The project will cover setting up the web framework, implementing the core calculation logic, developing a user-friendly interface, and ensuring the application's functionality through testing.
- Project Type: web app
- Architecture: MVC (Model-View-Controller) pattern, with Flask acting as the controller, HTML templates as the view, and Python modules for the model/logic.

## Implementation Plan
### Subtasks
- Establish Project Foundation and Develop User Interface
- Implement Core Calculator Logic and User Interaction
- Validate Functionality and User Experience

### Execution Order
- Establish Project Foundation and Develop User Interface
- Implement Core Calculator Logic and User Interaction
- Validate Functionality and User Experience

### Dependencies
- Establish Project Foundation and Develop User Interface: None
- Implement Core Calculator Logic and User Interaction: Establish Project Foundation and Develop User Interface
- Validate Functionality and User Experience: Implement Core Calculator Logic and User Interaction

### Parallel Groups
- None

### Critical Path
- Establish Project Foundation and Develop User Interface
- Implement Core Calculator Logic and User Interaction
- Validate Functionality and User Experience

## File Structure
### Files
- app.py: python - Main Flask application entry point, handles routing and serves web pages.
- calculator.py: python - Contains the core arithmetic logic for the calculator operations.
- requirements.txt: text - Lists all Python dependencies required for the project.
- config.py: python - Stores application configuration settings (e.g., secret key, debug mode).
- index.html: html - The main user interface template for the calculator.
- style.css: css - Provides styling for the calculator's user interface.
- script.js: javascript - Optional client-side scripting for enhanced user interaction or validation.
- test_calculator.py: python - Unit tests for the core calculator logic in calculator.py.

### Folder Structure
```
calculator_app/
├── app.py
├── calculator.py
├── requirements.txt
├── config.py
├── templates/
│   └── index.html
├── static/
│   ├── style.css
│   └── script.js
└── tests/
    └── test_calculator.py
```

### File Types
- python
- text
- html
- css
- javascript

## Technical Specifications
### app.py
- Imports: Flask, render_template, request, redirect, url_for, calculator, config
- Classes: Flask (app instance): The main web application object.
- Functions:
    - index(): Handles GET requests to the root URL, renders the calculator UI.
    - calculate(): Handles POST requests from the calculator form, processes input, calls calculator logic, and displays results.
- Data Structures: request.form: Dictionary-like object containing form data (num1, num2, operation).
- Logic Flows:
    1. Initialization: Create Flask app instance, load configuration from config.py.
    2. GET /: The `index()` function is called. It renders `index.html` with an empty result or previous result if available.
    3. POST /calculate: The `calculate()` function is called.
        a. Retrieve 'num1', 'num2', 'operation' from `request.form`.
        b. Convert 'num1' and 'num2' to float. Handle `ValueError` if conversion fails.
        c. Call `calculator.calculate_result(num1, num2, operation)`.
        d. Store the result or error message.
        e. Re-render `index.html` passing the result/error and original inputs.
- Error Handling:
    - ValueError: Catches errors during string-to-float conversion for numbers.
    - ZeroDivisionError: Catches division by zero errors from `calculator.py`.
    - General Exception: Catches any other unexpected errors during calculation.
    - Error messages are passed to the `index.html` template for display to the user.
- Connections:
    - Connects to `calculator.py` for core logic execution.
    - Renders `templates/index.html` for user interface.
    - Utilizes `config.py` for application settings.
    - Receives input from and sends output to the web browser (user interaction).
- Subtasks: Establish Project Foundation and Develop User Interface, Implement Core Calculator Logic and User Interaction

### calculator.py
- Imports: None
- Classes: None
- Functions:
    - calculate_result(num1: float, num2: float, operation: str) -> float | str: Performs the specified arithmetic operation on two numbers.
- Data Structures:
    - num1, num2: float (input numbers)
    - operation: str (e.g., '+', '-', '*', '/')
- Logic Flows:
    1. Input Validation: Ensure num1 and num2 are valid numbers (already handled by app.py conversion, but could add more checks here).
    2. Operation Dispatch: Use if/elif/else statements to match the 'operation' string.
        a. '+': Return `num1 + num2`.
        b. '-': Return `num1 - num2`.
        c. '*': Return `num1 * num2`.
        d. '/': Check if `num2` is zero. If so, raise `ZeroDivisionError`. Otherwise, return `num1 / num2`.
        e. Default: If operation is not recognized, return an error message string or raise a `ValueError`.
- Error Handling:
    - ZeroDivisionError: Explicitly raised if division by zero is attempted.
    - ValueError: Can be raised for unsupported operations.
- Connections:
    - Called by `app.py` to perform calculations.
- Subtasks: Implement Core Calculator Logic and User Interaction

### templates/index.html
- Imports: None
- Classes: None
- Functions: None
- Data Structures:
    - HTML form elements: input fields for numbers, select dropdown for operations, submit button.
    - Display area for results and error messages.
- Logic Flows:
    1. Page Load: Displays a title, input fields for 'Number 1' and 'Number 2'.
    2. Operation Selection: A dropdown menu (`<select>`) with options for '+', '-', '*', '/'.
    3. Submission: A 'Calculate' button (`<input type='submit'>`) that submits the form data to the `/calculate` endpoint.
    4. Result Display: An area (`<div>` or `<p>`) to show the calculated 'Result' or any 'Error' message passed from the Flask backend.
- Error Handling:
    - Displays error messages passed from the backend (e.g., 'Invalid input', 'Division by zero').
    - Optional: Client-side JavaScript (`script.js`) could add basic input validation before form submission.
- Connections:
    - Rendered by `app.py`.
    - Links to `static/style.css` for styling.
    - Can link to `static/script.js` for client-side logic.
    - Submits data to `app.py` via HTTP POST.
- Subtasks: Establish Project Foundation and Develop User Interface

### tests/test_calculator.py
- Imports: unittest, calculator
- Classes: TestCalculator(unittest.TestCase): A test suite for the calculator logic.
- Functions:
    - test_addition(): Tests the addition operation.
    - test_subtraction(): Tests the subtraction operation.
    - test_multiplication(): Tests the multiplication operation.
    - test_division(): Tests the division operation with valid inputs.
    - test_division_by_zero(): Tests the division operation with zero as divisor, expecting an error.
    - test_invalid_operation(): Tests an unsupported operation, expecting an error or specific handling.
- Data Structures: Test cases: Tuples or dictionaries containing input numbers, operation, and expected output/exception.
- Logic Flows:
    1. Setup: Each test method initializes specific inputs.
    2. Execution: Calls `calculator.calculate_result()` with the test inputs.
    3. Assertion: Uses `self.assertEqual()` to check if the actual result matches the expected result.
    4. Exception Testing: Uses `with self.assertRaises(ExpectedError):` to verify that specific error conditions raise the correct exceptions.
- Error Handling: Tests explicitly check for `ZeroDivisionError` and other potential `ValueError` scenarios from `calculator.py`.
- Connections: Imports and tests functions from `calculator.py`.
- Subtasks: Validate Functionality and User Experience

## Deployment Instructions
### Setup
1. Clone the repository: `git clone <repository_url> calculator_app`
2. Navigate into the project directory: `cd calculator_app`
3. Create a Python virtual environment: `python3 -m venv venv`
4. Activate the virtual environment:
   - On macOS/Linux: `source venv/bin/activate`
   - On Windows: `.\\venv\\Scripts\\activate`
5. Install required Python packages: `pip install -r requirements.txt`

### Build
For this Flask application, there is no explicit 'build' step like compiling. The application runs directly from its Python source files.

### Run
1. Ensure the virtual environment is activated (see setup step 4).
2. Set Flask environment variables:
   - On macOS/Linux: `export FLASK_APP=app.py`
   - On Windows: `set FLASK_APP=app.py`
   - (Optional, for development) On macOS/Linux: `export FLASK_ENV=development`
   - (Optional, for development) On Windows: `set FLASK_ENV=development`
3. Start the Flask development server: `flask run`
4. Access the application in your web browser at `http://127.0.0.1:5000` (or the address shown in the console).

### Environment Variables
- FLASK_APP: Specifies the main application file (e.g., `app.py`) that Flask should run.
- FLASK_ENV: Sets the environment mode for Flask. 'development' enables debug features like auto-reloading and debugger. 'production' disables these for security and performance.

### Testing
1. Ensure the virtual environment is activated (see setup step 4).
2. Navigate to the project root directory.
3. Run the unit tests using the Python unittest module:
   `python -m unittest discover tests`
4. Review the test output to ensure all tests pass, indicating the core logic is functioning correctly.
5. Manual UI Testing: Open the application in a web browser (after running it) and perform various calculations, including edge cases like division by zero, large numbers, and invalid inputs, to validate the user experience and error handling.