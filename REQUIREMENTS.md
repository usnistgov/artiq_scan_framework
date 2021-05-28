Requirements
============

## Hardware Requirements
1. Experimental control hardware running ARTIQ version 3.7

## Software Requirements
1. Python version 3.5
2. Version 3.7 of the ARTIQ python package (https://m-labs.hk/experiment-control/artiq/)
3. All python packages required by ARTIQ version 3.7.  
*Note: these are installed automatically when installing ARTIQ via the m-labs conda channel*
4. The numpy python package (https://numpy.org/) compatible with Python version 3.5
3. The scipy python package (https://www.scipy.org/) compatible with Python version 3.5
5. (Optional) The matplotlib python package (https://matplotlib.org/) compatible with Python version 3.5  
*Note: The matplotlib package is required only by testing routines in the curvefits.py module of the analysis 
subpackage.  It is not required for typical use of the scan framework.*
    