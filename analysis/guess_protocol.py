import sys
import os
import urllib2
import subprocess

if len(sys.argv) < 2:
    print 'did you forget to specify a model id?'
    sys.exit()
id = int(sys.argv[1])

initial_path = os.getcwd() + '/'

warnings = []

#
# download the zip file
#
# TODO: a better way to do this would be to find the link with the downloadzip id in the ShowModel page
#       BUT: that would require loading the ShowModel page
zip_file = urllib2.urlopen('http://senselab.med.yale.edu/ModelDB/eavBinDown.asp?o=%d&a=23&mime=application/zip' % id).read()
if zip_file == 'File not found!':
    # attribute 311 instead of 23 if an "alternate" version of the model
    zip_file = urllib2.urlopen('http://senselab.med.yale.edu/ModelDB/eavBinDown.asp?o=%d&a=311&mime=application/zip' % id).read()
    if zip_file == 'File not found!':
        print 'could not access the zip file; is the model id correct?'
        sys.exit()

if 'temp_files_guess_protocol' in os.listdir('.'):
    os.system('rm -fr temp_files_guess_protocol')

os.mkdir('temp_files_guess_protocol')
os.chdir('temp_files_guess_protocol')
with open('zipfile.zip', 'wb') as f:
    f.write(zip_file)

os.system('unzip zipfile.zip')

mosinit_locs = subprocess.Popen('find . -name mosinit.hoc', shell=True, stdout=subprocess.PIPE).communicate()[0].strip().split('\n')

assert(len(mosinit_locs) == 1)

mosinit_loc = mosinit_locs[0]
if mosinit_loc[:2] == './':
    mosinit_loc = mosinit_loc[2:]

model_directory = os.path.split(mosinit_loc)[0]
path_to_root = '../' * len(model_directory.split('/')) # linux/mac specific
chdir_command = 'cd %s' % model_directory

for model_name in os.listdir('.'):
    if model_name != 'zipfile.zip':
        break
        
os.chdir(model_directory)

with open('mosinit.hoc') as f:
    for first_line in f:
        break

mod_files = subprocess.Popen('find . -name "*.mod"', shell=True, stdout=subprocess.PIPE).communicate()[0].strip().split('\n')

if len([m for m in mod_files if m != '']):
    print 'mod_files:', mod_files
    if first_line[: 9] == '//moddir ':
        compile_instructions = 'nrnivmodl ' + first_line[9:].strip()
    else:
        compile_instructions = 'nrnivmodl'

    os.system(compile_instructions)
else:
    print 'mod_files:', mod_files
    print 'none'
    compile_instructions = None
    
from neuron import h

xbuttons = subprocess.Popen('grep -r xbutton .', shell=True, stdout=subprocess.PIPE).communicate()[0].strip().split('\n')
xbutton_labels = []
xbutton_commands = []
for button in xbuttons:
    if button:
        # strip out the filename
        print repr(button)
        button = button[button.index(':') + 1:].strip()
        if '//' in button:
            if button.index('//') < button.index('xbutton'):
                continue
        if button[:8] != 'xbutton(':
            warnings.append('xbutton not at beginning of line ignored: ' + button)
        else:
            button = button[8:]
            if ',' in button:
                comma = button.index(',')
                xbutton_labels.append(button[1 : comma - 1])
                right_part = button[comma : ]
                if '"' in right_part:
                    right_part = right_part[right_part.index('"') + 1 : -2].strip()
                else:
                    warnings.append('No " in xbutton command: ' + button)
                # unescape quotation marks
                # TODO: not strictly correct, but right most of the time
                right_part = right_part.replace(r'\"', '"')
                xbutton_commands.append('h.' + right_part)

load_neuron = 'nrngui -python'
load_model = ['from neuron import h, gui', 'h.load_file("mosinit.hoc")']

def print_compile_instructions():
    if compile_instructions is not None:
        print "            'compile': ['%s', '%s']," % (chdir_command, compile_instructions)
    else:
        print "            'compile': ['%s']," % (chdir_command)


def print_results_and_exit():
    print "    '%d':" % id
    print "        {"
    print_compile_instructions()
    print "            'launch': ['%s']," % load_neuron
    print "            'run': %r," % load_model
    print "            'cleanup': ['cd %s', 'rm -fr %s']" % (path_to_root, model_name)
    print "        },"

    import sys
    sys.exit()

def mosinit_runs_sim(*args):
    print_results_and_exit()

if len(xbutton_commands) == 1:
    load_model.append(xbutton_commands[0])

if len(xbutton_commands) == 0:
    h.CVode().extra_scatter_gather(0, mosinit_runs_sim)
    h.load_file('mosinit.hoc')
    # if we get here, mosinit does not run the sim, so need to do a run
    load_model.append('h.run()')
    print_results_and_exit()
elif len(xbutton_commands) == 1:
    h.load_file('mosinit.hoc')
    h.CVode().extra_scatter_gather(0, mosinit_runs_sim)
    h(xbutton_commands[0][3 : -2])
    # if we get here, mosinit does not run the sim, so need to do a run
    load_model.append('h.run()')
    print_results_and_exit()
else:
    i = 0
    for label, command in zip(xbutton_labels, xbutton_commands):
        i += 1
        print "    '%d_%d':" % (id, i)
        print "        {"
        print "            'variant': '%s'," % label.strip()
        print_compile_instructions()
        print "            'launch': ['%s']," % load_neuron
        print "            'run': %r," % (load_model + [command])
        print "            'cleanup': ['cd %s', 'rm -fr %s']" % (path_to_root, model_name)
        print "        },"


if len(warnings):
    print
    print '*** WARNING%s ***' % ('S' if len(warnings) > 1 else '')
    for warning in warnings:
        print warning

xradiobuttons = [item for item in subprocess.Popen('grep -r xradiobutton .', shell=True, stdout=subprocess.PIPE).communicate()[0].strip().split('\n') if item.strip() != '']

if len(xradiobuttons):
    print
    print '*** there were xradiobuttons ***'
    for line in xradiobuttons:
        print '    ', line

xstatebuttons = [item for item in subprocess.Popen('grep -r xstatebutton .', shell=True, stdout=subprocess.PIPE).communicate()[0].strip().split('\n') if item.strip() != '']

if len(xstatebuttons):
    print
    print '*** there were xstatebuttons ***'
    for line in xstatebuttons:
        print '    ', line
