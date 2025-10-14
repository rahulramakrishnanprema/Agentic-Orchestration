# Deployment Document for ENRG-1234

## Metadata
- **Issue Key:** ENRG-1234  
- **Summary:** Energy trading / market optimization  
- **Created At:** 2025-10-14T12:00:00Z  
- **Version:** 1.0  

## Project Overview
- **Description:** Energy trading / market optimization system that supports market participation, bidding, forecasting, and storage decisions.  
- **Project Type:** API  
- **Architecture:** Microservices with FastAPI, Celery, PostgreSQL, Redis  

## Implementation Plan

### Subtasks
- **Subtask 1:** Design and implement a unified data ingestion and storage platform that collects real‑time market prices, historical price data, demand response signals, and storage status from external APIs and internal databases, normalizes the data, and stores it in a consistent schema.  
- **Subtask 2:** Develop and deploy a high‑accuracy time‑series forecasting model (e.g., Prophet or LSTM) to predict 24‑hour ahead energy prices with a mean absolute error below 5% of the mean price.  
- **Subtask 3:** Build a market participation engine that integrates forecasted prices with market rules to generate optimal buy/sell bids, while incorporating demand response and storage decision logic to determine whether to sell, store, or consume energy.  
- **Subtask 4:** Execute end‑to‑end integration testing, performance benchmarking, and deploy the system to production using CI/CD pipelines, while setting up monitoring dashboards and anomaly alerts for data gaps, forecast drift, or bid execution failures.  

### Execution Order
- ST1 → ST2 → ST3 → ST4  

### Dependencies
- **ST2:** ST1  
- **ST3:** ST1, ST2  
- **ST4:** ST3  

### Parallel Groups
- *None*  

### Critical Path
- ST1 → ST2 → ST3 → ST4  

## File Structure

### Files
- **app/main.py** – python – FastAPI application entry point, defines API routes and background tasks.  
- **app/ingestion.py** – python – Handles data ingestion from external APIs and internal DBs, normalizes and stores data.  
- **app/models.py** – python – SQLAlchemy ORM models for market data, forecasts, bids, and storage status.  
- **app/forecast.py** – python – Implements Prophet/LSTM forecasting pipeline and model persistence.  
- **app/engine.py** – python – Market participation engine that generates bids and storage decisions.  
- **app/utils.py** – python – Utility functions for data processing, validation, and logging.  
- **app/config.py** – python – Loads configuration from YAML and environment variables.  
- **tests/test_ingestion.py** – python – Unit tests for ingestion module.  
- **tests/test_forecast.py** – python – Unit tests for forecasting module.  
- **tests/test_engine.py** – python – Unit tests for market engine.  
- **Dockerfile** – dockerfile – Builds Docker image for the API service.  
- **docker-compose.yml** – docker-compose – Orchestrates API, PostgreSQL, Redis, and Celery workers.  
- **requirements.txt** – requirements – Python dependencies.  
- **.env.example** – env – Example environment variables.  
- **config.yaml** – yaml – Application configuration file.  
- **README.md** – markdown – Project overview, setup, and usage.  
- **docs/architecture.md** – markdown – Detailed architecture diagram and component descriptions.  
- **docs/usage.md** – markdown – API usage examples and deployment instructions.  
- **.github/workflows/ci.yml** – yaml – GitHub Actions CI pipeline.  
- **monitoring/alert_rules.yaml** – yaml – Alert rules for Prometheus/Grafana.  
- **monitoring/dashboard.json** – json – Grafana dashboard configuration.  
- **LICENSE** – text – Project license.  

### Folder Structure
- **root**  
  - **app**  
    - main.py  
    - ingestion.py  
    - models.py  
    - forecast.py  
    - engine.py  
    - utils.py  
    - config.py  
  - **tests**  
    - test_ingestion.py  
    - test_forecast.py  
    - test_engine.py  
  - **docs**  
    - architecture.md  
    - usage.md  
  - **monitoring**  
    - alert_rules.yaml  
    - dashboard.json  
  - config.yaml  
  - .env.example  
  - Dockerfile  
  - docker-compose.yml  
  - requirements.txt  
  - README.md  
  - LICENSE  
  - **.github**  
    - **workflows**  
      - ci.yml  

### File Types
- python  
- yaml  
- dockerfile  
- docker-compose  
- requirements  
- env  
- markdown  
- json  
- text  

## Technical Specifications

### app/main.py
- **Imports:** fastapi, uvicorn, app.ingestion, app.forecast, app.engine, app.config, app.utils, celery, pydantic  
- **Classes:** `class APIApp: description='FastAPI application with background tasks.'`  
- **Functions:**  
  - `def create_app() -> FastAPI: description='Instantiate FastAPI, include routers, and set up background tasks.'`  
  - `async def startup_event(): description='Initialize DB connections and start Celery workers.'`  
  - `async def shutdown_event(): description='Gracefully shutdown resources.'`  
- **Data Structures:** `class Settings(BaseSettings): description='Application settings loaded from config and env.'`  
- **Logic Flows:**  
  1. Instantiate APIApp.  
  2. Register routes: /ingest, /forecast, /bid.  
  3. On startup, connect to PostgreSQL via SQLAlchemy, start Celery beat for scheduled ingestion.  
  4. On shutdown, close DB sessions and stop Celery.  
- **Error Handling:**  
  - Use FastAPI exception handlers for HTTP errors.  
  - Log exceptions with structured logging.  
  - Return JSON error responses with status code and message.  
- **Connections:** app.ingestion, app.forecast, app.engine, app.config, app.utils  

### app/ingestion.py
- **Imports:** requests, sqlalchemy, pandas, app.models, app.config, app.utils, logging  
- **Classes:** `class DataIngestor: description='Handles ingestion from external APIs and internal DBs.'`  
- **Functions:**  
  - `def fetch_market_prices() -> pd.DataFrame: description='Call market API, return raw DataFrame.'`  
  - `def fetch_historical_prices() -> pd.DataFrame: description='Query PostgreSQL for historical data.'`  
  - `def fetch_demand_response() -> pd.DataFrame: description='Retrieve demand response signals.'`  
  - `def fetch_storage_status() -> pd.DataFrame: description='Get storage status from internal DB.'`  
  - `def normalize_data(df: pd.DataFrame) -> pd.DataFrame: description='Apply schema normalization and unit conversion.'`  
  - `def store_data(df: pd.DataFrame): description='Persist normalized data to PostgreSQL via SQLAlchemy.'`  
- **Data Structures:** `class IngestionSchema: description='Pydantic model for normalized data schema.'`  
- **Logic Flows:**  
  1. For each source, call fetch_* function.  
  2. Concatenate dataframes.  
  3. Normalize using normalize_data.  
  4. Validate against IngestionSchema.  
  5. Store using store_data.  
- **Error Handling:**  
  - Retry logic with exponential backoff for API calls.  
  - Catch database connection errors and log.  
  - Validate schema; raise ValidationError if mismatch.  
- **Connections:** app.models, app.config, app.utils  

### app/models.py
- **Imports:** sqlalchemy, sqlalchemy.orm, pydantic, datetime  
- **Classes:**  
  - `class MarketPrice(Base): description='Table for market prices.'`  
  - `class HistoricalPrice(Base): description='Table for historical prices.'`  
  - `class DemandResponse(Base): description='Table for demand response signals.'`  
  - `class StorageStatus(Base): description='Table for storage status.'`  
  - `class Forecast(Base): description='Table for forecasted prices.'`  
  - `class Bid(Base): description='Table for generated bids.'`  
- **Functions:** *None*  
- **Data Structures:** `class MarketPriceSchema(BaseModel): description='Pydantic schema for MarketPrice.'`  
- **Logic Flows:**  
  1. Define SQLAlchemy models with appropriate columns and indexes.  
  2. Create Pydantic schemas for request/response validation.  
- **Error Handling:**  
  - Handle IntegrityError for duplicate entries.  
  - Use transaction rollback on failure.  
- **Connections:** app.config  

### app/forecast.py
- **Imports:** pandas, numpy, prophet, torch, torch.nn, torch.utils.data, app.models, app.config, app.utils, logging  
- **Classes:**  
  - `class ForecastModel: description='Encapsulates Prophet or LSTM model training and inference.'`  
  - `class LSTMForecast(nn.Module): description='LSTM architecture for time‑series forecasting.'`  
- **Functions:**  
  - `def train_model(df: pd.DataFrame) -> ForecastModel: description='Train model on historical data and return model instance.'`  
  - `def predict(model: ForecastModel, horizon: int) -> pd.DataFrame: description='Generate 24‑hour ahead forecast.'`  
  - `def evaluate(model: ForecastModel, df: pd.DataFrame) -> float: description='Compute MAE and return error metric.'`  
  - `def save_model(model: ForecastModel, path: str): description='Persist model to disk.'`  
  - `def load_model(path: str) -> ForecastModel: description='Load model from disk.'`  
- **Data Structures:** `class ForecastResult: description='Container for forecast values and metadata.'`  
- **Logic Flows:**  
  1. Load historical data via app.ingestion.  
  2. Split into train/test.  
  3. If using Prophet, instantiate Prophet, fit, predict.  
  4. If using LSTM, prepare sequences, train, predict.  
  5. Evaluate MAE; if below threshold, save model.  
  6. Return ForecastResult.  
- **Error Handling:**  
  - Catch model convergence errors.  
  - Validate input data shape.  
  - Log training progress and failures.  
- **Connections:** app.ingestion, app.models, app.config, app.utils  

### app/engine.py
- **Imports:** app.models, app.forecast, app.config, app.utils, datetime, logging  
- **Classes:** `class MarketEngine: description='Generates bids and storage decisions based on forecasts and market rules.'`  
- **Functions:**  
  - `def generate_bids(forecast: pd.DataFrame) -> List[Bid]: description='Create optimal buy/sell bids.'`  
  - `def decide_storage(forecast: pd.DataFrame, storage_status: pd.DataFrame) -> str: description='Return action: sell, store, consume.'`  
  - `def execute_bid(bid: Bid): description='Send bid to market API and record outcome.'`  
- **Data Structures:** `class Bid: description='Data class for bid details.'`  
- **Logic Flows:**  
  1. Retrieve latest forecast.  
  2. Apply market rules (price thresholds, capacity limits).  
  3. Generate bid objects.  
  4. Determine storage action using demand response and storage status.  
  5. Persist bids and decisions to DB.  
- **Error Handling:**  
  - Handle API failures with retry.  
  - Validate bid parameters.  
  - Log decision process.  
- **Connections:** app.forecast, app.models, app.config, app.utils  

### app/utils.py
- **Imports:** pandas, numpy, logging, datetime, typing  
- **Classes:** *None*  
- **Functions:**  
  - `def to_timestamp(df: pd.DataFrame, column: str) -> pd.DataFrame: description='Convert column to datetime.'`  
  - `def resample(df: pd.DataFrame, rule: str) -> pd.DataFrame: description='Resample time series.'`  
  - `def validate_schema(df: pd.DataFrame, schema: BaseModel) -> bool: description='Validate DataFrame against Pydantic schema.'`  
  - `def get_logger(name: str) -> logging.Logger: description='Return configured logger.'`  
- **Data Structures:** *None*  
- **Logic Flows:**  
  1. Provide reusable data transformations.  
  2. Centralize logging configuration.  
- **Error Handling:**  
  - Raise ValueError on invalid data.  
  - Log warnings for missing columns.  
- **Connections:** app.config  

### app/config.py
- **Imports:** pydantic, yaml, os  
- **Classes:** `class Settings(BaseSettings): description='Load config from YAML and env vars.'`  
- **Functions:** `def load_config(path: str) -> dict: description='Read YAML config file.'`  
- **Data Structures:** *None*  
- **Logic Flows:**  
  1. Load config.yaml.  
  2. Override with environment variables.  
  3. Validate required fields.  
- **Error Handling:**  
  - FileNotFoundError if config missing.  
  - ValidationError for missing keys.  
- **Connections:** *None*  

### tests/test_ingestion.py
- **Imports:** pytest, app.ingestion, app.models, app.config, sqlalchemy, pandas  
- **Classes:** *None*  
- **Functions:**  
  - `def test_fetch_market_prices(): description='Assert API returns DataFrame with expected columns.'`  
  - `def test_normalize_data(): description='Check schema compliance after normalization.'`  
  - `def test_store_data(): description='Verify data persisted to DB.'`  
- **Data Structures:** *None*  
- **Logic Flows:**  
  1. Mock external API responses.  
  2. Run ingestion functions.  
  3. Query DB to confirm records.  
- **Error Handling:**  
  - Use pytest.raises for expected exceptions.  
- **Connections:** app.ingestion, app.models  

### tests/test_forecast.py
- **Imports:** pytest, app.forecast, app.ingestion, pandas  
- **Classes:** *None*  
- **Functions:**  
  - `def test_train_model(): description='Model trains without errors.'`  
  - `def test_predict(): description='Forecast returns 24 rows.'`  
  - `def test_evaluate(): description='MAE below threshold.'`  
- **Data Structures:** *None*  
- **Logic Flows:**  
  1. Generate synthetic historical data.  
  2. Train model.  
  3. Predict horizon.  
  4. Evaluate MAE.  
- **Error Handling:** *None*  
- **Connections:** app.forecast, app.ingestion  

### tests/test_engine.py
- **Imports:** pytest, app.engine, app.forecast, app.models, pandas  
- **Classes:** *None*  
- **Functions:**  
  - `def test_generate_bids(): description='Bids generated correctly based on forecast.'`  
  - `def test_decide_storage(): description='Storage decision logic works.'`  
- **Data Structures:** *None*  
- **Logic Flows:**  
  1. Create mock forecast DataFrame.  
  2. Call generate_bids and decide_storage.  
  3. Assert outputs.  
- **Error Handling:** *None*  
- **Connections:** app.engine, app.forecast  

### Dockerfile
- **Logic Flows:**  
  1. `FROM python:3.11-slim.`  
  2. `WORKDIR /app.`  
  3. `COPY requirements.txt .`  
  4. `RUN pip install --no-cache-dir -r requirements.txt.`  
  5. `COPY . .`  
  6. `CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"].`  

### docker-compose.yml
- **Logic Flows:**  
  ```
  services:
    api:
      build: .
      ports: 
        - "80:80"
      env_file: .env
      depends_on: 
        - db
        - redis
    db:
      image: postgres:15
      environment: 
        POSTGRES_DB=energy
        POSTGRES_USER=energy
        POSTGRES_PASSWORD=energy
      volumes: 
        - db_data:/var/lib/postgresql/data
    redis:
      image: redis:7
    worker:
      build: .
      command: celery -A app.main.celery_app worker --loglevel=info
      depends_on: 
        - api
        - db
        - redis
  volumes:
    db_data:
  ```  

### requirements.txt
- **Logic Flows:**  
  ```
  fastapi
  uvicorn
  sqlalchemy
  psycopg2-binary
  pandas
  numpy
  prophet
  torch
  celery
  redis
  pyd