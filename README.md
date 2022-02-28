# The NIST Scan Framework for ARTIQ
The NIST scan framework is a framework that greatly simplifies the process of writing and maintaining
scans of experimental parameters using the ARTIQ control system and language.  The most common and repeated tasks 
of a scan are performed automatically by the framework:

1. Iterating over a list of scan points.
2. Repeating a measurement multiple times at each scan point. 
3. Mutating datasets with the experimental data collected during scan execution.
4. Calculation of statistics on the collected data.
5. Plotting of calculated mean values during execution.
5. Fitting of a function to the calculated mean values.
6. Validation of data before fitting.
7. Validation of the fitted parameters after fitting.

Fitting validation at the end of the scan gives the user control over what fitted parameters should be considered valid 
and helps avoid incorrect fit parameters from being saved and later used in an experiment.  The framework also adopts the 
philosophy of convention over configuration: datasets are stored for analysis and plotting in a standardize way which
removes much of the data handling that needs to performed by the writer of a scan.   

Please refer to https://stylus.ipages.nist.gov/scan_framework/ for the full scan framework documentation including 
many worked examples and a full API listing.  The following gives a broad overview of the most import aspects of 
the scan framework.

## Project Status
Active development

## Testing Summary
The framework has been thoroughly tested through its use in lab experiments at NIST since 2017.  It is currently being 
used by the Quantum Processing Group and the Ion Storage Group at NIST.   

## Getting started


### Prerequisites
The following are required for running the scan framework.  Please see also [REQUIREMENTS.md](REQUIREMENTS.md) for 
a list of these requirements.

#### Hardware Requirements
1. Experimental control hardware running ARTIQ version 3.7

#### Software Requirements
1. Version 3.7 of the [ARTIQ python package](https://m-labs.hk/experiment-control/artiq/).  Please see 
[Installing ARTIQ](https://m-labs.hk/artiq/manual-release-3/installing.html) for instructions on installing ARTIQ.
2. Python version 3.5  
*Note: this is also a requirement for ARTIQ v3 and is covered by the first requirement.* 
3. The [numpy](https://numpy.org/) python package compatible with Python version 3.5.  
*Note: numpy is installed automatically when installing ARTIQ via the m-labs conda channel.*
4. The [scipy](https://www.scipy.org/) python package compatible with Python version 3.5.  
*Note: scipy is installed automatically when installing ARTIQ via the m-labs conda channel.*

(Optional)
1. The [matplotlib](https://matplotlib.org/) python package compatible with Python version 3.5.   
*Note: The matplotlib package is required only by testing routines in the curvefits.py module of the analysis 
subpackage.  It is not required for typical use of the scan framework.*
        
### Installing
Below are instructions on performing a minimal install for getting started with the framework, which are intended
for users just getting started with ARTIQ.  Experienced ARTIQ users can follow the instructions in 
[INSTALLING.md](INSTALLING.md).

To install the framework, first [install git](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git) to your
computer.

Next, clone this repository to a location on your computer.  In Windows, for example, open a command prompt after 
installing git and run

```
    mkdir C:\src
    cd C:\src
    git clone https://github.com/usnistgov/scan_framework
    dir
    rem you should see a folder name scan_framework which contains all source code for the framework
```

This will download all of the required source files for the framework to ```C:\src\scan_framework```.  You can also
simply download the scan framework source directly from http://github.com/usnistgov/scan_framework and extract them 
to a folder of your choosing if you do not wish to install git.  Installing git makes it easier to receive future updates 
and bug fixes and is recommended.

Next, add the directory that contains the folder named ```scan_framework``` to your 
[PYTHONPATH](https://docs.python.org/3/using/cmdline.html#envvar-PYTHONPATH) environment variable.
For the Windows example above, [add an environment variable](https://docs.oracle.com/en/database/oracle/machine-learning/oml4r/1.5.1/oread/creating-and-modifying-environment-variables-on-windows.html#GUID-DD6F9982-60D5-48F6-8270-A27EC53807D0) 
with a variable name of ```PYTHONPATH``` and set it's value field to ```C:\src;```

To check that this was successful, close the current command prompt, open a new command prompt and type
```
    echo %PYTHONPATH%
```

If everything was successful, this will output ```C:\src;```.  Note, you will need to close the current command 
prompt and open a new prompt for the ```PYTHONPATH``` variable to be updated.

Next, install ARTIQ version 3 if it is not already installed on your computer.  Please see 
[Installing ARTIQ](https://m-labs.hk/artiq/manual-release-3/installing.html) for instructions on installing ARTIQ.

Next, start the ARTIQ master and ARTIQ dashboard programs.  

```
    artiq_master --device-db=C:/path/to/your/device_db.py --repository=C:/path/to/your/experiment/files
```

```
    artiq_dashboard
```

Please see the [ARTIQ manual release 3](https://m-labs.hk/artiq/manual-release-3) for more details on running the
 ```artiq_master``` and ```artiq_dashboard``` commands.  

Finally, create the ```current_scan``` applet for the scan framework in the ARTIQ dashboard.  In the ARTIQ dashboard 
navigate to the `Applets` tab, right click and select `New applet`.  Add the following source for the applet:

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

For getting started, only the ```current_scan``` applet above is needed.  Additional features of the scan framework 
require additional applets [listed below](#applets) in the Applets section.  To use those features you will 
also need to create those additional applets to the dashboard. 

### Examples
The best way to start using the scan framework is by looking through a few of the example scans below and running them 
in the ARTIQ dashboard.  A few examples do not require the ARTIQ hardware which allows testing the framework on a
computer not connected to ARTIQ hardware.
 
The first four examples below provide everything that is needed for a large set of use cases.  Examples are ordered from 
basic to advanced and are meant to be followed in more or less chronological order.
  
**Scan examples/tutorials**
- [Ex0: Minimal Scan](examples/scans/ex00_minimal_scan.py)
- [Ex1: Scan Arguments](examples/scans/ex01_scan_arguments.py) -- doesn't require ARTIQ hardware
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
- [Ex11: Fit Validations](examples/scans/ex11_fit_validations.py) -- doesn't require ARTIQ hardware
- [Ex12: Time Scans](examples/scans/ex12_time_scans.py) -- doesn't require ARTIQ hardware
- [Ex13: Formatting Plots](examples/scans/ex13_formatting_plots.py)
---

**Note:**
To run an example, right click the `Explorer` tab in the dashboard and choose `Open file outside repository`.  
Then navigate to the `directory containing scan framework source/scan_framework/examples/scans` folder and open and
the example scan.
---
Additional real world examples are provided in `scan_framework/examples/scans` and `scan_framework/examples/models` 
that illustrate how the scan class is used in a real lab setup.


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

###### Applet for Example 6
```
$python -m scan_framework.applets.plot_xy_ntrace_white
    example_6.m1.stats.mean
    --x1 example_6.m1.stats.points
    --error1 example_6.m1.stats.error
    --fit1 example_6.m1.fits.fitline
    example_6.m2.stats.mean
    --x2 example_6.m2.stats.points
    --error2 example_6.m2.stats.error
    --fit2 example_6.m2.fits.fitline
    example_6.m2.stats.mean
    --x3 example_6.m2.stats.points
    --error3 example_6.m2.stats.error
    --fit3 example_6.m2.fits.fitline
```

## Documentation
Full documentation is available at https://stylus.ipages.nist.gov/scan_framework/

Detailed APIs are also available:
TODO: Update Links
1. [API for scans](https://stylus.ipages.nist.gov/scan_framework/scans/api.html)
2. [API for models](https://stylus.ipages.nist.gov/scan_framework/models_ref.html)
3. [API for applets](https://stylus.ipages.nist.gov/scan_framework/applets/api.html)
4. [API for curve fitting](https://stylus.ipages.nist.gov/scan_framework/analysis/api.html)

### Scan framework settings
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

### Applets
Below are all the applet commands needed to view data generated by the scan framework.  These are also available in 
[applet_commands.txt](applet_commands.txt)

##### Current scan applet
The current scan applet displays the average value returned from the measure() method at each scan point.
Each point displayed is for a single scan point. Scans configured to calculate statistics will automatically
write statistics to the ```current_scan``` namespace.  The current scan applet plots this contained in the
```current_scan``` namespace.  This plot is updated as the scan executes.

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

##### Count monitor applet
The count monitor applet displays the average value returned by the measure() method after each scan point
completes.

```
${artiq_applet}big_number counts
```

##### Current histogram applet
The current histogram applet plots a histogram of all values returned by the measure() during a single scan point.
The histogram gives the distribution in measurement values only for the current scan point.  This plot is updated
as the scan executes.

```
$python -m scan_framework.applets.plot_hist current_hist.bins
    --x current_hist.bin_boundaries
    --x_units current_hist.x_units
    --x_label current_hist.x_label
    --plot_title current_hist.plot_title
```

##### Current histogram applet (aggregate over the entire scan)
The current aggregate histogram applet plots a histogram of all values returned by the measure() during the entire
scan.  The histogram is aggregate over all scan points.  This plot is updated as the scan executes.

```
$python -m scan_framework.applets.plot_hist current_hist.aggregate_bins
    --x current_hist.bin_boundaries
    --x_units current_hist.x_units
    --x_label current_hist.x_label
    --plot_title current_hist.plot_title
```



##### Current sub-scan applet applet (for 2D scans)
The current sub scan applet plots the mean value returned by the measure() method of the sub-scan of a 2D scan.
This plot is updated as the scan executes and is cleared after each sub-scan completes.
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
Same as the current sub-scan applet, except the curve of the best fit is not plotted.  
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

##### Current scan applet for The ARTIQ browser
Same as the current_scan appleta bove, but for the ARTIQ browser.

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
    --trigger 1
```

### Kernel invariants
The following scan attributes are marked as kernel invariants by default:
`self.npasses`, `self.nbins`, `self.nrepeats`, `self.npoints`, `self.nmeasurements`,
`self.do_fit`, `self.save_fit`, `self.fit_only`

The kernel invariants can be changed anywhere within the child scan class by manually setting `self.kernel_invariants` .

### `save=True`, `broadcast=False`, `persist=False` 

The default behavior of the scan model is to save all data to the HDf5 file of the experiment, but to 
not broadcast or persist datasets (i.e. `save=True`, `broadcast=False` and `persist=False` when 
datasets are created).

The exception to this rule is saved fit parameters which are both broadcast and persisted as well as saved to the 
HDf5 file  (i.e. `save=True`, `broadcast=True` and `persist=True` when 
datasets are created).

If you wish to override this behavior, set the `save`, `broadcast`, or `persist` attributes in the build method
of your scan model class

## Contributing
Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct, and the process for 
submitting pull requests to us.

## Authors & Main Contributors
1. Philip D. Kent, NIST and University of Colorado - Scan framework architecture and development.
2. Kyle S. McKay, NIST and University of Colorado - Scan framework design and user specifications. 
3. Daniel H. Slichter, NIST - Analysis subpackage and curve fitting routines.

See also the list of [contributors](AUTHORS.md) who participated in 
this project.
 
## Copyright
Also see the [LICENSE.md](LICENSE.md) and [LICENSES directory](LICENSES)

### curvefits.py in the analysis subpackage
This software was developed by employees of the National Institute of
Standards and Technology (NIST), an agency of the Federal Government and is
being made available as a public service. Pursuant to title 17 United States
Code Section 105, works of NIST employees are not subject to copyright
protection in the United States.  This software may be subject to foreign
copyright.  Permission in the United States and in foreign countries, to the
extent that NIST may hold copyright, to use, copy, modify, create derivative
works, and distribute this software and its documentation without fee is hereby
granted on a non-exclusive basis, provided that this notice and disclaimer of
warranty appears in all copies.

THE SOFTWARE IS PROVIDED 'AS IS' WITHOUT ANY WARRANTY OF ANY KIND, EITHER
EXPRESSED, IMPLIED, OR STATUTORY, INCLUDING, BUT NOT LIMITED TO, ANY WARRANTY
THAT THE SOFTWARE WILL CONFORM TO SPECIFICATIONS, ANY IMPLIED WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND FREEDOM FROM
INFRINGEMENT, AND ANY WARRANTY THAT THE DOCUMENTATION WILL CONFORM TO THE
SOFTWARE, OR ANY WARRANTY THAT THE SOFTWARE WILL BE ERROR FREE.  IN NO EVENT
SHALL NIST BE LIABLE FOR ANY DAMAGES, INCLUDING, BUT NOT LIMITED TO, DIRECT,
INDIRECT, SPECIAL OR CONSEQUENTIAL DAMAGES, ARISING OUT OF, RESULTING FROM,
OR IN ANY WAY CONNECTED WITH THIS SOFTWARE, WHETHER OR NOT BASED UPON
WARRANTY, CONTRACT, TORT, OR OTHERWISE, WHETHER OR NOT INJURY WAS SUSTAINED
BY PERSONS OR PROPERTY OR OTHERWISE, AND WHETHER OR NOT LOSS WAS SUSTAINED
FROM, OR AROSE OUT OF THE RESULTS OF, OR USE OF, THE SOFTWARE OR SERVICES
PROVIDED HEREUNDER.

To see the latest statement, please visit:
[Copyright, Fair Use, and Licensing Statements for SRD, Data, and Software](https://www.nist.gov/director/copyright-fair-use-and-licensing-statements-srd-data-and-software)

### All other source files
All other source files are distributed under the GNU Lesser General Public License v3.0 or later.  
SPDX-License-Identifier: LGPL-3.0-or-later

## Contact
Questions regarding this project can be directed to Philip D. Kent (NIST Assoc.) <philip.kent@nist.gov>.  
