import logging
import webbrowser
import time
from core.router import initialize_system, run_system, shutdown_system
from ui.ui import start_ui_server, stop_ui_server, config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(threadName)s] - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    try:
        logger.info("Starting AI Development System...")

        # Step 1: Initialize router system first - this must succeed
        if not initialize_system():
            logger.error("Failed to initialize router system")
            return False
        logger.info("Router system initialized successfully")

        # Step 2: Start Agentic_UI server after router is initialized
        if not start_ui_server():
            logger.error("Failed to start Agentic_UI server")
            shutdown_system()  # Clean up router if Agentic_UI fails
            return False
        logger.info("Agentic_UI server started successfully")

        # Open Agentic_UI in browser
        try:
            ui_url = f"http://localhost:{config.REACT_DEV_PORT}"
            logger.info(f"Opening Agentic_UI in browser: {ui_url}")
            webbrowser.open(ui_url)
        except Exception as browser_error:
            logger.warning(f"Could not open browser automatically: {browser_error}")
            logger.info(f"Please manually navigate to: {ui_url}")

        # Step 3: System is ready and waiting for ui trigger
        # DO NOT auto-start the workflow - wait for ui button click
        logger.info("System ready - waiting for ui trigger to start automation")
        run_system()
        return True

    except Exception as e:
        logger.error(f"System startup failed: {e}")
        return False

if __name__ == "__main__":
    try:
        if main():
            logger.info("System running - press Ctrl+C to stop")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Shutdown requested...")
                stop_ui_server()
                shutdown_system()
                logger.info("System shutdown complete")
        else:
            logger.error("System failed to start properly")
    except KeyboardInterrupt:
        logger.info("Shutdown requested...")
        stop_ui_server()
        shutdown_system()
        logger.info("System shutdown complete")