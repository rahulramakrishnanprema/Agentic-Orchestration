# settings.py
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """System configuration - All values loaded from .env file"""

    # General Configuration
    MAX_REBUILD_ATTEMPTS = int(os.getenv("MAX_REBUILD_ATTEMPTS"))
    REVIEW_THRESHOLD = float(os.getenv("REVIEW_THRESHOLD"))
    GOT_SCORE_THRESHOLD = float(os.getenv("GOT_SCORE_THRESHOLD"))
    HITL_TIMEOUT_SECONDS = int(os.getenv("HITL_TIMEOUT_SECONDS"))

    # LLM Configuration - Per-agent keys and URLs
    # Global fallback (optional - used if agent-specific not provided)
    LLM_API_KEY = os.getenv("LLM_API_KEY")
    LLM_API_URL = os.getenv("LLM_API_URL")

    # Hardcoded default LLM parameters (used by all agents, can be overridden in .env)
    DEFAULT_LLM_TEMPERATURE = 0.3
    DEFAULT_LLM_MAX_TOKENS = None

    # Planner Agent Configuration
    PLANNER_LLM_KEY = os.getenv("PLANNER_LLM_KEY", LLM_API_KEY)
    PLANNER_LLM_URL = os.getenv("PLANNER_LLM_URL", LLM_API_URL)
    PLANNER_LLM_MODEL = os.getenv("PLANNER_LLM_MODEL")
    PLANNER_LLM_TEMPERATURE = float(os.getenv("PLANNER_LLM_TEMPERATURE", DEFAULT_LLM_TEMPERATURE))
    PLANNER_LLM_MAX_TOKENS = int(os.getenv("PLANNER_LLM_MAX_TOKENS")) if os.getenv("PLANNER_LLM_MAX_TOKENS") else DEFAULT_LLM_MAX_TOKENS

    # Assembler Agent Configuration
    ASSEMBLER_LLM_KEY = os.getenv("ASSEMBLER_LLM_KEY", LLM_API_KEY)
    ASSEMBLER_LLM_URL = os.getenv("ASSEMBLER_LLM_URL", LLM_API_URL)
    ASSEMBLER_LLM_MODEL = os.getenv("ASSEMBLER_LLM_MODEL")
    ASSEMBLER_LLM_TEMPERATURE = float(os.getenv("ASSEMBLER_LLM_TEMPERATURE", DEFAULT_LLM_TEMPERATURE))
    ASSEMBLER_LLM_MAX_TOKENS = int(os.getenv("ASSEMBLER_LLM_MAX_TOKENS")) if os.getenv("ASSEMBLER_LLM_MAX_TOKENS") else DEFAULT_LLM_MAX_TOKENS

    # Developer Agent Configuration (also used by rebuilder)
    DEVELOPER_LLM_KEY = os.getenv("DEVELOPER_LLM_KEY", LLM_API_KEY)
    DEVELOPER_LLM_URL = os.getenv("DEVELOPER_LLM_URL", LLM_API_URL)
    DEVELOPER_LLM_MODEL = os.getenv("DEVELOPER_LLM_MODEL")
    DEVELOPER_LLM_TEMPERATURE = float(os.getenv("DEVELOPER_LLM_TEMPERATURE", DEFAULT_LLM_TEMPERATURE))
    DEVELOPER_LLM_MAX_TOKENS = int(os.getenv("DEVELOPER_LLM_MAX_TOKENS")) if os.getenv("DEVELOPER_LLM_MAX_TOKENS") else DEFAULT_LLM_MAX_TOKENS

    # Reviewer Agent Configuration
    REVIEWER_LLM_KEY = os.getenv("REVIEWER_LLM_KEY", LLM_API_KEY)
    REVIEWER_LLM_URL = os.getenv("REVIEWER_LLM_URL", LLM_API_URL)
    REVIEWER_LLM_MODEL = os.getenv("REVIEWER_LLM_MODEL")
    REVIEWER_LLM_TEMPERATURE = float(os.getenv("REVIEWER_LLM_TEMPERATURE", DEFAULT_LLM_TEMPERATURE))
    REVIEWER_LLM_MAX_TOKENS = int(os.getenv("REVIEWER_LLM_MAX_TOKENS")) if os.getenv("REVIEWER_LLM_MAX_TOKENS") else DEFAULT_LLM_MAX_TOKENS

    # Agentic ui Configuration
    UI_HOST = os.getenv("UI_HOST")
    UI_PORT = int(os.getenv("UI_PORT"))
    REACT_DEV_PORT = int(os.getenv("REACT_DEV_PORT"))
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    LOG_LEVEL = os.getenv("LOG_LEVEL")

    # Code Review Configuration
    REVIEW_BRANCH_NAME = os.getenv("REVIEW_BRANCH_NAME")

    # SonarQube Configuration
    SONAR_TOKEN = os.getenv("SONAR_TOKEN")
    SONAR_ORG = os.getenv("SONAR_ORG")
    SONAR_PROJECT_KEY = os.getenv("SONAR_PROJECT_KEY")
    SONAR_HOST_URL = os.getenv("SONAR_HOST_URL")

    # MongoDB Configuration
    MONGODB_CONNECTION_STRING = os.getenv("MONGODB_CONNECTION_STRING")
    MONGODB_COLLECTION_MATRIX = os.getenv("MONGODB_COLLECTION_MATRIX")
    MONGODB_PERFORMANCE_DATABASE = os.getenv("MONGODB_PERFORMANCE_DATABASE")
    MONGODB_AGENT_PERFORMANCE = os.getenv("MONGODB_AGENT_PERFORMANCE")
    MONGODB_REVIEWER_COLLECTION = os.getenv("MONGODB_REVIEWER_COLLECTION")
    MONGODB_URI = os.getenv("MONGODB_CONNECTION_STRING")  # Alias for ui compatibility
    MONGODB_ENABLED = os.getenv("MONGODB_ENABLED", "True").lower() == "true"

    # MongoDB Feedback Database Configuration
    MONGODB_DATABASE = os.getenv("MONGODB_DATABASE")
    MONGODB_FEEDBACK_DATABASE = os.getenv("MONGODB_FEEDBACK_DATABASE")
    DEVELOPER_AGENT_FEEDBACK = os.getenv("DEVELOPER_AGENT_FEEDBACK")
    ASSEMBLER_FEEDBACK = os.getenv("ASSEMBLER_FEEDBACK")

    # GitHub Configuration
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
    GITHUB_REPO_OWNER = os.getenv("GITHUB_REPO_OWNER")
    GITHUB_REPO_NAME = os.getenv("GITHUB_REPO_NAME")
    GITHUB_REPOSITORY = f"{os.getenv('GITHUB_REPO_OWNER')}/{os.getenv('GITHUB_REPO_NAME')}" if os.getenv(
        'GITHUB_REPO_OWNER') and os.getenv('GITHUB_REPO_NAME') else None

    # Jira Configuration
    JIRA_SERVER = os.getenv("JIRA_SERVER")
    JIRA_EMAIL = os.getenv("JIRA_EMAIL")
    JIRA_TOKEN = os.getenv("JIRA_TOKEN")
    PROJECT_KEY = os.getenv("PROJECT_KEY")

    # Additional paths
    STANDARDS_FOLDER = os.getenv("STANDARDS_FOLDER")


config = Config()