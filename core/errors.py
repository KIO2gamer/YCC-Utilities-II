class ModLogNotFound(Exception):

    def __str__(self):
        return 'No matching modlog entries found.'
