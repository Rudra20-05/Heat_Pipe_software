# Assumptions and missing manufacturer parameters

## Assumptions
1. Both coil sections have N rows deep (the "rows" input). Same fin height for both; fin length may differ per stream.
2. Total tubes shown as `2 x rows x tubes_per_row` is a labelled assumption; the circuiting definition is unconfirmed, so tubes per circuit is only reported when tubes_per_row divides evenly by the circuit count (not true for the demo: 31 / 2).
3. Working fluid isothermal between sections unless an internal resistance is entered.
4. Air is treated as an ideal gas mixture; constant cp for the dry thermal model; no frost modelling.
5. Wet-coil bypass factor is held constant (it normally depends on airflow and surface condition).
6. Tube OD and pitches are NEVER inferred from the nominal 1/2 in size. Fin height 984.25 mm is taken as printed in the screenshot.
7. Demo inputs are transcribed from the screenshot; the old software's printed psychrometric values are treated as reference values only.

## Manufacturer data needed to reach the target accuracy
* Actual tube OD, wall, longitudinal and transverse pitches for each model; confirm meaning of "32 x 28 mm".
* Fin geometry: wave height/pitch, ripple-edge details, collar height, hydrophobic coating effect.
* Circuiting: tubes per circuit, header layout, whether tubes-per-row covers both sections.
* Measured performance (outlet temperatures, effectiveness, dP for both streams) over several rows, fin pitches and face velocities - at least 6 VHP train points plus held-out validation points per configuration.
* Wet-coil data (condensate, off-coil RH) and operating limits of the heat pipe.
* Charge rule per circuit, internal volumes, casing/partition mass data, price list.
