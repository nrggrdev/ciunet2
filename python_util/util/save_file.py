from contextlib import ContextDecorator
import logging
import os


class open_savefile(ContextDecorator):
    """Save File context manager
    It is a I/O device for writing text and binary files, without losing existing data if the writing operation fails,
    similar to QSaveFile."""
    def __init__(self, filename, mode="w"):
        self.filename = filename
        self.mode = mode
        self.tmp_filename = filename + ".tmp"

    def __enter__(self):
        self.f = open(self.tmp_filename, self.mode)
        return self.f

    def __exit__(self, exc_type, _exc_value, _traceback):
        self.f.close()
        if exc_type is None:
            try:
                if os.path.exists(self.tmp_filename):
                    if os.path.exists(self.filename):
                        try:
                            os.remove(self.filename)
                        except Exception as e:
                            logging.info(f'{self.filename} was locked: retry')
                            os.remove(self.filename)
                    os.replace(self.tmp_filename, self.filename)
            except Exception as e:
                print(e)
                logging.error(f'could not save {self.filename}')
        else:
            try:
                os.remove(self.tmp_filename)
            except OSError:
                logging.error("Could not remove temporary save file.", exc_info=True)
        return False
