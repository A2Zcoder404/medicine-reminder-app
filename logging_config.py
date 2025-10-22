import logging
import os
from datetime import datetime

def setup_logging():
    """Set up logging configuration for the application"""
    # Create logs directory if it doesn't exist
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Set up logging format
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    # Configure root logger
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        datefmt=date_format,
        handlers=[
            # File handler with daily rotation
            logging.FileHandler(
                os.path.join(log_dir, f'app_{datetime.now().strftime("%Y%m%d")}.log'),
                encoding='utf-8'
            ),
            # Console handler
            logging.StreamHandler()
        ]
    )
    
    # Create logger for the application
    logger = logging.getLogger('MedicineReminder')
    logger.setLevel(logging.INFO)
    
    return logger

# Create and export the logger
logger = setup_logging()