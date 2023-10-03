class RewindAndLoadIon(Exception):
    pass


class IonPresent(Exception):
    pass


class Paused(Exception):
    """Exception raised on the core device when a scan should either pause and yield to a higher priority experiment or
    should terminate."""
    pass


class LostIon(Exception):
    pass


class LoadIon(Exception):
    pass


class ExitScan(Exception):
    pass


class BadFit(Exception):
    pass


class CantFit(Exception):
    pass
