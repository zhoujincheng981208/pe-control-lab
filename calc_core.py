# -*- coding: utf-8 -*-
"""
三相并网电流环 PI 整定内核（L 滤波 / LCL 等效）
=============================================================
场景：三相并网逆变器/PCS 的并网电流内环，工程 PI 整定。

对象建模（物理参数 -> 传函，不让用户填 G(s)）：
  功率级     Gp(s) = 1/(L*s + R)             逆变侧电感 + 等效电阻
  数字延迟   Gd(s) = 1/(1 + s*Td)            一阶近似，Td≈1.5*Tsw
  开环       L(s)  = C(s)*Gp(s)*Gd(s)
  PI         C(s)  = Kp + Ki/s

整定方法（复频域反解，在目标交越频率 wc 处幅值=1、相位=-180+PM）：
  ∠PI 需求   phi = -180 + PM + atan(wc*L/R) + atan(wc*Td)
  可行性     phi 必须落在 (-90°, 0°]；phi>0 表示 PM 超过该 fc 下最大可达值 -> 不可行
  比例       Kp = cos(phi)*sqrt(R²+(wc*L)²)*sqrt(1+(wc*Td)²)
  积分       Ki = Kp*wc*tan(-phi)

闭环三阶传函（用于时域数值仿真）：
  T(s) = (Kp*s + Ki) / [L*Td*s³ + (L+R*Td)*s² + (R+Kp)*s + Ki]
  双线性变换离散化 -> 递推求单位阶跃响应 -> 超调、调节时间(±2%)

LCL 模式：采用工程降阶——电容电流反馈有源阻尼后，逆变侧电流环等效对象
  取 L1（逆变侧电感），网侧 L2 与 Cf 折算为等效 R，明确标注为近似。

网页 index.html 的计算逻辑必须与本内核逐项一致（verify_web.js 校验）。
"""
import math


def _quad_roots(a, b, c):
    """实系数二次方程根，返回复数列表"""
    d = b*b - 4*a*c
    if d >= 0:
        sd = math.sqrt(d)
        return [(-b+sd)/(2*a)+0j, (-b-sd)/(2*a)+0j]
    sd = math.sqrt(-d)
    return [complex(-b/(2*a), sd/(2*a)), complex(-b/(2*a), -sd/(2*a))]


def _time_domain(den, z):
    """用主导二阶极点解析估算超调/调节时间。
    den=[a3,a2,a1,a0] 三阶分母；z=PI 零点(Ki/Kp)。
    闭环分母除以 (s+z) 近似降为二阶（PI 零点与慢极点近对消），
    取共轭主导极点的 ζ、ωn 算超调(2%)与调节时间(±2%)。"""
    a3, a2, a1, a0 = den
    # 多项式长除: 商 a3 s² + q1 s + q0, 余数应≈0
    q1 = a2 - a3*z
    q0 = a1 - q1*z
    roots = _quad_roots(a3, q1, q0)
    cp = [r for r in roots if r.imag > 1e-9]
    if not cp:  # 全实极点，无超调
        return 0.0, 4.0/min(abs(r.real) for r in roots if r.real != 0)/1000.0*1000.0
    r = cp[0]
    wn = abs(r)
    zeta = -r.real/wn
    zeta = min(max(zeta, 1e-4), 0.999)
    ov = math.exp(-math.pi*zeta/math.sqrt(1-zeta*zeta))*100.0
    ts = 4.0/(zeta*wn)*1000.0  # ms
    return ov, ts


def tune_one(L, R, Td, fc, PM_deg):
    """单方案整定。返回含 Kp/Ki/可行性/裕度/时域指标"""
    wc = 2*math.pi*fc
    ph_gp = math.degrees(math.atan2(wc*L, R))       # 对象相位(正的角度值)
    ph_dl = math.degrees(math.atan(wc*Td))          # 延迟相位(正的角度值)
    pm_max = 180.0 - ph_gp - ph_dl                  # Ki->0(纯P)时的最大可达PM
    phi = -180.0 + PM_deg + ph_gp + ph_dl           # 需要PI提供的相位(负值)

    feasible = (-90.0 < phi <= 0.0) and pm_max > 0
    if not feasible:
        return dict(feasible=False, Kp=None, Ki=None, pm_max=pm_max, phi=phi,
                    ph_gp=ph_gp, ph_dl=ph_dl, PM_req=PM_deg, fc=fc,
                    reason=('相位裕度要求超过该频率下最大值(需微分)' if phi > 0
                            else '目标频率过低/参数异常'),
                    ov=None, ts=None, PM_act=None)

    phir = math.radians(phi)
    Kp = math.cos(phir)*math.sqrt(R**2+(wc*L)**2)*math.sqrt(1+(wc*Td)**2)
    Ki = Kp*wc*math.tan(-phir)

    # 闭环三阶: T(s)=(Kp*s+Ki)/[L*Td*s3+(L+R*Td)*s2+(R+Kp)*s+Ki]
    den = [L*Td, L+R*Td, R+Kp, Ki]
    z = Ki/Kp                    # PI 零点
    ov, ts_ms = _time_domain(den, z)

    # 实际裕度：在算出的 wc 处回代校验
    mag_gp = 1/math.sqrt(R**2+(wc*L)**2)
    mag_dl = 1/math.sqrt(1+(wc*Td)**2)
    mag_pi = math.sqrt(Kp**2+(Ki/wc)**2)
    mag_ol = mag_pi*mag_gp*mag_dl
    phase_ol = -math.degrees(math.atan2(Ki/wc, Kp)) - ph_gp - ph_dl
    PM_act = 180 + phase_ol

    # 离散化系数(后向欧拉, Ts=1/fsw近似)供代码可用
    return dict(feasible=True, Kp=Kp, Ki=Ki, pm_max=pm_max, phi=phi,
                ph_gp=ph_gp, ph_dl=ph_dl, PM_req=PM_deg, fc=fc,
                mag_ol=mag_ol, PM_act=PM_act, ov=ov, ts=ts_ms,
                reason='')


def solve(p):
    """主入口：按推荐方案生成保守/推荐/激进三方案对比"""
    L   = p['L_uh']*1e-6
    R   = p['R_ohm']
    fsw = p['fsw_khz']*1e3
    Td  = p['delay_Tsw']/fsw
    if p['filter'] == 'LCL':
        # 工程降阶：电容电流反馈有源阻尼后，逆变侧电流环等效取 L1
        L = p['L1_uh']*1e-6
        R = R + p['R_esr_extra']
    fc0 = p['fc_hz']
    pm0 = p['PM_deg']

    schemes = {
        '保守': tune_one(L, R, Td, fc0*0.7, min(pm0+10, 75)),
        '推荐': tune_one(L, R, Td, fc0,     pm0),
        '激进': tune_one(L, R, Td, fc0*1.4, max(pm0-10, 20)),
    }
    return dict(L=L, R=R, Td=Td, fsw=fsw, schemes=schemes,
                pm_max_rec=schemes['推荐']['pm_max'])


P_DEMO = dict(filter='L', L_uh=250.0, L1_uh=250.0, R_ohm=0.05,
              R_esr_extra=0.02, fsw_khz=5.0, delay_Tsw=1.5,
              fc_hz=500.0, PM_deg=45.0)


if __name__ == '__main__':
    r = solve(P_DEMO)
    print(f"对象: L={r['L']*1e6:.0f}uH R={r['R']:.3f}Ω Td={r['Td']*1e6:.0f}us fsw={r['fsw']/1e3:.0f}kHz")
    print(f"推荐方案该频率下最大可达PM = {r['pm_max_rec']:.1f}°\n")
    for name, s in r['schemes'].items():
        print(f"--- {name} fc={s['fc']:.0f}Hz 目标PM={s['PM_req']:.0f}° ---")
        if not s['feasible']:
            print(f"  不可行: {s['reason']} (最大可达PM={s['pm_max']:.1f}°)")
        else:
            print(f"  Kp={s['Kp']:.4f}  Ki={s['Ki']:.1f}  实际PM={s['PM_act']:.1f}° "
                  f"超调={s['ov']:.1f}%  调节时间={s['ts']:.2f}ms")
            print(f"  幅值回校 |L(jwc)|={s['mag_ol']:.4f} (应≈1)")
