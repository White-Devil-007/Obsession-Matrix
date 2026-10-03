import re
from typing import Dict, Any, Optional, List
from backend.services import AppService

# Supported root command triggers
KNOWN_COMMANDS = [
    "start", "dashboard", "interests", "tree", "settings",
    "cd", "cd ..", "back", "ls", "dir", "mkdir", "touch", "help", "open",
    "current", "tasks", "add", "done", "task", "progress", "history", "clear", "exit"
]

def levenshtein_distance(s1: str, s2: str) -> int:
    """Calculates Levenshtein distance for fuzzy typo correction."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]

def suggest_closest_command(userInput: str) -> Optional[str]:
    first_word = userInput.split()[0].lower() if userInput.split() else ""
    if not first_word:
        return None
    best_match = None
    min_dist = 999
    for cmd in KNOWN_COMMANDS:
        dist = levenshtein_distance(first_word, cmd)
        if dist < min_dist and dist <= 2:
            min_dist = dist
            best_match = cmd
    return best_match

class CommandParser:
    def __init__(self, service: AppService):
        self.service = service
        self.active_interest_id: Optional[int] = None
        self.current_view: str = "main_menu" # 'main_menu', 'dashboard', 'interests', 'settings', 'topic_detail'

    def parse_and_execute(self, command_str: str) -> Dict[str, Any]:
        res = self._do_parse_and_execute(command_str)
        res["active_interest_id"] = self.active_interest_id
        res["current_view"] = self.current_view
        return res

    def _do_parse_and_execute(self, command_str: str) -> Dict[str, Any]:
        raw_cmd = command_str.strip()
        if not raw_cmd:
            return {"success": True, "message": "", "action": "none"}

        cmd_lower = raw_cmd.lower()

        # -------------------------------------------------------------
        # 0. START & MAIN MENU NAVIGATION
        # -------------------------------------------------------------
        if cmd_lower in ["start", "menu"]:
            self.active_interest_id = None
            self.current_view = "main_menu"
            menu_text = self._get_main_menu_text()
            return {"success": True, "command": "start", "message": menu_text, "action": "start_app", "prompt": "C:\\OBSESSION_MATRIX>"}

        # Handle cd .. / back
        if cmd_lower in ["cd ..", "back"]:
            if self.current_view == "topic_detail" and self.active_interest_id is not None:
                current_info = self.service.get_interest_by_id(self.active_interest_id)
                parent_id = current_info.get("parent_id")
                if parent_id is not None:
                    self.active_interest_id = parent_id
                    parent_info = self.service.get_interest_by_id(parent_id)
                    prompt_str = f"C:\\OBSESSION_MATRIX\\{parent_info['path'].replace(' → ', '\\')}>"
                    detail_res = self._format_single_interest_detail(parent_id)
                    detail_res["prompt"] = prompt_str
                    return detail_res
                else:
                    # Return to interests list — silent, user uses ls to see topics
                    self.active_interest_id = None
                    self.current_view = "interests"
                    return {"success": True, "command": "cd ..", "message": "", "action": "navigate_view", "target_view": "interests", "prompt": "C:\\OBSESSION_MATRIX\\interests>"}
            
            elif self.current_view in ["dashboard", "interests", "settings"]:
                self.current_view = "main_menu"
                self.active_interest_id = None
                menu_text = self._get_main_menu_text()
                return {"success": True, "command": "cd ..", "message": menu_text, "action": "go_back", "prompt": "C:\\OBSESSION_MATRIX>"}
            
            elif self.current_view == "main_menu":
                menu_text = self._get_main_menu_text()
                return {"success": True, "command": "cd ..", "message": "Already at root.\n\n" + menu_text, "action": "none", "prompt": "C:\\OBSESSION_MATRIX>"}

        # -------------------------------------------------------------
        # GLOBAL NAVIGATION: dashboard (cd dashboard / dashboard)
        # -------------------------------------------------------------
        if cmd_lower in ["dashboard", "cd dashboard"]:
            self.current_view = "dashboard"
            self.active_interest_id = None
            return self._render_dashboard()

        # -------------------------------------------------------------
        # MAIN MENU SECTIONS: interests, settings
        # -------------------------------------------------------------
        if self.current_view == "main_menu":
            if cmd_lower in ["interests", "tree", "cd interests", "cd tree"]:
                self.current_view = "interests"
                self.active_interest_id = None
                # Silent entry — user uses 'ls' to list topics
                return {"success": True, "command": "interests", "message": "", "action": "navigate_view", "target_view": "interests", "prompt": "C:\\OBSESSION_MATRIX\\interests>"}

            if cmd_lower in ["settings", "cd settings"]:
                self.current_view = "settings"
                self.active_interest_id = None
                # Silent entry — user uses 'ls' to view application settings
                return {"success": True, "command": "settings", "message": "", "action": "navigate_view", "target_view": "settings", "prompt": "C:\\OBSESSION_MATRIX\\settings>"}

            if cmd_lower.startswith("cd "):
                return {"success": False, "command": "cd", "message": "[WORKFLOW ERROR] You are at Main Menu. Enter 'interests' or 'dashboard' first before navigating.", "action": "none"}

        # Handle section switching attempt from sub-views
        if cmd_lower in ["interests", "tree", "settings"] and self.current_view != "main_menu":
            return {
                "success": False,
                "command": cmd_lower,
                "message": f"[WORKFLOW ERROR] You are currently inside {self.current_view.upper()}. Type 'cd ..' to return to Main Menu first.",
                "action": "none"
            }

        # -------------------------------------------------------------
        # 1. HELP
        # -------------------------------------------------------------
        if cmd_lower == "help":
            help_text = (
                "AVAILABLE TERMINAL COMMANDS:\n"
                "  dashboard / interests / settings  Navigate to main sections\n"
                "  ls / dir                       Show tree structure & sub-items of active interest topic\n"
                "  cd <topic_name>                Navigate into a topic directory by name\n"
                "  cd ..                          Navigate back up 1 directory level\n"
                "  mkdir <name>                   Create sub-topic folder under active topic\n"
                "  touch <title>                  Create task under active topic\n"
                "  rm <topic_name> / rmdir        Delete a topic folder or active directory\n"
                "  rm task <task_id>              Delete a task by ID\n"
                "  progress add \"<t>\" \"<d>\"        Add a progress log entry with title & description\n"
                "  progress view                  View timestamped progress log commits\n"
                "  progress delete <n>            Delete a progress log entry by index or title\n"
                "  current set <interest>         Set Current Obsession\n"
                "  current clear                  Clear Current Obsession\n"
                "  done <task_id>                 Mark task as completed\n"
                "  clear                          Clear terminal screen\n"
                "  exit                           Close application\n\n"
                "TIP: Press <Tab> anytime to auto-complete section names, commands, and topic folders."
            )
            return {"success": True, "command": "help", "message": help_text, "action": "print"}

        # -------------------------------------------------------------
        # 2. CLEAR & EXIT
        # -------------------------------------------------------------
        if cmd_lower == "clear":
            return {"success": True, "command": "clear", "message": "Terminal output cleared.", "action": "clear_terminal"}

        if cmd_lower == "exit":
            return {"success": True, "command": "exit", "message": "Exiting application...", "action": "exit_app"}

        # -------------------------------------------------------------
        # 4. LS / DIR — reveals contents of current location
        # -------------------------------------------------------------
        if cmd_lower in ["ls", "dir"]:
            if self.active_interest_id is not None:
                # Inside a topic: show its sub-topics and tasks tree
                return self._format_single_interest_detail(self.active_interest_id)
            elif self.current_view == "interests":
                # Inside interests root: show main topics list
                tree_msg = self._format_main_topics_message()
                return {"success": True, "command": "ls", "message": tree_msg, "action": "print"}
            elif self.current_view == "settings":
                # Inside settings root: show settings list
                return self._format_settings_message()
            elif self.current_view == "dashboard":
                return self._render_dashboard()
            elif self.current_view == "main_menu":
                return {"success": False, "command": "ls", "message": "Not inside a directory. Type 'dashboard', 'interests', or 'settings'.", "action": "none"}

        # -------------------------------------------------------------
        # 5. CD <TOPIC> / OPEN <TOPIC> / MKDIR / TOUCH
        # -------------------------------------------------------------
        if cmd_lower.startswith("cd ") or cmd_lower.startswith("open "):
            target_name = raw_cmd.split(maxsplit=1)[1].strip().strip('"').strip("'")
            if target_name == "..":
                pass
            else:
                return self._handle_cd_topic(target_name)

        if cmd_lower.startswith("mkdir "):
            topic_name = raw_cmd[6:].strip().strip('"').strip("'")
            try:
                parent_identifier = self.active_interest_id
                interest = self.service.create_interest(topic_name, parent_identifier=parent_identifier)
                return {"success": True, "command": "mkdir", "message": f"Created topic directory '{interest['path']}'", "action": "refresh", "data": interest}
            except Exception as e:
                return {"success": False, "command": "mkdir", "message": f"Error: {str(e)}", "action": "none"}

        if cmd_lower.startswith("touch "):
            task_title = raw_cmd[6:].strip().strip('"').strip("'")
            if self.active_interest_id is None:
                return {"success": False, "command": "touch", "message": "Select a topic first using 'cd <topic>' before creating a task.", "action": "none"}
            try:
                task = self.service.create_task(self.active_interest_id, task_title)
                return {"success": True, "command": "touch", "message": f"Created task #{task['id']} '{task['title']}'", "action": "refresh", "data": task}
            except Exception as e:
                return {"success": False, "command": "touch", "message": f"Error: {str(e)}", "action": "none"}

        # -------------------------------------------------------------
        # 5B. DELETE / RM COMMANDS (Topics, Sub-topics, Tasks)
        # -------------------------------------------------------------
        if cmd_lower.startswith("rm task ") or cmd_lower.startswith("delete task ") or cmd_lower.startswith("rm #"):
            target = ""
            for prefix in ["delete task ", "rm task ", "rm #"]:
                if cmd_lower.startswith(prefix):
                    target = raw_cmd[len(prefix):].strip()
                    break
            if target.isdigit():
                task_id = int(target)
                try:
                    self.service.delete_task(task_id)
                    return {"success": True, "command": "delete task", "message": f"Deleted task #{task_id}.", "action": "refresh"}
                except Exception as e:
                    return {"success": False, "command": "delete task", "message": f"Error deleting task: {str(e)}", "action": "none"}
            else:
                return {"success": False, "command": "delete task", "message": "Usage: rm task <task_id> (e.g. `rm task 3`)", "action": "none"}

        if cmd_lower.startswith("rm ") or cmd_lower.startswith("rmdir ") or cmd_lower.startswith("delete topic ") or cmd_lower.startswith("delete interest "):
            target = ""
            for prefix in ["delete interest ", "delete topic ", "rmdir ", "rm "]:
                if cmd_lower.startswith(prefix):
                    target = raw_cmd[len(prefix):].strip().strip('"').strip("'")
                    break
            try:
                resolved_id = self.service.resolve_interest_id(target, parent_id=self.active_interest_id)
                deleted_item = self.service.get_interest_by_id(resolved_id)
                deleted_name = deleted_item["name"]

                if self.active_interest_id == resolved_id:
                    parent_id = deleted_item["parent_id"]
                    self.service.delete_interest(resolved_id)
                    if parent_id is None:
                        self.current_view = "interests"
                        self.active_interest_id = None
                        prompt_str = "C:\\OBSESSION_MATRIX\\interests>"
                    else:
                        parent_item = self.service.get_interest_by_id(parent_id)
                        self.active_interest_id = parent_id
                        prompt_str = f"C:\\OBSESSION_MATRIX\\{parent_item['path'].replace(' → ', '\\')}>"
                    return {"success": True, "command": "rm", "message": f"Deleted topic '{deleted_name}' and returned to parent directory.", "action": "refresh", "prompt": prompt_str}
                else:
                    self.service.delete_interest(resolved_id)
                    return {"success": True, "command": "rm", "message": f"Deleted topic '{deleted_name}'.", "action": "refresh"}
            except Exception as e:
                return {"success": False, "command": "rm", "message": f"Error deleting topic: {str(e)}", "action": "none"}

        # -------------------------------------------------------------
        # 6. PROGRESS LOG — GitHub-style titled commit entries
        # -------------------------------------------------------------
        # Alias: history / git log -> progress view
        if cmd_lower in ["history", "git log"]:
            # Redirect to progress view handler
            return self.parse_and_execute("progress view")

        if cmd_lower.startswith("progress"):
            rest = raw_cmd[8:].strip()  # everything after 'progress'

            # -- progress delete / progress rm -----------------------
            if rest.lower().startswith("delete ") or rest.lower().startswith("rm "):
                log_ref = ""
                for prefix in ["delete ", "rm "]:
                    if rest.lower().startswith(prefix):
                        log_ref = rest[len(prefix):].strip()
                        break
                if self.active_interest_id is None:
                    return {"success": False, "command": "progress delete", "message": "Navigate into a topic first using 'cd <topic>'.", "action": "none"}
                try:
                    self.service.delete_progress_log(self.active_interest_id, log_ref)
                    return {"success": True, "command": "progress delete", "message": f"Deleted progress log entry '{log_ref}'.", "action": "refresh"}
                except Exception as e:
                    return {"success": False, "command": "progress delete", "message": f"Error deleting progress log: {str(e)}", "action": "none"}

            # -- progress view ----------------------------------------
            if rest == "" or rest.lower() == "view":
                if self.active_interest_id is None:
                    return {"success": False, "command": "progress", "message": "Navigate into a topic first using 'cd <topic>'.", "action": "none"}
                history = self.service.get_progress_history(self.active_interest_id)
                interest = self.service.get_interest_by_id(self.active_interest_id)
                if not history:
                    return {
                        "success": True, "command": "progress view",
                        "message": f"No progress log entries yet for '{interest['name']}'.\nUse: progress add \"<title>\" \"<description>\" to add your first entry.",
                        "action": "print"
                    }
                lines = [
                    "======================================================================",
                    f"PROGRESS LOG — {interest['path']}",
                    "======================================================================",
                    "  (type 'progress view <number>' or 'progress view <title>' to read an entry)",
                    ""
                ]
                for idx, log in enumerate(history, 1):
                    ts = log['created_at'][:16]  # trim seconds
                    has_desc = bool(log.get('description', '').strip())
                    desc_tag = " [+desc]" if has_desc else ""
                    lines.append(f"  {idx:>3}. [{ts}]  {log['title']}{desc_tag}")
                lines.append("")
                lines.append("[Options: 'progress view <n>', 'progress add \"<title>\" \"<desc>\"', 'cd ..']")
                return {"success": True, "command": "progress view", "message": "\n".join(lines), "action": "print"}

            # -- progress view <number or title> ----------------------
            if rest.lower().startswith("view "):
                query = rest[5:].strip().strip('"').strip("'")
                if self.active_interest_id is None:
                    return {"success": False, "command": "progress view", "message": "Navigate into a topic first.", "action": "none"}
                history = self.service.get_progress_history(self.active_interest_id)
                interest = self.service.get_interest_by_id(self.active_interest_id)
                entry = None
                if query.isdigit():
                    idx = int(query) - 1
                    if 0 <= idx < len(history):
                        entry = history[idx]
                else:
                    # Case-insensitive title match
                    entry = next((e for e in history if e['title'].lower() == query.lower()), None)
                    if not entry:
                        # Partial match fallback
                        entry = next((e for e in history if query.lower() in e['title'].lower()), None)
                if not entry:
                    return {"success": False, "command": "progress view", "message": f"No progress log entry found matching '{query}'.", "action": "none"}
                ts = entry['created_at'][:16]
                desc = entry.get('description', '').strip() or "(no description provided)"
                lines = [
                    "----------------------------------------------------------------------",
                    f"  COMMIT: {entry['title']}",
                    f"  DATE  : {ts}",
                    "----------------------------------------------------------------------",
                    "",
                    desc,
                    "",
                    "[Type 'progress view' to return to log list]"
                ]
                return {"success": True, "command": "progress view detail", "message": "\n".join(lines), "action": "print"}

            # -- progress add "<title>" "<description>" ---------------
            if rest.lower().startswith("add"):
                if self.active_interest_id is None:
                    return {"success": False, "command": "progress add", "message": "Navigate into a topic first using 'cd <topic>'.", "action": "none"}
                add_rest = rest[3:].strip()
                # Parse: "title" "description" or 'title' 'description'
                pattern = re.compile(r'^["\'](.+?)["\']\s+["\'](.+?)["\']$', re.DOTALL)
                m = pattern.match(add_rest)
                if m:
                    title = m.group(1).strip()
                    description = m.group(2).strip()
                else:
                    # Try: "title" only (no description)
                    single = re.match(r'^["\'](.+?)["\']$', add_rest)
                    if single:
                        title = single.group(1).strip()
                        description = ""
                    else:
                        return {
                            "success": False, "command": "progress add",
                            "message": (
                                "Usage: progress add \"<title>\" \"<description>\"\n"
                                "  e.g. progress add \"Completed chapter 3\" \"Understood neural networks and backprop basics.\""
                            ),
                            "action": "none"
                        }
                try:
                    log = self.service.add_progress_log(self.active_interest_id, title, description)
                    interest = self.service.get_interest_by_id(self.active_interest_id)
                    return {
                        "success": True, "command": "progress add",
                        "message": f"Progress log committed for '{interest['name']}':\n  Title: \"{log['title']}\"\n  Desc : {log.get('description','') or '(none)'}\n\n(Type 'progress view' to see all entries)",
                        "action": "refresh"
                    }
                except Exception as e:
                    return {"success": False, "command": "progress add", "message": f"Error: {str(e)}", "action": "none"}

            # -- Legacy: progress "<short text>" (single-field quick update) --
            if self.active_interest_id is not None:
                progress_text = rest.strip('"').strip("'")
                try:
                    interest = self.service.update_progress(self.active_interest_id, progress_text)
                    return {"success": True, "command": "progress", "message": f"Progress updated for '{interest['name']}': \"{interest['custom_progress']}\"", "action": "refresh"}
                except Exception as e:
                    return {"success": False, "command": "progress", "message": f"Error: {str(e)}", "action": "none"}

            return {"success": False, "command": "progress", "message": "Usage: progress view | progress view <n> | progress add \"<title>\" \"<desc>\"", "action": "none"}

        # -------------------------------------------------------------
        # 6.5 SETTINGS MODIFICATION (SET / TOGGLE)
        # -------------------------------------------------------------
        if cmd_lower.startswith("set "):
            rest = raw_cmd[4:].strip()
            if "=" in rest:
                key, val = rest.split("=", 1)
            else:
                parts = rest.split(maxsplit=1)
                if len(parts) < 2:
                    return {"success": False, "command": "set", "message": "Usage: set <key> <value> (e.g. `set paste_restriction false`)", "action": "none"}
                key, val = parts[0], parts[1]
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            try:
                self.service.update_setting(key, val)
                return {"success": True, "command": "set", "message": f"Setting '{key}' updated to '{val}'.", "action": "refresh"}
            except Exception as e:
                return {"success": False, "command": "set", "message": f"Error updating setting: {str(e)}", "action": "none"}

        if cmd_lower.startswith("toggle "):
            key = raw_cmd[7:].strip().strip('"').strip("'")
            settings = self.service.get_all_settings()
            if key not in settings:
                return {"success": False, "command": "toggle", "message": f"Unknown setting key '{key}'. Use 'ls' in settings to view available keys.", "action": "none"}
            curr_val = settings[key].lower()
            new_val = "false" if curr_val == "true" else "true"
            try:
                self.service.update_setting(key, new_val)
                return {"success": True, "command": "toggle", "message": f"Setting '{key}' toggled to '{new_val}'.", "action": "refresh"}
            except Exception as e:
                return {"success": False, "command": "toggle", "message": f"Error: {str(e)}", "action": "none"}

        # -------------------------------------------------------------
        # 7. CURRENT OBSESSION
        # -------------------------------------------------------------
        if cmd_lower == "current":
            obsession = self.service.get_current_obsession()
            if not obsession:
                return {"success": True, "command": "current", "message": "No Current Obsession set. Use `current set <interest>` to set one.", "action": "print"}
            return {"success": True, "command": "current", "message": f"CURRENT OBSESSION: {obsession['path']}\nProgress: {obsession['custom_progress']}", "action": "print", "data": obsession}

        if cmd_lower == "current clear":
            self.service.clear_current_obsession()
            return {"success": True, "command": "current clear", "message": "Cleared Current Obsession.", "action": "refresh"}

        if cmd_lower.startswith("current set "):
            target_name = raw_cmd[12:].strip().strip('"').strip("'")
            try:
                interest = self.service.set_current_obsession(target_name)
                return {"success": True, "command": "current set", "message": f"Set Current Obsession to: {interest['path']}", "action": "refresh", "data": interest}
            except Exception as e:
                return {"success": False, "command": "current set", "message": f"Error: {str(e)}", "action": "none"}

        # -------------------------------------------------------------
        # 8. TASKS & DONE
        # -------------------------------------------------------------
        if cmd_lower.startswith("task status "):
            parts = raw_cmd[12:].strip().split()
            if len(parts) < 2 or not parts[0].isdigit():
                return {"success": False, "command": "task status", "message": "Usage: task status <id> <not_started|in_progress|done>", "action": "none"}
            task_id = int(parts[0])
            status_val = parts[1].lower()
            try:
                task = self.service.update_task_status(task_id, status_val)
                return {"success": True, "command": "task status", "message": f"Updated task #{task['id']} status to '{task['status']}'", "action": "refresh", "data": task}
            except Exception as e:
                return {"success": False, "command": "task status", "message": f"Error: {str(e)}", "action": "none"}

        if cmd_lower.startswith("done "):
            task_id_str = raw_cmd[5:].strip()
            if not task_id_str.isdigit():
                return {"success": False, "command": "done", "message": "Usage: done <task_id> (e.g. `done 1`)", "action": "none"}
            try:
                task = self.service.update_task_status(int(task_id_str), "done")
                return {"success": True, "command": "done", "message": f"Completed task #{task['id']}: '{task['title']}'", "action": "refresh", "data": task}
            except Exception as e:
                return {"success": False, "command": "done", "message": f"Error: {str(e)}", "action": "none"}

        if cmd_lower.startswith("add interest "):
            rest = raw_cmd[13:].strip()
            match = re.match(r'^(?:"([^"]+)"|(\S+))\s+under\s+(?:"([^"]+)"|(\S+))$', rest, re.IGNORECASE)
            if match:
                child_name = match.group(1) or match.group(2)
                parent_name = match.group(3) or match.group(4)
                try:
                    interest = self.service.create_interest(child_name, parent_identifier=parent_name)
                    return {"success": True, "command": "add interest", "message": f"Created interest '{interest['path']}' under '{parent_name}'", "action": "refresh", "data": interest}
                except Exception as e:
                    return {"success": False, "command": "add interest", "message": f"Error: {str(e)}", "action": "none"}
            else:
                interest_name = rest.strip('"').strip("'")
                parent_identifier = self.active_interest_id
                try:
                    interest = self.service.create_interest(interest_name, parent_identifier=parent_identifier)
                    return {"success": True, "command": "add interest", "message": f"Created interest '{interest['path']}'", "action": "refresh", "data": interest}
                except Exception as e:
                    return {"success": False, "command": "add interest", "message": f"Error: {str(e)}", "action": "none"}

        if cmd_lower.startswith("add task "):
            rest = raw_cmd[9:].strip()
            match = re.match(r'^(?:"([^"]+)"|(\S+))\s+(.+)$', rest)
            if not match:
                if self.active_interest_id is not None:
                    try:
                        task = self.service.create_task(self.active_interest_id, rest.strip('"').strip("'"))
                        return {"success": True, "command": "add task", "message": f"Created task #{task['id']} '{task['title']}'", "action": "refresh", "data": task}
                    except Exception as e:
                        return {"success": False, "command": "add task", "message": f"Error: {str(e)}", "action": "none"}
                return {"success": False, "command": "add task", "message": "Usage: add task <interest> <task_title> or 'touch <title>' inside a topic", "action": "none"}
            interest_name = match.group(1) or match.group(2)
            task_title = match.group(3).strip().strip('"').strip("'")
            try:
                task = self.service.create_task(interest_name, task_title)
                return {"success": True, "command": "add task", "message": f"Created task #{task['id']} '{task['title']}' under '{interest_name}'", "action": "refresh", "data": task}
            except Exception as e:
                return {"success": False, "command": "add task", "message": f"Error: {str(e)}", "action": "none"}

        # -------------------------------------------------------------
        # UNKNOWN COMMAND / TYPO SUGGESTION
        # -------------------------------------------------------------
        suggestion = suggest_closest_command(raw_cmd)
        msg = f"Unknown command: '{raw_cmd}'."
        if suggestion:
            msg += f" Did you mean '{suggestion}'? Type `help` for command list."
        else:
            msg += " Type `help` for available commands."

        return {"success": False, "command": "unknown", "message": msg, "action": "none"}

    def _handle_cd_topic(self, target_name: str) -> Dict[str, Any]:
        try:
            target_id = self.service.resolve_interest_id(target_name, parent_id=self.active_interest_id)
            interest = self.service.get_interest_by_id(target_id, update_access=True)
            self.active_interest_id = interest["id"]
            self.current_view = "topic_detail"
            prompt_str = f"C:\\OBSESSION_MATRIX\\{interest['path'].replace(' → ', '\\')}>"
            # Silent entry — only the prompt changes. User runs 'ls' to see contents.
            return {"success": True, "command": "cd", "message": "", "action": "open_interest", "prompt": prompt_str}
        except Exception as e:
            return {"success": False, "command": "cd", "message": f"Error opening topic '{target_name}': {str(e)}", "action": "none"}

    def _format_settings_message(self) -> Dict[str, Any]:
        settings = self.service.get_all_settings()
        lines = [
            "======================================================================",
            "[APPLICATION SETTINGS]",
            "======================================================================",
            f"  1. paste_restriction     : {settings.get('paste_restriction', 'true')} (disables clipboard paste)",
            f"  2. theme                 : {settings.get('theme', 'classic-cmd')} (options: classic-cmd, matrix-green, powershell-blue, amber-crt)",
            f"  3. notifications_enabled : {settings.get('notifications_enabled', 'true')} (true / false)",
            f"  4. notification_interval : {settings.get('notification_interval', '60')} (minutes)",
            f"  5. notification_sound    : {settings.get('notification_sound', 'true')} (true / false)",
            "----------------------------------------------------------------------",
            "[Commands: 'set <key> <value>', 'toggle <key>', 'cd ..']"
        ]
        return {"success": True, "command": "ls", "message": "\n".join(lines), "action": "print"}

    def _get_main_menu_text(self) -> str:
        return (
            "======================================================================\n"
            "OBSESSION MATRIX LOCAL LEARNING TERMINAL v1.0.0\n"
            "======================================================================\n\n"
            "MAIN MENU SECTIONS:\n"
            "  * dashboard   - Dashboard Overview & Progress Summary\n"
            "  * interests   - Interest Hierarchy & Sub-topic Folders\n"
            "  * settings    - Application Settings\n\n"
            "Type 'dashboard', 'interests', or 'settings' to choose a section.\n"
            "(Press <Tab> anytime for command & topic auto-completion)"
        )

    def _format_main_topics_message(self) -> str:
        all_roots = [x for x in self.service.get_all_interests() if x.get("parent_id") is None]
        if not all_roots:
            return "No main topics recorded yet. Use 'mkdir <topic_name>' to create your first main topic."

        lines = [
            "======================================================================",
            "[MAIN INTEREST TOPICS]",
            "======================================================================",
            "MAIN TOPICS LIST:"
        ]
        for item in all_roots:
            obs = " [CURRENT OBSESSION]" if item["is_current_obsession"] else ""
            lines.append(f"  * {item['name']}{obs} (Progress: \"{item['custom_progress']}\")")

        lines.append("\nType 'cd <topic_name>' to enter a topic (e.g. 'cd Cybersecurity'), or 'mkdir <name>' to create a new topic.")
        return "\n".join(lines)

    def _render_dashboard(self) -> Dict[str, Any]:
        dashboard = self.service.get_dashboard_summary()
        obs = dashboard["current_obsession"]
        obs_str = f"{obs['path']} (Progress: \"{obs['custom_progress']}\")" if obs else "NONE SET"
        tc = dashboard["task_counts"]
        
        lines = [
            "----------------------------------------------------------------------",
            "[DASHBOARD OVERVIEW]",
            "----------------------------------------------------------------------",
            f"CURRENT OBSESSION : {obs_str}",
            f"TASK STATS        : Total: {tc['total']} | Not Started: {tc['not_started']} | In Progress: {tc['in_progress']} | Done: {tc['done']}",
            "\nTASKS IN PROGRESS:"
        ]
        if not dashboard["in_progress_tasks"]:
            lines.append("  (No active tasks in progress)")
        else:
            for t in dashboard["in_progress_tasks"]:
                lines.append(f"  #{t['id']} - {t['title']} [{t['interest_path']}]")

        lines.append("\nRECENTLY ACCESSED INTERESTS:")
        if not dashboard["recent_interests"]:
            lines.append("  (No interests created yet)")
        else:
            for i in dashboard["recent_interests"]:
                lines.append(f"  * {i['name']} ({i['path']}) [{i['custom_progress']}]")

        lines.append("")
        lines.append("----------------------------------------------------------------------")
        lines.append("AVAILABLE DASHBOARD COMMANDS:")
        lines.append("  * current set \"<topic>\"   — Set topic as Current Obsession")
        lines.append("  * current clear           — Clear Current Obsession")
        lines.append("  * done <task_id>          — Mark a task as completed")
        lines.append("  * cd <topic_name>         — Jump directly into a topic folder")
        lines.append("  * cd ..                   — Return to Main Menu")
        lines.append("----------------------------------------------------------------------")
        return {"success": True, "command": "dashboard", "message": "\n".join(lines), "action": "navigate_view", "target_view": "dashboard", "prompt": "C:\\OBSESSION_MATRIX\\dashboard>"}

    def _format_single_interest_detail(self, interest_id: int) -> Dict[str, Any]:
        interest = self.service.get_interest_by_id(interest_id, update_access=True)
        tasks = self.service.get_tasks_for_interest(interest_id)
        
        all_tree = self.service.get_interest_tree()
        
        def find_sub_tree(nodes, target_id):
            for n in nodes:
                if n["interest"]["id"] == target_id:
                    return n
                res = find_sub_tree(n["children"], target_id)
                if res: return res
            return None

        target_node = find_sub_tree(all_tree, interest_id)
        
        lines = [
            "======================================================================",
            f"TOPIC: {interest['name']}",
            "======================================================================",
            f"PATH     : \\{interest['path'].replace(' → ', '\\')}",
            f"PROGRESS : \"{interest['custom_progress']}\"",
            f"STATUS   : {'[CURRENT OBSESSION]' if interest['is_current_obsession'] else 'Normal'}",
            "\n[TREE STRUCTURE]:"
        ]

        if target_node and target_node["children"]:
            def format_sub_tree(node, prefix=""):
                i = node["interest"]
                obs_tag = " [CURRENT OBSESSION]" if i["is_current_obsession"] else ""
                lines.append(f"{prefix}├── {i['name']}{obs_tag} ({i['custom_progress']})")
                for child in node["children"]:
                    format_sub_tree(child, prefix + "│   ")
            
            lines.append(target_node["interest"]["name"])
            for child in target_node["children"]:
                format_sub_tree(child, "")
        else:
            lines.append(f"{interest['name']} (No sub-topics yet. Use 'mkdir <name>' to create one)")

        lines.append("\n[TASKS]:")
        if not tasks:
            lines.append("  (No tasks created. Use 'touch <title>' to create a task)")
        else:
            for t in tasks:
                lines.append(f"  #{t['id']} [{t['status'].upper()}] {t['title']}")

        lines.append("")
        lines.append("----------------------------------------------------------------------")
        lines.append("PROGRESS DESCRIPTION LOG:")
        lines.append("  1. progress view          — View all progress log entries (commit titles)")
        lines.append("  2. progress add           — Add a new progress log entry with title & description")
        lines.append("----------------------------------------------------------------------")
        lines.append("[Commands: 'cd <subtopic>', 'mkdir <name>', 'touch <title>', 'progress view', 'progress add \"<title>\" \"<desc>\"', 'cd ..']")
        return {"success": True, "command": "open", "message": "\n".join(lines), "action": "open_interest"}
