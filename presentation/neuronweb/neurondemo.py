import webgui
from neuron import h
h.load_file('stdrun.hoc')

soma = h.Section()
soma.insert('hh')

stim = h.IClamp(0.5)
stim.delay = 0
stim.dur = 0.1
stim.amp = 200

data = []
data_t = []
def timestep_callback():
    global data_t, data
    while data_t and h.t < data_t[-1]:
        data_t = data_t[ : -1]
        data = data[: -1]
    data_t.append(h.t)
    data.append([h.t, soma.v])
    graph.plot(data)

h.CVode().extra_scatter_gather(0, timestep_callback)

def do_init(data):
    h.finitialize()
def do_init_and_run(data):
    print 'init and run'
    h.run()
def do_stop(data):
    print 'stop'
def do_continue_til(data):
    print 'continue til'
def do_continue_for(data):
    print 'continue for'
def do_single_step(data):
    print 'single step'
def do_t(data):
    print 't'
def do_tstop(data):
    print 'tstop'
def do_dt(data):
    print 'dt'

runcontrol = webgui.Dialog('RunControl')
initbutton = webgui.Button('Init (mV)', do_init)
runcontrol.add(initbutton)
#init_v_field = webgui.TextField('')
#runcontrol.add(init_v_field)
initrunbutton = webgui.Button('Init & Run', do_init_and_run)
runcontrol.add(initrunbutton)
stopbutton = webgui.Button('Stop', do_stop)
runcontrol.add(stopbutton)
continuetilbutton = webgui.Button('Continue til (ms)', do_continue_til)
runcontrol.add(continuetilbutton)
continueforbutton = webgui.Button('Continue for (ms)', do_continue_for)
runcontrol.add(continueforbutton)
singlestepbutton = webgui.Button('Single Step', do_single_step)
runcontrol.add(singlestepbutton)
tbutton = webgui.Button('t (ms)', do_t)
runcontrol.add(tbutton)
tstopbutton = webgui.Button('Tstop (ms)', do_tstop)
runcontrol.add(tstopbutton)
dtbutton = webgui.Button('dt (ms)', do_dt)
runcontrol.add(dtbutton)
graph = webgui.Graph()
runcontrol.add(graph)
runcontrol.instantiate()

#graphwindow = webgui.Dialog('Graph')
#graphwindow.instantiate()

