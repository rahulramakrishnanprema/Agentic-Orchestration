"""Setup script for development and deployment."""
import subprocess
import sys
import os

def setup_development():
    """Set up the development environment."""
    print("Setting up development environment...")

    # Create necessary directories
    directories = ['logs', 'data', 'config/__pycache__', 'src/__pycache__']
    for directory in directories:
        os.makedirs(directory, exist_ok=True)

    # Install dependencies
    subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])

    # Set up pre-commit hooks if needed
    subprocess.run(['git', 'init'], check=False)

    print("Development environment setup complete!")

def setup_production():
    """Set up the production environment."""
    print("Setting up production environment...")
    subprocess.run(['docker-compose', 'build'])
    print("Production environment setup complete!")

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ['dev', 'prod']:
        print("Usage: python setup.py [dev|prod]")
        sys.exit(1)

    if sys.argv[1] == 'dev':
        setup_development()
    else:
        setup_production()
