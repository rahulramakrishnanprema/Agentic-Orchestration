""" Enhanced AI Development System - Agentic_UI Server and Connection Handler
A Agentic_UI server and connection interface for the AI development system featuring:
- React Agentic_UI integration for monitoring and control
- HTTP API endpoints for system interaction
- Environment variable configuration via Agentic_UI
- System status monitoring
- Integration with router.py for core functionality
- MongoDB Performance Tracking Integration

This module handles all Agentic_UI connections and HTTP server operations, while delegating core system functionality to router.py.
"""
# ui.py
import os
import json
import logging
import threading
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse
from typing import Dict, List, Any
from dotenv import load_dotenv
from pymongo import MongoClient

# Import config from settings
from config.settings import config

# Performance tracking import
from services.performance_tracker import MongoPerformanceTracker

# HTTP Server imports for React Agentic_UI integration
import socketserver

# Import the router for core functionality
import core.router

# Global workflow status tracking
workflow_status = {"agent": None}
workflow_status_lock = threading.Lock()

load_dotenv()

# Configure logging format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(threadName)s] - %(message)s'
)
logger = logging.getLogger(__name__)

# Agentic_UI Server components
ui_server = None
ui_server_thread = None

# Initialize performance tracker globally
performance_tracker = MongoPerformanceTracker()


def update_env_file(updates: Dict[str, str]) -> bool:
    """ Update the .env file with new key-value pairs.
    Args:
        updates: Dictionary of key-value pairs to update
    Returns:
        True if successful, False otherwise
    """
    try:
        env_path = '.env'
        env_vars = {}
        # Read existing .env file if it exists
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key] = value
        # Update with new values
        env_vars.update(updates)
        # Write back to .env file
        with open(env_path, 'w') as f:
            for key, value in env_vars.items():
                f.write(f"{key}={value}\n")
        # Reload environment variables
        load_dotenv(override=True)
        # Update config object with new values
        for key, value in updates.items():
            if hasattr(config, key):
                setattr(config, key, value)
        return True
    except Exception as e:
        logger.error(f"Failed to update .env file: {e}")
        return False

def get_env_config(keys: List[str]) -> Dict[str, str]:
    """ Get current values for specific environment variables.
    Args:
        keys: List of environment variable keys to retrieve
    Returns:
        Dictionary of key-value pairs
    """
    result = {}
    for key in keys:
        result[key] = os.getenv(key, "")
    return result

# React Agentic_UI Handler with proper HTTP responses
class ReactUIHandler(BaseHTTPRequestHandler):
    """HTTP handler for React Agentic_UI communication with MongoDB performance tracking"""

    def log_message(self, format, *args):
        """Suppress default HTTP request logging"""
        pass

    def do_GET(self):
        """Handle GET requests from React Agentic_UI"""
        try:
            parsed_path = urlparse(self.path)
            path = parsed_path.path

            if path == "/api/workflow_status":
                with workflow_status_lock:
                    status = workflow_status.copy()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(status).encode())
                return

            self.send_response(200)
            self.send_cors_headers()
            self.send_header('Content-Type', 'application/json')
            self.end_headers()

            if path == '/api/status':
                self.handle_status_request()
            elif path == '/api/stats':
                self.handle_stats_request()
            elif path == '/api/activity':
                self.handle_activity_request()
            elif path == '/api/health':
                self.handle_health_request()
            elif path == '/api/config':
                self.handle_config_request()
            elif path == '/api/env':
                self.handle_env_request()
            elif path == '/api/current-agents':  # NEW: Current session agents
                self.handle_current_agents_request()
            # NEW PERFORMANCE ENDPOINTS
            elif path == '/api/performance-data':
                self.handle_performance_data_request()
            elif path == '/api/performance/weekly':
                self.handle_weekly_performance_request()
            elif path == '/api/performance/realtime':
                self.handle_real_time_metrics_request()
            elif path == '/api/performance/agents':
                self.handle_agent_performance_request()
            else:
                self.wfile.write(json.dumps({"error": "Endpoint not found"}).encode('utf-8'))

        except Exception as e:
            logger.error(f'Error handling GET request: {e}')
            try:
                self.send_response(500)
                self.send_cors_headers()
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode('utf-8'))
            except:
                pass

    def do_POST(self):
        """Handle POST requests from React Agentic_UI"""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            # Send proper HTTP response with CORS
            self.send_response(200)
            self.send_cors_headers()
            self.send_header('Content-Type', 'application/json')
            self.end_headers()

            if self.path == '/api/start-automation' or self.path == '/api/start-task':
                if content_length > 0:
                    post_data = self.rfile.read(content_length)
                    data = json.loads(post_data.decode('utf-8'))
                    self.handle_start_automation(data)
                else:
                    self.wfile.write(json.dumps({"success": False, "error": "No data provided"}).encode('utf-8'))
            elif self.path == '/api/stop-automation':
                self.handle_stop_automation()
            elif self.path == '/api/reset-stats':
                self.handle_reset_stats()
            elif self.path == '/api/config/save':
                if content_length > 0:
                    post_data = self.rfile.read(content_length)
                    data = json.loads(post_data.decode('utf-8'))
                    self.handle_save_config(data)
                else:
                    self.wfile.write(json.dumps({"success": False, "error": "No data provided"}).encode('utf-8'))
            elif self.path == '/api/env/update':
                if content_length > 0:
                    post_data = self.rfile.read(content_length)
                    data = json.loads(post_data.decode('utf-8'))
                    self.handle_env_update(data)
                else:
                    self.wfile.write(json.dumps({"success": False, "error": "No data provided"}).encode('utf-8'))
            # NEW PERFORMANCE TRACKING POST ENDPOINTS
            elif self.path == '/api/performance/alerts':
                if content_length > 0:
                    post_data = self.rfile.read(content_length)
                    data = json.loads(post_data.decode('utf-8'))
                    self.handle_performance_alerts_update(data)
                else:
                    self.wfile.write(json.dumps({"success": False, "error": "No data provided"}).encode('utf-8'))
            else:
                self.wfile.write(json.dumps({"error": "Endpoint not found"}).encode('utf-8'))
        except Exception as e:
            logger.error(f'Error handling POST request: {e}')
            try:
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode('utf-8'))
            except:
                pass

    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self.send_response(200)
        self.send_cors_headers()
        self.end_headers()

    def send_cors_headers(self):
        """Send CORS headers for React development"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.send_header('Access-Control-Max-Age', '3600')

    def handle_status_request(self):
        """Handle system status request - delegate to router"""
        try:
            status_data = core.router.get_system_status()
            self.wfile.write(json.dumps(status_data, indent=2).encode('utf-8'))
            core.router.safe_stats_update({'ui_requests': 1})
        except Exception as e:
            logger.error(f"Status request error: {e}")
            self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode('utf-8'))

    def handle_stats_request(self):
        """Handle statistics request - delegate to router"""
        try:
            stats_data = core.router.get_system_stats()
            self.wfile.write(json.dumps(stats_data, indent=2).encode('utf-8'))
        except Exception as e:
            logger.error(f"Stats request error: {e}")
            self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode('utf-8'))

    def handle_activity_request(self):
        """Handle activity log request - delegate to router"""
        try:
            activity_data = core.router.get_system_activity()
            self.wfile.write(json.dumps(activity_data, indent=2).encode('utf-8'))
        except Exception as e:
            logger.error(f"Activity request error: {e}")
            self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode('utf-8'))

    def handle_health_request(self):
        """Handle health check request"""
        try:
            health_data = {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "uptime": "running",
                "version": "3.0.0",
                "performance_tracking": performance_tracker is not None,
                "mongodb_connected": self._check_mongodb_connection()
            }
            self.wfile.write(json.dumps(health_data, indent=2).encode('utf-8'))
        except Exception as e:
            logger.error(f"Health request error: {e}")
            self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode('utf-8'))

    def handle_config_request(self):
        """Handle configuration request - delegate to router"""
        try:
            config_data = core.router.get_system_config()
            self.wfile.write(json.dumps(config_data, indent=2).encode('utf-8'))
        except Exception as e:
            logger.error(f"Config request error: {e}")
            self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode('utf-8'))

    def handle_env_request(self):
        """Handle environment variables request - delegate to router"""
        try:
            env_vars = core.router.get_system_env_vars()
            self.wfile.write(json.dumps(env_vars, indent=2).encode('utf-8'))
        except Exception as e:
            logger.error(f"Env request error: {e}")
            self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode('utf-8'))

    def handle_env_update(self, data):
        """Handle environment variables update request"""
        try:
            updates = data.get('updates', {})
            if not updates:
                self.wfile.write(json.dumps({"success": False, "error": "No updates provided"}).encode('utf-8'))
                return
            # Update the .env file
            success = update_env_file(updates)
            if success:
                response_data = {
                    "success": True,
                    "message": "Environment variables updated successfully",
                    "updated_at": datetime.now().isoformat()
                }
                self.wfile.write(json.dumps(response_data).encode('utf-8'))
            else:
                self.wfile.write(
                    json.dumps({"success": False, "error": "Failed to update environment variables"}).encode('utf-8'))
        except Exception as e:
            logger.error(f"Env update error: {e}")
            self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode('utf-8'))

    def handle_save_config(self, data):
        """Handle configuration save request (legacy endpoint)"""
        try:
            service_id = data.get('service', 'unknown')
            config_updates = data.get('config', {})
            if not config_updates:
                self.wfile.write(json.dumps({"success": False, "error": "No configuration provided"}).encode('utf-8'))
                return
            # Update the .env file
            success = update_env_file(config_updates)
            if success:
                response_data = {
                    "success": True,
                    "message": "Configuration saved successfully",
                    "service": service_id,
                    "saved_at": datetime.now().isoformat()
                }
                self.wfile.write(json.dumps(response_data).encode('utf-8'))
            else:
                self.wfile.write(
                    json.dumps({"success": False, "error": "Failed to save configuration"}).encode('utf-8'))
        except Exception as e:
            logger.error(f"Config save error: {e}")
            self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode('utf-8'))

    def handle_start_automation(self, data):
        """Handle automation start request from React Agentic_UI - delegate to router"""
        try:
            result = core.router.handle_ui_automation_request(data)
            self.wfile.write(json.dumps(result, indent=2).encode('utf-8'))
        except Exception as error:
            logger.error(f"Agentic_UI automation request failed: {error}")
            self.wfile.write(json.dumps({
                "success": False,
                "error": str(error)
            }).encode('utf-8'))

    def handle_stop_automation(self):
        """Handle automation stop request from React Agentic_UI - delegate to router"""
        try:
            result = core.router.stop_ui_automation()
            self.wfile.write(json.dumps(result, indent=2).encode('utf-8'))
        except Exception as error:
            logger.error(f"Agentic_UI stop automation request failed: {error}")
            self.wfile.write(json.dumps({
                "success": False,
                "error": str(error)
            }).encode('utf-8'))

    def handle_reset_stats(self):
        """Handle statistics reset request - delegate to router"""
        try:
            result = core.router.reset_system_stats()
            self.wfile.write(json.dumps(result, indent=2).encode('utf-8'))
        except Exception as error:
            self.wfile.write(json.dumps({
                "success": False,
                "error": str(error)
            }).encode('utf-8'))

    # NEW: Current agents handler
    def handle_current_agents_request(self):
        """Handle current session agent stats request"""
        try:
            if not core.router.router_instance:
                # Return default agent stats if router is not initialized
                current_time = datetime.now().strftime("%I:%M:%S %p")
                default_agents = [
                    {
                        "id": "PlannerAgent",
                        "name": "Planner",
                        "status": "active",
                        "tasksProcessed": 0,
                        "tokensConsumed": 0,
                        "lastActivity": current_time
                    },
                    {
                        "id": "AssemblerAgent",  # FIXED: Added missing AssemblerAgent
                        "name": "Assembler",
                        "status": "active",
                        "tasksProcessed": 0,
                        "tokensConsumed": 0,
                        "lastActivity": current_time
                    },
                    {
                        "id": "DeveloperAgent",
                        "name": "Developer",
                        "status": "active",
                        "tasksProcessed": 0,
                        "tokensConsumed": 0,
                        "lastActivity": current_time
                    },
                    {
                        "id": "ReviewerAgent",
                        "name": "Reviewer",
                        "status": "active",
                        "tasksProcessed": 0,
                        "tokensConsumed": 0,
                        "lastActivity": current_time
                    }
                ]
                response = {
                    "success": True,
                    "current_agents": default_agents,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                current_agents = core.router.router_instance.get_current_agent_stats()
                response = {
                    "success": True,
                    "current_agents": current_agents,
                    "timestamp": datetime.now().isoformat()
                }
            self.wfile.write(json.dumps(response).encode('utf-8'))
        except Exception as e:
            logger.error(f"Current agents request error: {e}")
            current_time = datetime.now().strftime("%I:%M:%S %p")
            # Return default agents on error - FIXED: Added AssemblerAgent here too
            default_agents = [
                {
                    "id": "PlannerAgent",
                    "name": "Planner",
                    "status": "active",
                    "tasksProcessed": 0,
                    "tokensConsumed": 0,
                    "lastActivity": current_time
                },
                {
                    "id": "AssemblerAgent",  # FIXED: Added missing AssemblerAgent
                    "name": "Assembler",
                    "status": "active",
                    "tasksProcessed": 0,
                    "tokensConsumed": 0,
                    "lastActivity": current_time
                },
                {
                    "id": "DeveloperAgent",
                    "name": "Developer",
                    "status": "active",
                    "tasksProcessed": 0,
                    "tokensConsumed": 0,
                    "lastActivity": current_time
                },
                {
                    "id": "ReviewerAgent",
                    "name": "Reviewer",
                    "status": "active",
                    "tasksProcessed": 0,
                    "tokensConsumed": 0,
                    "lastActivity": current_time
                }
            ]
            response = {
                "success": True,
                "current_agents": default_agents,
                "timestamp": datetime.now().isoformat()
            }
            self.wfile.write(json.dumps(response).encode('utf-8'))

    # NEW: Performance data handler
    def handle_performance_data_request(self):
        """Handle performance data request for the last 7 days"""
        try:
            performance_data = performance_tracker.get_last_7_days_data()

            response_data = {
                "success": True,
                "performance_data": performance_data,
                "timestamp": datetime.now().isoformat()
            }

            self.wfile.write(json.dumps(response_data).encode('utf-8'))

        except Exception as e:
            logger.error(f"Performance data request error: {e}")
            self.wfile.write(json.dumps({
                "success": False,
                "error": str(e),
                "performance_data": []
            }).encode('utf-8'))

    def handle_weekly_performance_request(self):
        """Handle weekly performance data request"""
        try:
            # Get last 7 days data instead of weekly data (method doesn't exist)
            performance_data = performance_tracker.get_last_7_days_data()

            response_data = {
                "success": True,
                "performance_data": performance_data,
                "timestamp": datetime.now().isoformat()
            }

            self.wfile.write(json.dumps(response_data).encode('utf-8'))

        except Exception as e:
            logger.error(f"Weekly performance request error: {e}")
            self.wfile.write(json.dumps({
                "success": False,
                "error": str(e)
            }).encode('utf-8'))

    def handle_real_time_metrics_request(self):
        """Handle real-time metrics request"""
        try:
            real_time_data = performance_tracker.get_real_time_metrics()
            response = {
                "success": True,
                "data": real_time_data,
                "timestamp": datetime.now().isoformat()
            }
            self.wfile.write(json.dumps(response).encode('utf-8'))

        except Exception as e:
            logger.error(f"Real-time metrics request error: {e}")
            self.wfile.write(json.dumps({
                "success": False,
                "error": str(e)
            }).encode('utf-8'))

    def handle_agent_performance_request(self):
        """Handle agent performance data request"""
        try:
            agent_data = performance_tracker.get_agent_performance_data()
            response = {
                "success": True,
                "agent_performance": agent_data,
                "timestamp": datetime.now().isoformat()
            }
            self.wfile.write(json.dumps(response).encode('utf-8'))

        except Exception as e:
            logger.error(f"Agent performance request error: {e}")
            self.wfile.write(json.dumps({
                "success": False,
                "error": str(e)
            }).encode('utf-8'))

    def handle_performance_alerts_update(self, data):
        """Handle performance alerts configuration update"""
        try:
            alert_config = data.get('alerts', {})
            # Save alert configuration (you can extend this to save to MongoDB)
            response = {
                "success": True,
                "message": "Performance alerts configuration updated",
                "config": alert_config,
                "updated_at": datetime.now().isoformat()
            }
            self.wfile.write(json.dumps(response).encode('utf-8'))
        except Exception as e:
            logger.error(f"Performance alerts update error: {e}")
            self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode('utf-8'))

    def _check_mongodb_connection(self) -> bool:
        """Check if MongoDB connection is active"""
        try:
            if performance_tracker is not None and hasattr(performance_tracker, 'client'):
                # Try to ping the database
                performance_tracker.client.admin.command('ping')
                return True
        except Exception:
            pass
        return False

def start_ui_server():
    """Start HTTP server for React Agentic_UI communication"""
    global ui_server, ui_server_thread
    try:
        # Create HTTP server with thread-safe handler
        class ThreadedHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
            daemon_threads = True
            allow_reuse_address = True

        ui_server = ThreadedHTTPServer((config.UI_HOST, config.UI_PORT), ReactUIHandler)
        # Start server in separate thread
        ui_server_thread = threading.Thread(
            target=ui_server.serve_forever,
            daemon=True,
            name="ReactUIServer"
        )
        ui_server_thread.start()
        logger.info(f"React Agentic_UI API API server started on http://{config.UI_HOST}:{config.UI_PORT}")
        logger.info(f"React development server should be running on http://localhost:{config.REACT_DEV_PORT}")
        if performance_tracker is not None:
            logger.info("MongoDB Performance tracking is ACTIVE")
        else:
            logger.warning("Performance tracking is DISABLED - MongoDB not available")
        return True
    except Exception as error:
        logger.error(f"Failed to start Agentic_UI server: {error}")
        return False

def stop_ui_server():
    """Stop the Agentic_UI server"""
    global ui_server
    if ui_server:
        try:
            ui_server.shutdown()
            ui_server.server_close()
            logger.info("React Agentic_UI server stopped")
        except Exception as error:
            logger.error(f"Error stopping Agentic_UI server: {error}")

# Performance tracking integration functions
def track_ui_activity(activity_type: str, details: str = "", success: bool = True):
    """Track Agentic_UI-related activity in performance system"""
    if performance_tracker is not None:
        try:
            # Note: record_activity method may not exist in MongoPerformanceTracker
            # This is a placeholder for future implementation
            logger.debug(f"UI Activity tracked: {activity_type} - {details}")
        except Exception as e:
            logger.error(f"Error tracking Agentic_UI activity: {e}")

def get_performance_summary() -> Dict[str, Any]:
    """Get performance summary for Agentic_UI display"""
    if performance_tracker is None:
        return {"available": False, "message": "Performance tracking not available"}
    try:
        real_time_data = performance_tracker.get_real_time_metrics()
        return {
            "available": True,
            "today_summary": real_time_data.get("today_summary", {}),
            "active_agents": real_time_data.get("active_agents", []),
            "mongodb_connected": True
        }
    except Exception as e:
        logger.error(f"Error getting performance summary: {e}")
        return {"available": False, "error": str(e)}