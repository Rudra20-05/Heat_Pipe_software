# Engineering model (v0.1.0-preliminary)

Units: SI internally (degC, Pa, kg/s, m3/s, kW). Conversions happen at the API boundary. 1 CFM = 0.3048^3/60 = 4.71947e-4 m3/s.

## Implemented equations
| Item | Equation / source | Status |
|---|---|---|
| Saturation pressure | Hyland-Wexler (ASHRAE Fundamentals 2017 Ch.1 eq. 5/6); checked: 100 C -> 101.4 kPa | implemented, tested |
| Site pressure | P = 101325 (1 - 2.25577e-5 z)^5.2559, -500..11000 m, else rejected; or user override | implemented, tested |
| Humidity ratio | W = 0.621945 Pv/(P - Pv) | implemented, tested |
| Wet-bulb | ASHRAE eq. 35/37 (water/ice branch); wet-bulb from W by root-finding | implemented, tested |
| Dew point | solve Pws(Td) = Pv | implemented, tested |
| Enthalpy | h = 1.006 T + W (2501 + 1.86 T) | implemented |
| Density | v = 0.287042 (T+273.15)(1+1.607858 W)/P ; rho_humid = (1+W)/v ; dry-air basis 1/v | implemented, tested |
| Flow | Actual basis: m_dry = Q / v. Standard basis: dry air 20 C, 101.325 kPa (rho_dry 1.2041), m_dry = Q_std * rho_dry,std; actual Q = m_dry v | implemented, tested |
| Face velocity | v = Q_actual / (fin length x fin height) | tested vs screenshot (1.44 / 1.02 m/s) |
| Capacity rate | C = m_dry (1.006 + 1.86 W) [kW/K] (consistent with the enthalpy equation, so dry energy balance closes exactly) | implemented |
| Dry heat-pipe model | Isothermal-fluid series model: Q = (Th,in - Tc,in)/(1/(Ch eps_h) + 1/(Cc eps_c) + R_int), eps = 1 - exp(-UA/C) | implemented; **needs UA** |
| UA | UA = k A_face N_rows (v/v_ref)^n, k and n user-entered or fitted | framework; no built-in values |
| Effectiveness (primary) | Q_cold / (C_min (Th,in - Tc,in)); hot- and cold-side dT effectiveness also reported; enthalpy effectiveness Q/(m_min (h_hot - h_cold)) only if h_hot > h_cold | implemented |
| Wet coil | ADP/bypass-factor: coil surface saturated at evaporator fluid temp T_e; off-coil on the T-W line from inlet to ADP with BF; Q_refrigerant = m(h_in - h_off) - m_cond cp_w T_e; root-find T_e so both sections carry the same Q | implemented; **BF must be entered**; preliminary |
| Condensation screening | definite if dry cooled-outlet <= inlet dew point; possible if T_e < inlet dew point | implemented |
| Pressure drop | Provider interface. `power_law_per_row`: dP = c0 N_rows (rho/1.2) v^n, c0 and n user/fitted | framework only |
| Core mass | Cu tube + Al fin plate (no collars/corrugation, no casing) when OD, pitches entered | implemented, partial |

## Not implemented (and why)
* **Published finned-tube pressure-drop correlation** (e.g. wavy-fin correlations): coefficients could not be verified against a source in this build, so none were typed from memory. Add as a provider once the coefficients and validity range are checked against the paper.
* **Resistance-network UA** (air-side h, fin efficiency, wall, internal boiling/condensing): replace `thermal_model.section_ua`.
* **Heat-pipe operating limits** (capillary/boiling/entrainment): only a coarse -30..90 C working-fluid warning exists.
* **Refrigerant charge, price**: need internal volumes, charge rule, price list.
* HHP/WRHP: rejected by validation.

## Direction of heat flow
The warmer inlet stream is always the "hot" (evaporator) stream. The cooling/heating selector only labels the scenario and triggers a warning if it disagrees with the inlet temperatures.
