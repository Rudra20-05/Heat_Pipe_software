"""Automated API tests for the Vertical Heat Pipe Selection API.
Covers:
- Schema validation (422) and field-level error messages
- Successful demo calculation (geometry, face velocity, psychrometrics, unavailable tags)
- No fake results on failure or missing data
- CSV upload limits (413) and error reporting / guarded fit
- PDF and CSV report generation
- Derived psychrometrics, sweep, and project persistence
"""
import io
import unittest
from fastapi.testclient import TestClient
from app.main import app
from app.configuration.defaults import demo_case, empty_case


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_health(self):
        res = self.client.get("/api/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "ok")
        self.assertIn("model_version", data)

    def test_configuration(self):
        res = self.client.get("/api/configuration")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("demo_case", data)
        self.assertIn("catalogue", data)
        self.assertIn("discrepancies", data)
        self.assertIn("feature_status", data)

    # 1. Schema validation (422)
    def test_schema_validation_empty_body(self):
        res = self.client.post("/api/calculate", json={})
        self.assertEqual(res.status_code, 422)
        errors = res.json().get("detail", {}).get("errors", [])
        self.assertTrue(len(errors) > 0)
        fields = [e["field"] for e in errors]
        self.assertIn("equipment", fields)
        self.assertIn("supply", fields)

    def test_schema_validation_extra_fields_forbidden(self):
        case = demo_case()
        case["unrecognized_field"] = "bad"
        res = self.client.post("/api/calculate", json=case)
        self.assertEqual(res.status_code, 422)
        errors = res.json().get("detail", {}).get("errors", [])
        self.assertTrue(any("unrecognized_field" in e.get("field", "") for e in errors))

    def test_schema_validation_invalid_scenario(self):
        case = demo_case()
        case["scenario"] = "invalid_scenario"
        res = self.client.post("/api/calculate", json=case)
        self.assertEqual(res.status_code, 422)
        errors = res.json().get("detail", {}).get("errors", [])
        self.assertTrue(any("scenario" in e.get("field", "") for e in errors))

    def test_case_validation_negative_rows(self):
        case = demo_case()
        case["equipment"]["rows"] = -2
        res = self.client.post("/api/calculate", json=case)
        self.assertEqual(res.status_code, 422)
        errors = res.json().get("detail", {}).get("errors", [])
        self.assertTrue(any("equipment.rows" in e.get("field", "") for e in errors))

    def test_case_validation_unsupported_configuration(self):
        case = demo_case()
        case["equipment"]["configuration"] = "WRHP"
        res = self.client.post("/api/calculate", json=case)
        self.assertEqual(res.status_code, 422)
        errors = res.json().get("detail", {}).get("errors", [])
        self.assertTrue(any("equipment.configuration" in e.get("field", "") for e in errors))

    def test_case_validation_invalid_rh(self):
        case = demo_case()
        case["supply"]["rh"] = 120.0
        res = self.client.post("/api/calculate", json=case)
        self.assertEqual(res.status_code, 422)
        errors = res.json().get("detail", {}).get("errors", [])
        self.assertTrue(any("supply.rh" in e.get("field", "") for e in errors))

    def test_case_validation_wb_higher_than_db(self):
        case = demo_case()
        case["supply"]["input_mode"] = "db_wb"
        case["supply"]["db"] = 20.0
        case["supply"]["wb"] = 25.0
        res = self.client.post("/api/calculate", json=case)
        self.assertEqual(res.status_code, 422)
        errors = res.json().get("detail", {}).get("errors", [])
        self.assertTrue(any("supply" in e.get("field", "") for e in errors))

    # 2. Successful demo calculation
    def test_successful_demo_calculation(self):
        case = demo_case()
        res = self.client.post("/api/calculate", json=case)
        self.assertEqual(res.status_code, 200)
        data = res.json()

        # Overall status is ok because baseline models are configured
        self.assertEqual(data["status"], "ok")

        # Geometry checks vs screenshot
        geom = data["geometry"]
        self.assertEqual(geom["rows"], 4)
        self.assertEqual(geom["tubes_per_row"], 31)
        self.assertEqual(geom["parallel_circuits"], 2)
        self.assertIsNone(geom["tubes_per_circuit"])  # 31 / 2 is not integral; not invented

        streams = data["streams"]
        supply = streams["supply"]
        exhaust = streams["exhaust"]

        # Face area ~0.984 m2
        self.assertAlmostEqual(supply["geometry"]["face_area_m2"], 0.98425, delta=0.001)
        self.assertAlmostEqual(exhaust["geometry"]["face_area_m2"], 0.98425, delta=0.001)

        # Face velocity ~1.44 m/s (supply) and ~1.02 m/s (exhaust)
        self.assertAlmostEqual(supply["flow"]["face_velocity_ms"], 1.4385, delta=0.01)
        self.assertAlmostEqual(exhaust["flow"]["face_velocity_ms"], 1.016, delta=0.01)

        # Psychrometrics: supply 30 C / 50% RH
        self.assertAlmostEqual(supply["inlet"]["db"], 30.0)
        self.assertAlmostEqual(supply["inlet"]["w"] * 1000, 13.31, delta=0.02)
        self.assertAlmostEqual(supply["inlet"]["wb"], 22.0, delta=0.1)
        self.assertAlmostEqual(supply["inlet"]["h"], 64.21, delta=0.05)

        # Exhaust 25 C / WB 18.7 C
        self.assertAlmostEqual(exhaust["inlet"]["db"], 25.0)
        self.assertAlmostEqual(exhaust["inlet"]["rh"], 55.05, delta=0.1)
        self.assertAlmostEqual(exhaust["inlet"]["h"], 52.91, delta=0.05)

        # Thermal performance calculated
        perf = data["performance"]
        self.assertIsNotNone(perf.get("q_kw"))
        self.assertGreater(perf["q_kw"], 0)
        self.assertIsNotNone(perf.get("effectiveness_pct"))
        self.assertGreater(perf["effectiveness_pct"], 35.0)
        self.assertEqual(perf["hot_stream"], "supply")
        self.assertEqual(perf["cold_stream"], "exhaust")

        # Pressure drop calculated
        dp = data["pressure_drop"]
        self.assertIn(dp["supply"]["status"], ("preliminary", "baseline"))
        self.assertGreater(dp["supply"]["value_pa"], 0)
        self.assertGreater(dp["exhaust"]["value_pa"], 0)

        # Outlets calculated
        self.assertIsNotNone(supply["outlet"])
        self.assertIsNotNone(exhaust["outlet"])

    def test_missing_parameters_returns_unavailable(self):
        case = empty_case()
        res = self.client.post("/api/calculate", json=case)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "partial")
        perf = data["performance"]
        self.assertIsNone(perf.get("q_kw"))
        self.assertIsNone(perf.get("effectiveness_pct"))
        dp = data["pressure_drop"]
        self.assertEqual(dp["supply"]["status"], "unavailable")
        unavail_names = [u["output"] for u in data["unavailable"]]
        self.assertIn("thermal performance", unavail_names)
        self.assertIn("supply.pressure_drop", unavail_names)

    # 3. No fake results on failure
    def test_no_fake_results_on_failure(self):
        case = demo_case()
        case["supply"]["flow"] = -500.0  # Invalid negative flow
        res = self.client.post("/api/calculate", json=case)
        self.assertEqual(res.status_code, 422)
        # Verify no 200 result or partial body is returned
        body = res.json()
        self.assertNotIn("performance", body)
        self.assertNotIn("streams", body)
        self.assertIn("detail", body)

    # 4. CSV upload limits and error reporting
    def test_csv_upload_size_limit(self):
        oversized = b"x" * (2_000_000 + 10)
        files = {"file": ("huge.csv", io.BytesIO(oversized), "text/csv")}
        res = self.client.post("/api/calibration/validate-dataset", files=files)
        self.assertEqual(res.status_code, 413)

    def test_csv_malformed_text(self):
        files = {"file": ("bad.csv", io.BytesIO(b"\x80\x81\x82invalid-utf8"), "text/csv")}
        res = self.client.post("/api/calibration/validate-dataset", files=files)
        self.assertEqual(res.status_code, 422)

    def test_csv_template_validation(self):
        with open("sample_data/reference_template.csv", "rb") as f:
            content = f.read()
        files = {"file": ("reference_template.csv", io.BytesIO(content), "text/csv")}
        res = self.client.post("/api/calibration/validate-dataset", files=files)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["rows"], 1)
        self.assertTrue(data["ok"])  # WRHP row is an info issue, not fatal error

    def test_guarded_fit_refuses_insufficient_data(self):
        with open("sample_data/reference_template.csv", "rb") as f:
            content = f.read()
        files = {"file": ("reference_template.csv", io.BytesIO(content), "text/csv")}
        res = self.client.post("/api/calibration/fit", files=files)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("status"), "refused")
        self.assertIn("Need >= 6 VHP rows", data.get("reason", ""))

    def test_evaluate_endpoint_handles_skipped_cases(self):
        with open("sample_data/reference_template.csv", "rb") as f:
            content = f.read()
        files = {"file": ("reference_template.csv", io.BytesIO(content), "text/csv")}
        res = self.client.post("/api/calibration/evaluate", files=files, data={"models": "{}", "split": ""})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("skipped", data)
        self.assertTrue(any(s["case_id"] == "EX-WRHP-P7" for s in data["skipped"]))

    # 5. PDF and CSV report generation
    def test_report_pdf_generation(self):
        case = demo_case()
        res = self.client.post("/api/report/pdf", json=case)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers.get("content-type"), "application/pdf")
        self.assertIn("heat_pipe_report.pdf", res.headers.get("content-disposition", ""))
        self.assertTrue(res.content.startswith(b"%PDF"))

    def test_report_csv_generation(self):
        case = demo_case()
        res = self.client.post("/api/report/csv", json=case)
        self.assertEqual(res.status_code, 200)
        self.assertTrue("text/csv" in res.headers.get("content-type", ""))
        self.assertIn("heat_pipe_results.csv", res.headers.get("content-disposition", ""))
        text = res.content.decode("utf-8")
        self.assertIn("section,item,supply,exhaust,unit", text)
        self.assertIn("geometry,Face area,0.9842,0.9842,m2", text)

    def test_report_pdf_invalid_case_fails(self):
        case = demo_case()
        case["equipment"]["rows"] = 0
        res = self.client.post("/api/report/pdf", json=case)
        self.assertEqual(res.status_code, 422)

    # 6. Psychrometrics and sweep
    def test_psychrometrics_endpoint(self):
        res = self.client.post("/api/psychrometrics", json={"db": 30.0, "mode": "db_rh", "rh": 50.0, "altitude_m": 0})
        self.assertEqual(res.status_code, 200)
        state = res.json()["state"]
        self.assertAlmostEqual(state["w"] * 1000, 13.31, delta=0.02)
        self.assertAlmostEqual(state["h"], 64.21, delta=0.05)

    def test_psychrometrics_invalid_wb(self):
        res = self.client.post("/api/psychrometrics", json={"db": 20.0, "mode": "db_wb", "wb": 25.0, "altitude_m": 0})
        self.assertEqual(res.status_code, 422)

    def test_sweep_endpoint(self):
        case = demo_case()
        res = self.client.post("/api/sweep", json={"case": case, "factors": [0.8, 1.0, 1.2]})
        self.assertEqual(res.status_code, 200)
        pts = res.json()["points"]
        self.assertEqual(len(pts), 3)
        self.assertAlmostEqual(pts[0]["factor"], 0.8)
        self.assertAlmostEqual(pts[0]["supply_flow"], 3000 * 0.8)

    def test_sweep_non_positive_factor(self):
        case = demo_case()
        res = self.client.post("/api/sweep", json={"case": case, "factors": [-0.5, 1.0]})
        self.assertEqual(res.status_code, 422)

    # 7. Project persistence
    def test_project_lifecycle(self):
        case = demo_case()
        save_res = self.client.post("/api/projects", json=case)
        self.assertEqual(save_res.status_code, 200)
        pid = save_res.json()["project_id"]
        self.assertTrue(len(pid) > 0)

        list_res = self.client.get("/api/projects")
        self.assertEqual(list_res.status_code, 200)
        self.assertIn(pid, list_res.json()["projects"])

        get_res = self.client.get(f"/api/projects/{pid}")
        self.assertEqual(get_res.status_code, 200)
        retrieved = get_res.json()
        self.assertEqual(retrieved["equipment"]["configuration"], "VHP")

        not_found = self.client.get("/api/projects/nonexistent999")
        self.assertEqual(not_found.status_code, 404)


if __name__ == "__main__":
    unittest.main()
