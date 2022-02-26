Getting stated with models
==========================

Namespaces
----------------
Datasets are logically grouped under a common namespace.
Access to the datasets under a namespace is provided by defining a model and specifying it's namespace.  Namespaces can include % prefixed tokens which are replaced by the values of class variable that have the same name.  If a corresponding class variable is not found for a token, that token will stripped out of the namespace.  For example,

.. code-block:: python

    from app.models.model import *
    class MicrowavesModel(Model):
        namespace = 'microwaves.%transition.%foo'  #: Dataset namespace

    class MyExperiment(EnvExperiment):
        def build(self):
            self.model = MicrowavesModel(self, transition=1)
            print(self.model.namespace)
            self.model.set('frequency', 500*MHz)

will print **"microwaves.1"** (the namespace) and write 500,000,000 to the dataset **"microwaves.1.frequency"**

Re-Binding
----------------
A model can be re-bound to it's namespace at any time as class variables are either added or changed by calling the model's bind() method  e.g. `self.model.bind()`.  The current class variable values are used to fill out the namespace just as is done when the model is instantiated.  This allows for dynamic rebinding of a model to different namespaces.  An example is a single microwaves model which rebinds to different transitions to read pi times and frequencies as opposed to having one model for each transition.  If a token was stripped out of the namespace in a previous bind(), it is still apart of the namespace and can be used in future binds() once the class variable has been set.  Following the above example,

.. code-block:: python

    class MyExperiment(EnvExperiment):
        def build(self):
            self.model = MicrowavesModel(self, transition=1)
            print(self.model.namespace)
            self.model.foo = 'bar'
            self.model.bind()
            print(self.model.namespace)

will print **"microwaves.1"** (the first namespace), followed by **microwaves.1.bar** (the second namespace)


Broadcast, Persist, & Save
----------------------------
Default values for the broadcast, persist, and save arguments of set_dataset() can be tailored to the model when it's behavior is known.  For example:

.. code-block:: python

    from app.models.model import *
    class RsbModel(Model):
        namespace = 'heating_rate.rsb'
        persist = True
        broadcast = True
        save = False

    class MyExperiment(EnvExperiment):
        def build(self):
            self.model = RsbModel(self)
            self.model.set('ds_value', 12345)

Is equivalent to

.. code-block:: python

    self.set_dataset('heating_rate.rsb.ds_value', 12345, broadcast=True, persist=True, save=False)

Having to specify broadcast, persist, and save is then not necessary when you know the behavior of broadcast, persist,
and save for all datasets that will be set by the model.

For datasets that don't conform to the model assumptions, defaults can still be overridden as usual by specifying the
argument.  e.g.

.. code-block:: python

    self.model.set('ds_value', 12345, persist=False, save=True)

Dataset Mirroring
------------------
Model's can mirror all of their datasets to another namespace.  This is useful if you want to plot data for multiple
model's in a single applet by having the model's share the same mirror namespace.  Mirroring is enabled by default and
the mirror datasets are updated when either the :meth:`Model::set() <scan_framework.models.model.Model.set>`
or :meth:`Model::mutate() <scan_framework.models.model.Model.mutate>` methods are called.

.. note::
    To disable mirroring set the models :attr:`mirror <scan_framework.models.model.Model.mirror>` attribute to :code:`False`

