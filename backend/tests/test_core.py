"""Run: python -m unittest discover -s tests -v   (also collected by pytest).
Coefficients used in mechanics tests are ARBITRARY test values, not H&M data."""
import unittest, math
from app.services import psychrometrics as P, air_properties as A, geometry as G, heat_pipe_model as H
from app.services import pressure_drop as PD
from app.services.performance import calculate, CaseError
from app.configuration.defaults import demo_case, empty_case

P0 = 101325.0


def case_with(ua=0.5, n=0.6, **kw):
    c = demo_case(); c["models"]["thermal"].update(ua_coeff=ua, ua_exponent=n); c.update(kw); return c


class Psychro(unittest.TestCase):
    def test_pws_reference(self):  # ASHRAE table: 100 C -> 101.418 kPa ; 0 C -> 0.6112 kPa ; 30 C -> 4.246 kPa
        self.assertAlmostEqual(P.p_ws(100) / 1000, 101.418, delta=0.05)
        self.assertAlmostEqual(P.p_ws(0) / 1000, 0.6112, delta=0.001)
        self.assertAlmostEqual(P.p_ws(30) / 1000, 4.246, delta=0.005)

    def test_30C_50pct(self):
        s = P.state(30, P0, rh=50)
        self.assertAlmostEqual(s["w"] * 1000, 13.31, delta=0.01)
        self.assertAlmostEqual(s["h"], 64.21, delta=0.02)
        self.assertAlmostEqual(s["wb"], 22.0, delta=0.1)
        self.assertAlmostEqual(s["dp"], 18.45, delta=0.05)

    def test_roundtrip_wb_rh(self):
        for t, rh in [(5, 90), (25, 55), (40, 20), (-10, 60)]:
            s = P.state(t, P0, rh=rh)
            s2 = P.state(t, P0, wb=s["wb"])
            self.assertAlmostEqual(s2["rh"], rh, delta=0.01)

    def test_limits(self):
        for bad in (-1, 101):
            with self.assertRaises(P.StateError): P.state(25, P0, rh=bad)
        with self.assertRaises(P.StateError): P.state(25, P0, wb=26)
        with self.assertRaises(P.StateError): P.state(25, P0, w=0.1)  # supersaturated
        self.assertAlmostEqual(P.state(25, P0, rh=100)["dp"], 25, delta=1e-6)

    def test_altitude(self):
        self.assertAlmostEqual(P.p_atm_altitude(0), 101325)
        self.assertAlmostEqual(P.p_atm_altitude(1000), 89875, delta=10)
        with self.assertRaises(P.StateError): P.p_atm_altitude(20000)

    def test_density(self):  # dry air 20 C 101325 Pa = 1.204
        self.assertAlmostEqual(P.state(20, P0, w=0.0)["rho"], 1.204, delta=0.002)
        self.assertAlmostEqual(A.RHO_DRY_STD, 1.2041, delta=0.001)

    def test_cfm(self):
        self.assertAlmostEqual(A.to_m3s(2118.88, "cfm"), 1.0, delta=1e-4)
        self.assertAlmostEqual(A.to_m3s(3000, "cfm"), 1.41584, delta=1e-4)
        self.assertAlmostEqual(A.to_m3s(3600, "m3/h"), 1.0)

    def test_standard_vs_actual_basis(self):
        s = P.state(35, P0, rh=40)
        a = A.flow(1000, "cfm", "actual", s); b = A.flow(1000, "cfm", "standard", s)
        self.assertLess(a["m_dry_kgs"], b["m_dry_kgs"])  # warm air is less dense
        self.assertAlmostEqual(b["q_actual_m3s"] * s["rho_dry"], b["m_dry_kgs"], places=9)


class Geometry(unittest.TestCase):
    def test_face_area_matches_screenshot(self):
        g = G.face(demo_case()["equipment"]); self.assertAlmostEqual(g["face_area_m2"], 0.984, delta=0.0005)

    def test_catalogue_example_geometry(self):  # catalogue p.7: 1085 x 857.25 mm -> 0.93 m2
        self.assertAlmostEqual(1085 * 857.25 / 1e6, 0.93, delta=0.001)

    def test_uneven_circuits_not_invented(self):
        self.assertIsNone(G.circuits(demo_case()["equipment"])["tubes_per_circuit"])
        e = demo_case()["equipment"]; e["tubes_per_row"] = 30
        self.assertEqual(G.circuits(e)["tubes_per_circuit"], 4 * 30 // 2)

    def test_pitch_height_mismatch_warns(self):
        e = demo_case()["equipment"]; e["transverse_pitch_mm"] = 30
        self.assertTrue(G.face(e)["warnings"])


class Thermal(unittest.TestCase):
    def test_energy_balance_and_direction(self):
        r = calculate(case_with()); p = r["performance"]
        self.assertEqual(p["hot_stream"], "supply")
        self.assertLess(abs(p["energy_balance_error_pct"]), 1e-8)
        s, e = r["streams"]["supply"], r["streams"]["exhaust"]
        self.assertLess(s["outlet"]["db"], s["inlet"]["db"]); self.assertGreater(e["outlet"]["db"], e["inlet"]["db"])
        self.assertAlmostEqual(s["outlet"]["w"], s["inlet"]["w"], places=12)  # no moisture change (dry)
        self.assertTrue(0 < p["effectiveness_pct"] <= 100)

    def test_direction_reverses_with_inlets(self):
        c = case_with(); c["supply"].update(db=5, rh=80); c["exhaust"].update(db=22, input_mode="db_rh", rh=40, wb=None)
        r = calculate(c); self.assertEqual(r["performance"]["hot_stream"], "exhaust")
        self.assertGreater(r["streams"]["supply"]["outlet"]["db"], 5)
        self.assertLess(abs(r["performance"]["energy_balance_error_pct"]), 1e-8)

    def test_unequal_flows_effectiveness_range(self):
        c = case_with(ua=5.0); c["supply"]["flow"] = 8000
        p = calculate(c)["performance"]; self.assertTrue(0 < p["effectiveness_pct"] < 100)

    def test_equal_inlet_temperatures(self):
        c = case_with(); c["exhaust"].update(db=30)
        r = calculate(c); self.assertEqual(r["performance"]["q_kw"], 0.0)
        self.assertNotIn("effectiveness_pct", r["performance"])

    def test_missing_thermal_parameters_no_fake_results(self):
        r = calculate(empty_case())
        self.assertEqual(r["status"], "partial"); self.assertIsNone(r["streams"]["supply"]["outlet"])
        self.assertNotIn("q_kw", r["performance"])

    def test_baseline_demo_calculation(self):
        r = calculate(demo_case())
        self.assertEqual(r["status"], "ok")
        self.assertIsNotNone(r["performance"].get("q_kw"))
        self.assertGreater(r["performance"]["q_kw"], 0)
        self.assertGreater(r["performance"]["effectiveness_pct"], 35.0)

    def test_effectiveness_override(self):
        c = demo_case(); c["models"]["thermal"]["effectiveness_override"] = 0.5
        r = calculate(c); self.assertAlmostEqual(r["performance"]["effectiveness_pct"], 50.0, places=6)

    def test_series_model_limits(self):  # infinite UA -> eps = Cmin/Cmin... Q -> dT/(1/Ch+1/Cc)
        s = H.solve_dry(30, 10, 2.0, 1.0, 1e9, 1e9)
        self.assertAlmostEqual(s["q_kw"], 20 / (1 / 2 + 1), delta=1e-6)

    def test_invalid_inputs(self):
        for mut in (lambda c: c["supply"].update(flow=-5), lambda c: c["equipment"].update(configuration="WRHP"),
                    lambda c: c["supply"].update(rh=120), lambda c: c["equipment"].update(fin_length_mm=0),
                    lambda c: c["equipment"].update(refrigerant="R410A")):
            c = demo_case(); mut(c)
            with self.assertRaises(CaseError): calculate(c)

    def test_wet_coil_required_without_bypass_factor(self):
        c = case_with(ua=50.0); c["supply"].update(db=35, rh=70); c["exhaust"].update(db=5, wb=3)
        c["models"]["thermal"]["wet_bypass_factor"] = None
        r = calculate(c)
        self.assertEqual(r["performance"]["condensate"]["status"], "wet_coil_required")
        self.assertIsNone(r["streams"]["supply"]["outlet"])

    def test_wet_coil_with_bypass_factor_conserves_energy(self):
        c = case_with(ua=50.0); c["supply"].update(db=35, rh=70); c["exhaust"].update(db=5, wb=3)
        c["models"]["thermal"]["wet_bypass_factor"] = 0.3
        r = calculate(c); p = r["performance"]
        self.assertGreater(p["condensate"]["rate_lph"], 0)
        self.assertLess(abs(p["energy_balance_error_pct"]), 1e-4)
        self.assertLessEqual(r["streams"]["supply"]["outlet"]["rh"], 100.0001)


class Pressure(unittest.TestCase):
    def test_unavailable_by_default(self):
        r = calculate(empty_case()); self.assertEqual(r["pressure_drop"]["supply"]["status"], "unavailable")

    def test_power_law_scaling(self):
        cfg = {"provider": "power_law_per_row", "coeff_pa_per_row": 10.0, "exponent": 1.8}
        a = PD.compute(cfg, 4, 1.0, 1.2, {})["value_pa"]; b = PD.compute(cfg, 4, 2.0, 1.2, {})["value_pa"]
        self.assertAlmostEqual(a, 40.0); self.assertAlmostEqual(b / a, 2 ** 1.8)
        self.assertAlmostEqual(PD.compute(cfg, 8, 1.0, 1.2, {})["value_pa"], 80.0)

    def test_bad_coefficients_rejected(self):
        self.assertEqual(PD.compute({"provider": "power_law_per_row", "coeff_pa_per_row": -1, "exponent": 1}, 4, 1, 1.2, {})["status"], "unavailable")

    def test_extrapolation_flag(self):
        cfg = {"provider": "power_law_per_row", "coeff_pa_per_row": 10, "exponent": 1.8, "valid_velocity_range": [1.5, 3]}
        self.assertTrue(PD.compute(cfg, 4, 1.0, 1.2, {})["extrapolated"])


class OldSoftwareDiscrepancies(unittest.TestCase):
    """Documents where the old software's printed values do NOT reproduce (see docs/VALIDATION.md)."""
    def test_supply_enthalpy_and_wb(self):
        s = P.state(30, P0, rh=50)
        self.assertGreater(abs(s["h"] - 66.2), 1.5)     # old: 66.2, recomputed 64.21
        self.assertGreater(abs(s["wb"] - 22.53), 0.4)   # old: 22.53, recomputed ~22.0

    def test_exhaust_enthalpy(self):
        e = P.state(25, P0, wb=18.7)
        self.assertAlmostEqual(e["w"] * 1000, 10.91, delta=0.05)   # humidity ratio agrees
        self.assertAlmostEqual(e["rh"], 55.0, delta=0.2)          # RH agrees
        self.assertGreater(abs(e["h"] - 64.21), 10)              # old 64.21 vs recomputed 52.9

    def test_catalogue_page7_inlets_reproduce(self):
        s = P.state(33.8, P0, wb=25.8)
        self.assertAlmostEqual(s["w"] * 1000, 17.68, delta=0.05); self.assertAlmostEqual(s["h"], 79.33, delta=0.05)
        self.assertAlmostEqual(s["rh"], 53.19, delta=0.1)


if __name__ == "__main__":
    unittest.main()
