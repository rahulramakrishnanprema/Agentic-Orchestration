import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pymongo import MongoClient
from dotenv import load_dotenv
import logging

from config.settings import config

load_dotenv()
logger = logging.getLogger(__name__)

performance_tracker = None  # Global instance for import


class MongoPerformanceTracker:
    def __init__(self):
        self.connection_string = config.MONGODB_CONNECTION_STRING
        self.database_name = config.MONGODB_PERFORMANCE_DATABASE
        self.collection_name = config.MONGODB_COLLECTION_MATRIX
        self.client = None
        self.db = None
        self.collection = None
        self.initialize_connection()

    def initialize_connection(self):
        """Initialize MongoDB connection"""
        try:
            if not self.connection_string:
                return

            # Enhanced connection with better timeout and retry settings for replica sets
            self.client = MongoClient(
                self.connection_string,
                serverSelectionTimeoutMS=30000,  # Increased to 30 seconds
                connectTimeoutMS=20000,  # 20 seconds connection timeout
                socketTimeoutMS=20000,  # 20 seconds socket timeout
                retryWrites=True,
                retryReads=True,
                readPreference='primaryPreferred',  # Try primary, fall back to secondary
                maxPoolSize=50,
                minPoolSize=10
            )
            self.db = self.client[self.database_name]
            self.collection = self.db[self.collection_name]

            # Test connection with retry
            try:
                self.client.admin.command('ping')
                logger.info("MongoDB Performance Tracker connected successfully")
            except Exception as ping_error:
                logger.warning(f"MongoDB ping failed but continuing: {ping_error}")
                # Don't fail completely, just log warning

        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            logger.info("Continuing without MongoDB - data will not be persisted")
            self.client = None
            self.db = None
            self.collection = None

    def get_all_agents(self) -> List[str]:
        """Fetch all unique agent names from the collection."""
        try:
            pipeline = [
                {"$match": {"agent_activities": {"$exists": True}}},
                {"$project": {"agents": {"$objectToArray": "$agent_activities"}}},
                {"$unwind": "$agents"},
                {"$group": {"_id": None, "unique_agents": {"$addToSet": "$agents.k"}}}
            ]
            result = list(self.collection.aggregate(pipeline))
            return result[0]["unique_agents"] if result else []
        except Exception as e:
            logger.error(f"Failed to get unique agents: {e}")
            return []

    def normalize_agent_activities(self, activities: Dict, all_agents: List[str]) -> Dict:
        """Normalize agent activities to ensure consistent data structure."""
        normalized = {}
        for agent in all_agents:
            agent_data = activities.get(agent, {})
            normalized[agent] = {
                "Task_completed": agent_data.get("Task_completed", 0),
                "tokens_used": agent_data.get("tokens_used", 0),
                "LLM_model_used": agent_data.get("LLM_model_used", "unknown")
            }
        return normalized

    def generate_empty_agent_activities(self, all_agents: List[str]) -> Dict:
        """Generate empty agent activities structure"""
        return {
            agent: {
                "Task_completed": 0,
                "tokens_used": 0,
                "LLM_model_used": "unknown"
            }
            for agent in all_agents
        }

    def get_last_7_days_data(self) -> List[Dict[str, Any]]:
        """Get REAL performance data for the last 7 days including today"""
        if self.collection is None:
            logger.warning("MongoDB collection not available - returning empty data")
            return []

        try:
            # Calculate date range including today
            today = datetime.now().date()
            start_date = today - timedelta(days=6)  # Get 7 days including today

            logger.debug(f"Fetching data from {start_date} to {today}")  # Changed from INFO to DEBUG

            # Query MongoDB for real data
            query = {
                "date": {
                    "$gte": start_date.isoformat(),
                    "$lte": today.isoformat()
                }
            }

            # Fetch and sort documents
            documents = list(self.collection.find(query).sort("date", 1))

            # Get all unique agents
            all_agents = self.get_all_agents()
            if not all_agents:
                all_agents = ["PlannerAgent", "AssemblerAgent", "DeveloperAgent", "ReviewerAgent"]

            # Format the REAL data for Agentic_UI consumption
            formatted_data = []
            current_date = start_date
            date_map = {doc.get("date"): doc for doc in documents}

            # Ensure we have entries for all days including today
            while current_date <= today:
                date_str = current_date.isoformat()
                doc = date_map.get(date_str)

                if doc:
                    # Calculate success rate from real data
                    success_rate = self.calculate_success_rate(doc)
                    # Ensure code_quality_scores is properly formatted as percentage out of 100
                    code_quality = round(doc.get("code_quality_scores", 0.0), 1)
                    # Ensure it's within 0-100 range
                    code_quality = max(0.0, min(100.0, code_quality))

                    formatted_item = {
                        "date": date_str,
                        "tasks": doc.get("tasks_completed", 0),
                        "pullRequests": doc.get("pull_requests_created", 0),
                        "tokensUsed": doc.get("tokens_consumed", 0),
                        "successRate": success_rate,
                        "sonarScore": code_quality,  # Now properly formatted as 0-100 percentage
                        "agent_activities": self.normalize_agent_activities(doc.get("agent_activities", {}), all_agents)
                    }
                else:
                    # Create empty entry for missing date
                    formatted_item = {
                        "date": date_str,
                        "tasks": 0,
                        "pullRequests": 0,
                        "tokensUsed": 0,
                        "successRate": 0,
                        "sonarScore": 0,
                        "agent_activities": self.generate_empty_agent_activities(all_agents)
                    }

                formatted_data.append(formatted_item)
                current_date += timedelta(days=1)

            logger.debug(f"Successfully fetched {len(formatted_data)} days of data")  # Changed from INFO to DEBUG
            return formatted_data

        except Exception as e:
            logger.error(f"Failed to get performance data: {e}")
            return []

    def calculate_success_rate(self, doc: Dict) -> float:
        """Calculate success rate from document data"""
        try:
            success_count = doc.get("success_count", 0)
            failure_count = doc.get("failure_count", 0)
            total = success_count + failure_count

            if total == 0:
                return 0.0
            return round((success_count / total) * 100, 1)
        except:
            return 0.0

    def get_agent_performance_data(self) -> List[Dict[str, Any]]:
        """Get REAL agent performance data from MongoDB"""
        if self.collection is None:
            logger.error("MongoDB collection not available for agent performance")
            return []

        try:
            # Query last 7 days for agent performance
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)

            query = {
                "date": {
                    "$gte": start_date.isoformat()[:10],
                    "$lte": end_date.isoformat()[:10]
                },
                "agent_activities": {"$exists": True}
            }

            documents = list(self.collection.find(query))

            if not documents:
                logger.warning("No agent performance data found in MongoDB")
                return []

            # Aggregate agent data
            agent_totals = {}

            for doc in documents:
                agent_activities = doc.get("agent_activities", {})

                for agent_name, agent_data in agent_activities.items():
                    if agent_name not in agent_totals:
                        agent_totals[agent_name] = {
                            "total_tasks": 0,
                            "total_tokens": 0,
                            "success_count": 0,
                            "failure_count": 0,
                            "model_used": agent_data.get("LLM_model_used", "unknown")
                        }

                    agent_totals[agent_name]["total_tasks"] += agent_data.get("Task_completed", 0)
                    agent_totals[agent_name]["total_tokens"] += agent_data.get("tokens_used", 0)

                # Distribute success/failure proportionally
                doc_success = doc.get("success_count", 0)
                doc_failure = doc.get("failure_count", 0)

                total_agents = len(agent_activities)
                if total_agents > 0:
                    for agent_name in agent_activities.keys():
                        agent_totals[agent_name]["success_count"] += doc_success // total_agents
                        agent_totals[agent_name]["failure_count"] += doc_failure // total_agents

            # Format for Agentic_UI
            agent_data = []
            for agent_name, totals in agent_totals.items():
                total = totals["success_count"] + totals["failure_count"]
                success_rate = (totals["success_count"] / total * 100) if total > 0 else 0.0

                agent_data.append({
                    "agent": agent_name,
                    "tasks_processed": totals["total_tasks"],
                    "tokens_used": totals["total_tokens"],
                    "success_rate": round(success_rate, 1),
                    "model_used": totals["model_used"]
                })

            return agent_data

        except Exception as e:
            logger.error(f"Failed to fetch real agent performance: {e}")
            return []

    def ensure_7_days_data(self, data: List[Dict], start_date: datetime.date, end_date: datetime.date,
                           all_agents: List[str]) -> List[Dict]:
        """Ensure we have exactly 7 days of data, filling missing days with zeros"""
        data_by_date = {item["date"]: item for item in data}

        all_dates = []
        current_date = start_date
        while current_date <= end_date:
            all_dates.append(current_date.isoformat())
            current_date += timedelta(days=1)

        complete_data = []
        for date in all_dates:
            if date in data_by_date:
                item = data_by_date[date]
                for agent in all_agents:
                    if agent not in item["agent_activities"]:
                        item["agent_activities"][agent] = {
                            "Task_completed": 0,
                            "tokens_used": 0
                        }
                    else:
                        if "Task_completed" not in item["agent_activities"][agent]:
                            item["agent_activities"][agent]["Task_completed"] = 0
                complete_data.append(item)
            else:
                complete_data.append({
                    "date": date,
                    "tasks": 0,
                    "pullRequests": 0,
                    "tokens": 0,
                    "sonarScore": 0,
                    "success_rate": 0.0,
                    "agent_activities": {agent: {"Task_completed": 0, "tokens_used": 0} for agent in all_agents}
                })

        return complete_data

    def generate_empty_7_days_data(self, start_date: datetime.date, end_date: datetime.date, all_agents: List[str]) -> \
    List[Dict]:
        """Generate empty data structure for 7 days when no data exists"""
        empty_data = []
        current_date = start_date

        while current_date <= end_date:
            empty_data.append({
                "date": current_date.isoformat(),
                "tasks": 0,
                "pullRequests": 0,
                "tokens": 0,
                "sonarScore": 0,
                "success_rate": 0.0,
                "agent_activities": {agent: {"Task_completed": 0, "tokens_used": 0} for agent in all_agents}
            })
            current_date += timedelta(days=1)

        return empty_data

    def get_real_time_metrics(self) -> Dict[str, Any]:
        """Get real-time metrics from the most recent data"""
        last_7_days = self.get_last_7_days_data()

        if not last_7_days:
            return {
                "today_summary": {
                    "tasks": 0,
                    "pullRequests": 0,
                    "tokens": 0,
                    "sonarScore": 0
                },
                "active_agents": [],
                "trend": "stable"
            }

        today_data = last_7_days[-1] if last_7_days else {}

        active_agents = self.get_active_agents_from_recent_data()

        trend = "stable"
        if len(last_7_days) >= 2:
            today_tasks = today_data.get("tasks", 0)
            yesterday_tasks = last_7_days[-2].get("tasks", 0)
            trend = "up" if today_tasks > yesterday_tasks else "down" if today_tasks < yesterday_tasks else "stable"

        return {
            "today_summary": {
                "tasks": today_data.get("tasks", 0),
                "pullRequests": today_data.get("pullRequests", 0),
                "tokens": today_data.get("tokens", 0),
                "sonarScore": today_data.get("sonarScore", 0)
            },
            "active_agents": active_agents,
            "trend": trend
        }

    def get_active_agents_from_recent_data(self) -> List[str]:
        """Get list of active agents from recent MongoDB data"""
        if self.collection is None:
            return []

        try:
            recent_date = (datetime.now() - timedelta(days=2)).isoformat()[:10]

            query = {
                "date": {"$gte": recent_date},
                "agent_activities": {"$exists": True}
            }

            documents = list(self.collection.find(query))
            active_agents = set()

            for doc in documents:
                agent_activities = doc.get("agent_activities", {})
                for agent_name in agent_activities.keys():
                    if agent_name:
                        active_agents.add(agent_name)

            return list(active_agents) if active_agents else ["PlannerAgent", "DeveloperAgent", "ReviewerAgent"]

        except Exception as e:
            logger.error(f"Failed to get active agents: {e}")
            return ["PlannerAgent", "DeveloperAgent", "ReviewerAgent"]

    def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()

    def increment_daily_metrics(self, metrics: Dict[str, Any], agent_metrics: Optional[Dict[str, Dict[str, Any]]] = None):
        """Increment daily metrics in MongoDB"""
        if self.collection is None:
            logger.warning("MongoDB collection not available - metrics not saved")
            return False

        try:
            today = datetime.now().date().isoformat()
            query = {"date": today}
            doc = self.collection.find_one(query)
            if doc is None:
                doc = {
                    "date": today,
                    "tasks_completed": 0,
                    "pull_requests_created": 0,
                    "tokens_consumed": 0,
                    "code_quality_scores": 0.0,
                    "success_count": 0,
                    "failure_count": 0,
                    "agent_activities": {},
                    "last_updated": datetime.now().isoformat(),
                    "num_scores": 0,
                    "total_quality_score": 0.0
                }
            # Update simple increments
            for key in ["tasks_completed", "pull_requests_created", "tokens_consumed", "success_count", "failure_count"]:
                if key in metrics:
                    doc[key] = doc.get(key, 0) + metrics[key]
            # Update average for code_quality_scores
            if "code_quality_score" in metrics:
                doc["total_quality_score"] = doc.get("total_quality_score", 0.0) + metrics["code_quality_score"]
                doc["num_scores"] = doc.get("num_scores", 0) + 1
                doc["code_quality_scores"] = doc["total_quality_score"] / doc["num_scores"] if doc["num_scores"] > 0 else 0
            # Update agent activities
            if agent_metrics:
                for agent_name, data in agent_metrics.items():
                    if agent_name not in doc["agent_activities"]:
                        doc["agent_activities"][agent_name] = {
                            "Task_completed": 0,
                            "LLM_model_used": data.get("LLM_model_used", "unknown"),
                            "tokens_used": 0
                        }
                    for key, value in data.items():
                        if key == "Task_completed":
                            doc["agent_activities"][agent_name][key] = doc["agent_activities"][agent_name].get(key, 0) + value
                        elif key == "LLM_model_used":
                            doc["agent_activities"][agent_name][key] = value
                        elif key == "tokens_used":
                            doc["agent_activities"][agent_name][key] = doc["agent_activities"][agent_name].get(key, 0) + value
            doc["last_updated"] = datetime.now().isoformat()
            self.collection.replace_one(query, doc, upsert=True)
            logger.info(f"Updated daily metrics for {today}")
        except Exception as e:
            logger.error(f"Failed to increment daily metrics: {e}")

    def update_daily_metrics_after_pr(self,
                                      pr_data: Dict[str, Any],
                                      agent_metrics: Dict[str, Dict[str, Any]],
                                      sonarqube_score: Optional[float] = None,
                                      success: bool = True,
                                      thread_id: str = "unknown") -> bool:
        """
        Update daily metrics after PR creation with all agent data.
        Increments existing existing or creates new.

        Args:
            pr_data: PR information (issue_key, pr_url, etc.)
            agent_metrics: Dictionary with agent names as keys and their metrics
            sonarqube_score: Optional SonarQube quality score
            success: Whether PR creation was successful
            thread_id: Thread identifier for logging

        Returns:
            bool: True if successful, False otherwise
        """
        if self.collection is None:
            logger.error(f"[{thread_id}] MongoDB collection not available")
            return False

        try:
            today = datetime.now().date().isoformat()

            logger.info(f"[{thread_id}] Updating daily metrics for {today}")

            # Find or create today's document
            query = {"date": today}
            existing_doc = self.collection.find_one(query)

            if existing_doc is None:
                # Create new document for today
                doc = {
                    "date": today,
                    "tasks_completed": 0,
                    "pull_requests_created": 0,
                    "tokens_consumed": 0,
                    "code_quality_scores": 0.0,
                    "success_count": 0,
                    "failure_count": 0,
                    "agent_activities": {},
                    "last_updated": datetime.now().isoformat(),
                    "num_scores": 0,
                    "total_quality_score": 0.0
                }
                logger.info(f"[{thread_id}] Creating new daily metrics document for {today}")
            else:
                doc = existing_doc
                logger.info(f"[{thread_id}] Updating existing daily metrics for {today}")

            # Increment pull requests if success
            if success:
                doc["pull_requests_created"] = doc.get("pull_requests_created", 0) + 1

            # Increment tasks completed (1 PR = 1 task completed)
            doc["tasks_completed"] = doc.get("tasks_completed", 0) + 1

            # Increment success/failure count
            if success:
                doc["success_count"] = doc.get("success_count", 0) + 1
            else:
                doc["failure_count"] = doc.get("failure_count", 0) + 1

            # Update code quality score (average)
            if sonarqube_score is not None:
                doc["total_quality_score"] = doc.get("total_quality_score", 0.0) + sonarqube_score
                doc["num_scores"] = doc.get("num_scores", 0) + 1
                doc["code_quality_scores"] = doc["total_quality_score"] / doc["num_scores"] if doc["num_scores"] > 0 else 0.0
                logger.info(
                    f"[{thread_id}] Updated quality score: {doc['code_quality_scores']:.2f} (avg of {doc['num_scores']} scores)")

            # Update agent activities and total tokens
            total_tokens = 0
            for agent_name, metrics in agent_metrics.items():
                # Initialize agent if not exists
                if agent_name not in doc["agent_activities"]:
                    doc["agent_activities"][agent_name] = {
                        "Task_completed": 0,
                        "LLM_model_used": metrics.get("LLM_model_used", "unknown"),
                        "tokens_used": 0
                    }

                # Increment task completed for this agent
                doc["agent_activities"][agent_name]["Task_completed"] += metrics.get("Task_completed", 1)

                # Update model used (keep latest)
                doc["agent_activities"][agent_name]["LLM_model_used"] = metrics.get("LLM_model_used",
                                                                                    doc["agent_activities"][agent_name][
                                                                                        "LLM_model_used"])

                # Increment tokens used
                tokens = metrics.get("tokens_used", 0)
                doc["agent_activities"][agent_name]["tokens_used"] += tokens
                total_tokens += tokens

                logger.info(
                    f"[{thread_id}] {agent_name}: +{tokens} tokens, total tasks: {doc['agent_activities'][agent_name]['Task_completed']}")

            # Update total tokens consumed
            doc["tokens_consumed"] = doc.get("tokens_consumed", 0) + total_tokens

            # Update timestamp
            doc["last_updated"] = datetime.now().isoformat()

            # Upsert (update or insert)
            self.collection.replace_one(query, doc, upsert=True)

            logger.info(f"[{thread_id}] ✓ Daily metrics updated successfully for {today}")
            logger.info(f"[{thread_id}] Summary: {doc['tasks_completed']} tasks, {doc['pull_requests_created']} PRs, "
                        f"{doc['tokens_consumed']} tokens, {doc['code_quality_scores']:.2f} quality")

            return True

        except Exception as e:
            logger.error(f"[{thread_id}] Failed to update daily metrics: {e}")
            return False

# Initialize global performance_tracker
performance_tracker = MongoPerformanceTracker()