"""Two-section heat-pipe exchanger model with an isothermal working fluid (+ optional internal resistance).

Hot-side (evaporator) section:  Q = C_h * eps_h * (T_h,in - T_e),   eps_h = 1 - exp(-UA_h/C_h)
Cold-side (condenser) section:  Q = C_c * eps_c * (T_cd - T_c,in), eps_c = 1 - exp(-UA_c/C_c)
Fluid temperature drop between sections: T_e - T_cd = Q * R_int  (R_int = 0 -> ideal heat pipe)
=> Q = (T_h,in - T_c,in) / (1/(C_h eps_h) + 1/(C_c eps_c) + R_int).
This is a standard series-conductance model, valid for a heat pipe operating within its limits.
UA values must come from a calibrated correlation or user input - none is built in.
"""
import math
from scipy.optimize import brentq
from . import psychrometrics as P

CP_LIQ_WATER = 4.186  # kJ/kg K


def eps_section(ua, c):
    return 1.0 - math.exp(-ua / c)


def solve_dry(t_hot, t_cold, c_hot, c_cold, ua_hot, ua_cold, r_int=0.0):
    eh, ec = eps_section(ua_hot, c_hot), eps_section(ua_cold, c_cold)
    q = (t_hot - t_cold) / (1 / (c_hot * eh) + 1 / (c_cold * ec) + r_int)
    return {"q_kw": q, "t_evap": t_hot - q / (c_hot * eh), "t_cond": t_cold + q / (c_cold * ec),
            "eps_hot_section": eh, "eps_cold_section": ec}


def solve_fixed_effectiveness(t_hot, t_cold, c_hot, c_cold, eps):
    return {"q_kw": eps * min(c_hot, c_cold) * (t_hot - t_cold), "t_evap": None, "t_cond": None}


def solve_wet(hot, cold, m_hot, m_cold, bf_hot, ua_cold, r_int=0.0):
    """Cooled (hot) stream may condense: apparatus-dew-point / bypass-factor method.

    The coil surface is assumed saturated at the evaporator fluid temperature T_e (ADP = T_e).
    Off-coil state lies on the straight line (in T-W) from inlet to ADP: x_off = x_adp + BF (x_in - x_adp).
    Heat to the refrigerant = m (h_in - h_off) - m_cond * cp_w * T_e (condensate leaves at T_e).
    The cold stream is dry. Root-find T_e so both sections carry the same Q.
    """
    c_cold = m_cold * P.cp_moist(cold["w"])
    ec = eps_section(ua_cold, c_cold)

    def hot_side(te):
        ws = P.w_sat(te, hot["p"])
        t_off = te + bf_hot * (hot["db"] - te)
        w_off = ws + bf_hot * (hot["w"] - ws) if ws < hot["w"] else hot["w"]
        h_off = P.enthalpy(t_off, w_off)
        m_c = m_hot * (hot["w"] - w_off)
        q = m_hot * (hot["h"] - h_off) - m_c * CP_LIQ_WATER * te
        return q, t_off, w_off, m_c

    def resid(te):
        q = hot_side(te)[0]
        return q - c_cold * ec * ((te - q * r_int) - cold["db"])

    te = brentq(resid, cold["db"], hot["db"], xtol=1e-10)
    q, t_off, w_off, m_c = hot_side(te)
    return {"q_kw": q, "t_evap": te, "t_cond": te - q * r_int, "t_off_hot": t_off, "w_off_hot": w_off,
            "condensate_kgs": m_c, "t_off_cold": cold["db"] + q / c_cold, "c_cold": c_cold}
