from artiq.experiment import *


class Exp(EnvExperiment):

    def build(self):
        self.setattr_device('core')
        self.components = []
        b = B(self)
        b.a =
        self.components.append(A(self))
        self.components.append(B(self))

    @kernel
    def run(self):
        print(self.components[0].a())
        print(self.components[1].a())

class A(HasEnvironment):

    def a(self):
        return 1

class B(HasEnvironment):

    def a(self):
        return 2
