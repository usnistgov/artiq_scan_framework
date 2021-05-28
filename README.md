The NIST Scan Framework
=======================

The NIST scan framework is a framework that greatly simplifies the process of writing and maintaining
scans of experimental parameters using the ARTIQ control system and language.  The framework adopts the 
philosophy of convention over configuration where datasets are stored for analysis and plotting in a standard
directory structure. 

The framework provides a number of useful features such as automatic calculation of statistics, fitting, validation
of fits, and plotting that do not need to be performed by the user.  This reduces the size and complexity of 
scan experiments to make them fast to implement, easy to read, and easy to maintain.   

Please refer to [TODO: add link to documentation]() for the full scan framework documentation including many worked examples and a
full API listing.  The following gives a broad overview of the most import aspects of the scan framework.

## Getting started
The best way to start using the scan framework is by looking through and running a few example 
scans listed below.  

To start using  the framework:
1. Add the directory containing the 'scan_framework' folder to your 
[PYTHONPATH](https://docs.python.org/3/using/cmdline.html#envvar-PYTHONPATH) environment variable.
2. Add to the `Applets` tab in the dashboard the "current scan", "count monitor", "current histogram", and 
   "current aggregate histogram", applets [listed below](#applets)
3. View the source code for the example scans below and run them in the dashboard.  The first four examples 
   provide everything that is needed for a large set of use cases.  Examples are ordered from basic to advanced 
   and are meant to be followed in chronological order.
   
**Scan examples/tutorials**
- [Ex0: Minimal Scan](examples/scans/ex00_minimal_scan.py)
- [Ex1: Scan Arguments](examples/scans/ex01_scan_arguments.py)
- [Ex2: Calculating & Plotting Statistics](examples/scans/ex02_models.py)
- [Ex3: Fitting](examples/scans/ex03_fitting.py)
- [Ex4: Callbacks](examples/scans/ex04_callbacks.py) -- see the documentation for details on all available [callbacks]().
- [Ex5: Multiple Measurements](examples/scans/ex05_measurements.py) -- Also create the 'example_5' applet below
- [Ex6: Dynamic Models](examples/scans/ex06_dynamic_models.py) -- Also create the 'example_6' applet below
- [Ex7a: Warmup Points 1](examples/scans/ex07a_warmup_points.py)
- [Ex7b: Warmup Points 2](examples/scans/ex07b_warmup_points.py)
- [Ex7c: Warmup Points 3](examples/scans/ex07c_warmup_points.py)
- [Ex8: Rename Main Fit](examples/scans/ex08_rename_main_fit_dataset.py)
- [Ex9: After Measure Callback](examples/scans/ex09_after_measure.py)
- [Ex10: Fit Guess Arguments](examples/scans/ex10_fit_guess_arguments.py)
- [Ex11: Fit Validations](examples/scans/ex11_fit_validations.py)
  
---

**Note:**

To run an example, right click the `Explorer` tab in the dashboard and choose `Open file outside repository`.  Then navigate to the `scan_framework/examples/scans` folder.

---

Additional real world examples are provided in `scan_framework/examples/scans` and `scan_framework/examples/models` that illustrate 
how the scan class is used in a real lab setup.

## Documentation
Full documentation is available at TODO: add link to documentation (Documentation)[]

Detailed APIs are also available:
TODO: Update Links
1. [API for scans](http://nist.gov/pages/scan_framework/public/scans/api.html)
2. [API for models](http://nist.gov/pages/scan_framework/public/models/api.html)
3. [API for applets](http://nist.gov/pages/scan_framework/public/applets/api.html)
4. [API for curve fitting](http://nist.gov/pages/scan_framework/public/analysis/api.html)

## Scan framework settings
Framework features can be enabled or disabled in the `build()` method of your scan class
by setting the associated class attribute listed below to either True or False:

| Scan feature          | Enabled by default? | Associated settings                             | Associated methods                     
| --------------------- | ------------------- | ----------------------------------------------- | ------------------------------------- 
| Dataset mutating      |  Yes                | `self.enable_mutate`                            |                                       
| Fitting               |  Yes                | `self.enable_fitting`                           |                                       
| Pausing/Terminating   |  Yes                | `self.enable_pausing`                           |                                       
| Count monitoring      |  Yes                | `self.enable_count_monitor` `self.counts_prec`  |                                       
| Reporting             |  Yes                | `self.enable_reporting`                         | `self.report()` `self.report_fit()`   
| Warm-up points        |  No                 | `self.nwarmup_points`                           |                                       
| Auto tracking         |  No                 | `self.enable_auto_tracking`                     |                                       
| Host scans            |  No                 | `self.run_on_core`                              |
| Scan simulating       |  No                 | `self.enable_simulations`                       |                                       
| Profiling/Timing      |  No                 | `self.enable_profiling` `self.enable_timing`    |                                       

| Setting                     | Description                                                                                                                   
| --------------------------- | ----------------------------------------------------------------------------------------------------------------------------- 
| `self.enable_mutate`        | Mutate mean values and standard errors datasets after each scan point.  Used to monitor progress of scan while it is running. 
| `self.enable_fitting`       | Enable or disable all fitting features                                                                                        
| `self.enable_pausing`       | Check pause via `self.scheduler.check_pause()` and automatically yield/terminate the scan when needed.                        
| `self.enable_count_monitor` | Update the '/counts' dataset with the average of all values returned by 'measure()' during a single scan point.
| `self.counts_prec`          | Set to a value >= 0 to round the '/counts' dataset to the specified number of digits.
| `self.enable_reporting`     | Print useful information to the Log window before a scan starts (i.e. number of passes, etc.) and when a fit is performed (fitted values, etc.)
| `self.nwarmup_points`       | Number of warm-up points
| `self.enable_auto_tracking` | Auto center the scan range around the last fitted value.
| `self.run_on_core`          | Set to False to run scans entirely on the host and not on the core device
| `self.enable_simulations`   | Turn on GUI arguments for simulating scans                                                                                   
| `self.enable_profiling`     | Profile the execution of the scan to find bottlenecks                                                                        
| `self.enable_timing`        | Enable automatic timing of certain events.  Currently only compilation time is timed

## Applets
Below are all the applet commands provided to view data generated by the scan framework.  These are also available in [applet_commands.txt](applet_commands.txt)

##### Current scan applet
```
$python -m scan_framework.applets.plot_xy current_scan.plots.y
    --x current_scan.plots.x
    --fit current_scan.plots.fitline
    --title current_scan.plots.plot_title
    --x_scale current_scan.plots.x_scale
    --x_units current_scan.plots.x_units
    --y_scale current_scan.plots.y_scale
    --x_label current_scan.plots.x_label
    --y_units current_scan.plots.y_units
    --y_label current_scan.plots.y_label
    --rid current_scan.rid
    --error current_scan.plots.error
```

##### Current histogram applet
```
$python -m scan_framework.applets.plot_hist current_hist.bins
    --x current_hist.bin_boundaries
    --x_units current_hist.x_units
    --x_label current_hist.x_label
    --plot_title current_hist.plot_title
```

##### Current histogram applet (aggregate over the entire scan)
```
$python -m scan_framework.applets.plot_hist current_hist.aggregate_bins
    --x current_hist.bin_boundaries
    --x_units current_hist.x_units
    --x_label current_hist.x_label
    --plot_title current_hist.plot_title
```

##### Count monitor applet
```
${artiq_applet}big_number counts
```

##### Current sub-scan applet applet (for 2D scans)
```
$python -m scan_framework.applets.plot_xy current_scan.plots.dim1.y
    --x current_scan.plots.dim1.x
    --fit current_scan.plots.dim1.fitline
    --title current_scan.plots.dim1.plot_title
    --x_scale current_scan.plots.dim1.x_scale
    --x_units current_scan.plots.dim1.x_units
    --x_label current_scan.plots.dim1.x_label
    --y_units current_scan.plots.dim1.y_units
    --y_label current_scan.plots.dim1.y_label
    --trigger current_scan.plots.trigger
    --rid current_scan.rid
    --i_plot current_scan.plots.subplot.i_plot
```

##### Current sub-scan applet without fits applet (for 2D scans)
```
$python -m scan_framework.applets.plot_xy current_scan.plots.dim1.y
    --x current_scan.plots.dim1.x
    --title current_scan.plots.dim1.plot_title
    --x_scale current_scan.plots.dim1.x_scale
    --x_units current_scan.plots.dim1.x_units
    --x_label current_scan.plots.dim1.x_label
    --y_units current_scan.plots.dim1.y_units
    --y_label current_scan.plots.dim1.y_label
    --trigger current_scan.plots.trigger
    --rid current_scan.rid
    --i_plot current_scan.plots.subplot.i_plot
```

###### Applet for Example 4
```
$python -m scan_framework.applets.plot_xy_ntrace_white
    example_4.m1.stats.mean
    --x1 example_4.m1.stats.points
    --error1 example_4.m1.stats.error
    --fit1 example_4.m1.fits.fitline
    example_4.m2.stats.mean
    --x2 example_4.m2.stats.points
    --error2 example_4.m2.stats.error
    --fit2 example_4.m2.fits.fitline
    example_4.m2.stats.mean
    --x3 example_4.m2.stats.points
    --error3 example_4.m2.stats.error
    --fit3 example_4.m2.fits.fitline
```

###### Applet for Example 5
```
$python -m scan_framework.applets.plot_xy_ntrace_white
    example_5.m1.stats.mean
    --x1 example_5.m1.stats.points
    --error1 example_5.m1.stats.error
    --fit1 example_5.m1.fits.fitline
    example_5.m2.stats.mean
    --x2 example_5.m2.stats.points
    --error2 example_5.m2.stats.error
    --fit2 example_5.m2.fits.fitline
    example_5.m2.stats.mean
    --x3 example_5.m2.stats.points
    --error3 example_5.m2.stats.error
    --fit3 example_5.m2.fits.fitline
```

## Kernel invariants
The following scan attributes are marked as kernel invariants by default:
`self.npasses`, `self.nbins`, `self.nrepeats`, `self.npoints`, `self.nmeasurements`,
`self.do_fit`, `self.save_fit`, `self.fit_only`

The kernel invariants can be changed anywhere within the child scan class by manually setting `self.kernel_invariants` .

## `save=True`, `broadcast=False`, `persist=False` 

The default behavior of the scan model is to save all data to the HDf5 file of the experiment, but to 
not broadcast or persist datasets (i.e. `save=True`, `broadcast=False` and `persist=False` when 
datasets are created).

The exception to this rule is saved fit parameters which are both broadcast and persisted as well as saved to the 
HDf5 file  (i.e. `save=True`, `broadcast=True` and `persist=True` when 
datasets are created).

If you wish to override this behavior, set the `save`, `broadcast`, or `persist` attributes in the build method
of your scan model class

## License
The NIST scan framework is distributed under the GNU Lesser General Public License v3.0 or later.  

SPDX-License-Identifier: LGPL-3.0-or-later