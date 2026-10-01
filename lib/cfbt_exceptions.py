import lib.cfbt_i18n as i18n


# The user cancelled a running process
class CancelledException(Exception):
    pass


# The user declined a confirmation prompt, which means aborting the process
class DeclinedException(Exception):
    pass


# An anticipated problem (e.g. an invalid input file), explained to the user
# by its message instead of a technical error dialog
class ExpectedException(Exception):

    # <key> is a language file key (or, for messages not converted yet, the plain English message).
    # str(e) is always the English text (for the log), key and params allow the UI to localize it
    def __init__(self, key, **params):
        self.key = key
        self.params = params
        super().__init__(i18n.t_en(key, **params))


# The run was paused on purpose (e.g. after terminology, so that the user can review it)
class PausedException(Exception):
    pass
