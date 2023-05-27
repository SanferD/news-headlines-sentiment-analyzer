import os
import logging

def setup_logging():
    """
    Configure logging based on the environment variable.

    If the environment variable IS_LOCAL is set to "true", logging is configured for cli execution.
    Otherwise, logging is configured for aws lambda execution.
    """
    if os.environ.get("IS_LOCAL", "False").lower() == "true":
        logging.basicConfig(level=logging.INFO)
        log = logging
    else:
        log = logging.getLogger()
        log.setLevel(logging.INFO)
    return log
