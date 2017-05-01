#!/usr/bin/python

from __future__ import print_function
import sys
import os
import re
import textwrap
import subprocess 
from subprocess import Popen, PIPE

'''
  Patrick J. Lestrange 2017
        
  gaussian-sub.py: Builds a PBS submission script to run
                   Gaussian on the Hyak Ikt/Mox clusters.

                   Also used as a teaching aid in UW's
                   CHEM 465/565 Computations in Chemistry.
'''

#----------------------------------------------------------------------------
def get_user_input():
    """Grab input from the user about what type of job to run."""

    global f_input, gdv, queue, allocation, version, n_nodes
    global linda, n_cores, time, f_output, gen, memory
    gdv = False

    #--------------------------------------
    # Determine which generation machine we're on
    gen  = 'ikt'
    host = Popen('hostname',stdout=PIPE).stdout.read()
    if 'mox' in host: gen = 'mox'
    #--------------------------------------

    #--------------------------------------
    # There should only be one argument: the Gaussian input file.
    if len(sys.argv) != 2: 
        print(textwrap.fill(textwrap.dedent("""\
            ERROR: There should only be one argument to 
            gaussian-sub.py""")))
        sys.exit()
    if sys.argv[1] == '-h' or 'help' in sys.argv[1]:
        print_help()
        sys.exit()  
    #--------------------------------------

    #--------------------------------------
    # Check that the argument is a .com or .gjf and that it exists.
    f_input= sys.argv[1].split('.')
    if not os.path.isfile(sys.argv[1]):
        print('ERROR: The input file '+sys.argv[1]+' does not exist')
        sys.exit()
    if len(f_input) != 2:
        print('ERROR: The filename must include the extension')
        sys.exit()
    if f_input[1] != 'com' and f_input[1] != 'gjf':
        print('ERROR: The file extension must be .com or .gjf')
        sys.exit()
    #--------------------------------------

    #--------------------------------------
    # Check that the user has the right permissions to use Gaussian.
    username = Popen('whoami',stdout=PIPE).stdout.read().strip()
    command = 'groups '+username
    groups = Popen(command,stdout=PIPE,shell=True).stdout.read().split(' ')
    groups[-1] = groups[-1].strip()
    if 'ligroup-gaussian' not in groups: 
        print(textwrap.fill(textwrap.dedent("""\
            ERROR: You must be part of the ligroup-gaussian Unix group 
            to use Gaussian. Contact Prof. Xiaosong Li (xsli@uw.edu) to 
            be added to the group."""), 60))
        sys.exit()
    if 'ligroup-gdv' in groups: gdv = True
    #--------------------------------------

    #--------------------------------------
    # Determine which queue to submit to.
    queue = raw_input(textwrap.fill(textwrap.dedent("""\
            Which queue would you like to submit to?
            [batch] - (default) or [bf|ckpt] : """),100))
    if queue == '': queue = 'batch'
    if queue == 'bf' and gen == 'mox': queue = 'ckpt'
    if queue == 'ckpt' and gen == 'ikt': queue = 'bf'
    if queue != 'batch' and queue != 'bf' and queue != 'ckpt':
        print('ERROR: Invalid option for a queue. Must be batch, bf, or ckpt')
        sys.exit()
    print('Using the '+queue+' queue\n')
    #--------------------------------------

    #--------------------------------------
    # Determine which group's nodes to use. STF is the default if available.
    allocation = ''
    if queue == 'batch' or queue == 'ckpt':
        allocs= []
        for group in groups:
            if 'hyak-' in group and 'test' not in group: allocs.append(group)
        if len(allocs) > 1:
            print('Whose allocation would you like to use?')
            for allocation in allocs:
                print('['+allocation+']',end=' ') 
                if 'hyak-stf' in allocation: print('- (default) ',end='')
            if 'hyak-stf' not in allocs: print('- (default) ',end='')
            print(': ',end='')
            allocation = raw_input('')
            if allocation == '' and 'hyak-stf' in allocs: 
                allocation = 'hyak-stf'
            elif allocation == '' and 'hyak-stf' not in allocs: 
                allocation = allocs[-1]
            if allocation not in allocs:
                print(textwrap.fill(textwrap.dedent("""\
                    ERROR: You must choose an allocation that you 
                    are a part of"""),100))
                sys.exit()
        else:
            allocation = str(allocs[0])
        print('Submitting to the '+allocation+' allocation\n')
    #--------------------------------------

    #--------------------------------------
    # Ask how many nodes to use.
    if queue == 'batch':
        if allocation != 'hyak-stf':
            print('Checking how many nodes are in this allocation...')
            allocation_name = allocation.split('-')
            if gen == 'ikt':
                command = 'nodestate '+allocation_name[1]+' | grep n0 | wc -l'
                max_nodes = Popen(command,stdout=PIPE,shell=True)
                max_nodes = int(max_nodes.stdout.read())
            elif gen == 'mox':
                command = 'hyakalloc | grep '+allocation_name[1]
                specs = Popen(command,stdout=PIPE,shell=True).stdout.read().split()
                max_nodes = int(specs[1])
                smallest_mem = int(specs[2][:-1])
        else: # STF allocation
            if   gen == 'ikt': max_nodes = 54
            elif gen == 'mox': max_nodes = 40
    else:
        max_nodes = 1000
    n_nodes = raw_input('How many nodes do you want to use? (default=1) : ')
    if n_nodes == '': n_nodes = 1
    else: n_nodes = int(n_nodes)
    if max_nodes == 0:
        print(textwrap.fill(textwrap.dedent("""\
            ERROR: There are no nodes available for this allocation"""),100))
        sys.exit()
    elif n_nodes < 1 or n_nodes >= max_nodes:
        print(textwrap.fill(textwrap.dedent("""\
            ERROR: You must select at least one node and
            less than %d""" % max_nodes),100))
        sys.exit()
    if n_nodes > 1: linda = True
    else: linda = False
    if linda:
        print('NOTE: You must include "%lindaworker" in your\n'
             +'      input file when using more than one node') 
    #--------------------------------------
 
    #--------------------------------------
    # Ask how many cores/memory on each node to use.
    if queue == 'batch':
        if allocation != 'hyak-stf':
            print('Checking what types of nodes are in this allocation...')
            if gen == 'ikt':
                command = 'mdiagn -t '+allocation_name[1]+' | grep ":28 " | wc -l'
                max_28_cores = Popen(command,stdout=PIPE,shell=True)
                max_28_cores = int(max_28_cores.stdout.read())
                if max_28_cores != 0: smallest_node = 28 
                command = 'mdiagn -t '+allocation_name[1]+' | grep ":16 " | wc -l'
                max_16_cores = Popen(command,stdout=PIPE,shell=True)
                max_16_cores = int(max_16_cores.stdout.read())
                if max_16_cores != 0: smallest_node = 16 
                command = 'mdiagn -t '+allocation_name[1]+' | grep ":12 " | wc -l'
                max_12_cores = Popen(command,stdout=PIPE,shell=True)
                max_12_cores = int(max_12_cores.stdout.read())
                if max_12_cores != 0: smallest_node = 12 
                command = 'mdiagn -t '+allocation_name[1]+' | grep ":8 " | wc -l'
                max_8_cores = Popen(command,stdout=PIPE,shell=True)
                max_8_cores = int(max_8_cores.stdout.read())
                if max_8_cores != 0: smallest_node = 8
            elif gen == 'mox':
                command = 'hyakalloc '+allocation_name[1]
                specs = Popen(command,stdout=PIPE,shell=True).stdout.read().split()
                smallest_node = 28
                max_8_cores   = 0
                max_12_cores  = 0
                max_16_cores  = 0
                max_28_cores  = int(specs[11])
        else:
            if gen == 'ikt':
                smallest_node = 16
                max_8_cores   = 0
                max_12_cores  = 0
                max_16_cores  = 54
            elif gen == 'mox':
                smallest_node = 28
                max_8_cores   = 0
                max_12_cores  = 0
                max_16_cores  = 0
                max_28_cores  = 40
    else:
        if gen == 'ikt':
            smallest_node = 8
            max_8_cores   = 171
            max_12_cores  = 257
            max_16_cores  = 430
            max_28_cores  = 0
        elif gen == 'mox':
            smallest_node = 28
            max_8_cores   = 0
            max_12_cores  = 0
            max_16_cores  = 0
            max_28_cores  = 208
    n_cores = raw_input(textwrap.fill(textwrap.dedent("""\
              How many cores do you want to use
              on each node? (default=%d) : """ % smallest_node).strip()))
    if n_cores == '': n_cores = 0
    if int(n_cores) < smallest_node:
        print(textwrap.fill(textwrap.dedent("""\
            Setting number of cores to be the smallest
            option in this allocation"""),100))
        n_cores = smallest_node
    too_much = True
    if n_cores == 8 and n_nodes > max_8_cores:
        n_nodes = max_8_cores
    elif n_cores == 12 and n_nodes > max_12_cores:
        n_nodes = max_12_cores
    elif n_cores == 16 and n_nodes > max_16_cores:
        n_nodes = max_16_cores
    else:
        too_much = False
    if too_much:
        print('You requested too many nodes with '+n_cores+' cores'
             +'Resetting to maximum number of nodes with that many cores')

    if gen == 'ikt':
        print('Using %d node(s) with %d cores\n' % 
            (n_nodes, n_cores))
    elif gen == 'mox':
        smallest_mem = 128
        memory = raw_input(textwrap.fill(textwrap.dedent("""\
                  How much memory do you want to use
                  on each node? (default=%dGb) : """ % smallest_mem).strip()))
        if memory == '': memory = smallest_mem
        else: memory = int(memory)
        print('Using %d node(s) with %d cores and %d Gb\n' % 
            (n_nodes, n_cores, memory))
    #--------------------------------------

    #--------------------------------------
    # Determine which version of Gaussian to use.
    if gen == 'ikt':
        g09_versions = ['d01','e01']
        g16_versions = ['a03']
        gdv_versions = ['i03','i03p','i04p','i06','i06p','i09']
    elif gen == 'mox':
        g09_versions = []
        g16_versions = ['a03']
        gdv_versions = ['i03p','i04p','i06p','i10pp']
    print('Which version of Gaussian would you like to use?')
    for version in g09_versions: print('[g09.'+version+']',end=' ') 
    for version in g16_versions: print('[g16.'+version+']',end=' ') 
    if gdv:
        for version in gdv_versions: print('[gdv.'+version+']',end=' ') 
    print('- (default) : ',end='')
    version = raw_input('')
    if version == '':
        if gdv: version = 'gdv.'+gdv_versions[-1]
        else: version = 'g16.'+g16_versions[-1]
    version_name = version.split('.')
    if len(version_name) != 2:
        print("Can't recognize the specificed version")
        sys.exit()
    bad_version = False
    if version_name[0] == 'g09':
        if version_name[1] not in g09_versions:
            bad_version = True
    elif version_name[0] == 'g16':
        if version_name[1] not in g16_versions:
            bad_version = True
    elif version_name[0] == 'gdv':
        if version_name[1] not in gdv_versions:
						bad_version = True
    else:
        bad_version = True
    if bad_version:
        print('Choose a valid version of Gaussian. Not %s.%s' % (version_name[0], version_name[1]))
        sys.exit()
    print('Using the '+version+' version of Gaussian\n')  
    #--------------------------------------

    #--------------------------------------
    # Check what the max walltime should be.
    if queue != 'bf' and queue != 'ckpt':
        default = 1
        unit    = 'hr'
        time = raw_input(textwrap.fill(textwrap.dedent("""\
               For how many hours do you want to run your
               calculation? (default=%d hr) : """ % default).strip(),100))
    else:
        default = 260
        unit    = 'min'
        time = raw_input(textwrap.fill(textwrap.dedent("""\
               For how many minutes do you want to run your
               calculation? (default=%d min) : """ % default).strip(),100))
    if time == '': time = default
    else: time = int(time)
    if queue == 'bf' and time != 260:
        print(textwrap.fill(textwrap.dedent("""\
            You want to specify 260 min when using the bf queue
            if you expect your job to run longer than 4 hrs. 
            This is just a warning."""),100))
    print('Running the calculation for %d %s(s)\n' % (time, unit))
    #--------------------------------------

    #--------------------------------------
    # Get a name for the .pbs script.
    extension = 'pbs'
    if gen == 'mox': extension = 'sh'
    f_output = raw_input(textwrap.fill(textwrap.dedent("""\
               What should the .%s script be named? 
               (default=%s.%s) : """ % ( extension, f_input[0].strip(), 
                                         extension) )))
    if f_output == '': f_output = f_input[0]+'.'+extension
    else: f_output = f_output+'.'+extension
    #--------------------------------------

#----------------------------------------------------------------------------

#----------------------------------------------------------------------------
def check_Gaussian_input():
    """Read the Gaussian input file and check for problems."""

    gauss_input = str(f_input[0])+'.'+str(f_input[1])
    f = open(gauss_input,'r')
    contents = f.readlines()
    found_linda = False
    memory = 0
    nproc  = 0
    warnings = []
    exit = False

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
                warning = textwrap.dedent("""\
                    This script only checks the memory specfication if it 
                    is in Gb. Your calculation may still be fine, but 
                    this script won't check. This is just a warning.""")
                warnings.append(warning)
        if 'nproc' in line.lower():
            nproc_line = line.split('=')
            nproc_line[-1] = nproc_line[-1].strip()
            nproc = int(nproc_line[1])

    if gb and allocation == 'hyak-stf':
        if gen == 'ikt' and memory > 32:
            warning = textwrap.dedent("""\
                Generally you don't want to specify more than half the
                memory on a node. You've asked for %dGb and most STF
                nodes only have 64Gb.
                This is just a warning.""" % memory)
            warnings.append(warning)
        elif gen == 'mox' and memory > 64:
            warning = textwrap.dedent("""\
                Generally you don't want to specify more than half the
                memory on a node. You've asked for %dGb and most STF
                nodes only have 128Gb.
                This is just a warning.""" % memory)
            warnings.append(warning)

    if allocation == 'hyak-stf':
        if gen == 'ikt' and nproc > 16:
            warning = textwrap.dedent("""\
                You should not specify to use more cores than the number
                available on your node. The STF nodes have 16 cores
                and you've asked for %d cores. Please lower the number 
                of cores you've requested in your input file.
                Not forming PBS script.""" % nproc)
            warnings.append(warning)
            exit = True
        elif gen == 'mox' and nproc > 28:
            warning = textwrap.dedent("""\
                You should not specify to use more cores than the number
                available on your node. The STF nodes have 28 cores
                and you've asked for %d cores. Please lower the number 
                of cores you've requested in your input file.
                Not forming SBATCH script.""" % nproc)
            warnings.append(warning)
            exit = True
 
    if allocation == 'hyak-stf':
        if gen == 'ikt' and nproc < 16:
            warning = textwrap.dedent("""\
                You usually want to use all the cores on a node. The
                STF nodes have 16 cores and you've asked for %d cores.
                This is just a warning.""" % nproc)
            warnings.append(warning)
        elif gen == 'mox' and nproc < 28:
            warning = textwrap.dedent("""\
                You usually want to use all the cores on a node. The
                STF nodes have 28 cores and you've asked for %d cores.
                This is just a warning.""" % nproc)
            warnings.append(warning)

    if linda and not found_linda:
        warning = textwrap.dedent("""\
            Your input file does not contain %lindaworker, but
            you have asked to use more than one node. Please add this
            line or request only one node. Not forming PBS script.""")
        warnings.append(warning)
        exit = True
    
    if found_linda and n_nodes == 1:
        warning = textwrap.dedent("""\
            Your input file contains %lindaworker, but you have
            only asked to use one node. Please remove this line or
            request more than one node. Not forming PBS script.""")
        warnings.append(warning)
        exit = True

    # Print warnings and exit if there are too many errors.
    if len(warnings) > 0:
      print('\n'+'#'*40+'\n'
           +' '*15+'WARNINGS\n'
           +'#'*40)
    for warning in warnings:
        print('\n'+textwrap.fill(warning, 60))
    if exit:
      print("\nExiting without writing PBS file.\n")
      sys.exit()
#----------------------------------------------------------------------------

#----------------------------------------------------------------------------
def write_Ikt_script():
    """Make a .pbs script based on user specifications."""

    gauss_input = str(f_input[0])+'.'+str(f_input[1])
    print('Writing to '+f_output+'\n')
    pwd = Popen('pwd',stdout=PIPE,shell=True).stdout.read().strip()
    f = open(f_output,'w')

    f.write(textwrap.dedent("""\
        #!/bin/bash
        #PBS -N %s
        #PBS -l nodes=%d:ppn=%d,feature=%dcore""" 
        % (f_input[0], n_nodes, n_cores, n_cores))) 
    if queue != 'bf':
      f.write('\n#PBS -l walltime=%d:00:00\n' % time)
    else:
      f.write('\n#PBS -l walltime=0:%d:00\n' % time)
    f.write(textwrap.dedent("""\
        #PBS -j oe
        #PBS -o %s
        #PBS -d %s""" % (pwd, pwd)))
    if queue == 'batch': 
        f.write('\n#PBS -W group_list=%s\n' % allocation)
    f.write(textwrap.dedent("""\
        #PBS -q %s

        # load Gaussian environment
        module load contrib/%s

        # debugging information
        HYAK_NPE=$(wc -l < $PBS_NODEFILE) 
        HYAK_NNODES=$(uniq $PBS_NODEFILE | wc -l ) 
        echo "**** Job Debugging Information ****"
        echo "This job will run on $HYAK_NPE CPUs on $HYAK_NNODES nodes"
        echo ""
        echo Node:CPUs Used 
        uniq -c $PBS_NODEFILE | awk '{print $2 ":" $1}' 
        echo "SHARED LIBRARY CHECK"
        ldd ./test
        echo "ENVIRONMENT VARIABLES"
        set
        echo "**********************************************" """ 
        % (queue, version)))

    if linda:
        f.write(textwrap.dedent("""\
            \n
            # add linda nodes
            HYAK_NNODES=$(uniq $PBS_NODEFILE | wc -l )
            nodes=()
            nodes+=(`uniq -c $PBS_NODEFILE | awk '{print $2}'`)
            for ((i=0; i<${#nodes[*]}-1; i++));
            do
            \tstring+=${nodes[$i]}
            \tstring+=","
            done 
            string+=${nodes[$HYAK_NNODES-1]}
            sed -i -e "s/%%LindaWorker.*/%%LindaWorker=$string/Ig" %s

            # check that the Linda nodes are correct
            lindaline=(`grep -i 'lindaworker' %s`)
            if [[ $lindaline == *$string ]]
            then
            \techo "Using the correct nodes for Linda"
            else
            \techo "Using the wrong nodes for Linda"
            \techo "Nodes assigned by scheduler = $string"
            \techo "Line in Gaussian input file = $lindaline"
            \texit 1
            fi """ % (gauss_input, gauss_input)))

    if queue == 'bf':
        f.write(textwrap.dedent("""\
          \n
          # copy last log file to another name
          num=`ls -l %s*.log | wc -l`
          let "num += 1"
          cp %s.log %s$num.log""" % (f_input[0], f_input[0], f_input[0])))

    if 'gdv' in version: 
        command = 'gdv'
    elif 'g16' in version:
        command = 'g16'
    else:
        command = 'g09'
    f.write(textwrap.dedent("""\
        \n
        # run Gaussian
        %s %s 

        exit 0 """ % (command, gauss_input)))

    print("""Please run 'qsub %s' to submit to the scheduler\n""" % f_output)
#----------------------------------------------------------------------------

#----------------------------------------------------------------------------
def write_Mox_script():
    """Make a .sh script based on user specifications."""

    gauss_input = str(f_input[0])+'.'+str(f_input[1])
    print('Writing to '+f_output+'\n')
    pwd = Popen('pwd',stdout=PIPE,shell=True).stdout.read().strip()
    f = open(f_output,'w')
    short_name = re.split('-',allocation)[1]
    partition, account = short_name, short_name
    if queue == 'bf' or queue == 'ckpt':
        partition = queue
        account = short_name+'-ckpt'

    f.write(textwrap.dedent("""\
        #!/bin/bash
        #SBATCH --job-name=%s
        #SBATCH --nodes=%d 
        #SBATCH --time=%d:00:00
        #SBATCH --mem=%dG
        #SBATCH --workdir=%s
        #SBATCH --partition=%s
        #SBATCH --account=%s\n\n""" 
        % (f_input[0], n_nodes, time, memory, pwd, partition, account))) 
    f.write(textwrap.dedent("""\
        # load Gaussian environment
        module load contrib/%s

        # debugging information
        echo "**** Job Debugging Information ****"
        echo "This job will run on $SLURM_JOB_NODELIST"
        echo ""
        echo "ENVIRONMENT VARIABLES"
        set
        echo "**********************************************" """ 
        % version))

    if linda:
        f.write(textwrap.dedent("""\
            \n
            # add linda nodes
            nodes=()
            nodes+=(`scontrol show hostnames $SLURM_JOB_NODELIST `)
            for ((i=0; i<${#nodes[*]}-1; i++));
            do
            \tstring+=${nodes[$i]}
            \tstring+=","
            done 
            string+=${nodes[$SLURM_NNODES-1]}
            sed -i -e "s/%%LindaWorker.*/%%LindaWorker=$string/Ig" %s

            # check that the Linda nodes are correct
            lindaline=(`grep -i 'lindaworker' %s`)
            if [[ $lindaline == *$string ]]
            then
            \techo "Using the correct nodes for Linda"
            else
            \techo "Using the wrong nodes for Linda"
            \techo "Nodes assigned by scheduler = $string"
            \techo "Line in Gaussian input file = $lindaline"
            \texit 1
            fi """ % (gauss_input, gauss_input)))

    if queue == 'bf' or queue == 'ckpt':
        f.write(textwrap.dedent("""\
          \n
          # copy last log file to another name
          num=`ls -l %s*.log | wc -l`
          let "num += 1"
          cp %s.log %s$num.log""" % (f_input[0], f_input[0], f_input[0])))

    if 'gdv' in version: 
        command = 'gdv'
    elif 'g16' in version:
        command = 'g16'
    else:
        command = 'g09'
    f.write(textwrap.dedent("""\
        \n
        # run Gaussian
        %s %s 

        exit 0 """ % (command, gauss_input)))

    print("""Please run 'sbatch %s' to submit to the scheduler\n""" % f_output)
#----------------------------------------------------------------------------

#----------------------------------------------------------------------------
def print_help():
    """Print a description of the script for the user."""
 
    print(textwrap.dedent("""\
        NAME
           \tGaussian-Submit
        DESCRIPTION
          \tThis program will help submit Gaussian calculations to
          \tthe Hyak Ikt and Mox clusters. The script will ask questions 
          \tabout the calculation to help set up the .pbs/.sh script.

          \tIt will check for the types of nodes available to
          \tset appropriate defaults. It will also read your input
          \tfile to check for potential issues if using the STF
          \tallocation.
        EXAMPLES
          \tpython gaussian-sub.py input{.gjf,.com}
        AUTHOR
          \tPatrick J. Lestrange <patricklestrange@gmail.com>"""))
#----------------------------------------------------------------------------

#----------------------------------------------------------------------------
if __name__ == '__main__':
    get_user_input()
    check_Gaussian_input()
    if   gen == 'ikt': write_Ikt_script()
    elif gen == 'mox': write_Mox_script()
#----------------------------------------------------------------------------

