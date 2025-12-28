import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def check_database_connection():
    # Check if the database is configured correctly
    if not settings.DATABASES:
        logger.error("DATABASES setting is not configured !!")
        raise ValueError("DATABASES setting is not configured")

    # Check if the database is connected properly or not
    try:
        from django.db import connection

        if connection.ensure_connection():
            logger.info("Database connection established")
        else:
            logger.error("Database connection failed !!")

    except Exception as e:
        logger.error(f"Database connection error: {e}")
        raise ValueError(f"Database connection error: {e}")
