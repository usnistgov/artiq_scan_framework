from artiq.experiment import *



class Paused(Exception):
    """Exception raised on the core device when a scan should either pause and yield to a higher priority experiment or
    should terminate."""
    pass

class MyClass(HasEnvironment):

    def build(self, parent):
        self.parent = parent

    @kernel
    def kernel_method(self):
        print('MyClass::kernel_method')
        self.parent.loop()

class TestContinuousScan(EnvExperiment):


    def build(self):
        self.setattr_device('core')
        self.setattr_device('scheduler')
        self.my_class = MyClass(self, self)
        self.kernel_method = self.my_class.kernel_method

    @kernel
    def run(self):
        try:
            self.kernel_method()
        except Paused:
            print('paused')
        finally:
            print('finally')

    @kernel
    def kernel_method(self):
        print('TestContinuousScan::kernel_method')

    @kernel
    def loop(self):
        while True:
            print('check_pause')
            self.check_pause()