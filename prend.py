#!/usr/bin/env python
'''
Parallel Povray rendering script for Povray3.6
'''

import os,sys, re

def find_factor(n) :
    '''Find the closet factor of two from a number'''
    a = 1
    b = n
    diff = n - 1
    for i in range(1, n) :
        if (n % i) == 0 :
            c = n / i
            if abs(c - i) < diff :
                a = c
                b = i
                diff = abs(c - i)
                if(a == b) : break
    result = [a, b]
    result.sort()
    return result

def data_segment(width, height, nnodes) :
    '''Segment 2D image data, return a list of coordinate'''
    a, b = find_factor(nnodes)
    if height > width :
        hp = b
        wp = a
    else :
        hp = a
        wp = b
    height_piece = height / hp
    width_piece = width / wp
    if height_piece == 0 or width_piece == 0 :
        hp = nnodes
        wp = 0
        height_piece = height / hp
        width_piece = width

    result = []
    begin_x = 0
    begin_y = 0
    if (height % height_piece) != 0 :
        max_height = height_piece * (hp + 1)
    if (width % width_piece) != 0 :
        max_width = width_piece * (wp + 1)

    #print 'max_height = %d' % max_height
    #print 'max_width = %d' % max_width
    for y in range(height_piece, max_height + 1, height_piece) :
        if y > height: y = height
        for x in range(width_piece, max_width + 1, width_piece) :
            if x > width : x = width
            if begin_x < width and begin_y < height: 
                result.append((begin_x, begin_y, x, y))
            begin_x = x
            if begin_x >= width :
                begin_x = 0
        begin_y = y
        if begin_y >= height :
            begin_y = 0

    return result
        
def parse_povray_args(args) :
    '''Parse povrary arg and return width & height'''
    has_nodisplay = 0

    result = {'args' : []}
    for arg in args :
        if arg.startswith('+H') :
            result['height'] = int(arg[2:].strip())
            result['args'].append(arg)
        elif arg.startswith('+W') :
            result['width'] = int(arg[2:].strip())
            result['args'].append(arg)
        elif arg.startswith('+O') :
            result['out'] = arg[2:]
        elif arg.startswith('+SR') or arg.startswith('+ER') \
                or arg.startswith('+SC') or arg.startswith('+EC') \
                or arg.startswith('+D') :
            pass
        elif arg.startswith('-D') :
            have_nodisplay = 1
        else :
            result['args'].append(arg)
    if not has_nodisplay :
        result['args'].append('-D')
        
    return result

if __name__ == '__main__' :
    if len(sys.argv) <= 3 :
        print >>sys.stderr, 'Usage: %s <number of segment (nodes)> <povray args>' % sys.argv[0]
        sys.exit(1)

    sge_re = re.compile(r'Your\s+job\s+(?P<jid>[0-9]+)\s+\(.*', re.IGNORECASE | re.DOTALL)
    job_scr = '''\
#!/bin/sh
#$ -cwd
#$ -j y
#$ -o %(img_name)s.out
#$ -N %(img_name)s

povray %(pov_args)s +SC%(start_x)d +EC%(end_x)d +SR%(start_y)d +ER%(end_y)d
'''

    merger_scr = '''\
#!/bin/sh
#$ -cwd
#$ -j y 
#$ -o %(img_name)s_merge.out
#$ -N %(img_name)s_merge

~/work/prender/img-merge -w %(width)s -h %(height)s %(pattern)s %(output)s
'''

    nnodes = int(sys.argv[1])
    img_data = parse_povray_args(sys.argv[2:])
    pov_args = sys.argv[2:]
    pieces = data_segment(img_data['width'], img_data['height'], nnodes)
    jid_list = []
    for piece in pieces :
        # generate SGE qsub command
        qsub_stdin, qsub_stdout = os.popen2('qsub')
        name, ext = os.path.splitext(img_data['out'])
        output_name = name + '_%d_%d_%d_%d' % piece + ext
        args = {'img_name': output_name,
                'pov_args': ' '.join(img_data['args'] + ['+O' + output_name]),
                'start_x': piece[0], 'start_y': piece[1], 'end_x': piece[2], 'end_y': piece[3]}
        qsub_stdin.write(job_scr % args)
        qsub_stdin.close()
        output = qsub_stdout.readline()
        m = sge_re.match(output)
        if not m :
            raise IOError('Invalid output from SGE')
        jid_list.append(m.group('jid'))
        print output,
        qsub_stdout.close()

    output_path = os.path.join(os.getcwd(), img_data['out'])
    output_path = output_path.replace('/fs/home/somsak_sr/work/povray/', '')
    name, ext = os.path.splitext(output_path)
    output_path = name + '_*' + ext
    os.system('/usr/bin/firefox "http://tera.thaigrid.or.th/~somsak_sr/cgi-bin/img-merge.cgi?delay=5&mode=html&pattern=%s&width=%d&height=%d"' % (output_path, img_data['width'], img_data['height']))
