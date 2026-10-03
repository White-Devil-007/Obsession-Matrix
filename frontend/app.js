/* ==========================================================================
   OBSESSION MATRIX - CMD TERMINAL CONTROLLER (PURE CLIENT STREAM & TAB AUTOFILL)
   ========================================================================== */

(function () {
    let commandHistory = [];
    let historyIndex = -1;
    let pasteRestrictionEnabled = true;
    let allInterests = [];
    let currentActiveInterestId = null;
    let currentView = "main_menu";
    let tabCycleState = null;

    // Base System Commands (Note: 'start' and 'exit' explicitly excluded from Tab autofill)
    const BASE_COMMANDS = [
        "dashboard", "interests", "settings",
        "cd", "cd ..", "back", "help", "open", "current", "current set", "current clear",
        "mkdir", "touch", "rm", "rmdir", "rm task", "delete topic", "delete task",
        "progress", "progress view", "progress add", "progress delete", "history", "done", "set", "toggle", "ls", "dir", "clear"
    ];

    // ----------------------------------------------------------------------
    // PYWEBVIEW API CONNECTOR
    // ----------------------------------------------------------------------
    async function getApi() {
        if (window.pywebview && window.pywebview.api) {
            return window.pywebview.api;
        }
        return new Promise((resolve) => {
            const check = () => {
                if (window.pywebview && window.pywebview.api) {
                    resolve(window.pywebview.api);
                } else {
                    setTimeout(check, 50);
                }
            };
            setTimeout(check, 100);
        });
    }

    // ----------------------------------------------------------------------
    // INITIALIZATION & DYNAMIC TOPIC SUGGESTIONS FETCHING
    // ----------------------------------------------------------------------
    document.addEventListener("DOMContentLoaded", () => {
        initEventListeners();
        window.addEventListener('pywebviewready', () => initApp());
        setTimeout(() => initApp(), 300);
    });

    async function initApp() {
        try {
            const api = await getApi();
            if (api) {
                const settings = await api.get_settings();
                applySettings(settings);
                await refreshTopicSuggestions(api);
                if (api.get_current_context) {
                    const ctx = await api.get_current_context();
                    if (ctx) {
                        currentActiveInterestId = (ctx.active_interest_id !== undefined) ? ctx.active_interest_id : null;
                        currentView = ctx.current_view || "main_menu";
                    }
                }
            }
            focusPrompt();
        } catch (e) {
            console.error("Init Error:", e);
        }
    }

    function applySettings(settings) {
        if (!settings) return;
        pasteRestrictionEnabled = settings.paste_restriction === "true";
        if (settings.theme) {
            document.body.classList.remove('theme-classic-cmd', 'theme-matrix-green', 'theme-powershell-blue', 'theme-amber-crt');
            document.body.classList.add(`theme-${settings.theme}`);
        }
    }

    async function refreshTopicSuggestions(api) {
        try {
            if (!api) api = await getApi();
            if (api && api.get_all_interests) {
                const interests = await api.get_all_interests();
                if (Array.isArray(interests)) {
                    allInterests = interests;
                }
            }
        } catch (e) {
            console.error("Error fetching topic suggestions:", e);
        }
    }

    function focusPrompt() {
        const input = document.getElementById("cli-input");
        if (input) input.focus();
    }

    // ----------------------------------------------------------------------
    // TERMINAL LOG STREAM
    // ----------------------------------------------------------------------
    function logTerminal(text, type = "sys") {
        if (!text) return;
        const out = document.getElementById("terminal-output");
        const line = document.createElement("div");
        line.className = `term-line term-${type}`;
        line.innerText = text;
        out.appendChild(line);
        out.scrollTop = out.scrollHeight;
    }

    function clearTerminal() {
        const out = document.getElementById("terminal-output");
        out.innerHTML = "";
    }

    function getCurrentPromptText() {
        const label = document.querySelector(".cmd-prompt-label");
        return label ? label.innerText : "C:\\OBSESSION_MATRIX>";
    }

    // ----------------------------------------------------------------------
    // RESOLVE ACTIVE CONTEXT (FAILSAFE COMBINING STATE & PROMPT)
    // ----------------------------------------------------------------------
    function resolveActiveContext() {
        let activeId = (currentActiveInterestId !== undefined && currentActiveInterestId !== null) ? currentActiveInterestId : null;
        let view = currentView || "main_menu";

        const promptText = getCurrentPromptText();
        const match = promptText.match(/^C:\\OBSESSION_MATRIX\\([^>]+)>/i);

        if (match) {
            const rawPath = match[1].trim();
            const lowerPath = rawPath.toLowerCase();

            if (lowerPath === "interests") {
                return { activeId: null, view: "interests" };
            }
            if (lowerPath === "settings") {
                return { activeId: null, view: "settings" };
            }
            if (lowerPath === "dashboard") {
                return { activeId: null, view: "dashboard" };
            }

            // Inside a topic or sub-topic folder
            view = "topic_detail";
            if (activeId === null && allInterests.length > 0) {
                const normPath = rawPath.replace(/\\/g, " → ").toLowerCase();
                const found = allInterests.find(i => 
                    (i.path || i.name).toLowerCase() === normPath || 
                    i.name.toLowerCase() === rawPath.toLowerCase()
                );
                if (found) {
                    activeId = found.id;
                }
            }
        } else {
            return { activeId: null, view: "main_menu" };
        }

        return { activeId, view };
    }

    // ----------------------------------------------------------------------
    // EXECUTE CLI COMMAND VIA PYTHON BACKEND
    // ----------------------------------------------------------------------
    async function executeCliCommand(inputStr) {
        const cmd = inputStr.trim();
        if (!cmd) return;

        tabCycleState = null;
        const currentPrompt = getCurrentPromptText();

        // Log user command
        logTerminal(`${currentPrompt} ${cmd}`, "user");

        // History
        commandHistory.push(cmd);
        historyIndex = commandHistory.length;

        // Execute Command on Backend
        const api = await getApi();
        if (!api) {
            logTerminal("Error: Backend API not connected.", "error");
            return;
        }

        try {
            const res = await api.execute_command(cmd);

            // Synchronize active navigation state
            if (res.active_interest_id !== undefined) {
                currentActiveInterestId = res.active_interest_id;
            }
            if (res.current_view !== undefined) {
                currentView = res.current_view;
            }

            // Handle Application Exit
            if (res.action === "exit_app" || cmd.toLowerCase() === "exit") {
                if (api && api.exit_app) {
                    api.exit_app();
                } else {
                    window.close();
                }
                return;
            }

            if (res.action === "clear_terminal") {
                clearTerminal();
                return;
            }

            if (res.prompt) {
                const promptLabel = document.querySelector(".cmd-prompt-label");
                if (promptLabel) promptLabel.innerText = res.prompt;
            }

            if (res.message) {
                const type = res.success ? "sys" : "error";
                logTerminal(res.message, type);
            }

            const cmdLower = cmd.toLowerCase();

            // Refresh settings if set or toggle command was run
            if (res.success && (cmdLower.startsWith("set ") || cmdLower.startsWith("toggle "))) {
                const updatedSettings = await api.get_settings();
                applySettings(updatedSettings);
            }

            // Continuously refresh topic suggestions for live Tab autofill after any successful command
            if (res.success) {
                refreshTopicSuggestions(api);
            }
        } catch (err) {
            logTerminal(`Execution Error: ${err.message || err}`, "error");
        }
    }

    // ----------------------------------------------------------------------
    // SYSTEM WIDE DYNAMIC TAB AUTO-COMPLETION & STRICT HIERARCHICAL CYCLING
    // ----------------------------------------------------------------------
    function handleTabCompletion(e) {
        const input = document.getElementById("cli-input");
        if (!input) return;

        // 1. Consecutive Tab Press: Cycle through active candidates
        if (tabCycleState && tabCycleState.candidates.length > 0 && input.value === tabCycleState.lastValue) {
            if (e && e.shiftKey) {
                tabCycleState.index = (tabCycleState.index - 1 + tabCycleState.candidates.length) % tabCycleState.candidates.length;
            } else {
                tabCycleState.index = (tabCycleState.index + 1) % tabCycleState.candidates.length;
            }
            applyCompletionCandidate(input, tabCycleState);
            return;
        }

        // 2. Fresh Tab Completion: Reset cycle state and build candidate list
        tabCycleState = null;
        const val = input.value;
        const valLower = val.toLowerCase();

        // Prevent autofill for start or exit
        if (valLower === "start" || valLower === "exit") {
            return;
        }

        const { activeId, view } = resolveActiveContext();
        let cmdPrefix = "";
        let candidates = [];

        // Check commands that take topic/subtopic arguments
        const topicCmds = [
            "cd ", "open ", "rm ", "rmdir ", "delete topic ", "delete interest ",
            "current set ", "add task "
        ];

        let matchedTopicCmd = topicCmds.find(c => valLower.startsWith(c));

        if (matchedTopicCmd) {
            cmdPrefix = val.substring(0, matchedTopicCmd.length);
            const rawArg = val.substring(matchedTopicCmd.length).trim();
            const arg = rawArg.replace(/^["']/, "").toLowerCase();

            if (matchedTopicCmd === "cd " || matchedTopicCmd === "open " || matchedTopicCmd === "rm " || matchedTopicCmd === "rmdir " || matchedTopicCmd.startsWith("delete topic") || matchedTopicCmd.startsWith("delete interest")) {
                if (activeId !== null) {
                    // Inside an active topic: STRICTLY and ONLY immediate child sub-topics of THIS topic!
                    const children = allInterests.filter(i => 
                        i.parent_id !== null && i.parent_id !== undefined && Number(i.parent_id) === Number(activeId)
                    );
                    const matchingChildren = children.filter(i => i.name.toLowerCase().startsWith(arg));

                    // Neat hierarchy: never propose main topics or other topics' sub-topics
                    candidates = matchingChildren.map(i => i.name);
                } else if (view === "interests") {
                    // At interests root: STRICTLY and ONLY top-level root topics (parent_id is null)
                    const roots = allInterests.filter(i => i.parent_id === null || i.parent_id === undefined || i.parent_id === "");
                    const matchingRoots = roots.filter(i => i.name.toLowerCase().startsWith(arg));

                    // Neat hierarchy: never propose sub-topics
                    candidates = matchingRoots.map(i => i.name);
                } else if (view === "dashboard") {
                    // From Dashboard: allow navigating to ANY topic or subtopic shown in dashboard!
                    const matching = allInterests.filter(i => i.name.toLowerCase().startsWith(arg));
                    candidates = matching.map(i => i.name);
                } else if (view === "main_menu") {
                    // At root menu: available sections are dashboard, interests, settings
                    const sections = ["dashboard", "interests", "settings"];
                    candidates = sections.filter(s => s.startsWith(arg));
                } else {
                    const roots = allInterests.filter(i => i.parent_id === null || i.parent_id === undefined || i.parent_id === "");
                    candidates = roots.filter(i => i.name.toLowerCase().startsWith(arg)).map(i => i.name);
                }
            } else if (matchedTopicCmd === "current set ") {
                // Setting current obsession can target any topic across the system
                candidates = allInterests.filter(i => i.name.toLowerCase().startsWith(arg)).map(i => i.name);
            } else {
                candidates = allInterests.filter(i => i.name.toLowerCase().startsWith(arg)).map(i => i.name);
            }
        } else if (valLower.startsWith("progress ")) {
            cmdPrefix = "progress ";
            const subArg = val.substring(9).toLowerCase().trim();
            const subOptions = ["view", "add", "delete"];
            candidates = subOptions.filter(o => o.startsWith(subArg));
        } else if (valLower.startsWith("task status ")) {
            cmdPrefix = val.substring(0, val.lastIndexOf(" ") + 1);
            const stArg = val.substring(cmdPrefix.length).toLowerCase().trim();
            candidates = ["not_started", "in_progress", "done"].filter(s => s.startsWith(stArg));
        } else if (valLower.startsWith("set theme ")) {
            cmdPrefix = "set theme ";
            const thArg = val.substring(10).toLowerCase().trim();
            candidates = ["classic-cmd", "matrix-green", "powershell-blue", "amber-crt"].filter(t => t.startsWith(thArg));
        } else if (valLower.startsWith("set ") || valLower.startsWith("toggle ")) {
            const spaceIdx = val.indexOf(" ") + 1;
            cmdPrefix = val.substring(0, spaceIdx);
            const setArg = val.substring(spaceIdx).toLowerCase().trim();
            const keys = ["paste_restriction", "theme", "notifications_enabled", "notification_interval", "notification_sound"];
            candidates = keys.filter(k => k.startsWith(setArg));
        } else {
            // Typing starting letters or base commands directly (e.g. 'w' for WebSec)
            const raw = valLower.trim();

            if (activeId !== null) {
                // User is inside a topic: STRICTLY and ONLY sub-topics of THIS topic!
                const children = allInterests.filter(i => 
                    i.parent_id !== null && i.parent_id !== undefined && Number(i.parent_id) === Number(activeId)
                );
                const matchingChildren = children.filter(i => i.name.toLowerCase().startsWith(raw));

                // Convert matching sub-topics to "cd <subtopic>"
                const subTopicCmds = matchingChildren.map(i => 
                    `cd ${i.name.includes(" ") ? `"${i.name}"` : i.name}`
                );

                // Base commands matching this starting letter
                const matchingCmds = BASE_COMMANDS.filter(c => c.toLowerCase().startsWith(raw));

                // Sub-topics inside the main topic come first, then commands
                candidates = [...subTopicCmds, ...matchingCmds];
            } else if (view === "interests") {
                // User is at interests root: STRICTLY and ONLY main topics!
                const roots = allInterests.filter(i => i.parent_id === null || i.parent_id === undefined || i.parent_id === "");
                const matchingRoots = roots.filter(i => i.name.toLowerCase().startsWith(raw));

                const rootTopicCmds = matchingRoots.map(i => 
                    `cd ${i.name.includes(" ") ? `"${i.name}"` : i.name}`
                );

                const matchingCmds = BASE_COMMANDS.filter(c => c.toLowerCase().startsWith(raw));

                candidates = [...rootTopicCmds, ...matchingCmds];
            } else if (view === "dashboard") {
                // User is in Dashboard: can navigate to topics/subtopics shown in dashboard
                const matching = allInterests.filter(i => i.name.toLowerCase().startsWith(raw));
                const topicCmds = matching.map(i => 
                    `cd ${i.name.includes(" ") ? `"${i.name}"` : i.name}`
                );

                const matchingCmds = BASE_COMMANDS.filter(c => c.toLowerCase().startsWith(raw));

                candidates = [...topicCmds, ...matchingCmds];
            } else if (view === "main_menu") {
                const sections = ["dashboard", "interests", "settings"];
                const matchingSections = sections.filter(s => s.startsWith(raw));
                const matchingCmds = BASE_COMMANDS.filter(c => c.toLowerCase().startsWith(raw));

                candidates = Array.from(new Set([...matchingSections, ...matchingCmds]));
            } else {
                candidates = BASE_COMMANDS.filter(c => c.toLowerCase().startsWith(raw));
            }
        }

        if (candidates.length === 0) {
            return;
        }

        tabCycleState = {
            cmdPrefix: cmdPrefix,
            candidates: candidates,
            index: 0,
            lastValue: ""
        };

        applyCompletionCandidate(input, tabCycleState);
    }

    function applyCompletionCandidate(input, state) {
        const candidate = state.candidates[state.index];
        let text = candidate;
        if (state.cmdPrefix) {
            if (candidate.includes(" ") && !candidate.startsWith('"') && !candidate.endsWith('"')) {
                text = `"${candidate}"`;
            }
            input.value = `${state.cmdPrefix}${text}`;
        } else {
            // Add trailing space for prefix commands if matching complete command
            if (["cd", "mkdir", "touch", "open", "rm", "rmdir", "done", "set", "toggle"].includes(candidate)) {
                text = `${candidate} `;
            }
            input.value = text;
        }
        state.lastValue = input.value;
        input.setSelectionRange(input.value.length, input.value.length);
    }

    // ----------------------------------------------------------------------
    // EVENT LISTENERS & KEYBOARD BINDINGS
    // ----------------------------------------------------------------------
    function initEventListeners() {
        // CRT Toggle
        const crtBtn = document.getElementById("btn-toggle-crt");
        if (crtBtn) {
            crtBtn.onclick = () => {
                document.body.classList.toggle("crt-overlay");
                crtBtn.innerText = document.body.classList.contains("crt-overlay") ? "CRT: ON" : "CRT: OFF";
            };
        }

        // Prompt Input Key Events
        const cliInput = document.getElementById("cli-input");
        if (!cliInput) return;

        cliInput.addEventListener("input", () => {
            tabCycleState = null;
        });

        cliInput.addEventListener("keydown", (e) => {
            if (e.key === "Enter") {
                e.preventDefault();
                tabCycleState = null;
                const val = cliInput.value;
                cliInput.value = "";
                executeCliCommand(val);
            } else if (e.key === "Tab") {
                e.preventDefault();
                handleTabCompletion(e);
            } else if (e.key === "ArrowUp") {
                e.preventDefault();
                tabCycleState = null;
                if (commandHistory.length > 0 && historyIndex > 0) {
                    historyIndex--;
                    cliInput.value = commandHistory[historyIndex];
                }
            } else if (e.key === "ArrowDown") {
                e.preventDefault();
                tabCycleState = null;
                if (historyIndex < commandHistory.length - 1) {
                    historyIndex++;
                    cliInput.value = commandHistory[historyIndex];
                } else {
                    historyIndex = commandHistory.length;
                    cliInput.value = "";
                }
            } else if (e.key !== "Shift" && e.key !== "Control" && e.key !== "Alt") {
                tabCycleState = null;
            }
        });

        // Paste Restriction
        document.addEventListener("paste", (e) => {
            if (pasteRestrictionEnabled) {
                e.preventDefault();
                logTerminal("[PASTE RESTRICTION] Manual typing enforced. Clipboard paste disabled.", "error");
            }
        }, true);

        // Always keep focus on terminal prompt input
        document.addEventListener("click", () => {
            focusPrompt();
        });
    }

})();
