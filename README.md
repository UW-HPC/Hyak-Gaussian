Gaussian-Submitter
==============

Builds a PBS or an SBATCH script to run Gaussian on 
the Hyak Ikt and Mox clusters

About
-----

This program will aid in the submission of Gaussian
calculations to the Ikt and Mox clusters. The script will 
ask questions about the calculation to help set up the .pbs
or .sh scripts. It will check for the types of nodes available
to set appropriate defaults and it will read your input
file to check for potential issues if using the STF
allocation.


Usage
-----
`gaussian-sub.py input.com`

`gaussian-sub.py input.gjf`
