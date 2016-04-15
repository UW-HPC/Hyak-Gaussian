#!/usr/bin/python
from __future__ import print_function
import subprocess, sys, os

'''
  (C) Patrick Lestrange 2016
        
  gaussian-sub.py: a script to build a PBS submission 
                   script to run Gaussian on Hyak
'''

##########################################################
def checkInput():
  # read the Gaussian input file and check for problems

  gauss_input = str(f_input[0])+'.'+str(f_input[1])
  f = open(gauss_input,'r')
  contents = f.readlines()
  found_linda = False
  memory = 0
  nproc  = 0

  for line in contents:
    if 'lindaworker' in line.lower(): found_linda = True 
    if 'mem' in line.lower():
      mem_line = line.split('=')
      mem_line[-1] = mem_line[-1].strip()
      if 'gb' in mem_line[1].lower(): 
        gb = True
        mem = mem_line[1].lower().split('gb')
        memory = int(mem[0])
      else:
        gb = False
        print('\nThis script only checks the memory if it\'s specified\n'
             +'in Gb. Your calculation may still be fine, but this\n'
             +'script won\'t check. This is just a warning.\n')
    if 'nproc' in line.lower():
      nproc_line = line.split('=')
      nproc_line[-1] = nproc_line[-1].strip()
      nproc = int(nproc_line[1])

  if memory > 32 and gb and allocation == 'hyak-stf':
    print('\nGenerally you don\'t want to specify more than half\n'
         +'the memory on a node. You\'ve asked for '+str(memory)+'Gb and\n'
         +'the STF nodes only have 64Gb (except for n0868/n0870)\n'
         +'This is just a warning.\n')

  if nproc > 16 and allocation == 'hyak-stf':
    print('\nYou should not specify to use more cores than the\n'
         +'number available on your node. The STF nodes have 16 cores\n'
         +'and you\'ve asked for '+str(nproc)+' cores. Please lower\n'
         +'the number of cores you\'ve requested in your input file.\n')
    sys.exit()
 
  if nproc < 16 and allocation == 'hyak-stf':
    print('You usually want to use all the cores on a node. The\n'
         +'STF nodes have 16 cores and you\'ve only asked for '+str(nproc)+' cores.\n'
         +'There are some situations where you may want to use fewer\n'
         +'than the maximum number of cores, however, such as in the\n'
         +'case where you want to limit the memory requirements for\n'
         +'the calculation. This is just a warning.\n')

  if linda and not found_linda:
    print('\nYour input file does not contain %lindaworker, but\n'
         +'you have asked to use more than one node. Please add\n'
         +'this line or request only one node.\n')
    sys.exit()
  
  if found_linda and n_nodes == 1:
    print('\nYour input file contains %lindaworker, but you have\n'
         +'only asked to use one node. Please remove this line or\n'
         +'request more than one node.\n')
    sys.exit()

##########################################################

##########################################################
def getInput():
  # grab input from the user about what type of job to run

  global f_input, gdv, queue, allocation, version, n_nodes, linda, n_cores, time, f_output

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
  allocation = ''
  if queue == 'batch':
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
      if allocation == '' and 'hyak-stf' in allocs: allocation = 'hyak-stf'
      if allocation not in allocs:
        print('You must choose an allocation that you are a part of')
        printHelp()
        sys.exit()
    else:
      allocation = str(allocs[0])
    print('Submitting to the '+allocation+' allocation\n')
  #--------------------------------------

  #--------------------------------------
  # ask how many nodes to use
  if queue == 'batch':
    if allocation != 'hyak-stf':
      print('Checking how many nodes are in this allocation...')
      allocation_name = allocation.split('-')
      command = 'nodestate '+allocation_name[1]+' | grep n0 | wc -l'
      proc = subprocess.Popen(command, stdout=subprocess.PIPE,shell=True)
      max_nodes = int(proc.stdout.read())
    else:
      max_nodes = 54
  else:
    max_nodes = 1000
  n_nodes = raw_input('How many nodes do you want to use? (default=1) : ')
  if n_nodes == '': n_nodes = 1
  else: n_nodes = int(n_nodes)
  if n_nodes < 1 or n_nodes >= max_nodes:
    print('You must select at least one node and less than '+str(max_nodes))
    printHelp()
    sys.exit()
  if n_nodes > 1: linda = True
  else: linda = False
  if linda:
    print('NOTE: You must include "%lindaworker" in your\n'
         +'      input file when using more than one node') 
  #--------------------------------------
 
  #--------------------------------------
  # ask how many cores on each node to use
  if queue == 'batch':
    if allocation != 'hyak-stf':
      print('Checking what types of nodes are in this allocation...')
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
    else:
      smallest_node = 16
      max_8_cores   = 0
      max_12_cores  = 0
      max_16_cores  = 54
  else:
    smallest_node = 8
    max_8_cores   = 171
    max_12_cores  = 257
    max_16_cores  = 430
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
    if gdv: version = 'gdv.'+gdv_versions[-1]
    else: version = 'g09.'+g09_versions[-1]
  version_name = version.split('.')
  if version_name[1] not in g09_versions: 
    if version_name[1] not in gdv_versions and gdv == False:
      print('You have not chosen a valid version of Gaussian - '+version_name[1])
      printHelp()
      sys.exit()
  print('Using the '+version+' version of Gaussian\n')  
  #--------------------------------------

  #--------------------------------------
  # check what the max walltime should be
  default = 1
  if queue == 'bf': default = 5
  time = raw_input('For how many hours do you want to run your calculation? (default='+str(default)+') : ')
  if time == '': time = default
  else: time = int(time)
  if queue == 'bf' and time != 5:
    print('You generally want to specify 5 hrs when using the bf queue\n'
         +'This is just a warning.')
  print('Running the calculation for '+str(time)+' hr(s)\n')
  #--------------------------------------

  #--------------------------------------
  # get a name for the .pbs script
  f_output = raw_input('What should we call the .pbs script? (default='+f_input[0]+'.pbs) : ')
  if f_output == '': f_output = f_input[0]+'.pbs'
  else: f_output = f_output+'.pbs'
  #--------------------------------------

##########################################################

##########################################################
def printHelp():
  # print some helpful information for the user
 
  print('\nNAME\n'
       +'\tGaussian-Submit\n\n'
       +'DESCRIPTION\n'
       +'\tThis program will aid in the submission of Gaussian\n'
       +'\tcalculations to the Hyak cluster. The script will ask\n'
       +'\tquestions about the calculation to help set up the .pbs\n'
       +'\tscript. It will check for the types of nodes available\n' 
       +'\tto set appropriate defaults and it will read your input\n' 
       +'\tfile to check for potential issues if using the STF\n'
       +'\tallocation.\n\n'
       +'EXAMPLES\n'
       +'\tgaussian-sub.py input{.gjf,.com}\n\n'
       +'AUTHOR\n'
       +'\tPatrick J Lestrange <patricklestrange@gmail.com>\n') 

##########################################################

##########################################################
def writePBS():
  # make a .pbs script based on the user specifications

  gauss_input = str(f_input[0])+'.'+str(f_input[1])
  print('Writing to '+f_output+'\n')
  proc = subprocess.Popen('pwd', stdout=subprocess.PIPE,shell=True)
  pwd = proc.stdout.read()
  pwd = pwd.strip()
  f = open(f_output,'w')

  f.write('#!/bin/bash\n')
  f.write('#PBS -N '+f_input[0]+'\n')
  f.write('#PBS -l nodes='+str(n_nodes)+':ppn='+str(n_cores)+',feature='+str(n_cores)+'core\n') 
  f.write('#PBS -l walltime='+str(time)+':00:00\n')
  f.write('#PBS -j oe\n')
  f.write('#PBS -o '+pwd+'\n')
  f.write('#PBS -d '+pwd+'\n')
  if queue == 'batch': f.write('#PBS -W group_list='+allocation+'\n')
  f.write('#PBS -q '+queue+'\n')

  f.write('\n# load Gaussian environment\n')
  f.write('module load contrib/'+version+'\n')

  f.write('\n# debugging information\n')
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
  f.write('echo "**********************************************"\n') 

  if linda:
    f.write('\n# add linda nodes\n')
    f.write('HYAK_NNODES=$(uniq $PBS_NODEFILE | wc -l )\n')
    f.write('nodes=()\n')
    f.write('nodes+=(`uniq -c $PBS_NODEFILE | awk \'{print $2}\'`)\n')
    f.write('for ((i=0; i<${#nodes[*]}-1; i++));\n')
    f.write('do\n')
    f.write('\tstring+=${nodes[$i]}\n')
    f.write('\tstring+=","\n')
    f.write('done\n')
    f.write('string+=${nodes[$HYAK_NNODES-1]}\n')
    f.write('sed -i -e "s/%LindaWorker.*/%LindaWorker=$string/Ig" '+gauss_input+'\n')

    f.write('\n# check that the Linda nodes are correct\n')
    f.write('lindaline=(`grep -i \'lindaworker\' '+gauss_input+'`)\n')
    f.write('if [[ $lindaline == *$string ]]\n')
    f.write('then\n')
    f.write('\techo "Using the correct nodes for Linda"\n')
    f.write('else\n')
    f.write('\techo "Using the wrong nodes for Linda"\n')
    f.write('\techo "Nodes assigned by scheduler = $string"\n')
    f.write('\techo "Line in Gaussian input file = $lindaline"\n')
    f.write('\texit 1\n')
    f.write('fi\n')

  if queue == 'bf':
    f.write('\n# copy last log file to another name\n') 
    f.write('num=`ls -l '+f_input[0]+'*.log | wc -l`\n')
    f.write('let "num += 1"\n')
    f.write('cp '+f_input[0]+'.log '+f_input[0]+'$num.log\n')

  f.write('\n# run Gaussian\n')
  if 'gdv' in version: 
    f.write('gdv '+gauss_input+'\n')
  else:
    f.write('g09 '+gauss_input+'\n')
  
  f.write('\nexit 0')
  print('Please run \'qsub '+f_output+'\' to submit to the scheduler\n')

##########################################################

##########################################################
if __name__ == '__main__':

  getInput()
  checkInput()
  writePBS()

