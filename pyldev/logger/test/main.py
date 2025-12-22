import os, sys

LOGGER_DIR_PATH = os.path.dirname(os.path.dirname(__file__))
if __name__ == "__main__":
    sys.path.append(os.path.dirname(LOGGER_DIR_PATH))


from logger import Logger, LoggerPrintIntercept

logger = LoggerPrintIntercept(logs_dir=os.path.dirname(__file__))
# logger.auto_config()
logger.custom_config()
logger.start()

print("This is a debug log")
logger.log_error("This is a custom logged error.")
print("This an other debug log")

# logger will eventually crash when program stops (no flush), which is intended.
