import logging

# Error Logging
def init_logger(log_file="errors.log"):
    logging.basicConfig(
        filename=log_file,
        level=logging.ERROR,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

def log_Error(message):
    logging.error(message)
