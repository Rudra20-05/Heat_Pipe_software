"""Coil geometry. Never invents pitches/diameters: missing data -> None + reason."""
import math

RHO_CU, RHO_AL = 8960.0, 2700.0  # kg/m3 (generic handbook values, configurable in future)


def face(eq, fin_length_override_mm=None):
    """Face dimensions for one stream's coil section."""
    warns, missing = [], []
    L = fin_length_override_mm or eq.get("fin_length_mm")
    H, tpr, pt = eq.get("fin_height_mm"), eq.get("tubes_per_row"), eq.get("transverse_pitch_mm")
    H_src = "entered" if H else None
    if H and tpr and pt and abs(H - tpr * pt) / H > 0.005:
        warns.append(f"Fin height {H} mm differs from tubes_per_row x transverse_pitch = {tpr * pt:.2f} mm (>0.5%).")
    if not H and tpr and pt:
        H, H_src = tpr * pt, "calculated from tubes/row x transverse pitch"
    if not L:
        missing.append("fin_length_mm")
    if not H:
        missing.append("fin_height_mm (or tubes_per_row and transverse_pitch_mm)")
    area = (L * H / 1e6) if (L and H) else None
    return {"fin_length_mm": L, "fin_height_mm": H, "fin_height_source": H_src, "face_area_m2": area,
            "missing": missing, "warnings": warns}


def circuits(eq):
    """Tube counts per coil section; per-circuit counts only if the split is integral."""
    rows, tpr, nc = eq.get("rows"), eq.get("tubes_per_row"), eq.get("circuits")
    out = {"tubes_per_coil_section": None, "tubes_per_circuit": None, "warnings": [], "missing": []}
    if rows and tpr:
        out["tubes_per_coil_section"] = rows * tpr
    else:
        out["missing"].append("rows / tubes_per_row")
    if rows and tpr and nc:
        if tpr % nc != 0:
            out["warnings"].append(
                f"{tpr} tubes per row cannot be divided evenly into {nc} circuits; tubes per circuit not determined. "
                "Confirm the circuiting definition with the manufacturer.")
        else:
            out["tubes_per_circuit"] = rows * tpr // nc
    return out


def core_mass(eq, fin_length_mm, fin_height_mm):
    """Bare core mass (copper tubes + aluminium fins) of ONE coil section.
    Excludes casing, headers/return bends, partition, refrigerant. Returns (kg|None, missing)."""
    need = {k: eq.get(k) for k in ("tube_od_mm", "tube_thk_mm", "longitudinal_pitch_mm", "fin_thk_mm",
                                   "fin_pitch_mm", "rows", "tubes_per_row")}
    miss = [k for k, v in need.items() if not v]
    if miss or not (fin_length_mm and fin_height_mm):
        return None, miss + ([] if fin_length_mm and fin_height_mm else ["face dimensions"])
    od, t = need["tube_od_mm"] / 1e3, need["tube_thk_mm"] / 1e3
    if t * 2 >= od:
        return None, ["tube_thk_mm too large for tube_od_mm"]
    n_tubes = need["rows"] * need["tubes_per_row"]
    m_tube = n_tubes * math.pi * (od - t) * t * (fin_length_mm / 1e3) * RHO_CU
    n_fins = fin_length_mm / need["fin_pitch_mm"]
    plate = (fin_height_mm / 1e3) * (need["rows"] * need["longitudinal_pitch_mm"] / 1e3) - n_tubes * math.pi / 4 * od ** 2
    m_fin = n_fins * plate * (need["fin_thk_mm"] / 1e3) * RHO_AL
    return m_tube + m_fin, []
