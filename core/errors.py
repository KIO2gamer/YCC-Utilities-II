class ModLogNotFound(Exception):

    def __init__(self, case_id: int):
        self.case_id = case_id

    def __str__(self):
        return f'Case {self.case_id} not found.'
