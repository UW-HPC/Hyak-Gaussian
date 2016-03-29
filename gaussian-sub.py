from __future__ import print_function
import sys, os
import subprocess

'''
  (C) Patrick Lestrange 2016
        
  gaussian-sub.py: a script to build a PBS submission script 
                   to run Gaussian on Hyak
'''

def getInput():
 
  # there should only be one argument (Gaussian input file) 
  if len(sys.argv) != 2: 
    print('There should only be one argument to gaussian-sub.py')
    printHelp()
    sys.exit()

  # check that the file is a .com or .gjf
  filename = sys.argv[1].split('.')
  if len(filename) != 2:
    print('File must have an extension')
    printHelp()
    sys.exit()
  if filename[1] != 'com' and filename[1] != 'gjf':
    print('File extension must be .com or .gjf')
    printHelp()
    sys.exit()

  # check that the user has the right permissions to use Gaussian
  proc = subprocess.Popen('groups', stdout=subprocess.PIPE)
  groups = proc.stdout.read()
  groups = groups.split(' ')
  groups[-1] = groups[-1].strip()
  if 'ligroup-gaussian' not in groups: 
    print('You must be part of the ligroup-gaussian Unix group to use Gaussian')
    printHelp()
    sys.exit()
  if 'ligroup-gdv' in groups:
    gdv = True
  else:
    gdv = False 

  # determine which queue to submit to
  queue = raw_input('\nWhich queue would you like to submit to?\n'
                   +'[batch]-(default) or [bf] : ')
  if queue == '':
    queue = 'batch'
  if queue != 'batch' and queue != 'bf':
    print('Invalid option for a queue. Must be batch or bf')
    printHelp()
    sys.exit()
  print('Using the '+queue+' queue\n')

  # determine which group's nodes to use (stf is default if available)
  allocs= []
  for group in groups:
    if 'hyak-' in group and 'test' not in group: allocs.append(group)
  if len(allocs) > 1:
    print('Whose allocation would you like to use?')
    for allocation in allocs:
      print('['+allocation+']',end='') 
      if 'hyak-stf' in allocation: print('-(default) ',end='')
    print(': ',end='')
    allocation = raw_input('')
    if allocation == '' and 'hyak-stf' in allocs:
      allocation = 'hyak-stf'
    if allocation not in allocs:
      print('You must choose an allocation that you are a part of')
      printHelp()
      sys.exit()
  else:
    allocation = allocs
  print('Submitting to the '+allocation+' allocation\n')

  # determine which version of Gaussian to use (no default)
  g09_versions = ['d01','e01']
  gdv_versions = ['h12p','i01p','i03','i03p','i04p']
  print('Which version of Gaussian would you like to use?')
  for version in g09_versions: print('[g09.'+version+']',end=' ') 
  if (gdv):
    for version in gdv_versions: print('[gdv.'+version+']',end=' ') 
  print(': ',end='')
  version = raw_input('')
  if version == '':
    print('You must choose a version of Gaussian.\nThere is no default')
    printHelp()
    sys.exit()
  version_name = version.split('.')
  if version_name[1] not in g09_versions: 
    if version_name[1] not in gdv_versions and gdv == False:
      print('You have not chosen a valid version of Gaussian')
      printHelp()
      sys.exit()
  print('Using the '+version+' version of Gaussian')  



 

def printHelp():
 
  print('This is a really long line,', \
         'but we can make it across multiple lines.')


if __name__ == '__main__':

  getInput()

