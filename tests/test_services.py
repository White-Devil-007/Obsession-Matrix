import unittest
import os
import tempfile
from backend.database import Database
from backend.services import AppService

class TestServices(unittest.TestCase):
    def setUp(self):
        self.tmp_fd, self.tmp_path = tempfile.mkstemp(suffix=".db")
        self.db = Database(self.tmp_path)
        self.service = AppService(self.db)

    def tearDown(self):
        os.close(self.tmp_fd)
        if os.path.exists(self.tmp_path):
            os.remove(self.tmp_path)

    def test_interest_hierarchy(self):
        root = self.service.create_interest("Cybersecurity")
        sub = self.service.create_interest("Web Security", parent_identifier="Cybersecurity")
        subsub = self.service.create_interest("XSS", parent_identifier=sub["id"])

        path_str = self.service.get_path_string(subsub["id"])
        self.assertEqual(path_str, "Cybersecurity → Web Security → XSS")

        tree = self.service.get_interest_tree()
        self.assertEqual(len(tree), 1)
        self.assertEqual(tree[0]["interest"]["name"], "Cybersecurity")
        self.assertEqual(len(tree[0]["children"]), 1)
        self.assertEqual(tree[0]["children"][0]["interest"]["name"], "Web Security")
        self.assertEqual(tree[0]["children"][0]["children"][0]["interest"]["name"], "XSS")

    def test_current_obsession(self):
        root = self.service.create_interest("Quantum Computing")
        sub = self.service.create_interest("Qubits", parent_identifier="Quantum Computing")

        self.service.set_current_obsession("Qubits")
        obsession = self.service.get_current_obsession()
        self.assertIsNotNone(obsession)
        self.assertEqual(obsession["name"], "Qubits")
        self.assertEqual(obsession["path"], "Quantum Computing → Qubits")

        self.service.clear_current_obsession()
        self.assertIsNone(self.service.get_current_obsession())

    def test_manual_progress_and_tasks(self):
        interest = self.service.create_interest("Rust")
        
        # Manual progress update
        updated = self.service.update_progress("Rust", "Phase 2: Async/Await")
        self.assertEqual(updated["custom_progress"], "Phase 2: Async/Await")

        # Tasks
        t1 = self.service.create_task("Rust", "Read Tokio docs")
        t2 = self.service.create_task("Rust", "Build mini HTTP server")
        self.assertEqual(t1["status"], "not_started")

        # Status flip
        u_t1 = self.service.update_task_status(t1["id"], "in_progress")
        self.assertEqual(u_t1["status"], "in_progress")

        done_t1 = self.service.update_task_status(t1["id"], "done")
        self.assertEqual(done_t1["status"], "done")

        # Reversibility
        rev_t1 = self.service.update_task_status(t1["id"], "not_started")
        self.assertEqual(rev_t1["status"], "not_started")

        summary = self.service.get_dashboard_summary()
        self.assertEqual(summary["task_counts"]["total"], 2)
        self.assertEqual(summary["task_counts"]["not_started"], 2)

if __name__ == "__main__":
    unittest.main()
