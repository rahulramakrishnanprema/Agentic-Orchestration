import logging
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
from threading import Lock

import requests
from github import Github
from pymongo import MongoClient

from graph.sonarcube_graph import build_sonarcube_graph, SonarQubeState  # NEW: Import the graph builder

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

workflow_lock = Lock()
stats_lock = Lock()

class FixedSonarQube:
    def __init__(self, config):
        # Trim trailing slash and quotes
        self.sonar_host = config.SONAR_HOST_URL.strip().strip('"').rstrip('/')
        self.sonar_token = config.SONAR_TOKEN
        self.sonar_org = config.SONAR_ORG.strip().strip('"')
        self.sonar_project_key = config.SONAR_PROJECT_KEY

        self.headers = {
            "Authorization": f"Bearer {self.sonar_token}",
            "Content-Type": "application/json"
        }
        self.gh_token = config.GITHUB_TOKEN
        self.gh_repo = config.GITHUB_REPOSITORY

        # Initialize MongoDB if configured
        self.mongo_collection = None
        if hasattr(config, 'MONGODB_CONNECTION_STRING'):
            try:
                mongo_client = MongoClient(config.MONGODB_CONNECTION_STRING)
                mongo_db = mongo_client[config.MONGODB_DATABASE or 'code_review']
                self.mongo_collection = mongo_db['sonarqube_results']
                logger.info("MongoDB connection for SonarQube initialized")
            except Exception as e:
                logger.error(f"Failed to initialize MongoDB for SonarQube: {e}")

        self.workflow = build_sonarcube_graph()  # CHANGED: Use imported builder instead of self._build_workflow()
        self.stats = {
            'analyses_executed': 0,
            'successful_analyses': 0,
            'failed_analyses': 0,
            'total_processing_time': 0.0,
            'average_score': 0.0
        }

        logger.debug("Fixed SonarQube Agent initialized")

    def analyze_latest_pr(self, thread_id: Optional[str] = None) -> Dict[str, Any]:
        if not thread_id:
            thread_id = "SONAR-" + str(int(time.time()))[-6:]
        start_time = time.time()

        with stats_lock:
            self.stats['analyses_executed'] += 1

        initial_state = SonarQubeState(
            thread_id=thread_id,
            latest_pr={},
            issues=[],
            measures={},
            pr_files=[],
            overall_score=0.0,
            all_issues=[],
            success=False,
            error=None,
            processing_time=0.0
        )

        final_state = self.workflow.invoke(initial_state, {"configurable": {"thread_id": thread_id}})
        final_state['processing_time'] = time.time() - start_time

        with stats_lock:
            if final_state['success']:
                self.stats['successful_analyses'] += 1
                total = self.stats['successful_analyses']
                avg = self.stats['average_score']
                self.stats['average_score'] = ((avg * (total - 1)) + final_state['overall_score']) / total
            else:
                self.stats['failed_analyses'] += 1
            self.stats['total_processing_time'] += final_state['processing_time']

        return final_state