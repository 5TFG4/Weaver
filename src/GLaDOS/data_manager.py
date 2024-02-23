from .error_handler import ErrorHandler

class DataManager:
    def __init__(self):
        pass

    def save_data(self, data):
        try:
            # Logic to save data
            pass
        except Exception as e:
            ErrorHandler().handle_error(e, 'Error saving data')
            # Optionally, re-raise the exception if it should not be silently handled
            raise

    def retrieve_data(self):
        try:
            # Logic to retrieve data
            pass
        except Exception as e:
            ErrorHandler().handle_error(e, 'Error retrieving data')
            # Optionally, re-raise the exception if it should not be silently handled
            raise
