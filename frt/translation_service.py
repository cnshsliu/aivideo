#!/usr/bin/env python3
"""
DOCX Translation Service
This service handles DOCX file translation and updates the database.
"""

import os
import sys
import json
import time
import shutil
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

# Database imports
import psycopg2
from psycopg2.extras import RealDictCursor
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('translation_service.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class TranslationService:
    def __init__(self, database_url: str = None):
        """Initialize the translation service with database connection."""
        self.database_url = database_url or os.getenv('DATABASE_URL', 'postgresql://root:mysecretpassword@localhost:5432/local')
        self.engine = create_engine(self.database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

        logger.info("Translation service initialized")

    def get_pending_tasks(self, limit: int = 5) -> list[Dict[str, Any]]:
        """Get tasks that are pending Python processing."""
        try:
            with self.engine.connect() as conn:
                query = text("""
                    SELECT tt.*, tq.queue_status, tq.attempts, tq.max_attempts
                    FROM translation_task tt
                    LEFT JOIN task_queue tq ON tt.task_id = tq.task_id
                    WHERE tt.status = 'pending_python_processing'
                    ORDER BY tt.created_at ASC
                    LIMIT :limit
                """)

                result = conn.execute(query, {'limit': limit})
                tasks = []
                for row in result.fetchall():
                    task_dict = dict(row._mapping)
                    tasks.append(task_dict)

                logger.info(f"Found {len(tasks)} pending tasks")
                return tasks

        except Exception as e:
            logger.error(f"Error getting pending tasks: {e}")
            return []

    def update_task_status(self, task_id: str, status: str, error_message: str = None,
                          translated_file_path: str = None, translated_content: str = None):
        """Update task status in database."""
        try:
            with self.engine.connect() as conn:
                # Update translation_task
                update_query = text("""
                    UPDATE translation_task
                    SET status = :status,
                        completed_at = :completed_at,
                        error_message = :error_message,
                        docx_path = :docx_path,
                        source_content = :source_content
                    WHERE task_id = :task_id
                """)

                conn.execute(update_query, {
                    'status': status,
                    'completed_at': datetime.utcnow() if status == 'completed' else None,
                    'error_message': error_message,
                    'docx_path': translated_file_path,
                    'source_content': translated_content,
                    'task_id': task_id
                })

                # Update task_queue
                update_queue_query = text("""
                    UPDATE task_queue
                    SET queue_status = :queue_status,
                        completed_at = :completed_at,
                        error_message = :error_message
                    WHERE task_id = :task_id
                """)

                conn.execute(update_queue_query, {
                    'queue_status': status,
                    'completed_at': datetime.utcnow() if status == 'completed' else None,
                    'error_message': error_message,
                    'task_id': task_id
                })

                conn.commit()
                logger.info(f"Updated task {task_id} status to {status}")

        except Exception as e:
            logger.error(f"Error updating task {task_id} status: {e}")
            raise

    def translate_docx_file(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Translate a DOCX file (stub implementation - returns source file).

        Args:
            task: Task dictionary containing file information

        Returns:
            Dictionary with translation results
        """
        try:
            task_id = task['task_id']
            source_file_path = task['source_file_path']
            source_language = task['source_language']
            target_language = task['target_language']

            # Get original file information
            original_file_extension = task.get('original_file_extension', 'docx')
            original_file_name = task.get('original_file_name', f'{task_id}.{original_file_extension}')

            logger.info(f"Processing DOCX translation for task {task_id}")
            logger.info(f"Source file: {source_file_path}")
            logger.info(f"Original filename: {original_file_name}")
            logger.info(f"Original extension: {original_file_extension}")
            logger.info(f"Language pair: {source_language} -> {target_language}")

            # Check if source file exists
            if not os.path.exists(source_file_path):
                raise FileNotFoundError(f"Source file not found: {source_file_path}")

            # Create uploads directory if it doesn't exist
            uploads_dir = Path("uploads")
            uploads_dir.mkdir(exist_ok=True)

            # Generate output file path using new naming convention: TASK_ID_translated.ORIGINAL_SUFFIX
            output_filename = f"{task_id}_translated.{original_file_extension}"
            output_file_path = uploads_dir / output_filename

            # STUB IMPLEMENTATION: Just copy the source file
            # This will be replaced with actual translation logic later
            logger.info(f"Using stub implementation - copying source file to {output_file_path}")
            shutil.copy2(source_file_path, output_file_path)

            # Extract text content for database storage (placeholder)
            content_preview = f"[TRANSLATED] {original_file_name}"

            result = {
                'success': True,
                'output_file': str(output_file_path),
                'translated_content': content_preview,
                'message': 'Translation completed (stub implementation)'
            }

            logger.info(f"Translation completed for task {task_id}")
            logger.info(f"Output file: {output_file_path}")
            return result

        except Exception as e:
            logger.error(f"Translation failed for task {task.get('task_id', 'unknown')}: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': f'Translation failed: {e}'
            }

    def process_tasks(self):
        """Main processing loop."""
        logger.info("Starting translation service processing loop")

        while True:
            try:
                # Get pending tasks
                tasks = self.get_pending_tasks(limit=3)

                if not tasks:
                    logger.info("No pending tasks, waiting...")
                    time.sleep(10)  # Wait 10 seconds before checking again
                    continue

                # Process each task
                for task in tasks:
                    task_id = task['task_id']
                    logger.info(f"Processing task: {task_id}")

                    try:
                        # Mark task as processing
                        self.update_task_status(task_id, 'processing')

                        # Process the translation
                        result = self.translate_docx_file(task)

                        if result['success']:
                            # Mark as completed
                            self.update_task_status(
                                task_id=task_id,
                                status='completed',
                                translated_file_path=result['output_file'],
                                translated_content=result['translated_content']
                            )
                            logger.info(f"Task {task_id} completed successfully")
                        else:
                            # Mark as failed
                            self.update_task_status(
                                task_id=task_id,
                                status='failed',
                                error_message=result['error']
                            )
                            logger.error(f"Task {task_id} failed: {result['error']}")

                    except Exception as e:
                        logger.error(f"Error processing task {task_id}: {e}")
                        # Mark as failed
                        self.update_task_status(
                            task_id=task_id,
                            status='failed',
                            error_message=str(e)
                        )

                # Small delay between batches
                time.sleep(5)

            except KeyboardInterrupt:
                logger.info("Received interrupt signal, shutting down...")
                break
            except Exception as e:
                logger.error(f"Unexpected error in processing loop: {e}")
                time.sleep(30)  # Wait longer on errors

def main():
    """Main entry point."""
    try:
        # Get database URL from environment or use default
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            # Try to read from .env file
            if os.path.exists('.env'):
                with open('.env', 'r') as f:
                    for line in f:
                        if line.startswith('DATABASE_URL='):
                            database_url = line.strip().split('=', 1)[1].strip('"\'')
                            break

        if not database_url:
            logger.error("DATABASE_URL environment variable not set")
            sys.exit(1)

        # Initialize and run service
        service = TranslationService(database_url)
        logger.info("Starting translation service...")
        service.process_tasks()

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()