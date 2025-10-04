#!/usr/bin/env python3
"""
Startup script for the translation service
"""

import os
import sys
import subprocess
import logging
from pathlib import Path

def install_dependencies():
    """Install required Python dependencies."""
    print("📦 Installing Python dependencies...")
    try:
        result = subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
                              capture_output=True, text=True, check=True)
        print("✅ Dependencies installed successfully")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        print(f"Stdout: {e.stdout}")
        print(f"Stderr: {e.stderr}")
        return False
    return True

def check_database():
    """Check if database is accessible."""
    print("🗄️ Checking database connection...")
    try:
        from translation_service import TranslationService
        service = TranslationService()
        tasks = service.get_pending_tasks(limit=1)
        print("✅ Database connection successful")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def start_service():
    """Start the translation service."""
    print("🚀 Starting translation service...")
    try:
        # Import and run the service
        from translation_service import TranslationService
        service = TranslationService()
        service.process_tasks()
    except KeyboardInterrupt:
        print("\n👋 Service stopped by user")
    except Exception as e:
        print(f"❌ Service failed to start: {e}")
        return False
    return True

def main():
    """Main startup function."""
    print("🐍 Translation Service Startup")
    print("=" * 40)

    # Install dependencies if needed
    if not install_dependencies():
        sys.exit(1)

    # Check database
    if not check_database():
        print("Please ensure PostgreSQL is running and DATABASE_URL is set")
        sys.exit(1)

    # Start service
    if not start_service():
        sys.exit(1)

if __name__ == "__main__":
    main()