# -*- coding: utf-8 -*-
import json, calc_core as c
r = c.solve(c.P_DEMO)
out = {'L':r['L'],'R':r['R'],'Td':r['Td'],'fsw':r['fsw'],'pm_max_rec':r['pm_max_rec']}
for name, s in r['schemes'].items():
    out[name] = {k:s[k] for k in ['feasible','Kp','Ki','fc','PM_req','PM_act','pm_max','phi','ph_gp','ph_dl','mag_ol','ov','ts'] if k in s and s[k] is not None}
# LCL 三元件谐振量单独导出（网页切到 LCL 标签用 DEMO_LCL 校验）
rl = c.solve(c.P_DEMO_LCL)
out['LCL'] = {k:rl['lcl'][k] for k in ['Leq','fres','Zres','zeta','ratio','chk_range','chk_sep','chk_damp']}
for name, s in rl['schemes'].items():
    out['LCL_'+name] = {k:s[k] for k in ['feasible','Kp','Ki','fc','PM_req','PM_act','pm_max','phi','ph_gp','ph_dl','mag_ol','ov','ts'] if k in s and s[k] is not None}
print(json.dumps(out, ensure_ascii=False))
