import os
from run_protocols import protocol

# start with an empty file
with open('model_stats.csv', 'w') as f:
    f.write('protocol, num_cells, total_secs, total_3dpts, avg_3dpts_per_cell\n')

for key in protocol:
    os.system('python go_count_stats.py %s' % key)
