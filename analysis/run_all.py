import os
from run_protocols import protocol

for key in protocol:
    os.system('python go.py %s' % key)
