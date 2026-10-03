from typing import Dict, Any, Optional, Union
from backend.services import AppService
from backend.command_parser import CommandParser
from backend.database import get_db

class AppApi:
    def __init__(self, service: Optional[AppService] = None):
        self.service = service or AppService(get_db())
        self.parser = CommandParser(self.service)

    # -------------------------------------------------------------
    # CLI COMMAND EXECUTION
    # -------------------------------------------------------------
    def execute_command(self, command_str: str) -> Dict[str, Any]:
        try:
            return self.parser.parse_and_execute(command_str)
        except Exception as e:
            return {"success": False, "command": "error", "message": f"Execution Error: {str(e)}", "action": "none"}

    def get_current_context(self) -> Dict[str, Any]:
        return {
            "active_interest_id": self.parser.active_interest_id,
            "current_view": self.parser.current_view,
        }

    def exit_app(self) -> None:
        import webview
        import sys
        try:
            if webview.windows:
                webview.windows[0].destroy()
            else:
                sys.exit(0)
        except Exception:
            sys.exit(0)

    # -------------------------------------------------------------
    # DASHBOARD & DATA FETCHERS
    # -------------------------------------------------------------
    def get_dashboard(self) -> Dict[str, Any]:
        return self.service.get_dashboard_summary()

    def get_interest_tree(self) -> list:
        return self.service.get_interest_tree()

    def get_all_interests(self) -> list:
        return self.service.get_all_interests()

    def get_interest_details(self, identifier: Union[int, str]) -> Dict[str, Any]:
        try:
            interest_id = self.service.resolve_interest_id(identifier)
            interest = self.service.get_interest_by_id(interest_id, update_access=True)
            tasks = self.service.get_tasks_for_interest(interest_id)
            return {
                "success": True,
                "interest": interest,
                "tasks": tasks
            }
        except Exception as e:
            return {"success": False, "message": str(e)}

    # -------------------------------------------------------------
    # INTEREST MUTATIONS
    # -------------------------------------------------------------
    def add_interest(self, name: str, parent: Optional[str] = None) -> Dict[str, Any]:
        try:
            res = self.service.create_interest(name, parent_identifier=parent)
            return {"success": True, "interest": res}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def rename_interest(self, identifier: Union[int, str], new_name: str) -> Dict[str, Any]:
        try:
            res = self.service.rename_interest(identifier, new_name)
            return {"success": True, "interest": res}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def delete_interest(self, identifier: Union[int, str]) -> Dict[str, Any]:
        try:
            ok = self.service.delete_interest(identifier)
            return {"success": ok}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def update_progress(self, identifier: Union[int, str], text: str) -> Dict[str, Any]:
        try:
            res = self.service.update_progress(identifier, text)
            return {"success": True, "interest": res}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def set_obsession(self, identifier: Union[int, str]) -> Dict[str, Any]:
        try:
            res = self.service.set_current_obsession(identifier)
            return {"success": True, "interest": res}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def clear_obsession(self) -> Dict[str, Any]:
        try:
            ok = self.service.clear_current_obsession()
            return {"success": ok}
        except Exception as e:
            return {"success": False, "message": str(e)}

    # -------------------------------------------------------------
    # TASK MUTATIONS
    # -------------------------------------------------------------
    def add_task(self, interest_identifier: Union[int, str], title: str, description: str = "") -> Dict[str, Any]:
        try:
            task = self.service.create_task(interest_identifier, title, description)
            return {"success": True, "task": task}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def update_task_status(self, task_id: int, status: str) -> Dict[str, Any]:
        try:
            task = self.service.update_task_status(task_id, status)
            return {"success": True, "task": task}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def edit_task(self, task_id: int, title: Optional[str] = None, description: Optional[str] = None) -> Dict[str, Any]:
        try:
            task = self.service.edit_task(task_id, title, description)
            return {"success": True, "task": task}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def delete_task(self, task_id: int) -> Dict[str, Any]:
        try:
            ok = self.service.delete_task(task_id)
            return {"success": ok}
        except Exception as e:
            return {"success": False, "message": str(e)}

    # -------------------------------------------------------------
    # SETTINGS & UTILS
    # -------------------------------------------------------------
    def get_settings(self) -> Dict[str, str]:
        return self.service.get_all_settings()

    def update_setting(self, key: str, value: str) -> Dict[str, Any]:
        try:
            res = self.service.update_setting(key, value)
            return {"success": True, "settings": res}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def export_data(self) -> Dict[str, Any]:
        try:
            data = self.service.export_data()
            return {"success": True, "data": data}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def reset_database(self) -> Dict[str, Any]:
        try:
            ok = self.service.reset_database()
            return {"success": ok}
        except Exception as e:
            return {"success": False, "message": str(e)}
