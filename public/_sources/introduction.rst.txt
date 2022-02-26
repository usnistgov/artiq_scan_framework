Introduction
============

The NIST scan framework is a framework that greatly simplifies the process of writing and maintaining
scans of experimental parameters using the ARTIQ control system and language.  Multiple types of scan
experiments can be created in ARTIQ by inheriting from a set of predefined classes.  By inheriting
from these classes useful features such as automatic calculation of statistics, automatic fitting of
statistics to fit functions, validation of extracted fit parameters, and plotting are performed
automatically and do not need to be performed by the user.  This reduces the size and complexity of
scan experiments to make them fast to implement, easy to read, and easy to maintain.

