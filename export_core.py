# -*- coding: utf-8 -*-
import json, calc_core as c
r = c.solve(c.P_DEMO)
out = {'L':r['L'],'R':r['R'],'Td':r['Td'],'fsw':r['fsw'],'pm_max_rec':r['pm_max_rec']}
for name, s in r['schemes'].items():
    out[name] = {k:s[k] for k in ['feasible','Kp','Ki','fc','PM_req','PM_act','pm_max','phi','ph_gp','ph_dl','mag_ol','ov','ts'] if k in s and s[k] is not None}
print(json.dumps(out, ensure_ascii=False))
