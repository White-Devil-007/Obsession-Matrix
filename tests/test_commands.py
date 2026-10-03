import unittest
import os
import tempfile
from backend.database import Database
from backend.services import AppService
from backend.command_parser import CommandParser

class TestCommandParser(unittest.TestCase):
    def setUp(self):
        self.tmp_fd, self.tmp_path = tempfile.mkstemp(suffix=".db")
        self.db = Database(self.tmp_path)
        self.service = AppService(self.db)
        self.parser = CommandParser(self.service)

    def tearDown(self):
        os.close(self.tmp_fd)
        if os.path.exists(self.tmp_path):
            os.remove(self.tmp_path)

    def test_help_command(self):
        res = self.parser.parse_and_execute("help")
        self.assertTrue(res["success"])
        self.assertIn("AVAILABLE TERMINAL COMMANDS", res["message"])

    def test_add_interest_and_nested(self):
        res1 = self.parser.parse_and_execute('add interest "Cybersecurity"')
        self.assertTrue(res1["success"])

        res2 = self.parser.parse_and_execute('add interest "Web Security" under "Cybersecurity"')
        self.assertTrue(res2["success"])
        self.assertIn("Cybersecurity → Web Security", res2["message"])

    def test_task_lifecycle_commands(self):
        self.parser.parse_and_execute('add interest "Rust"')
        
        # Add task
        res_t = self.parser.parse_and_execute('add task "Rust" "Learn Memory Ownership"')
        self.assertTrue(res_t["success"])
        task_id = res_t["data"]["id"]

        # Set status in_progress
        res_p = self.parser.parse_and_execute(f'task status {task_id} in_progress')
        self.assertTrue(res_p["success"])
        self.assertEqual(res_p["data"]["status"], "in_progress")

        # Mark done
        res_d = self.parser.parse_and_execute(f'done {task_id}')
        self.assertTrue(res_d["success"])
        self.assertEqual(res_d["data"]["status"], "done")

    def test_progress_and_current(self):
        self.parser.parse_and_execute('add interest "Blender"')
        
        # Navigate into the topic (sets active_interest_id)
        self.parser.current_view = "interests"
        self.parser.parse_and_execute('cd Blender')

        # Add titled progress log
        res_p = self.parser.parse_and_execute('progress add "Phase 1: Mesh Modeling" "Completed basic mesh tools"')
        self.assertTrue(res_p["success"])
        self.assertIn("Phase 1", res_p["message"])

        # View progress list
        res_v = self.parser.parse_and_execute('progress view')
        self.assertTrue(res_v["success"])
        self.assertIn("Phase 1", res_v["message"])

        # Go back to main menu
        self.parser.parse_and_execute('cd ..')
        self.parser.parse_and_execute('cd ..')

        res_c = self.parser.parse_and_execute('current set "Blender"')
        self.assertTrue(res_c["success"])
        
        res_c_view = self.parser.parse_and_execute('current')
        self.assertTrue(res_c_view["success"])
        self.assertIn("Blender", res_c_view["message"])

    def test_settings_navigation_and_commands(self):
        # Enter settings
        res1 = self.parser.parse_and_execute('settings')
        self.assertTrue(res1["success"])
        self.assertEqual(res1["prompt"], "C:\\OBSESSION_MATRIX\\settings>")

        # List settings via ls
        res_ls = self.parser.parse_and_execute('ls')
        self.assertTrue(res_ls["success"])
        self.assertIn("APPLICATION SETTINGS", res_ls["message"])

        # Toggle paste_restriction
        res_t = self.parser.parse_and_execute('toggle paste_restriction')
        self.assertTrue(res_t["success"])

        # Set theme
        res_s = self.parser.parse_and_execute('set theme matrix-green')
        self.assertTrue(res_s["success"])
        self.assertEqual(self.service.get_all_settings()["theme"], "matrix-green")

        # Return back to main menu
        res_b = self.parser.parse_and_execute('cd ..')
        self.assertTrue(res_b["success"])
        self.assertEqual(res_b["prompt"], "C:\\OBSESSION_MATRIX>")

    def test_typo_suggestion(self):
        res = self.parser.parse_and_execute('intrests')
        self.assertFalse(res["success"])
        self.assertIn('Did you mean \'interests\'?', res["message"])

    def test_delete_commands(self):
        # 1. Create topic & subtopic & task
        self.parser.parse_and_execute('interests')
        self.parser.parse_and_execute('mkdir Cybersecurity')
        self.parser.parse_and_execute('cd Cybersecurity')
        self.parser.parse_and_execute('mkdir WebSec')
        res_task = self.parser.parse_and_execute('touch "Audit SSL"')
        task_id = res_task["data"]["id"]

        # Add progress log
        self.parser.parse_and_execute('progress add "Initial Scan" "Finished nmap scan"')

        # Delete progress log
        res_del_log = self.parser.parse_and_execute('progress delete 1')
        self.assertTrue(res_del_log["success"])

        # Delete task
        res_del_task = self.parser.parse_and_execute(f'rm task {task_id}')
        self.assertTrue(res_del_task["success"])

        # Delete topic WebSec
        res_del_sub = self.parser.parse_and_execute('rm WebSec')
        self.assertTrue(res_del_sub["success"])

        # Delete active topic Cybersecurity (should navigate back up)
        res_del_main = self.parser.parse_and_execute('rmdir Cybersecurity')
        self.assertTrue(res_del_main["success"])
        self.assertEqual(res_del_main["prompt"], "C:\\OBSESSION_MATRIX\\interests>")

    def test_context_and_subtopic_navigation(self):
        # Verify active_interest_id and current_view in command execution
        res1 = self.parser.parse_and_execute('interests')
        self.assertEqual(res1["current_view"], "interests")
        self.assertIsNone(res1["active_interest_id"])

        self.parser.parse_and_execute('mkdir "Python"')
        res_cd = self.parser.parse_and_execute('cd Python')
        self.assertTrue(res_cd["success"])
        self.assertEqual(res_cd["current_view"], "topic_detail")
        self.assertIsNotNone(res_cd["active_interest_id"])
        python_id = res_cd["active_interest_id"]

        # Create subtopic
        self.parser.parse_and_execute('mkdir "Basics"')
        res_cd_sub = self.parser.parse_and_execute('cd Basics')
        self.assertTrue(res_cd_sub["success"])
        self.assertNotEqual(res_cd_sub["active_interest_id"], python_id)

        # Navigate back up
        res_back = self.parser.parse_and_execute('cd ..')
        self.assertEqual(res_back["active_interest_id"], python_id)

    def test_root_menu_and_dashboard_navigation(self):
        # 1. cd .. back to root shows options (dashboard, interests, settings)
        self.parser.parse_and_execute('interests')
        res_root = self.parser.parse_and_execute('cd ..')
        self.assertTrue(res_root["success"])
        self.assertEqual(res_root["prompt"], "C:\\OBSESSION_MATRIX>")
        self.assertIn("dashboard", res_root["message"])
        self.assertIn("interests", res_root["message"])
        self.assertIn("settings", res_root["message"])

        # 2. cd dashboard opens dashboard and renders contents directly without ls
        res_dash = self.parser.parse_and_execute('cd dashboard')
        self.assertTrue(res_dash["success"])
        self.assertEqual(res_dash["prompt"], "C:\\OBSESSION_MATRIX\\dashboard>")
        self.assertIn("DASHBOARD OVERVIEW", res_dash["message"])
        self.assertIn("CURRENT OBSESSION", res_dash["message"])

        # 3. Create topic and subtopic, and navigate directly from dashboard
        self.service.create_interest("DevOps")
        devops = self.service.get_interest_by_id(self.service.resolve_interest_id("DevOps"))
        sub = self.service.create_interest("Docker", parent_identifier=devops["id"])

        # From dashboard, navigate to subtopic Docker
        self.parser.current_view = "dashboard"
        self.parser.active_interest_id = None
        res_nav = self.parser.parse_and_execute('cd Docker')
        self.assertTrue(res_nav["success"])
        self.assertEqual(res_nav["current_view"], "topic_detail")
        self.assertEqual(res_nav["active_interest_id"], sub["id"])
        self.assertIn("DevOps\\Docker", res_nav["prompt"])

if __name__ == "__main__":
    unittest.main()


