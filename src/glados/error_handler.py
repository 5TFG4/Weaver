import logging
import sys

class ErrorHandler:
    def __init__(self):
        # Configure logging
        self.logger = logging.getLogger('error_logger')
        self.logger.setLevel(logging.ERROR)
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(handler)

    def handle_error(self, error, context=''):
        """
        Handles errors by logging and reporting them.

        :param error: The exception object caught.
        :param context: Additional context information about where the error occurred.
        """
        # Log the error information
        self.logger.error(f'Error: {error}, Context: {context}')
        # TODO: Implement error reporting logic, e.g., send email, report to a monitoring system

# Example of use
# error_handler = ErrorHandler()
# try:
#     # Your code logic here
#     pass
# except Exception as e:
#     error_handler.handle_error(e, 'Specific context information')
