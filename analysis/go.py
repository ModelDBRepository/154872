import sys
import os
import urllib2
from run_protocols import protocol

p = sys.argv[1]
id = int(p.split('_')[0])

protocol = protocol[p]

initial_path = os.getcwd() + '/'

#
# download the zip file
#
# TODO: a better way to do this would be to find the link with the downloadzip id in the ShowModel page
#       especially since we will do that later anyways
zip_file = urllib2.urlopen('http://senselab.med.yale.edu/ModelDB/eavBinDown.asp?o=%d&a=23&mime=application/zip' % id).read()
if zip_file == 'File not found!':
    # attribute 311 instead of 23 if an "alternate" version of the model
    zip_file = urllib2.urlopen('http://senselab.med.yale.edu/ModelDB/eavBinDown.asp?o=%d&a=311&mime=application/zip' % id).read()
    if zip_file == 'File not found!':
        print 'could not access the zip file; is the model id correct?'
        sys.exit()


with open('zipfile.zip', 'wb') as f:
    f.write(zip_file)


#
# compile the model mechanisms
#
assert(protocol['compile'][0][: 3] == 'cd ')
dir_name = protocol['compile'][0][3:]
os.system('unzip zipfile.zip')
os.system('cp json_generator.py %s/' % dir_name)
os.chdir(dir_name)

for i, command in enumerate(protocol['compile']):
    if i > 0 or command[:3] != 'cd ':
        os.system(command)

#
# load the model into NEURON
#
assert(len(protocol['launch']) == 1)
assert(protocol['launch'][0] == 'nrngui -python')

# this import has to be done after the mod files have been compiled
from neuron import h

#
# act as if we're going to run it, but generate the json and exit when the
# first fadvance occurs
#
def generate_json(*args, **kwargs):
    global dir_name
    if h.t <= 0: return
    # json_generator expects to be run from the terminal, so update sys.argv
    sys.argv = ['json_generator.py', id, 'norun', p]
    import json_generator
    os.system('cp *.json ' + initial_path)
    os.chdir(initial_path)
    os.remove('zipfile.zip')
    if '/' in dir_name: dir_name = dir_name[:dir_name.index('/')] # linux-specific
    os.system('rm -fr %s' % dir_name)
    if not good:
        print 'WARNING: Never actually did an fadvance'
    sys.exit()

# add the cwd to the path (needed for Python models)
sys.path = [os.getcwd()] + sys.path

good = True    
for i, command in enumerate(protocol['run']):
    if i == len(protocol['run']) - 1 and protocol.get('stopmidsim', True):
        h.CVode().extra_scatter_gather(0, generate_json)
    exec(command)

print 'WARNING: Never actually did an fadvance.'
print '         Attempting to generate JSON anyways.'
h.t = 1
good = False
generate_json()
print 'WARNING: Never actually did an fadvance.'

