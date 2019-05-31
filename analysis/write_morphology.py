from neuron import h
import numpy
import json
from urllib import urlopen
import os
import sys
import math
import re


h.define_shape()

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


def pt_from_seg(seg):
    sec = seg.sec
    n = int(h.n3d(sec=sec))
    x = [h.x3d(i, sec=sec) for i in xrange(n)]
    y = [h.y3d(i, sec=sec) for i in xrange(n)]
    z = [h.z3d(i, sec=sec) for i in xrange(n)]
    arc = [h.arc3d(i, sec=sec) for i in xrange(n)]
    f = seg.x * sec.L
    return (numpy.interp(f, arc, x), numpy.interp(f, arc, y), numpy.interp(f, arc, z))



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


def secs_with_root(root):
    return [sec for sec in h.allsec() if get_root(sec) == root]

with open('morphology.txt', 'w') as f:
    for root in root_sections:
        f.write(json.dumps(morph_per_root(root)))

