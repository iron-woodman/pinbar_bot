## -*- coding: utf-8 -*-
import logging
import os
from datetime import datetime

date_str = datetime.now().strftime("%Y%m%d")
log_file = f'logs/{date_str}_patternsbot.log'


def configure_logging(log_level=logging.INFO):
    if not os.path.exists(log_file):
        with open(log_file, 'w'):
            pass

    log_format = '%(asctime)s - %(levelname)s - %(message)s'
    logging.basicConfig(filename=log_file, level=log_level, format=log_format)


configure_logging()


def info(message):
    logger = logging.getLogger(__name__)
    logger.info(message)


def error(message):
    logger = logging.getLogger(__name__)
    logger.error(message)


def warning(message):
    logger = logging.getLogger(__name__)
    logger.warning(message)


