
import os, sys

LOGGER_DIR_PATH = os.path.dirname(os.path.dirname(__file__))
if __name__ == "__main__":
    sys.path.append(os.path.dirname(LOGGER_DIR_PATH))


from logger import Logger, LoggerPrintIntercept

# This a wrong use, and will result in double logging (messages are logged twice by Logger and LoggerPrintIntercept respectively.)
if 0:
    logger_standard = Logger()
    logger_standard.log_info("test message")
    logger_print = LoggerPrintIntercept()
    logger_print.start()

    print("an other test")

    logger_print.stop()

    print("a stopped test")

    logger_standard.log_info("no longer tracking prints")

# This englobe the standard Logger features, and should be the only logger used, when needed.
if 1:
    print_logger = LoggerPrintIntercept()
    print_logger.log_info("starting print logging")
    print_logger.start()
    print("this is a test log message")
    print_logger.log_info("stopping print logging")
    print_logger.stop()
    print("this musn't appear in the logs content")
    print_logger.log_debug("Check if the print logger stopped correctly.")
