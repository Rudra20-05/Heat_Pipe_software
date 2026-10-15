"""Condensation screening and condensate rate."""


def screen(t_out_hot_dry, dp_hot_in, t_evap):
    """Return 'definite', 'possible' or 'none' for the cooled stream (dry-model screening)."""
    if t_out_hot_dry <= dp_hot_in + 1e-9:
        return "definite"
    if t_evap is not None and t_evap < dp_hot_in:
        return "possible"
    return "none"


def litres_per_hour(kg_per_s):
    return kg_per_s * 3600.0  # 1 kg water ~ 1 L
