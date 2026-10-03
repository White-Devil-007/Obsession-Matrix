import unittest
import os
import tempfile
from backend.database import Database

class TestDatabase(unittest.TestCase):
    def setUp(self):
        self.tmp_fd, self.tmp_path = tempfile.mkstemp(suffix=".db")
        self.db = Database(self.tmp_path)

    def tearDown(self):
        os.close(self.tmp_fd)
        if os.path.exists(self.tmp_path):
            os.remove(self.tmp_path)

    def test_database_initialization(self):
        with self.db.get_cursor() as cursor:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row["name"] for row in cursor.fetchall()]
            self.assertIn("interests", tables)
            self.assertIn("tasks", tables)
            self.assertIn("settings", tables)

    def test_foreign_key_cascading(self):
        with self.db.get_cursor() as cursor:
            # Create root interest
            cursor.execute("INSERT INTO interests (name) VALUES ('Parent')")
            parent_id = cursor.lastrowid
            
            # Create child interest
            cursor.execute("INSERT INTO interests (name, parent_id) VALUES ('Child', ?)", (parent_id,))
            child_id = cursor.lastrowid

            # Create task under child
            cursor.execute("INSERT INTO tasks (interest_id, title) VALUES (?, 'SubTask')", (child_id,))

            # Delete parent
            cursor.execute("DELETE FROM interests WHERE id = ?", (parent_id,))

        with self.db.get_cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as cnt FROM interests WHERE id = ?", (child_id,))
            self.assertEqual(cursor.fetchone()["cnt"], 0)
            
            cursor.execute("SELECT COUNT(*) as cnt FROM tasks WHERE interest_id = ?", (child_id,))
            self.assertEqual(cursor.fetchone()["cnt"], 0)

if __name__ == "__main__":
    unittest.main()
