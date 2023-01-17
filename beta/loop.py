from artiq.experiment import *



class Loop(HasEnvironment):
    kernel_invariants = {'nrepeats', 'npoints', 'nmeasurements'}

    def init(self, nmeasurements, ncalcs, measurements):
        raise Exception("Loop::init() method needs to be implemented")

    @portable
    def loop(self, resume=False):
        raise Exception("Loop::loop() method needs to be implemented")

    @rpc(flags={"async"})
    def mutate_datasets(self, i, i_point, i_plot, data):
        raise Exception("Loop::mutate_datasets() method needs to be implemented")

    def terminate(self):
        pass

    def fit(self, entry, save, use_mirror, dimension, i):
        raise Exception("Loop::fit() method needs to be implemented")
