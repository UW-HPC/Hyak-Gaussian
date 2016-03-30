from __future__ import print_function
import subprocess, sys, os

'''
  (C) Patrick Lestrange 2016
        
  gaussian-sub.py: a script to build a PBS submission 
                   script to run Gaussian on Hyak
'''

##########################################################
def getInput():

  global f_input, gdv, queue, allocation, version, n_nodes, n_cores, time, f_output

  #--------------------------------------
  # there should only be one argument (Gaussian input file) 
  if len(sys.argv) != 2: 
    print('There should only be one argument to gaussian-sub.py')
    printHelp()
    sys.exit()
  #--------------------------------------

  #--------------------------------------
  # check that the file is a .com or .gjf
  f_input= sys.argv[1].split('.')
  if len(f_input) != 2:
    print('File must have an extension')
    printHelp()
    sys.exit()
  if f_input[1] != 'com' and f_input[1] != 'gjf':
    print('File extension must be .com or .gjf')
    printHelp()
    sys.exit()
  #--------------------------------------

  #--------------------------------------
  # check that the user has the right permissions to use Gaussian
  proc = subprocess.Popen('groups', stdout=subprocess.PIPE)
  groups = proc.stdout.read()
  groups = groups.split(' ')
  groups[-1] = groups[-1].strip()
  if 'ligroup-gaussian' not in groups: 
    print('You must be part of the ligroup-gaussian Unix group to use Gaussian')
    printHelp()
    sys.exit()
  if 'ligroup-gdv' in groups: gdv = True
  else: gdv = False 
  #--------------------------------------

  #--------------------------------------
  # determine which queue to submit to
  queue = raw_input('\nWhich queue would you like to submit to?\n'
                   +'[batch] - (default) or [bf] : ')
  if queue == '': queue = 'batch'
  if queue != 'batch' and queue != 'bf':
    print('Invalid option for a queue. Must be batch or bf')
    printHelp()
    sys.exit()
  print('Using the '+queue+' queue\n')
  #--------------------------------------

  #--------------------------------------
  # determine which group's nodes to use (stf is default if available)
  allocs= []
  for group in groups:
    if 'hyak-' in group and 'test' not in group: allocs.append(group)
  if len(allocs) > 1:
    print('Whose allocation would you like to use?')
    for allocation in allocs:
      print('['+allocation+']',end=' ') 
      if 'hyak-stf' in allocation: print('- (default) ',end='')
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
  #--------------------------------------

  #--------------------------------------
  # determine which version of Gaussian to use (no default)
  g09_versions = ['d01','e01']
  gdv_versions = ['h12p','i01p','i03','i03p','i04p']
  print('Which version of Gaussian would you like to use?')
  for version in g09_versions: print('[g09.'+version+']',end=' ') 
  if gdv:
    for version in gdv_versions: print('[gdv.'+version+']',end=' ') 
  print('- (default) ',end='')
  print(': ',end='')
  version = raw_input('')
  if version == '':
    if gdv:
      version = 'gdv.'+gdv_versions[-1]
    else:
      version = 'g09.'+g09_versions[-1]
  version_name = version.split('.')
  if version_name[1] not in g09_versions: 
    if version_name[1] not in gdv_versions and gdv == False:
      print('You have not chosen a valid version of Gaussian - '+version_name[1])
      printHelp()
      sys.exit()
  print('Using the '+version+' version of Gaussian\n')  
  #--------------------------------------

  #--------------------------------------
  # ask how many nodes to use
  allocation_name = allocation.split('-')
  command = 'nodestate '+allocation_name[1]+' | grep n0 | wc -l'
  proc = subprocess.Popen(command, stdout=subprocess.PIPE,shell=True)
  max_nodes = int(proc.stdout.read())
  n_nodes = raw_input('How many nodes do you want to use? (default=1) : ')
  if n_nodes == '':
    n_nodes = 1
  else:
    n_nodes = int(n_nodes)
  if n_nodes < 1 or n_nodes >= max_nodes:
    print('You must select at least one node and less than '+str(max_nodes))
    printHelp()
    sys.exit()
  if n_nodes > 1:
    linda = True
  else:
    linda = False
  if linda:
    print('NOTE: You must include "%lindaworker" in your\n'
         +'      input file when using more than one node') 
  #--------------------------------------
 
  #--------------------------------------
  # ask how many cores on each node to use
  print('Checking what types of nodes are available...')
  max_cores = []
  command = 'mdiagn -t '+allocation_name[1]+' | grep ":16 " | wc -l'
  proc = subprocess.Popen(command, stdout=subprocess.PIPE,shell=True)
  max_16_cores= int(proc.stdout.read())
  if max_16_cores != 0: smallest_node = 16 
  command = 'mdiagn -t '+allocation_name[1]+' | grep ":12 " | wc -l'
  proc = subprocess.Popen(command, stdout=subprocess.PIPE,shell=True)
  max_12_cores= int(proc.stdout.read())
  if max_12_cores != 0: smallest_node = 12 
  command = 'mdiagn -t '+allocation_name[1]+' | grep ":8 " | wc -l'
  proc = subprocess.Popen(command, stdout=subprocess.PIPE,shell=True)
  max_8_cores= int(proc.stdout.read())
  if max_8_cores != 0: smallest_node = 8
  n_cores = raw_input('How many cores do you want to use on each node? (default='+str(smallest_node)+') : ')
  if n_cores == '': n_cores = 0
  if int(n_cores) < smallest_node:
    print('Setting number of cores to be smallest option in this allocation')
    n_cores = smallest_node
  if n_cores == 8 and n_nodes > max_8_cores:
    too_much = True
    n_nodes = max_8_cores
  elif n_cores == 12 and n_nodes > max_12_cores:
    too_much = True
    n_nodes = max_12_cores
  elif n_cores == 16 and n_nodes > max_16_cores:
    too_much = True
    n_nodes = max_16_cores
  else:
    too_much = False
  if too_much:
    print('You requested too many nodes with '+n_cores+' cores'
         +'Resetting to maximum number of nodes with that many cores')
  print('Using '+str(n_nodes)+' node(s) with '+str(n_cores)+' cores\n')
  #--------------------------------------

  #--------------------------------------
  time = raw_input('For how many hours do you want to run your calculation? (default=1) : ')
  if time == '':
    time = int(1)
  else:
    time = int(time)
  print('Running the calculation for '+str(time)+' hr(s)\n')
  #--------------------------------------

  #--------------------------------------
  f_output = raw_input('What should we call the .pbs script? (default='+f_input[0]+'.pbs) : ')
  if f_output == '': 
    f_output = f_input[0]+'.pbs'
  else:
    f_output = f_output+'.pbs'
  #--------------------------------------

##########################################################

##########################################################
def printHelp():
 
  print('\nNAME\n'
       +'\tGaussian-Submit\n\n'
       +'DESCRIPTION\n'
       +'\tThis program will aid in the submission of Gaussian\n'
       +'\tcalculations to the Hyak cluster.\n')

##########################################################

##########################################################
def writePBS():

  print('Writing to '+f_output+'\n')
  proc = subprocess.Popen('pwd', stdout=subprocess.PIPE,shell=True)
  pwd= proc.stdout.read()
  pwd = pwd.strip()
  f = open(f_output,'w')

  f.write('#!/bin/bash\n')
  f.write('#PBS -N '+f_input[0]+'\n')
  f.write('#PBS -l nodes='+str(n_nodes)+':ppn='+str(n_cores)+',feature='+str(n_cores)+'core\n') 
  f.write('#PBS -l walltime='+str(time)+':00:00\n')
  f.write('#PBS -j oe\n')
  f.write('#PBS -o '+pwd+'\n')
  f.write('#PBS -d '+pwd+'\n')
  f.write('#PBS -W group_list='+allocation+'\n')
  f.write('#PBS -q '+queue+'\n\n')

  f.write('# load Gaussian environment\n')
  f.write('module load contrib/'+version+'\n\n')

  f.write('# debugging information\n')
  f.write('HYAK_NPE=$(wc -l < $PBS_NODEFILE)\n') 
  f.write('HYAK_NNODES=$(uniq $PBS_NODEFILE | wc -l )\n')
  f.write('echo "**** Job Debugging Information ****"\n') 
  f.write('echo "This job will run on $HYAK_NPE total CPUs on $HYAK_NNODES different nodes"\n') 
  f.write('echo ""\n') 
  f.write('echo Node:CPUs Used\n')
  f.write('uniq -c $PBS_NODEFILE | awk \'{print $2 ":" $1}\'\n') 
  f.write('echo "SHARED LIBRARY CHECK"\n') 
  f.write('ldd ./test\n') 
  f.write('echo "ENVIRONMENT VARIABLES"\n') 
  f.write('set\n') 
  f.write('echo "**********************************************"\n\n') 

  f.write('# run Gaussian\n')
  if 'gdv' in version: 
    f.write('gdv '+str(f_input[0])+'.'+str(f_input[1])+'\n\n')
  else:
    f.write('g09 '+str(f_input[0])+'.'+str(f_input[1])+'\n\n')
  
  f.write('exit 0')
  print('Please run \'qsub '+f_output+'\' to submit to the scheduler\n')

##########################################################

##########################################################
if __name__ == '__main__':

  getInput()
  writePBS()

