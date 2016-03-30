Gaussian-Submitter
==============

Builds a PBS script to run Gaussian on the Hyak cluster

About
-----

This program will aid in the submission of Gaussian
calculations to the Hyak cluster. The script will ask
questions about the calculation to help set up the .pbs
script. It will check for the types of nodes available
to set appropriate defaults and it will read your input
file to check for potential issues if using the STF
allocation.


Usage
-----
`python gaussian-sub.py input.com`

`python gaussian-sub.py input.gjf`
