# Deployment Document for IPM-001

## Metadata
- Issue Key: IPM-001
- Summary: Investment Portfolio Management
- Created At: 2023-10-27T10:00:00Z
- Version: 1.0

## Project Overview
- Description: Build a minimal viable product (MVP) web user interface with dummy data for managing client stock portfolios focused on Indian equity markets. The application will store portfolio details, provide advisory signals (Buy/Hold/Sell) based on historical performance, technical indicators, sector potential, and market buzz, and present visuals and reports for advisors only.
- Project Type: Web Application
- Architecture: Layered Architecture (Presentation, Business Logic, Data Access) using Flask/Python

## Implementation Plan
### Subtasks
- Establish Core Infrastructure, Data Foundation, and Advisor Authentication
- Develop Portfolio Management and Advisory Signal Features
- Deliver Advisor Visuals, Reports, and Ensure MVP Viability

### Execution Order
- subtask_1
- subtask_2
- subtask_3

### Dependencies
- subtask_1: None
- subtask_2: subtask_1
- subtask_3: subtask_2

### Parallel Groups
- No parallel groups defined.

### Critical Path
- subtask_1
- subtask_2
- subtask_3

## File Structure
### Files
- app.py: python - Main Flask application entry point, configuration loading, and blueprint registration.
- config.py: python - Application configuration settings (database URI, secret key, debug mode).
- requirements.txt: text - Lists all Python dependencies required for the project.
- database.py: python - Initializes SQLAlchemy, manages database connection and session.
- models.py: python - Defines SQLAlchemy ORM models for User, Portfolio, StockHolding, and AdvisorySignal.
- auth_routes.py: python - Flask blueprint for user authentication routes (login, register, logout).
- portfolio_routes.py: python - Flask blueprint for portfolio management routes (create, view, update, delete portfolios and holdings).
- advisory_routes.py: python - Flask blueprint for displaying advisory signals for portfolios.
- report_routes.py: python - Flask blueprint for generating and displaying portfolio reports.
- services/portfolio_service.py: python - Business logic for portfolio operations (CRUD, valuation calculations).
- services/advisory_service.py: python - Business logic for generating advisory signals based on various indicators.
- services/report_service.py: python - Business logic for compiling and formatting portfolio reports.
- utils/data_loader.py: python - Script to load dummy historical stock data and initial user/portfolio data.
- utils/technical_indicators.py: python - Helper functions for calculating technical indicators (e.g., SMA, RSI, MACD).
- templates/base.html: html - Base Jinja2 template for common layout, navigation, and styling.
- templates/auth/login.html: html - HTML template for the advisor login form.
- templates/auth/register.html: html - HTML template for advisor registration.
- templates/dashboard.html: html - HTML template for the main advisor dashboard displaying an overview.
- templates/portfolio/list.html: html - HTML template to list all managed client portfolios.
- templates/portfolio/detail.html: html - HTML template to display detailed information for a specific portfolio.
- templates/advisory/signals.html: html - HTML template to display generated advisory signals for a portfolio.
- templates/reports/summary.html: html - HTML template to display a summary report for a portfolio.
- static/css/style.css: css - Custom CSS styles for the web application.
- static/js/main.js: javascript - Custom JavaScript for interactive elements and client-side logic.
- static/img/logo.png: image - Application logo or other static images.
- Dockerfile: dockerfile - Defines the Docker image for containerized deployment.
- README.md: markdown - Project documentation, setup instructions, and usage guide.
- .env.example: text - Example file for environment variables.

### Folder Structure
```
.
├── app.py
├── config.py
├── requirements.txt
├── database.py
├── models.py
├── auth_routes.py
├── portfolio_routes.py
├── advisory_routes.py
├── report_routes.py
├── services/
│   ├── __init__.py
│   ├── portfolio_service.py
│   ├── advisory_service.py
│   └── report_service.py
├── utils/
│   ├── __init__.py
│   ├── data_loader.py
│   └── technical_indicators.py
├── templates/
│   ├── base.html
│   ├── auth/
│   │   ├── login.html
│   │   └── register.html
│   ├── portfolio/
│   │   ├── list.html
│   │   └── detail.html
│   ├── advisory/
│   │   └── signals.html
│   ├── reports/
│   │   └── summary.html
│   └── dashboard.html
├── static/
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   └── main.js
│   └── img/
│       └── logo.png
├── Dockerfile
├── README.md
└── .env.example
```

### File Types
- python
- text
- html
- css
- javascript
- image
- dockerfile
- markdown

## Technical Specifications
### app.py
- Imports: Flask, config, database, auth_routes, portfolio_routes, advisory_routes, report_routes
- Classes: None
- Functions: create_app(): Initializes Flask app, loads config, initializes DB, registers blueprints.
- Data Structures: Flask application instance.
- Logic Flows:
  - 1. Load configuration from `config.py`.
  - 2. Initialize SQLAlchemy database instance.
  - 3. Register blueprints for authentication, portfolio, advisory, and reports.
  - 4. Start Flask development server if run directly.
- Error Handling: Basic Flask error handling for 404/500 errors (can be extended with custom error pages).
- Connections:
  - Connects to `config.py` for settings.
  - Connects to `database.py` for DB initialization.
  - Registers blueprints from `auth_routes.py`, `portfolio_routes.py`, `advisory_routes.py`, `report_routes.py`.
  - Related to subtask_1 (Core Infrastructure).

### models.py
- Imports: database (db object), datetime (for timestamps)
- Classes:
  - User: Represents an advisor, with id, username, password_hash, email, created_at. (subtask_1)
  - Portfolio: Represents a client's portfolio, with id, user_id (FK to User), name, description, created_at. (subtask_2)
  - StockHolding: Represents a stock held within a portfolio, with id, portfolio_id (FK to Portfolio), stock_symbol, quantity, purchase_price, purchase_date. (subtask_2)
  - AdvisorySignal: Stores generated signals, with id, portfolio_id (FK to Portfolio), stock_symbol, signal_type (Buy/Hold/Sell), rationale, generated_at. (subtask_2)
- Functions:
  - User.set_password(password): Hashes and sets user password.
  - User.check_password(password): Verifies password against hash.
- Data Structures:
  - SQLAlchemy ORM models mapping to database tables.
  - Relationships: One-to-many (User to Portfolio, Portfolio to StockHolding, Portfolio to AdvisorySignal).
- Logic Flows:
  - 1. Define table schemas and column types.
  - 2. Establish foreign key relationships between models.
  - 3. Implement password hashing for User model.
- Error Handling: Database integrity constraints (e.g., unique usernames, foreign key violations) handled by SQLAlchemy/DB.
- Connections:
  - Connected to `database.py` for `db` instance.
  - Used by `auth_routes.py` for user management.
  - Used by `portfolio_routes.py` and `services/portfolio_service.py` for portfolio data.
  - Used by `advisory_routes.py` and `services/advisory_service.py` for signal data.
  - Related to subtask_1 (Data Foundation) and subtask_2 (Portfolio Management, Advisory Signals).

### services/advisory_service.py
- Imports: database (db object), models (Portfolio, StockHolding, AdvisorySignal), pandas, numpy, utils.technical_indicators, datetime
- Classes: AdvisoryService: Encapsulates business logic for signal generation.
- Functions:
  - AdvisoryService.get_historical_data(stock_symbol, start_date, end_date): Fetches dummy historical stock data.
  - AdvisoryService.generate_signals_for_portfolio(portfolio_id): Main function to generate signals for all holdings in a portfolio.
  - AdvisoryService._analyze_stock(stock_symbol, historical_data): Private method to apply technical indicators and other logic to generate a signal for a single stock.
  - AdvisoryService._evaluate_sector_potential(stock_symbol): Placeholder for sector analysis logic.
  - AdvisoryService._evaluate_market_buzz(stock_symbol): Placeholder for market sentiment analysis.
- Data Structures:
  - Pandas DataFrames for historical stock data.
  - Dictionary/JSON for advisory signal output.
- Logic Flows:
  - 1. For a given portfolio, retrieve all stock holdings.
  - 2. For each stock holding:
    - a. Fetch dummy historical data.
    - b. Calculate technical indicators using `utils.technical_indicators`.
    - c. Apply rules based on historical performance, technical indicators, sector potential, and market buzz.
    - d. Determine 'Buy', 'Hold', or 'Sell' signal.
    - e. Store the generated signal in the `AdvisorySignal` model.
  - 3. Return all generated signals for the portfolio.
- Error Handling:
  - Handle cases where historical data is not available for a stock.
  - Log errors during signal generation.
  - Graceful degradation if external (dummy) data fetching fails.
- Connections:
  - Interacts with `models.py` to retrieve holdings and store signals.
  - Uses `utils.technical_indicators.py` for calculations.
  - Called by `advisory_routes.py` to display signals.
  - Related to subtask_2 (Advisory Signal Features).

### templates/dashboard.html
- Imports: Jinja2 templating engine
- Classes: None
- Functions: None
- Data Structures: Context variables passed from Flask route (e.g., `user`, `portfolios_summary`).
- Logic Flows:
  - 1. Extends `base.html` for consistent layout.
  - 2. Displays advisor's username.
  - 3. Iterates through a summary of client portfolios (e.g., name, total value, number of holdings).
  - 4. Provides links to view detailed portfolio information or generate reports.
  - 5. Includes placeholders for overall market insights or alerts.
- Error Handling: Jinja2 handles missing variables gracefully (can be configured to strict).
- Connections:
  - Rendered by Flask routes (e.g., a main dashboard route in `app.py` or a dedicated `dashboard_routes.py`).
  - Links to `portfolio/list.html`, `advisory/signals.html`, `reports/summary.html`.
  - Related to subtask_3 (Advisor Visuals).

## Deployment Instructions
### Setup
- 1. Clone the repository: `git clone <repository_url>`
- 2. Navigate to the project directory: `cd investment-portfolio-management`
- 3. Create a Python virtual environment: `python3 -m venv venv`
- 4. Activate the virtual environment: `source venv/bin/activate` (Linux/macOS) or `.\venv\Scripts\activate` (Windows)
- 5. Install required Python packages: `pip install -r requirements.txt`
- 6. Create a `.env` file based on `.env.example` and fill in necessary environment variables (e.g., `SECRET_KEY`, `DATABASE_URL`). For MVP, `DATABASE_URL` can point to a local SQLite file (e.g., `sqlite:///site.db`).
- 7. Initialize the database and load dummy data: `python -c 'from app import create_app; from database import db; from utils.data_loader import load_dummy_data; app = create_app(); with app.app_context(): db.create_all(); load_dummy_data()'`

### Build
**For Docker Deployment:**
- 1. Ensure Docker is installed and running.
- 2. Build the Docker image: `docker build -t ipm-app:1.0 .`

### Run
**Local Development (with virtual environment):**
- 1. Activate virtual environment (if not already active): `source venv/bin/activate`
- 2. Run the Flask application: `flask run` (or `python app.py`)
- 3. Access the application in your browser at `http://127.0.0.1:5000`

**Docker Container:**
- 1. Run the Docker container: `docker run -p 5000:5000 --env-file ./.env ipm-app:1.0`
- 2. Access the application in your browser at `http://localhost:5000`

### Environment Variables
- SECRET_KEY: A strong, random string used for session management and security. **REQUIRED**.
- DATABASE_URL: The SQLAlchemy database connection string (e.g., `sqlite:///site.db` for SQLite, `postgresql://user:password@host:port/dbname` for PostgreSQL). **REQUIRED**.
- DEBUG: Set to `True` for development mode (enables debug features, auto-reloading). Set to `False` for production. (Default: `False`)

### Testing
- 1. **Access Login Page**: Navigate to `/login` and attempt to log in with dummy advisor credentials (e.g., `advisor/password`).
- 2. **Portfolio Management**: After logging in, navigate to the dashboard. Create a new portfolio, add some dummy stock holdings.
- 3. **Advisory Signals**: View the advisory signals for a created portfolio. Verify that 'Buy', 'Hold', or 'Sell' signals are displayed with rationale.
- 4. **Reports**: Generate and view a report for a portfolio. Check if key metrics and visuals are present.
- 5. **Authentication**: Test logout functionality. Attempt to access advisor-only pages without logging in (should redirect to login).
- 6. **Data Integrity**: Verify that portfolio and holding data persists after application restart (if using a persistent database).