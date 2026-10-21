#!/usr/bin/env python3
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
from cshow import urdf

if __name__ == '__main__':
    n = int(sys.argv[1])
    if len(sys.argv) > 2:
        text = open(sys.argv[2]).read()
    else:
        path = subprocess.check_output(['rospack', 'find', 'clover_description'],
                                       universal_newlines=True).strip()
        text = urdf.run_xacro(os.path.join(path, 'urdf/clover/clover4.xacro'))
    print(urdf.postprocess(text, n, sys.argv[3] if len(sys.argv) > 3 else '1.13'))
