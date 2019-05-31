from neuron import h
import numpy
import json
from urllib import urlopen
from bs4 import BeautifulSoup, Comment
import os
import sys
import math
import re

try:
    from run_protocols import protocol
except:
    protocol = {}

if len(sys.argv) < 2:
    print 'Usage: python %s MODELID' % sys.argv[0]
    sys.exit()

active_model = None
commands = {}

blank_line = {'text': ''}

try:
    with open('/home/tmm46/nrntest/verify/nrnziprun.dat') as f:
        for line in f:
            line = line.strip()
            if not line:
                commands[int(active_model)] = current
                active_model = None
            elif active_model is None:
                if ' ' in line:
                    active_model = line.split()[1]
                else:
                    active_model = line
                current = []
            else:
                current.append(line)
except:
    pass

model_id = int(sys.argv[1])

# load, run the model
if sys.argv < 3 or sys.argv[2].lower() != 'norun':
    h.load_file('mosinit.hoc')
    try:
        h.init()
    except:
        pass
    if model_id in commands:
        for command in commands[model_id]:
            print 'running: ', command
            h(command)

# TODO: add this to modeldb, then read from there
mech_types = {
    32992: {
        'hd': 'I-h',
        'kad': 'K-A',
        'kap': 'K-A',
        'kdr': 'K-dr',
        'na3': 'Na',
        'nax':  'Na'
    },
    125857: {
        'kahp': 'K-AHP',
        'nap': 'Na,p',
        'kc': 'K-Ca',
        'kdr': 'K-dr'
    },
    150240: {
        'hh2': 'Na + K',
        'it': 'T-type Ca',
        'im': 'K (M current)'
    }
}.get(model_id, {})

h.define_shape()

# load the modeldb entry
modeldb_html = urlopen('http://senselab.med.yale.edu/modeldb/ShowModel.asp?model=%d' % model_id).read()
modeldb_soup = BeautifulSoup(modeldb_html, 'html5lib')
paper_doi = []
paper_links = []
pubmed_links = []
for link_ref in modeldb_soup.find_all(id='reference'):
    for link in link_ref.find_all('a'):
        if link.text.lower().strip() != 'pubmed':
            href = link.get('href')
            if href is not None:
                paper_links.append('<a href="%s">%s</a>' % (href, link.text))
        else:
            href = link.get('href')
            if href is not None:
                pubmed_links.append('<a href="%s">%s</a>' % (href, link.text))
if len(paper_links) == 0:
    paper_links = pubmed_links

full_title = modeldb_soup.find_all('title')[0].text
title, short_title = '('.join(full_title.split('(')[:-1]).strip(), full_title.split('(')[-1][:-1].strip()
# trim out any leading ModelDB
if full_title[:9] == 'ModelDB: ':
    full_title = full_title[9:]
title = full_title


# get the top level folder name (assumes we are running inside that)
top_level_folder = os.getcwd().split(os.path.sep)[-1]

# scan the MOD files to find SUFFIX and POINT_PROCESS information
mech_files = {}
mech_modulates = {}
mech_depends = {}
mech_counts = {}
for root, dirs, files in os.walk('.'):
    # TODO: block the other architecture libraries too
    # TODO: of course, there's nothing inherently wrong with a mod file being in one of these
    #       folders... it's just that those tend to be copies made by nrnivmodl
    if 'x86_64' not in root:
        for filename in files:
            if filename[-4:].lower() == '.mod':
                depends_on = []
                modulates = []
                mech_name = None
                with open(os.path.join(root, filename)) as f:
                    for line in f:
                        # strip comments (this isn't quite right because : could be inside of a VERBATIM)
                        if ':' in line:
                            line = line[: line.index(':')]
                        # TODO: really should be checking to make sure I'm inside of a NEURON block
                        split_line = line.strip().split()
                        split_lower = line.lower().split()
                        if len(split_line) == 2 and split_line[0] in ('SUFFIX', 'POINT_PROCESS'):
                            mech_name = split_line[1]
                            mech_files[mech_name] = os.path.join(root, filename)[2:]
                        if len(split_lower) and split_lower[0] == 'nonspecific_current':
                            modulates.append('Nonspecific Current')
                        if len(split_lower) and split_lower[0] == 'useion':
                            ion_name = split_lower[1]
                            if 'read' in split_lower:
                                values = re.search('READ (.*?)( WRITE| CHARGE| VALENCE|$)', line).groups()
                                if values is not None and values[0] != '':
                                    depends_on.append(values[0].strip())
                            if 'write' in split_lower: 
                                values = re.search('WRITE (.*?)( READ| CHARGE| VALENCE|$)', line).groups()
                                if values is not None and values[0] != '':
                                    modulates.append(values[0].strip())

                if mech_name is not None:
                    mech_depends[mech_name] = depends_on
                    mech_modulates[mech_name] = modulates
                    count = 0
                    for sec in h.allsec():
                        if hasattr(sec(0.5), mech_name):
                            count += 1
                    mech_counts[mech_name] = count
                            


mech_xref = {}
for name, filename in mech_files.iteritems():
    link = '<a href="http://senselab.med.yale.edu/modeldb/ShowModel.asp?model=%d&file=/%s/%s">%s</a>' % (model_id, top_level_folder, filename, filename.split(os.path.sep)[-1])
    if name in mech_types:
        row = '%s, %s' % (mech_types[name], link)
    else:
        row = link
    mech_xref[name] = ' (%s)' % row

h.load_file("mview.hoc")

mview = h.ModelView(1)

items = []
def navigate(hlist):
    items = []
    i=0
    for ho in hlist:
        item = {'text': ho.s.lstrip(' *')}
        if ho.children:
            item['children'] = navigate(ho.children)
        items.append(item)
    return items

# TODO: build these in instead of scraping from classic ModelView
classic_rows = navigate(mview.display.top)
nsegs = {}
uniques = {}
constant_parms = {}

def process_nseg(root):
    if 'root ' in root['text']:
        root_name = root['text'].split('root ')[1]
        nsegs[root_name] = root['children'][1]
        for child in root['children']:
            if 'with unique parameters' in child['text']:
                uniques[root_name] = child
            if 'with constant parameters' in child['text']:
                constant_parms[root_name] = child
    else:
        # get here if talking about all instances of a class instead of a specific one
        pass

point_processes = blank_line
for row in classic_rows:
    words = row['text'].split()
    # NOTE: the row contains all its children in the same format as in the JSON
    if len(words) == 3 and words[1] == 'LinearMechanism':
        linear_mechanisms = row
    if len(words) >= 3 and words[1] == 'artificial':
        artificial_cells = row
    if len(words) >= 3 and words[1] == 'real' and words[2] == 'cells':
        for root in row['children']:
            if root['text'][:5] != 'root ':
                for item in root['children']:
                    process_nseg(item)
            else:
                process_nseg(root)
                    
    if row['text'] == 'Density Mechanisms':
        for child_row in row['children']:
            if child_row['text'] == 'Global parameters for density mechanisms':
                global_param_for_density = child_row
            if child_row['text'] == 'KSChan definitions for density mechanisms':
                kschan_defs = child_row
            if child_row['text'] == 'Homogeneous Parameters':
                homogeneous_parameters = child_row
            if child_row['text'] == 'Heterogeneous Parameters':
                # TODO: colorize
                heterogeneous_parameters = child_row
    
    row_split = row['text'].split()
    if len(row_split) >= 3 and row_split[1] == 'point' and row_split[2] == 'processes':
        point_processes = row

# TODO: make a general highlight_if that takes a function to do matching

def highlight_if_sec(secs, match_sec):
    """return a list of segments matching a given section"""
    result = []
    i = 0
    for sec in secs:
        if sec == match_sec:
            result += range(i, i + sec.nseg)
        i += sec.nseg
    return result

def all_segs_have(sec, name, val):
    """returns True iff all segments in the section have the same property value
    
    We compare their representations with %g rather than their exact values.
    """
    if name in ('cm', 'Ra'):
        return '%g' % sec.__getattribute__(name) == '%g' % val
    for seg in sec:
        if not hasattr(seg, name):
            return False
        if '%g' % seg.__getattribute__(name) != '%g' % val:
            return False
    return True
        

def highlight_if_sec_parms(secs, parms):
    """return a list of segments that belong to a section where all nodes have the stated parameters"""
    result = []
    i = 0
    for sec in secs:
        if all(all_segs_have(sec, name, value) for name, value in parms.iteritems()):
            result += range(i, i + sec.nseg)
        i += sec.nseg
    return result


def highlight_if_secname(secs, match_secname):
    """return a list of segments matching a given section"""
    result = []
    i = 0
    for sec in secs:
        if sec.name() == match_secname:
            result += range(i, i + sec.nseg)
        i += sec.nseg
    return result

def highlight_if_mech_present(secs, mech):
    """returns a list of the segments containing the mechanism"""
    result = []
    i = 0
    for sec in secs:
        if hasattr(sec, mech) or hasattr(sec(0.5), mech):
            result += range(i, i + sec.nseg)
        i += sec.nseg
    return result




def get_pts_between(x, y, z, d, arc, lo, hi):
    left_x = numpy.interp(lo, arc, x, left=x[0], right=x[-1])
    left_y = numpy.interp(lo, arc, y, left=y[0], right=y[-1])
    left_z = numpy.interp(lo, arc, z, left=z[0], right=z[-1])
    left_d = numpy.interp(lo, arc, d, left=d[0], right=d[-1])
    right_x = numpy.interp(hi, arc, x, left=x[0], right=x[-1])
    right_y = numpy.interp(hi, arc, y, left=y[0], right=y[-1])
    right_z = numpy.interp(hi, arc, z, left=z[0], right=z[-1])
    right_d = numpy.interp(hi, arc, d, left=x[0], right=d[-1])
    in_between = [[x0, y0, z0, d0] for (x0, y0, z0, d0, a0) in zip(x, y, z, d, arc) if lo < a0 < hi]
    if len(in_between) == 0:
        # ensure there is at least one interior point
        in_between = [[(left_x + right_x) * 0.5, (left_y + right_y) * 0.5, (left_z + right_z) * 0.5, (left_d + right_d) * 0.5]]
    return [[left_x, left_y, left_z, left_d]] + in_between + [[right_x, right_y, right_z, right_d]]

def get_root(sec):
    return h.SectionRef(sec=sec).root().sec

root_sections = []
for sec in h.allsec():
    if not h.SectionRef(sec).has_parent():
        root_sections.append(sec)

# get all mech names
mech_names = []
h("""
objref mt
json_var = 0
strdef mname
""")
h.mt = h.MechanismType(0)
for i in xrange(int(h.mt.count())):
    h.mt.select(i)
    h('mt.selected(mname)')
    mech_names.append(h.mname)

# get all point process names
pointprocess_names = []
h.mt = h.MechanismType(1)
for i in xrange(int(h.mt.count())):
    h.mt.select(i)
    h('mt.selected(mname)')
    pointprocess_names.append(h.mname)

def pt_from_seg(seg):
    sec = seg.sec
    n = int(h.n3d(sec=sec))
    x = [h.x3d(i, sec=sec) for i in xrange(n)]
    y = [h.y3d(i, sec=sec) for i in xrange(n)]
    z = [h.z3d(i, sec=sec) for i in xrange(n)]
    arc = [h.arc3d(i, sec=sec) for i in xrange(n)]
    f = seg.x * sec.L
    return (numpy.interp(f, arc, x), numpy.interp(f, arc, y), numpy.interp(f, arc, z))


pointprocess_locs_by_root = {}
pointprocess_mouseovers_by_root = {}
for name in pointprocess_names:
    pointprocess_locs_by_root[name] = {}
    pointprocess_mouseovers_by_root[name] = {}
    for root in root_sections:
        pointprocess_locs_by_root[name][root] = []
        pointprocess_mouseovers_by_root[name][root] = []
    #pointprocess_locs_by_root[name] = {root: [] for root in root_sections}
    #pointprocess_mouseovers_by_root[name] = {root: [] for root in root_sections}
    ell = h.List(name)
    for i in xrange(int(ell.count())):
        obj = ell.o(i)
        if obj.has_loc():
            seg = obj.get_segment()
            pt = list(pt_from_seg(seg))
            pointprocess_locs_by_root[name][get_root(seg.sec)].append(pt)
            pointprocess_mouseovers_by_root[name][get_root(seg.sec)].append('%s at %s(%g)<br/>(%g, %g, %g)' % (name, seg.sec.name(), seg.x, pt[0], pt[1], pt[2]))

if 'children' in point_processes:
    base = point_processes['children']
    if len(base):
        text = base[0]['text'].split()
        if len(text) == 3 and text[1] == 'Point' and text[2] == 'Processes' and 'children' in base[0]:
            base = base[0]['children']
    for child in base:
        name = child['text'].split()[1]
        if name in mech_files:
            child['text'] += ' ' + mech_xref[name]
        elif name in ['AlphaSynapse', 'Exp2Syn', 'ExpSyn', 'IClamp', 'IntFire1', 'IntFire2', 'IntFire4', 'NetStim', 'SEClamp', 'VClamp']:
            # TODO: this will need changed if help documentation is moved
            child['text'] += ' (builtin: <a href="http://neuron.yale.edu/neuron/static/new_doc/modelspec/programmatic/mechanisms/mech.html#%s">ref</a>)' % name
        child['action'] = []
        for i, root in enumerate(root_sections):
            #print 'name:', name
            #print 'root:', root
            #print pointprocess_locs_by_root
            action = {'kind': 'neuronviewer', 'id': i}
            try:
                action['markers'] = pointprocess_locs_by_root[name][root]
                action['marker_mouseovers'] = pointprocess_mouseovers_by_root[name][root]
            except:
                pass
            child['action'].append(action)

        if 'children' in child:
            for grandchild in child['children']:
                grandchild['noop'] = True




# get the names of mechanism parameters (range_vars)
range_vars = {}
for mech in mech_names:
    h.mt = h.MechanismStandard(mech)
    range_vars[mech] = []
    suffix = '_' + mech
    lensuffix = len(suffix)
    for i in xrange(int(h.mt.count())):
        h('mt.name(mname, %d)' % i)
        mname = h.mname
        if mname[-lensuffix :] == suffix:
            mname = mname[: -lensuffix]
        range_vars[mech].append(mname)
    if not range_vars[mech]: del range_vars[mech]
#print 'range_vars:', range_vars


def mechs_present(secs):
    result = []
    for name in mech_names:
        for sec in secs:
            if hasattr(sec(0.5), name):
                result.append(name)
                break
    return ['Ra', 'cm'] + result

def two_char_hex(n):
    s = hex(int(n))[-2 :]
    if s[0] == 'x':
        s = '0' + s[1]
    return s

def hex_rgb(r, g, b):
    """expects r, g, b between 0 and 1"""
    return '#' + two_char_hex(r * 255) + two_char_hex(g * 255) + two_char_hex(b * 255)

def values_to_colors(values):
    non_nan = [v for v in values if not numpy.isnan(v)]
    if len(non_nan) == 0:
        return ['black'] * len(values)
    lo = min(non_nan)
    hi = max(non_nan)
    length = float(hi - lo)
    if lo == hi:
        return ['black' if numpy.isnan(v) else 'red' for v in values]
    else:
        values = numpy.array([(v - lo) / length for v in values])
        # gradient from blue (lo) to red (hi)
        return [(hex_rgb(v, 0, 1 - v) if not numpy.isnan(v) else 'black') for v in values]

def morph_per_root(root):
    morph = []
    h.define_shape()
    for sec in secs_with_root(root):
        n3d = int(h.n3d(sec=sec))
        x = [h.x3d(i, sec=sec) for i in xrange(n3d)]
        y = [h.y3d(i, sec=sec) for i in xrange(n3d)]
        z = [h.z3d(i, sec=sec) for i in xrange(n3d)]
        d = [h.diam3d(i, sec=sec) for i in xrange(n3d)]
        arc = [h.arc3d(i, sec=sec) for i in xrange(n3d)]
        length = sec.L
        half_dx = 0.5 / sec.nseg
        for seg in sec:
            morph.append(get_pts_between(x, y, z, d, arc, (seg.x - half_dx) * length, (seg.x + half_dx) * length))
    
    # add end points
    for end_pt in [0, 1]:
        for sec in secs_with_root(root):
            n3d = int(h.n3d(sec=sec))
            pt1 = [h.x3d(0, sec=sec), h.y3d(0, sec=sec), h.z3d(0, sec=sec), h.diam3d(0, sec=sec)]
            pt2 = [h.x3d(n3d - 1, sec=sec), h.y3d(n3d - 1, sec=sec), h.z3d(n3d - 1, sec=sec), h.diam3d(n3d - 1, sec=sec)]
            if h.section_orientation(sec=sec) == 0:
                morph.append([pt1] if end_pt == 0 else [pt2])
            else:
                morph.append([pt2] if end_pt == 0 else [pt1])
    return morph

def seg_names_per_root(root):
    names = []
    for sec in secs_with_root(root):
        for seg in sec:
            names.append('%s(%g)' % (sec.name(), seg.x))
    for end_pt in [0, 1]:
        for sec in secs_with_root(root):
            names.append('%s(%d)' % (sec.name(), end_pt))
    return names
    

def secs_with_root(root):
    return [sec for sec in h.allsec() if get_root(sec) == root]

def sec_seg(secs):
    if len(secs) == 1:
        num_secs = '1 section'
    else:
        num_secs = '%d sections' % len(secs)
    num_segs = sum(sec.nseg for sec in secs)
    if num_segs == 1:
        num_segs = '1 segment'
    else:
        num_segs = '%d segments' % num_segs
    return '%s; %s' % (num_secs, num_segs)

def set_action_to_all(tree, action):
    for row in tree:
        row['action'] = action
        if 'children' in row:
            set_action_to_all(row['children'], action)

def nseg_analysis(secs, cell_id, root_name):
    dx_max = 0
    dxs = []
    for sec in secs:
        dx = sec.L / sec.nseg
        dxs += ['dx = %g' % dx] * sec.nseg
        if dx > dx_max:
            dx_max = dx
            dx_max_loc = sec
    result = nsegs[root_name]
    
    # compute bar chart for nseg distribution
    min_nseg = min(sec.nseg for sec in secs)
    max_nseg = max(sec.nseg for sec in secs)
    num_bins = 10
    delta_nseg = max(math.ceil((max_nseg + 1 - min_nseg) / float(num_bins)), 1)
    nseg_counts = [0 for i in xrange(num_bins)]
    for sec in secs:
        nseg_counts[int((sec.nseg - min_nseg) / delta_nseg)] += 1
    nseg_bar_data = [[i * delta_nseg + min_nseg, nseg_count] for i, nseg_count in enumerate(nseg_counts)]

    # TODO: bar chart for dlambda, dx        
    set_action_to_all([result], [{'kind': 'neuronviewer', 'id': cell_id}])
    
    # add bar chart for distinct values of nseg
    # TODO: tooltips!
    result['action'].append({
        'kind': 'flot',
        'data': [{'data': nseg_bar_data, 'bars': {'show': True, 'barWidth': delta_nseg, 'fillColor': 'blue'}}],
        'xaxes': [{'axisLabel': 'nseg', 'labelcolor': 'black'}],
        'yaxes': [{'axisLabel': 'count', 'labelcolor': 'black'}],
        'color': 'black',
        'title': 'nseg frequency distribution'
    })
    
    if result['text'] == '1 distinct values of nseg':
        result['text'] = '1 distinct value of nseg'
    # Longest dx section
    result['children'][0]['action'] = [{'kind': 'neuronviewer', 'id': cell_id, 'highlight': highlight_if_sec(secs, dx_max_loc), 'hover_text': dxs}]
    return result
    """
    dx_max = 0
    for sec in secs:
        if sec.L / sec.nseg > dx_max:
            dx_max = sec.L / sec.nseg
            dx_max_loc = sec
        nsegs[sec.nseg] = 0
    return {
        'text': '%d distinct value%s of nseg' % (len(nsegs.values()), 's' if len(nsegs.values()) != 1 else ''),
        'action': [{'kind': 'neuronviewer', 'id': cell_id}],
        'children': [
            {
                'text': 'Longest dx is %g at %s with nseg=%d' % (dx_max, dx_max_loc.name(), dx_max_loc.nseg),
                'action': [{'kind': 'neuronviewer', 'id': cell_id, 'colors': colorize_if_sec(secs, dx_max_loc)}]
            }
        ]
    }
    """

def min_no_nan(values):
    values = [v for v in values if not numpy.isnan(v)]
    if values:
        return min(values)
    else:
        return None

def max_no_nan(values):
    values = [v for v in values if not numpy.isnan(v)]
    if values:
        return max(values)
    else:
        return None

def colorize_homogeneous(tree):
    for row in tree['children']:
        prop = row['text'].split()[0]
        action = []
        for cell_id, root in enumerate(root_sections):
            secs = secs_with_root(root)
            action.append({
                'kind': 'neuronviewer',
                'highlight': highlight_if_mech_present(secs, prop),
                'id': cell_id                
            })
        row['action'] = action
    return tree

def colorize_by_mech_value(secs, mech, name):
    values = []
    if mech[-4 : ] == '_ion':
        # need to do this to allow e.g. nao, a "property" of na_ion that stands alone
        value_getter = lambda seg: getattr(seg, name)
    else:
        value_getter = lambda seg: getattr(getattr(seg, mech), name)
    indices = []
    i = 0
    seg_count = 0
    reverse_indices = []
    for sec in secs:
        try:
            v = value_getter(sec(0.5))
            for seg in sec:
                values.append(value_getter(seg))
                indices.append(i)
                reverse_indices.append(seg_count)
                i += 1
                seg_count += 1
        except:    
            if not hasattr(sec(0.5), mech):
                values += [numpy.nan] * sec.nseg
                indices += [-1] * sec.nseg
                seg_count += sec.nseg

    return values_to_colors(values), values, min_no_nan(values), max_no_nan(values), indices, reverse_indices

def flot_by_distance_from_root(root, mech, name, secs):
    # measure distance from the midpt of the root
    if mech[-4 : ] == '_ion':
        # need to do this to allow e.g. nao, a "property" of na_ion that stands alone
        value_getter = lambda seg: getattr(seg, name)
    else:
        value_getter = lambda seg: getattr(getattr(seg, mech), name)
    h.distance(0, 0.5, sec=root)
    data = []
    for sec in secs:
        try:
            v = value_getter(sec(0.5))
            for seg in sec:
                data.append([h.distance(1, seg.x, sec=sec), value_getter(seg)])
        except:
            pass
    return [{
        'data': data,
        'color': 'black',
        'points': {'show': True}
    }]

def seg_mechanisms(secs):
    result = []
    for sec in secs:
        mechanisms = 'Mechanisms present:<br/>' + '<br/>'.join(['&nbsp;&nbsp; ' + m for m in mechs_present([sec])])
        result += [mechanisms] * sec.nseg
    return result

def cell_mech_analysis(secs, cell_id):
    mps = mechs_present(secs)
    mechs = [name + mech_xref.get(name, '') for name in mps]
    children = []
    for mech_text, mech in zip(mechs, mps):
        child = {
            'text': mech_text,
            'action': [
                {
                    'kind': 'neuronviewer',
                    'highlight': highlight_if_mech_present(secs, mech),
                    'id': cell_id
                }
            ]
        }
        if mech in range_vars:
            child_parts = []
            for name in range_vars[mech]:
                flotchart = flot_by_distance_from_root(root_sections[cell_id], mech, name, secs)
                colors, values, lo, hi, indices, reverse_indices = colorize_by_mech_value(secs, mech, name)
                values = [repr(v) for v in values]
                if lo is not None:
                    nv_action = {'kind': 'neuronviewer', 'id': cell_id, 'colors': colors, 'colorbar': 0, 'colorbar_orientation': 'horizontal', 'colorbar_low': '%g' % lo, 'colorbar_high': '%g' % hi, 'colored_var': name, 'values': values, 'flotindices': indices}
                else:
                    nv_action = {'kind': 'neuronviewer', 'id': cell_id}
                child_parts.append({
                    'text': name,
                    'action': [
                        nv_action,
                        {
                            'kind': 'flot',
                            'data': flotchart,
                            'xaxes': [{'axisLabel': 'Distance from root', 'labelcolor': 'black'}],
                            'yaxes': [{'axisLabel': '%s.%s' % (mech, name), 'labelcolor': 'black'}],
                            'hoverable': True,
                            'clickable': True,
                            'neuron_highlight_id': cell_id,
                            'neuron_highlight_segs': reverse_indices
                        }
                    ]
                })
            child['children'] = child_parts
        children.append(child)
    return {
        'text': '%d inserted mechanisms' % len(mechs),
        'action': [{'kind': 'neuronviewer', 'id': cell_id, 'hover_text': seg_mechanisms(secs)}],
        'children': children
    }



def cell_tree(root):
    cell_id = root_sections.index(root)
    secs = secs_with_root(root)
    # TODO: subsets with constant parameters, point processes
    if root.name() in nsegs:
        result = [
            {
                'text': sec_seg(secs),
                'action': [{'kind': 'neuronviewer', 'id': cell_id}]
            },
            nseg_analysis(secs, cell_id, root.name()),
            cell_mech_analysis(secs, cell_id)
        ]
    else:
        # TODO: better fallback for the non-first members of a group then to simply
        #       omit all nseg analysis?
        result = [
            {
                'text': sec_seg(secs),
                'action': [{'kind': 'neuronviewer', 'id': cell_id}]
            },
            cell_mech_analysis(secs, cell_id)
        ]
    unique = uniques.get(root.name())
    constant_parm = constant_parms.get(root.name())
    if constant_parm:
        result.append(constant_parm)
    if unique:
        result.append(unique)
    return result


# summary
summary = {
    'text': sec_seg(list(h.allsec()))
}

# real cells
# TODO: action: display all cells
real_cells = {
    'text': '%d real cell%s' % (len(root_sections), 's' if len(root_sections) != 1 else ''),
    'action': [
        {
            'kind': 'neuronviewer',
            'id': i
        } for i in xrange(len(root_sections))
    ]
}
if root_sections:
    real_cells['children'] = []
    for cell_id, root in enumerate(root_sections):
        # TODO: action: when clicking on a specific cell, display just that one
        real_cells['children'].append({'text': 'root %s' % root.name(), 'children': cell_tree(root), 'action': [{'kind': 'neuronviewer', 'id': cell_id}]})

if len(paper_links):
    children = [{'text': 'Paper in %s' % item, 'noop': True} for item in paper_links]
else:
    children = []
children.append({
    'text': '<a href="http://senselab.med.yale.edu/modeldb/ShowModel.asp?model=%d">ModelDB Entry</a>' % model_id,
    'noop': True
})
references = {
    'text': 'References',
    'children': children,
    'noop': True
}

if len(sys.argv) > 3:
    # sys.argv[3] assumed to be the run protocol
    if sys.argv[3] in protocol:
        p = protocol[sys.argv[3]]
        references['children'].append({
            'text': 'Run Protocol',
            'noop': True,
            'children': [
                {
                    'text': 'Compiling',
                    'children': [{'text': line, 'noop': True} for line in p['compile']],
                    'noop': True
                },
                {
                    'text': 'Launching NEURON',
                    'children': [{'text': line, 'noop': True} for line in p['launch']],
                    'noop': True
                },
                {
                    'text': 'Running',
                    'children': [{'text': line, 'noop': True} for line in p['run']],
                    'noop': True
                }
            ]
        })


# process uniques to remove {} and add highlighting
for cell_id, root in enumerate(root_sections):
    if root.name() in uniques:
        all_uniques = set([])
        for row in uniques[root.name()]['children']:
            secname = row['text'].rstrip(' {')
            row['text'] = secname
            highlight = highlight_if_secname(secs_with_root(root), secname)
            all_uniques = all_uniques.union(highlight)
            action = [{'kind': 'neuronviewer', 'id': cell_id, 'highlight': highlight}]
            row['action'] = action
            if row['children'][-1]['text'].strip() == '}':
                row['children'] = row['children'][: -1]
            for child in row['children']:
                child['action'] = action
        uniques[root.name()]['action'] = [{'kind': 'neuronviewer', 'id': cell_id, 'highlight': list(all_uniques)}]

def parm_subset_properties(node):
    """reads the tree to construct a dictionary of parameter values"""
    result = {}
    for row in node.get('children', []):
        text = row['text'].split()
        result[text[0]] = float(text[-1])
    return result

# process constant_parms to add highlighting
for cell_id, root in enumerate(root_sections):
    if root.name() in constant_parms:
        all_constants = set([])
        delete_rows = []
        for i, row in enumerate(constant_parms[root.name()]['children']):
            # TODO: the problem with this approach is that it ignores inserted mechanisms with no parameters (e.g. ds in 32992), but the tree we're scraping does not ignore that
            parms = parm_subset_properties(row)
            if parms:
                highlight = highlight_if_sec_parms(secs_with_root(root), parms)
                all_constants = all_constants.union(highlight)
                action = [{'kind': 'neuronviewer', 'id': cell_id, 'highlight': highlight}]
                row['action'] = action
                for child in row['children']:
                    child['action'] = action
            else:
                delete_rows.append(i)
        # remove the subsets with no parameters (these correspond to mechanisms with no parameters, but we cannot visualize that)
        for item in delete_rows[::-1]:
            del constant_parms[root.name()]['children'][item]
        # TODO: map these section lists to named section lists (or their unions/intersections/etc... arbitrarily complicated problem)
        constant_parms[root.name()]['text'] = '%d subsets with constant parameters' % len(constant_parms[root.name()]['children'])
        constant_parms[root.name()]['action'] = [{'kind': 'neuronviewer', 'id': cell_id, 'highlight': list(all_constants)}]

# mechanisms in use
mechs = [{'text': name + mech_xref.get(name, '')} for name in mechs_present(list(h.allsec()))]
for row in mechs:
    mech_name = row['text'].split()[0]
    depends = mech_depends.get(mech_name, [])
    modulates = mech_modulates.get(mech_name, [])
    count = mech_counts.get(mech_name, 0)    
    if len(depends) or len(modulates) or count:
        row['children'] = []
    if len(depends):
        row['children'].append({'text': 'READs: %s' % ', '.join(depends)})
    if len(modulates):
        row['children'].append({'text': 'WRITEs: %s' % ', '.join(modulates)})
    if count:
        row['children'].append({'text': 'Present in %d sections' % count})
mech_in_use = {'text': '%d mechanisms in use' % len(mechs), 'children': mechs}

# density mechanisms
density_mechanisms = {
    'text': 'Density Mechanisms',
    'children': [
        mech_in_use,
        colorize_homogeneous(homogeneous_parameters),
        heterogeneous_parameters,
        global_param_for_density,
        kschan_defs
    ]
}

def process_values(name, values):
    if len(values) == 1:
        # TODO: plot location
        return {'text': '%s = %g' % (name, values[0])}
    else:
        # TODO: plot location, plot values as a function of distance to root
        return {
            'text': '%d values for %s from %g to %g' % (len(values), name, min(values), max(values)),
            'children': [{'text': v} for v in values]
        }

# NetCon (based on ncview.hoc)
netcon_list = h.List('NetCon')
netcons = {'text': '%d NetCon objects' % netcon_list.count()}
if netcon_list.count():
    weights = []
    delays = []
    threshold = []
    # TODO: talk to Michael about why this doesn't work in pure python
    for i in xrange(int(netcon_list.count())):
        h.mt = netcon_list.object(i)
        h('json_var = mt.weight')
        weights.append(h.json_var)
        h('json_var = mt.delay')
        delays.append(h.json_var)
        h('json_var = mt.threshold')
        threshold.append(h.json_var)
    weights = sorted(set(weights))
    delays = sorted(set(delays))
    threshold = sorted(set(threshold))
    netcons['children'] = [
        process_values('weight', weights),
        process_values('delay', delays),
        process_values('threshold', threshold)
    ]


# include for components data
# TODO: make this use an API to get dynamically
components = {'include': '//senselab.med.yale.edu/modeldb/modelview_components.asp?model=%d&callback=jsonp_callback_' % model_id}

# make all of the components noop
def make_noop(tree):
    for row in tree:
        row['noop'] = True
        if 'children' in row:
            make_noop(row['children'])
make_noop([components])


data = {
    'modelview_version': 0,
    'neuron': [{'title': 'root: ' + root.name(), 'morphology': morph_per_root(root), 'seg_names': seg_names_per_root(root)} for root in root_sections],
    'title': title, 
    'short_title': short_title,
    'neuronviewer': range(len(root_sections)),
    'tree': [
            summary,
            blank_line,
            real_cells,
            artificial_cells,
            netcons,
            linear_mechanisms,
            blank_line,
            density_mechanisms,
            point_processes,
            blank_line,
            components,
            blank_line,
            references #, {'text': 'green circle', 'action': [{'kind': 'svg', 'svg': '<circle id="greencircle" cx="30" cy="30" r="30" fill="green" />', 'viewbox': '0 0 60 60'}]}
    ],
    'colorbars': [
        {
            'type': 'css',
            'css': """
                /* from http://www.colorzilla.com/gradient-editor/#0000ff+0,ff0000+100; accessed 26 Nov 2013 */
                background: #0000ff;
                background: url(data:image/svg+xml;base64,PD94bWwgdmVyc2lvbj0iMS4wIiA/Pgo8c3ZnIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyIgd2lkdGg9IjEwMCUiIGhlaWdodD0iMTAwJSIgdmlld0JveD0iMCAwIDEgMSIgcHJlc2VydmVBc3BlY3RSYXRpbz0ibm9uZSI+CiAgPGxpbmVhckdyYWRpZW50IGlkPSJncmFkLXVjZ2ctZ2VuZXJhdGVkIiBncmFkaWVudFVuaXRzPSJ1c2VyU3BhY2VPblVzZSIgeDE9IjAlIiB5MT0iMCUiIHgyPSIxMDAlIiB5Mj0iMCUiPgogICAgPHN0b3Agb2Zmc2V0PSIwJSIgc3RvcC1jb2xvcj0iIzAwMDBmZiIgc3RvcC1vcGFjaXR5PSIxIi8+CiAgICA8c3RvcCBvZmZzZXQ9IjEwMCUiIHN0b3AtY29sb3I9IiNmZjAwMDAiIHN0b3Atb3BhY2l0eT0iMSIvPgogIDwvbGluZWFyR3JhZGllbnQ+CiAgPHJlY3QgeD0iMCIgeT0iMCIgd2lkdGg9IjEiIGhlaWdodD0iMSIgZmlsbD0idXJsKCNncmFkLXVjZ2ctZ2VuZXJhdGVkKSIgLz4KPC9zdmc+);
                background: -moz-linear-gradient(left,  #0000ff 0%, #ff0000 100%);
                background: -webkit-gradient(linear, left top, right top, color-stop(0%,#0000ff), color-stop(100%,#ff0000));
                background: -webkit-linear-gradient(left,  #0000ff 0%,#ff0000 100%);
                background: -o-linear-gradient(left,  #0000ff 0%,#ff0000 100%);
                background: -ms-linear-gradient(left,  #0000ff 0%,#ff0000 100%);
                background: linear-gradient(to right,  #0000ff 0%,#ff0000 100%);
                filter: progid:DXImageTransform.Microsoft.gradient( startColorstr='#0000ff', endColorstr='#ff0000',GradientType=1 );
            """
        }
    ]
}

if len(sys.argv) < 4:
    with open('%d.json' % model_id, 'w') as f:
        f.write(json.dumps(data))
else:
    with open('%s.json' % sys.argv[3], 'w') as f:
        f.write(json.dumps(data))
    
if len(paper_links) == 0:
    print 'No paper link found.'
    
