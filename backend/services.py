import json
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from backend.database import get_db, Database
from backend.models import InterestModel, TaskModel, InterestTreeNode
from backend.config import VALID_TASK_STATUSES, DEFAULT_SETTINGS

class AppService:
    def __init__(self, db: Optional[Database] = None):
        self.db = db or get_db()

    # ------------------------------------------------------------------
    # HELPER RESOLVERS
    # ------------------------------------------------------------------
    def _now_str(self) -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def resolve_interest_id(self, identifier: Union[int, str], parent_id: Optional[int] = None) -> int:
        """Resolves interest ID from either an integer ID or exact/case-insensitive name.
        If parent_id is specified, prioritizes matching children of that parent."""
        if isinstance(identifier, int) or (isinstance(identifier, str) and identifier.isdigit()):
            int_id = int(identifier)
            with self.db.get_cursor() as cursor:
                cursor.execute("SELECT id FROM interests WHERE id = ?", (int_id,))
                row = cursor.fetchone()
                if row:
                    return row["id"]
        
        # Try matching by name
        name_str = str(identifier).strip()
        with self.db.get_cursor() as cursor:
            if parent_id is not None:
                cursor.execute("SELECT id FROM interests WHERE LOWER(name) = LOWER(?) AND parent_id = ?", (name_str, parent_id))
                row = cursor.fetchone()
                if row:
                    return row["id"]

            cursor.execute("SELECT id FROM interests WHERE LOWER(name) = LOWER(?)", (name_str,))
            row = cursor.fetchone()
            if row:
                return row["id"]

        # If name_str contains path separators (e.g. "Cybersecurity\WebSec" or "Cybersecurity → WebSec")
        clean_name = name_str.replace(" → ", "\\").replace(" -> ", "\\").replace("/", "\\")
        if "\\" in clean_name:
            last_segment = [p.strip() for p in clean_name.split("\\") if p.strip()][-1]
            try:
                return self.resolve_interest_id(last_segment, parent_id=parent_id)
            except ValueError:
                pass
            for item in self.get_all_interests():
                item_path_clean = item["path"].replace(" → ", "\\")
                if item_path_clean.lower() == clean_name.lower():
                    return item["id"]
                
        raise ValueError(f"Interest '{identifier}' not found.")

    def get_interest_path(self, interest_id: int) -> List[Dict[str, Any]]:
        """Builds ordered path list from root parent down to target interest."""
        path = []
        curr_id: Optional[int] = interest_id
        visited = set()
        
        while curr_id is not None and curr_id not in visited:
            visited.add(curr_id)
            with self.db.get_cursor() as cursor:
                cursor.execute(
                    "SELECT id, name, parent_id, is_current_obsession, custom_progress, status FROM interests WHERE id = ?",
                    (curr_id,)
                )
                row = cursor.fetchone()
                if not row:
                    break
                path.insert(0, dict(row))
                curr_id = row["parent_id"]
                
        return path

    def get_path_string(self, interest_id: int) -> str:
        path = self.get_interest_path(interest_id)
        return " → ".join(node["name"] for node in path) if path else ""

    # ------------------------------------------------------------------
    # INTEREST MANAGEMENT
    # ------------------------------------------------------------------
    def create_interest(self, name: str, parent_identifier: Optional[Union[int, str]] = None) -> Dict[str, Any]:
        name = name.strip()
        if not name:
            raise ValueError("Interest name cannot be empty.")
            
        parent_id = None
        if parent_identifier is not None:
            parent_id = self.resolve_interest_id(parent_identifier)

        now = self._now_str()
        with self.db.get_cursor() as cursor:
            # Check for duplicate sibling names under the same parent
            if parent_id is None:
                cursor.execute("SELECT id FROM interests WHERE LOWER(name) = LOWER(?) AND parent_id IS NULL", (name,))
            else:
                cursor.execute("SELECT id FROM interests WHERE LOWER(name) = LOWER(?) AND parent_id = ?", (name, parent_id))
            
            if cursor.fetchone():
                raise ValueError(f"An interest named '{name}' already exists in this topic level.")

            cursor.execute(
                """
                INSERT INTO interests (name, parent_id, is_current_obsession, custom_progress, status, created_at, updated_at, accessed_at)
                VALUES (?, ?, 0, 'Not Started', 'active', ?, ?, ?)
                """,
                (name, parent_id, now, now, now)
            )
            new_id = cursor.lastrowid

        return self.get_interest_by_id(new_id)

    def get_interest_by_id(self, interest_id: int, update_access: bool = False) -> Dict[str, Any]:
        now = self._now_str()
        with self.db.get_cursor() as cursor:
            if update_access:
                cursor.execute("UPDATE interests SET accessed_at = ? WHERE id = ?", (now, interest_id))

            cursor.execute("SELECT * FROM interests WHERE id = ?", (interest_id,))
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Interest with ID {interest_id} does not exist.")
            
            data = dict(row)
            data["is_current_obsession"] = bool(data["is_current_obsession"])
            data["path"] = self.get_path_string(interest_id)
            return data

    def rename_interest(self, identifier: Union[int, str], new_name: str) -> Dict[str, Any]:
        interest_id = self.resolve_interest_id(identifier)
        new_name = new_name.strip()
        if not new_name:
            raise ValueError("New interest name cannot be empty.")
            
        now = self._now_str()
        with self.db.get_cursor() as cursor:
            cursor.execute("UPDATE interests SET name = ?, updated_at = ? WHERE id = ?", (new_name, now, interest_id))

        return self.get_interest_by_id(interest_id)

    def delete_interest(self, identifier: Union[int, str]) -> bool:
        interest_id = self.resolve_interest_id(identifier)
        with self.db.get_cursor() as cursor:
            cursor.execute("DELETE FROM interests WHERE id = ?", (interest_id,))
            return cursor.rowcount > 0

    def archive_interest(self, identifier: Union[int, str], archive: bool = True) -> Dict[str, Any]:
        interest_id = self.resolve_interest_id(identifier)
        status_val = "archived" if archive else "active"
        now = self._now_str()
        with self.db.get_cursor() as cursor:
            cursor.execute("UPDATE interests SET status = ?, updated_at = ? WHERE id = ?", (status_val, now, interest_id))
        return self.get_interest_by_id(interest_id)

    def get_all_interests(self, include_archived: bool = False) -> List[Dict[str, Any]]:
        with self.db.get_cursor() as cursor:
            if include_archived:
                cursor.execute("SELECT * FROM interests ORDER BY name ASC")
            else:
                cursor.execute("SELECT * FROM interests WHERE status = 'active' ORDER BY name ASC")
            rows = cursor.fetchall()
            
        results = []
        for r in rows:
            d = dict(r)
            d["is_current_obsession"] = bool(d["is_current_obsession"])
            d["path"] = self.get_path_string(d["id"])
            results.append(d)
        return results

    def get_interest_tree(self, include_archived: bool = False) -> List[Dict[str, Any]]:
        all_interests = self.get_all_interests(include_archived=include_archived)
        
        # Get task counts per interest
        with self.db.get_cursor() as cursor:
            cursor.execute("""
                SELECT interest_id, status, COUNT(*) as count 
                FROM tasks 
                GROUP BY interest_id, status
            """)
            task_rows = cursor.fetchall()

        task_counts_map: Dict[int, Dict[str, int]] = {}
        for r in task_rows:
            iid = r["interest_id"]
            st = r["status"]
            cnt = r["count"]
            if iid not in task_counts_map:
                task_counts_map[iid] = {"total": 0, "not_started": 0, "in_progress": 0, "done": 0}
            task_counts_map[iid][st] = cnt
            task_counts_map[iid]["total"] += cnt

        # Map nodes
        nodes_by_id: Dict[int, Dict[str, Any]] = {}
        for item in all_interests:
            iid = item["id"]
            item_counts = task_counts_map.get(iid, {"total": 0, "not_started": 0, "in_progress": 0, "done": 0})
            nodes_by_id[iid] = {
                "interest": item,
                "children": [],
                "task_counts": item_counts
            }

        root_nodes = []
        for item in all_interests:
            iid = item["id"]
            pid = item["parent_id"]
            if pid is None or pid not in nodes_by_id:
                root_nodes.append(nodes_by_id[iid])
            else:
                nodes_by_id[pid]["children"].append(nodes_by_id[iid])

        return root_nodes

    # ------------------------------------------------------------------
    # CURRENT OBSESSION
    # ------------------------------------------------------------------
    def set_current_obsession(self, identifier: Union[int, str]) -> Dict[str, Any]:
        interest_id = self.resolve_interest_id(identifier)
        now = self._now_str()
        
        with self.db.get_cursor() as cursor:
            cursor.execute("UPDATE interests SET is_current_obsession = 0")
            cursor.execute(
                "UPDATE interests SET is_current_obsession = 1, accessed_at = ?, updated_at = ? WHERE id = ?",
                (now, now, interest_id)
            )

        return self.get_interest_by_id(interest_id)

    def clear_current_obsession(self) -> bool:
        with self.db.get_cursor() as cursor:
            cursor.execute("UPDATE interests SET is_current_obsession = 0")
            return cursor.rowcount >= 0

    def get_current_obsession(self) -> Optional[Dict[str, Any]]:
        with self.db.get_cursor() as cursor:
            cursor.execute("SELECT * FROM interests WHERE is_current_obsession = 1 LIMIT 1")
            row = cursor.fetchone()
            if not row:
                return None
            data = dict(row)
            data["is_current_obsession"] = True
            data["path"] = self.get_path_string(data["id"])
            return data

    # ------------------------------------------------------------------
    # MANUAL PROGRESS & LOG HISTORY (GITHUB COMMIT STYLE)
    # ------------------------------------------------------------------
    def update_progress(self, identifier: Union[int, str], custom_progress: str) -> Dict[str, Any]:
        interest_id = self.resolve_interest_id(identifier)
        custom_progress = custom_progress.strip()
        if not custom_progress:
            raise ValueError("Progress status text cannot be empty.")

        now = self._now_str()
        with self.db.get_cursor() as cursor:
            cursor.execute(
                "UPDATE interests SET custom_progress = ?, updated_at = ? WHERE id = ?",
                (custom_progress, now, interest_id)
            )
            cursor.execute(
                "INSERT INTO progress_logs (interest_id, title, description, progress_text, created_at) VALUES (?, ?, ?, ?, ?)",
                (interest_id, custom_progress, '', custom_progress, now)
            )

        return self.get_interest_by_id(interest_id)

    def add_progress_log(self, identifier: Union[int, str], title: str, description: str) -> Dict[str, Any]:
        """Add a titled progress log entry (GitHub-commit style) with a full description body."""
        interest_id = self.resolve_interest_id(identifier)
        title = title.strip().strip('"').strip("'")
        description = description.strip().strip('"').strip("'")
        if not title:
            raise ValueError("Progress log title cannot be empty.")

        now = self._now_str()
        with self.db.get_cursor() as cursor:
            # Update the interest's short progress status to the title
            cursor.execute(
                "UPDATE interests SET custom_progress = ?, updated_at = ? WHERE id = ?",
                (title, now, interest_id)
            )
            cursor.execute(
                "INSERT INTO progress_logs (interest_id, title, description, progress_text, created_at) VALUES (?, ?, ?, ?, ?)",
                (interest_id, title, description, title, now)
            )
            new_id = cursor.lastrowid

        with self.db.get_cursor() as cursor:
            cursor.execute("SELECT * FROM progress_logs WHERE id = ?", (new_id,))
            return dict(cursor.fetchone())

    def get_progress_history(self, identifier: Union[int, str]) -> List[Dict[str, Any]]:
        interest_id = self.resolve_interest_id(identifier)
        with self.db.get_cursor() as cursor:
            cursor.execute(
                "SELECT * FROM progress_logs WHERE interest_id = ? ORDER BY created_at DESC",
                (interest_id,)
            )
            rows = cursor.fetchall()
        return [dict(r) for r in rows]

    def get_progress_log_detail(self, identifier: Union[int, str], title: str) -> Optional[Dict[str, Any]]:
        """Find a specific progress log entry by title (case-insensitive) for a given interest."""
        interest_id = self.resolve_interest_id(identifier)
        title = title.strip().strip('"').strip("'")
        with self.db.get_cursor() as cursor:
            cursor.execute(
                "SELECT * FROM progress_logs WHERE interest_id = ? AND LOWER(title) = LOWER(?) ORDER BY created_at DESC LIMIT 1",
                (interest_id, title)
            )
            row = cursor.fetchone()
        return dict(row) if row else None

    def delete_progress_log(self, identifier: Union[int, str], log_ref: Union[int, str]) -> bool:
        """Delete a progress log entry by index (1-indexed) or title."""
        interest_id = self.resolve_interest_id(identifier)
        history = self.get_progress_history(interest_id)
        if not history:
            raise ValueError("No progress logs found for this topic.")

        target_log_id = None
        log_ref_str = str(log_ref).strip().strip('"').strip("'")

        if log_ref_str.isdigit():
            idx = int(log_ref_str)
            if 1 <= idx <= len(history):
                target_log_id = history[idx - 1]["id"]
            else:
                for log in history:
                    if log["id"] == idx:
                        target_log_id = log["id"]
                        break
        else:
            for log in history:
                if log["title"].lower() == log_ref_str.lower():
                    target_log_id = log["id"]
                    break

        if target_log_id is None:
            raise ValueError(f"Progress log entry '{log_ref_str}' not found.")

        with self.db.get_cursor() as cursor:
            cursor.execute("DELETE FROM progress_logs WHERE id = ?", (target_log_id,))
            return cursor.rowcount > 0

    # ------------------------------------------------------------------
    # TASK MANAGEMENT
    # ------------------------------------------------------------------
    def create_task(self, interest_identifier: Union[int, str], title: str, description: str = "") -> Dict[str, Any]:
        interest_id = self.resolve_interest_id(interest_identifier)
        title = title.strip()
        if not title:
            raise ValueError("Task title cannot be empty.")

        now = self._now_str()
        with self.db.get_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO tasks (interest_id, title, description, status, created_at, updated_at)
                VALUES (?, ?, ?, 'not_started', ?, ?)
                """,
                (interest_id, title, description, now, now)
            )
            new_id = cursor.lastrowid

        return self.get_task_by_id(new_id)

    def get_task_by_id(self, task_id: int) -> Dict[str, Any]:
        with self.db.get_cursor() as cursor:
            cursor.execute(
                """
                SELECT t.*, i.name as interest_name 
                FROM tasks t 
                JOIN interests i ON t.interest_id = i.id 
                WHERE t.id = ?
                """,
                (task_id,)
            )
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Task with ID {task_id} does not exist.")
            
            d = dict(row)
            d["interest_path"] = self.get_path_string(d["interest_id"])
            return d

    def update_task_status(self, task_id: int, status: str) -> Dict[str, Any]:
        status = status.lower().strip()
        if status not in VALID_TASK_STATUSES:
            raise ValueError(f"Invalid status '{status}'. Must be one of: {', '.join(VALID_TASK_STATUSES)}")

        now = self._now_str()
        with self.db.get_cursor() as cursor:
            cursor.execute(
                "UPDATE tasks SET status = ?, updated_at = ? WHERE id = ?",
                (status, now, task_id)
            )
            if cursor.rowcount == 0:
                raise ValueError(f"Task with ID {task_id} not found.")

        return self.get_task_by_id(task_id)

    def edit_task(self, task_id: int, title: Optional[str] = None, description: Optional[str] = None) -> Dict[str, Any]:
        current = self.get_task_by_id(task_id)
        new_title = title.strip() if title is not None else current["title"]
        new_desc = description if description is not None else current["description"]
        
        if not new_title:
            raise ValueError("Task title cannot be empty.")

        now = self._now_str()
        with self.db.get_cursor() as cursor:
            cursor.execute(
                "UPDATE tasks SET title = ?, description = ?, updated_at = ? WHERE id = ?",
                (new_title, new_desc, now, task_id)
            )

        return self.get_task_by_id(task_id)

    def delete_task(self, task_id: int) -> bool:
        with self.db.get_cursor() as cursor:
            cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            return cursor.rowcount > 0

    def get_tasks_for_interest(self, interest_identifier: Union[int, str]) -> List[Dict[str, Any]]:
        interest_id = self.resolve_interest_id(interest_identifier)
        with self.db.get_cursor() as cursor:
            cursor.execute("SELECT * FROM tasks WHERE interest_id = ? ORDER BY id ASC", (interest_id,))
            rows = cursor.fetchall()
            
        res = []
        path_str = self.get_path_string(interest_id)
        for r in rows:
            d = dict(r)
            d["interest_path"] = path_str
            res.append(d)
        return res

    def get_all_tasks(self) -> List[Dict[str, Any]]:
        with self.db.get_cursor() as cursor:
            cursor.execute(
                """
                SELECT t.*, i.name as interest_name 
                FROM tasks t 
                JOIN interests i ON t.interest_id = i.id 
                WHERE i.status = 'active'
                ORDER BY t.id ASC
                """
            )
            rows = cursor.fetchall()
            
        res = []
        for r in rows:
            d = dict(r)
            d["interest_path"] = self.get_path_string(d["interest_id"])
            res.append(d)
        return res

    def get_all_tasks_grouped(self) -> Dict[str, List[Dict[str, Any]]]:
        all_tasks = self.get_all_tasks()
        grouped = {
            "not_started": [],
            "in_progress": [],
            "done": []
        }
        for task in all_tasks:
            st = task["status"]
            if st in grouped:
                grouped[st].append(task)
        return grouped

    # ------------------------------------------------------------------
    # DASHBOARD SUMMARY
    # ------------------------------------------------------------------
    def get_dashboard_summary(self) -> Dict[str, Any]:
        obsession = self.get_current_obsession()
        
        # Recent interests (most recently accessed)
        with self.db.get_cursor() as cursor:
            cursor.execute(
                "SELECT * FROM interests WHERE status = 'active' ORDER BY accessed_at DESC LIMIT 5"
            )
            recent_rows = cursor.fetchall()
            
        recent_interests = []
        for r in recent_rows:
            d = dict(r)
            d["is_current_obsession"] = bool(d["is_current_obsession"])
            d["path"] = self.get_path_string(d["id"])
            recent_interests.append(d)

        # Overall Task Summary
        tasks_grouped = self.get_all_tasks_grouped()
        task_counts = {
            "total": sum(len(v) for v in tasks_grouped.values()),
            "not_started": len(tasks_grouped["not_started"]),
            "in_progress": len(tasks_grouped["in_progress"]),
            "done": len(tasks_grouped["done"]),
        }

        return {
            "current_obsession": obsession,
            "recent_interests": recent_interests,
            "task_counts": task_counts,
            "in_progress_tasks": tasks_grouped["in_progress"],
        }

    # ------------------------------------------------------------------
    # SETTINGS & DATABASE UTILS
    # ------------------------------------------------------------------
    def get_all_settings(self) -> Dict[str, str]:
        with self.db.get_cursor() as cursor:
            cursor.execute("SELECT key, value FROM settings")
            rows = cursor.fetchall()
        settings = dict(DEFAULT_SETTINGS)
        for r in rows:
            settings[r["key"]] = r["value"]
        return settings

    def update_setting(self, key: str, value: str) -> Dict[str, str]:
        with self.db.get_cursor() as cursor:
            cursor.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = ?",
                (key, value, value)
            )
        return self.get_all_settings()

    def export_data(self) -> Dict[str, Any]:
        interests = self.get_all_interests(include_archived=True)
        tasks = self.get_all_tasks()
        settings = self.get_all_settings()
        return {
            "version": "1.0",
            "exported_at": self._now_str(),
            "interests": interests,
            "tasks": tasks,
            "settings": settings,
        }

    def reset_database(self) -> bool:
        with self.db.get_cursor() as cursor:
            cursor.execute("DELETE FROM progress_logs")
            cursor.execute("DELETE FROM tasks")
            cursor.execute("DELETE FROM interests")
            cursor.execute("DELETE FROM settings")
            for k, v in DEFAULT_SETTINGS.items():
                cursor.execute("INSERT INTO settings (key, value) VALUES (?, ?)", (k, v))
        return True
