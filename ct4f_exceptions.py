# The user cancelled a running process
class CancelledException(Exception):
    pass


# The user declined a confirmation prompt, which means aborting the process
class DeclinedException(Exception):
    pass


# An anticipated problem (e.g. an invalid input file), explained to the user
# by its message instead of a technical error dialog
class ExpectedException(Exception):
    pass
