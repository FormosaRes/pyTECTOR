# -*- coding: utf-8 -*-
"""Read an old TENSOR site file, invert it, and show both report forms:
what the interface displays, and what gets written to the file."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pytensor import core, invdir, report, tensorfile

P = (sys.argv[1] if len(sys.argv) > 1 else
     os.path.join(ROOT))

site = tensorfile.read_site(P)
folder = os.path.dirname(P)
info = os.path.join(folder, 'INFO1')
pass_no = 1
if os.path.exists(info):
    pass_no = tensorfile.read_info_lambda(info).get('pass_no', 1)

n, s = site.n, site.s
r = invdir.run(n, s, n_pass=pass_no)
res = core.summary(r['T'], n, s)
res_inv = core.summary(r['T_invdir'], n, s)
lam = r['lambda_trace'][-1]['lam_printed']

kw = dict(site_file=site.name, res=res, n_data=len(site), invdir=res_inv,
          lam_invdir=lam, pass_no=pass_no, site='01')

print('=' * 74)
print('INFO1 tab, what the interface shows')
print('=' * 74)
print(report.info1_text(compact=True, **kw))
print('=' * 74)
print('MOHR1 tab')
print('=' * 74)
print(report.mohr1_text(res, len(site), site='01'))
print('=' * 74)
print('the exported INFO1 file keeps the full layout (%d lines)'
      % report.info1_text(full_header=True, **kw).count('\n'))
