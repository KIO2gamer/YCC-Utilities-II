class ModLogNotFound(Exception):

    def __str__(self):
        return 'No matching modlog entries found.'


class DurationError(Exception):

    def __str__(self):
        return 'An invalid duration was specified.'
