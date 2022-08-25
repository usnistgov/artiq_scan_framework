from .scan import *


# NOTE: MetaScan has been deprecated by Scan2D
class MetaScan(Scan1D):
    """Support for 2D scan of scan.  A top level scan is defined by inheriting from MetaScan.  That top level scan then
    executes a separate 1D scan that inherits from Scan1D."""
    scan_registry = {}  # dictionary containing instance of sub-scans that will be run by the top-level scan.

    def register_scan(self, scan, name=None, enable_pausing=False):
        """Register a sub scan.  By registering a scan, it's prepare(), _initialize_scan(), and prepare_scan() methods
        will automatically be called immediately before those methods are called on the top level scan.
        Scan's must be registered in the build method of the top level scan.
        :param scan: Instance of the scan to register
        :param name: Name of the scan to register, must be unique.
        :param enable_pausing: pausing/terminating sub-scans does not work with the current scan architecture,
        it is recommended to keep this set to False.  This will override the enable_pausing attribute of the passed
        in scan instance.
        """
        if name != None:
            if name in self.scan_registry:
                raise Exception("Cannot register the scan named '{0}' the name has already been used.  "
                                "You must pick a unique name to register this scan under.".format(name))
            scan.enable_pausing = enable_pausing
            self.scan_registry[name] = scan
            self.logger.debug('registered scan \'{0}\' of type \'{1}\''.format(name, scan.__class__.__name__))
        else:
            raise Exception("Cannot register scan.  The name argument is required.")

    # prepare sub scans
    def prepare(self):
        super().prepare()
        for name, s in self.scan_registry.items():
            self.logger.debug('calling \'{0}.prepare()\''.format(name))
            s.prepare()

    # sub scans are always initialized before top level scan
    def _initialize(self, resume):
        # initialize sub scans
        for name, s in self.scan_registry.items():
            self.logger.debug('calling \'{0}.initialize()\''.format(name))
            s._initialize(resume)

        # initialize top level scan
        super()._initialize(resume)

    # sub scans are always prepared before top level scan
    def prepare_scan(self):
        # prepare sub scans
        for name, s in self.scan_registry.items():
            self.logger.debug('calling \'{0}.prepare_scan()\''.format(name))
            s.prepare_scan()

        # prepare top level scan
        super().prepare_scan()
