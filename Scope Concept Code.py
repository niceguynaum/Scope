import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import os
import shutil
from collections import Counter
import re
import datetime
import json
import sys
from tkinter import font

# --- Global Data Storage and Configuration ---
SESSIONS_INDEX_FILE = "scope_sessions_index_file.json"
EXCEPTION_DEFINITIONS_FILE = "exceptions_data.json"
SESSION_BASE_DIR = "Scope_Sessions"
SESSION_DATA_FILENAME = "session.json"
SESSION_LOGS_SUBDIR = "logs"

ESCALATION_TEMPLATE_FILE = "EscalationTemplate.md"

troubleshooting_sessions = {}
current_session_name = None
current_selected_stack_trace_content = None


class ScopeApp:
    def __init__(self, master):
        self.master = master
        master.title("Scope")
        master.geometry("1000x700")

        self.stack_trace_font_size = 9
        self.notes_default_font_family = "Ubuntu"
        self.notes_default_font_size = 11

        self.define_button = None 
        self.status_textbox = None 
        self.current_session_data = None
        self.relevant_files_label = None
        self.search_entry = None
        self.search_term_var = tk.StringVar()

        try:
            self.load_exception_definitions()
            self.load_escalation_template()
        except (FileNotFoundError, RuntimeError) as e:
            messagebox.showerror("Initialization Error", f"Scope cannot start: {e}\nPlease ensure '{EXCEPTION_DEFINITIONS_FILE}' and '{ESCALATION_TEMPLATE_FILE}' exist and are valid.")
            master.destroy()
            sys.exit(1)

        self.load_sessions()
        os.makedirs(SESSION_BASE_DIR, exist_ok=True)

        self.create_main_menu()

    def load_sessions(self):
        global troubleshooting_sessions
        if os.path.exists(SESSIONS_INDEX_FILE):
            try:
                with open(SESSIONS_INDEX_FILE, 'r') as f:
                    troubleshooting_sessions = json.load(f)
            except json.JSONDecodeError as e:
                messagebox.showerror("Error", f"Could not load session index from {SESSIONS_INDEX_FILE}: {e}\nStarting with no previous sessions.")
                troubleshooting_sessions = {}
        else:
            messagebox.showinfo("Info", "No previous sessions index found. Starting fresh.")
            troubleshooting_sessions = {}

    def save_sessions(self):
        global troubleshooting_sessions
        try:
            with open(SESSIONS_INDEX_FILE, 'w') as f:
                json.dump(troubleshooting_sessions, f, indent=4)
        except Exception as e:
            messagebox.showerror("Error", f"Could not save session index to {SESSIONS_INDEX_FILE}: {e}")

    def load_exception_definitions(self):
        global exception_definitions
        if not os.path.exists(EXCEPTION_DEFINITIONS_FILE):
            raise FileNotFoundError(f"Exception definitions file '{EXCEPTION_DEFINITIONS_FILE}' not found.")
        try:
            with open(EXCEPTION_DEFINITIONS_FILE, 'r', encoding='utf-8') as f:
                exception_definitions = json.load(f)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse JSON in '{EXCEPTION_DEFINITIONS_FILE}': {e}")
        except Exception as e:
            raise RuntimeError(f"Failed to load exception definitions from '{EXCEPTION_DEFINITIONS_FILE}': {e}")

    def load_escalation_template(self):
        global escalation_template_content
        if not os.path.exists(ESCALATION_TEMPLATE_FILE):
            raise FileNotFoundError(f"Escalation template file '{ESCALATION_TEMPLATE_FILE}' not found.")
        try:
            with open(ESCALATION_TEMPLATE_FILE, 'r', encoding='utf-8') as f:
                raw_template = f.read()
            
            if "# Place contents of Note Here after clicking \"Escalation Template\"" not in raw_template:
                raise RuntimeError(f"Escalation template '{ESCALATION_TEMPLATE_FILE}' is missing the required '# Place contents...' section.")
            
            escalation_template_content = raw_template

        except Exception as e:
            raise RuntimeError(f"Failed to load escalation template from '{ESCALATION_TEMPLATE_FILE}': {e}")

    def create_main_menu(self):
        for widget in self.master.winfo_children():
            widget.destroy()

        self.main_frame = tk.Frame(self.master)
        self.main_frame.pack(expand=True, fill="both")

        tk.Label(self.main_frame, text="Welcome to Scope!", font=("Ubuntu", 24, "bold")).pack(pady=60)

        self.start_button = tk.Button(self.main_frame, text="Start Troubleshooting", command=self.show_start_window, width=30, height=3, font=("Ubuntu", 16, "bold"), bg="#4CAF50", fg="black", activebackground="#45a049", activeforeground="black")
        self.start_button.pack(pady=30)

        self.continue_button = tk.Button(self.main_frame, text="Continue Troubleshooting", command=self.show_continue_troubleshooting_window, width=30, height=3, font=("Ubuntu", 16, "bold"), bg="#2196F3", fg="black", activebackground="#1976D2", activeforeground="black")
        self.continue_button.pack(pady=30)

        self.exit_button = tk.Button(self.main_frame, text="Exit", command=self.master.quit, width=30, height=3, font=("Ubuntu", 16, "bold"), bg="#F44336", fg="black", activebackground="#D32F2F", activeforeground="black")
        self.exit_button.pack(pady=30)

    def show_start_window(self):
        for widget in self.master.winfo_children():
            widget.destroy()

        self.start_frame = tk.Frame(self.master)
        self.start_frame.pack(expand=True, fill="both", padx=60, pady=60)

        tk.Label(self.start_frame, text="Select Log File(s) to Analyze:", font=("Ubuntu", 16, "bold")).pack(pady=25)

        self.log_file_paths_var = tk.StringVar(value="No files selected.")
        self.log_file_paths_label = tk.Label(self.start_frame, textvariable=self.log_file_paths_var, wraplength=500, justify="left", font=("Ubuntu", 10), bd=1, relief="sunken", bg="white", fg="black")
        self.log_file_paths_label.pack(pady=10, fill="x", padx=20)

        self.browse_button = tk.Button(self.start_frame, text="Browse Files", command=self.browse_log_files, font=("Ubuntu", 12), bg="#607D8B", fg="black", activeforeground="black")
        self.browse_button.pack(pady=15)

        self.analyze_button = tk.Button(self.start_frame, text="Start Analysis", command=self.start_new_troubleshooting_session, font=("Ubuntu", 16, "bold"), bg="#FFC107", fg="black", activeforeground="black")
        self.analyze_button.pack(pady=20)

        # Status Textbox on Start Window
        tk.Label(self.start_frame, text="Status:", font=("Ubuntu", 12, "bold")).pack(pady=(10, 5), anchor="w")
        self.status_textbox = scrolledtext.ScrolledText(self.start_frame, height=5, wrap="word", font=("Courier New", 10), 
                                                        bg="#2F3136", fg="white", relief="sunken", bd=1, state="disabled")
        self.status_textbox.pack(pady=(0, 10), fill="x", padx=20)

        self.back_button = tk.Button(self.start_frame, text="Back to Main Menu", command=self.create_main_menu, font=("Ubuntu", 12), activeforeground="black")
        self.back_button.pack(pady=10)

    def browse_log_files(self):
        file_paths = filedialog.askopenfilenames(
            title="Select Log Files",
            filetypes=[("Log files", "*.log"), ("Text files", "*.txt"), ("All files", "*.*")]
        )
        if file_paths:
            self.selected_log_files = file_paths
            display_text = "\n".join([os.path.basename(p) for p in file_paths])
            if len(file_paths) > 3:
                display_text = f"{len(file_paths)} files selected:\n" + "\n".join([os.path.basename(p) for p in file_paths[:3]]) + "\n..."
            self.log_file_paths_var.set(display_text)
        else:
            self.selected_log_files = ()
            self.log_file_paths_var.set("No files selected.")


    def _update_status(self, message, append=True):
        if self.status_textbox:
            self.status_textbox.config(state="normal")
            if not append:
                self.status_textbox.delete("1.0", tk.END)
            self.status_textbox.insert(tk.END, message + "\n")
            self.status_textbox.see(tk.END)
            self.status_textbox.config(state="disabled")
            self.master.update_idletasks()

    def start_new_troubleshooting_session(self):
        if not hasattr(self, 'selected_log_files') or not self.selected_log_files:
            messagebox.showerror("Error", "Please select one or more log files to analyze.")
            return

        self._update_status("Starting new session...", append=False)

        try:
            global current_session_name
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            default_session_name = f"Session_{timestamp}"
            i = 1
            temp_name = default_session_name
            while temp_name in troubleshooting_sessions:
                temp_name = f"{default_session_name}_{i}"
                i += 1
            current_session_name = temp_name

            session_root_dir = os.path.join(SESSION_BASE_DIR, current_session_name)
            logs_subdir = os.path.join(session_root_dir, SESSION_LOGS_SUBDIR)
            os.makedirs(logs_subdir, exist_ok=True)

            total_files_to_process = len(self.selected_log_files)
            self._update_status(f"Reading {total_files_to_process} file(s) for analysis...")
            
            log_contents_dict = {}
            for i, original_path in enumerate(self.selected_log_files):
                filename = os.path.basename(original_path)
                self._update_status(f"Reading '{filename}' ({i+1}/{total_files_to_process})...")
                try:
                    with open(original_path, 'r', encoding='utf-8', errors='ignore') as f:
                        log_contents_dict[filename] = f.read()
                except Exception as e:
                    self._update_status(f"WARNING: Could not read '{filename}': {e}. Skipping.", append=True)
                    log_contents_dict[filename] = ""
            
            if not log_contents_dict or all(not content for content in log_contents_dict.values()):
                self._update_status("ERROR: No readable content found among your selection. Aborting.", append=True)
                messagebox.showerror("Error", "No readable log files found among your selection. Aborting analysis.")
                shutil.rmtree(session_root_dir)
                return

            self._update_status(f"Copying {len(log_contents_dict)} file(s) to '{os.path.basename(logs_subdir)}' in session directory...")
            copied_files_for_analysis_paths = []
            copied_count = 0
            for i, (filename, content) in enumerate(log_contents_dict.items()):
                if content:
                    dest_path = os.path.join(logs_subdir, filename)
                    self._update_status(f"Saving '{filename}' ({i+1}/{len(log_contents_dict)})...")
                    try:
                        with open(dest_path, 'w', encoding='utf-8') as f:
                            f.write(content)
                        copied_files_for_analysis_paths.append(dest_path)
                        copied_count += 1
                    except Exception as e:
                        self._update_status(f"WARNING: Failed to save '{filename}' to session directory: {e}. This file may not be in session folder.", append=True)

            if copied_count == 0:
                self._update_status("ERROR: No log files could be saved to the session directory. Aborting.", append=True)
                messagebox.showerror("Error", "No log files could be saved to the session directory. Aborting analysis.")
                shutil.rmtree(session_root_dir)
                return

            self._update_status(f"Aggregating content from {copied_count} copied file(s) for analysis...")
            full_log_content = ""
            for copied_file_path in copied_files_for_analysis_paths:
                try:
                    with open(copied_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        full_log_content += f.read() + "\n"
                except Exception as e:
                    self._update_status(f"WARNING: Could not read copied file '{os.path.basename(copied_file_path)}' for aggregation: {e}.", append=True)

            if not full_log_content.strip():
                self._update_status("ERROR: No aggregated content found for analysis. Aborting.", append=True)
                messagebox.showerror("Error", "No aggregated content found for analysis. Aborting analysis.")
                return

            self._update_status("Analyzing log file(s) for stack traces. This may take a moment...")
            self.master.update_idletasks()

            unique_stack_traces_raw = self.extract_stack_traces(full_log_content)
            counted_traces = Counter(unique_stack_traces_raw)
            processed_traces = self.process_stack_traces_for_dashboard(counted_traces)

            self.current_session_data = {
                "session_name": current_session_name,
                "notes": "",
                "files_path": session_root_dir,
                "stack_traces_data": processed_traces,
                "current_selected_stack_trace_content": None
            }
            session_data_file_path = os.path.join(session_root_dir, SESSION_DATA_FILENAME)
            with open(session_data_file_path, 'w', encoding='utf-8') as f:
                json.dump(self.current_session_data, f, indent=4)

            troubleshooting_sessions[current_session_name] = session_root_dir
            self.save_sessions()

            self._update_status("Analysis complete. Loading dashboard...", append=True)
            self.master.after(500, lambda s=self: s.show_troubleshooting_dashboard(current_session_name))
            
        except Exception as e:
            self._update_status(f"CRITICAL ERROR: {e}. Analysis aborted.", append=True)
            messagebox.showerror("Analysis Error", f"An unexpected error occurred during analysis: {e}")
            if 'session_root_dir' in locals() and os.path.exists(session_root_dir):
                try:
                    shutil.rmtree(session_root_dir)
                    self._update_status(f"Cleaned up partially created session directory '{os.path.basename(session_root_dir)}'.", append=True)
                except Exception as cleanup_e:
                    self._update_status(f"WARNING: Failed to clean up session directory: {cleanup_e}.", append=True)


    def extract_stack_traces(self, log_content):
        stack_trace_pattern = re.compile(
            r"(?:Traceback \(most recent call last\):[\s\S]*?(?=\n(?:[A-Z]+:\s+\S+|\d{4}-\d{2}-\d{2})|\Z)"
            r"|\b(?:[a-zA-Z_][a-zA-Z0-9_]*\.)*[a-zA-Z_][a-zA-Z0-9_]*(?:Error|Exception|Warning|Throwable|RuntimeException)(?=[:\s\n]|$)(?:.*?\n)*?(?=\n(?!(?:\s*at\s+|Caused by:|^\s*\.\.\.\s+\d+\s+more\s*$))(?=\S+)|^\s*(?:[A-Z]+:\s+\S+|\d{4}-\d{2}-\d{2})|^\s*\)\s*\}\s*$|^\s*\)\s*\)\s*$|\Z))",
            re.MULTILINE | re.DOTALL
        )
        return stack_trace_pattern.findall(log_content)

    def process_stack_traces_for_dashboard(self, counted_traces):
        processed_data = {}
        full_exception_name_regex = re.compile(
            r'\b(?:[a-zA-Z_][a-zA-Z0-9_]*\.)*[a-zA-Z_][a-zA-Z0-9_]*(?:Error|Exception|Warning|Throwable|RuntimeException)\b(?=:\s|$)'
        )
        simple_exception_name_regex = re.compile(
            r'([a-zA-Z_][a-zA-Z0-9_]*(?:Error|Exception|Warning|Throwable|RuntimeException))\b$'
        )

        for trace_content, count in counted_traces.items():
            assigned_weight = 1
            displayed_exception_name = "Unknown Error"
            
            best_exception_class_key = None
            best_log_package_key = None
            
            highest_exc_weight = 0
            
            longest_pkg_match_len = 0

            extracted_full_name_from_log = None
            extracted_simple_name_from_log = None
            
            lines = trace_content.split('\n')
            for line in lines:
                full_match = full_exception_name_regex.search(line)
                if full_match:
                    extracted_full_name_from_log = full_match.group(0)
                    simple_match = simple_exception_name_regex.search(extracted_full_name_from_log)
                    if simple_match:
                        extracted_simple_name_from_log = simple_match.group(1)
                    break

            if extracted_full_name_from_log:
                displayed_exception_name = extracted_full_name_from_log

                if extracted_simple_name_from_log and extracted_simple_name_from_log in exception_definitions:
                    def_data = exception_definitions[extracted_simple_name_from_log]
                    if "weighting" in def_data: 
                        best_exception_class_key = extracted_simple_name_from_log
                        highest_exc_weight = def_data["weighting"]

                for defined_key, def_data in exception_definitions.items():
                    if "." in defined_key and "weighting" not in def_data:
                        if defined_key in extracted_full_name_from_log:
                            if len(defined_key) > longest_pkg_match_len:
                                best_log_package_key = defined_key
                                longest_pkg_match_len = len(defined_key)
            
            assigned_weight = max(highest_exc_weight, 1)

            processed_data[trace_content] = {
                "count": count,
                "weight": assigned_weight,
                "exception_name": displayed_exception_name,
                "exception_class_key": best_exception_class_key,
                "log_package_key": best_log_package_key,
                "selected_for_investigation": False
            }
        return processed_data

    def show_troubleshooting_dashboard(self, session_name):
        global current_session_name
        current_session_name = session_name

        session_root_path = troubleshooting_sessions[current_session_name]
        session_data_file = os.path.join(session_root_path, SESSION_DATA_FILENAME)
        try:
            with open(session_data_file, 'r', encoding='utf-8') as f:
                self.current_session_data = json.load(f)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load session data for '{session_name}': {e}")
            self.create_main_menu()
            return


        for widget in self.master.winfo_children():
            widget.destroy()

        self.dashboard_frame = tk.Frame(self.master, padx=10, pady=10, bg="#2F3136")
        self.dashboard_frame.pack(expand=True, fill="both")

        top_frame = tk.Frame(self.dashboard_frame, bg="#2F3136")
        top_frame.pack(fill="x", pady=(0, 10))

        self.dashboard_title_var = tk.StringVar(value=current_session_name)
        self.dashboard_title_label = tk.Label(top_frame, textvariable=self.dashboard_title_var, font=("Ubuntu", 20, "bold"), bg="#2F3136", fg="black")
        self.dashboard_title_label.pack(side="left", padx=(0, 20))

        rename_frame = tk.Frame(top_frame, bg="#2F3136")
        rename_frame.pack(side="left", fill="x", expand=True)

        tk.Label(rename_frame, text="Rename:", font=("Ubuntu", 11), bg="#2F3136", fg="white").pack(side="left")
        self.rename_entry = tk.Entry(rename_frame, width=30, font=("Ubuntu", 11), bd=1, relief="solid",
                                   insertbackground="blue", selectbackground="#A0C8F0", selectforeground="black",
                                   highlightbackground="grey", highlightcolor="grey", highlightthickness=1)
        self.rename_entry.pack(side="left", padx=5)
        tk.Button(rename_frame, text="Apply Rename", command=lambda s=self: s.rename_dashboard(), font=("Ubuntu", 10), bg="#4CAF50", fg="black", activeforeground="black").pack(side="left")

        # Search Bar
        self.search_term_var.set("")
        search_frame = tk.Frame(top_frame, bg="#2F3136")
        search_frame.pack(side="right", padx=(20,0))

        tk.Label(search_frame, text="Search:", font=("Ubuntu", 11), bg="#2F3136", fg="white").pack(side="left")
        self.search_entry = tk.Entry(search_frame, textvariable=self.search_term_var, width=20, font=("Ubuntu", 11), bd=1, relief="solid",
                                    insertbackground="blue", selectbackground="#A0C8F0", selectforeground="black",
                                    highlightbackground="grey", highlightcolor="grey", highlightthickness=1)
        self.search_entry.pack(side="left", padx=5)
        self.search_entry.bind("<KeyRelease>", lambda e, s=self: s._perform_search(e))


        self.master_pane = tk.PanedWindow(self.dashboard_frame, orient=tk.VERTICAL, sashrelief=tk.RAISED, sashwidth=8, bd=2, bg="#2F3136")
        self.master_pane.pack(expand=True, fill="both")

        self.top_horizontal_pane = tk.PanedWindow(self.master_pane, orient=tk.HORIZONTAL, sashrelief=tk.RAISED, sashwidth=8, bd=2, bg="#2F3136")
        self.master_pane.add(self.top_horizontal_pane)

        traces_pane = tk.Frame(self.top_horizontal_pane, bd=2, relief="groove", bg="#FFFFFF")
        self.top_horizontal_pane.add(traces_pane)

        traces_header_frame = tk.Frame(traces_pane, bg="#FFFFFF")
        traces_header_frame.pack(fill="x", pady=(10, 5), padx=10)

        tk.Label(traces_header_frame, text="Detected Stack Traces:", font=("Ubuntu", 14, "bold"), bg="#FFFFFF").pack(side="left", padx=(0, 10))

        self.define_button = tk.Button(traces_header_frame, text="Define", command=lambda s=self: s.open_definition_popup(),
                                       font=("Ubuntu", 10, "bold"), bg="#607D8B", fg="black", activebackground="#455A64", activeforeground="black",
                                       state=tk.DISABLED)
        self.define_button.pack(side="right")

        self.trace_canvas = tk.Canvas(traces_pane, bg="#FFFFFF")
        self.trace_scrollbar = tk.Scrollbar(traces_pane, orient="vertical", command=self.trace_canvas.yview)
        self.scrollable_trace_frame = tk.Frame(self.trace_canvas, bg="#FFFFFF")

        self.scrollable_trace_frame.bind(
            "<Configure>",
            lambda e: self.trace_canvas.configure(
                scrollregion=self.trace_canvas.bbox("all")
            )
        )

        self.trace_canvas.create_window((0, 0), window=self.scrollable_trace_frame, anchor="nw")
        self.trace_canvas.configure(yscrollcommand=self.trace_scrollbar.set)

        self.trace_canvas.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        self.trace_scrollbar.pack(side="right", fill="y")

        self.trace_buttons = {}
        sorted_traces = sorted(self.current_session_data["stack_traces_data"].items(),
                               key=lambda item: (item[1]['weight'], item[1]['count']), reverse=True)

        for trace_content, data in sorted_traces:
            button_text = f"[{data['weight']}] {data['exception_name']} (x{data['count']})"
            btn = tk.Button(self.scrollable_trace_frame, text=button_text,
                            command=lambda s=self, tc=trace_content: s.select_stack_trace(tc),
                            font=("Ubuntu", 10), anchor="w", justify="left",
                            bg="#E0E0E0", fg="black", activebackground="#D0D0D0", activeforeground="black", bd=1, relief="raised")
            btn.pack(fill="x", pady=2, padx=5)
            btn.trace_data_keys = {'exception_class_key': data['exception_class_key'], 'log_package_key': data['log_package_key']}
            self.trace_buttons[trace_content] = btn

        details_pane = tk.Frame(self.top_horizontal_pane, bd=2, relief="groove", bg="#FFFFFF")
        self.top_horizontal_pane.add(details_pane)

        stack_trace_header_frame = tk.Frame(details_pane, bg="#FFFFFF")
        stack_trace_header_frame.pack(fill="x", pady=(10, 5), padx=10)

        tk.Label(stack_trace_header_frame, text="Full Stack Trace:", font=("Ubuntu", 14, "bold"), bg="#FFFFFF").pack(side="left")
        self.current_stack_trace_title = tk.Label(stack_trace_header_frame, text="No Trace Selected", font=("Ubuntu", 12, "italic"), bg="#FFFFFF")
        self.current_stack_trace_title.pack(side="left", padx=10, expand=True, fill="x")

        tk.Button(stack_trace_header_frame, text="Copy Trace", command=lambda s=self: s.copy_stack_trace_to_clipboard(),
                                           font=("Ubuntu", 10, "bold"), bg="#607D8B", fg="black", activebackground="#455A64", activeforeground="black").pack(side="right", padx=(5, 0))

        tk.Button(stack_trace_header_frame, text="A+", command=lambda s=self: s.increase_stack_trace_font_size(),
                                       font=("Ubuntu", 10, "bold"), bg="#607D8B", fg="black", activebackground="#455A64", activeforeground="black").pack(side="right", padx=(5, 0))

        tk.Button(stack_trace_header_frame, text="A-", command=lambda s=self: s.decrease_stack_trace_font_size(),
                                       font=("Ubuntu", 10, "bold"), bg="#607D8B", fg="black", activebackground="#455A64", activeforeground="black").pack(side="right")

        self.stack_trace_code_block = scrolledtext.ScrolledText(details_pane, height=1, wrap="word", font=("Courier New", self.stack_trace_font_size),
                                                                 background="#f0f0f0", foreground="black", relief="sunken", bd=1,
                                                                 insertbackground="blue", selectbackground="#A0C8F0", selectforeground="black",
                                                                 highlightthickness=0)
        self.stack_trace_code_block.pack(fill="both", expand=True, pady=5, padx=10)
        self.stack_trace_code_block.config(state="disabled")

        self.stack_trace_code_block.tag_configure("search_highlight", background="yellow", foreground="black")


        bottom_pane_content = tk.Frame(self.master_pane, bg="#2F3136")
        self.master_pane.add(bottom_pane_content)

        notes_toolbar_frame = tk.Frame(bottom_pane_content, bg="#2F3136")
        notes_toolbar_frame.pack(fill="x", anchor="w", padx=10, pady=(5,0))

        tk.Label(notes_toolbar_frame, text="Notes:", font=("Ubuntu", 14, "bold"), bg="#2F3136", fg="white").pack(side="left", padx=(0,10))

        tk.Button(notes_toolbar_frame, text="Escalation Template", command=lambda s=self: s._apply_escalation_template(),
                                           font=("Ubuntu", 10), bg="#607D8B", fg="black", activebackground="#455A64", activeforeground="black").pack(side="left", padx=5)

        tk.Button(notes_toolbar_frame, text="Insert Code Block", command=lambda s=self: s.insert_code_block(),
                  font=("Ubuntu", 10), bg="#607D8B", fg="black", activebackground="#455A64", activeforeground="black").pack(side="left", padx=5)

        tk.Button(notes_toolbar_frame, text="Insert Trace Name", command=lambda s=self: s.insert_trace_name(),
                  font=("Ubuntu", 10), bg="#607D8B", fg="black", activebackground="#455A64", activeforeground="black").pack(side="left", padx=5)

        self.notes_text = scrolledtext.ScrolledText(bottom_pane_content, height=8, wrap="word", font=(self.notes_default_font_family, self.notes_default_font_size), relief="sunken", bd=1,
                                                 insertbackground="blue", selectbackground="#A0C8F0", selectforeground="black",
                                                 highlightthickness=0)
        self.notes_text.insert(tk.END, self.current_session_data.get("notes", ""))
        self.notes_text.pack(fill="both", expand=True, pady=5, padx=10)
        self.notes_text.bind("<KeyRelease>", lambda e, s=self: s._on_notes_change(e))
        
        self.notes_text.tag_configure("code_block_tag", font=("Courier New", self.notes_default_font_size), background="#404245", foreground="white", relief="flat", borderwidth=0)
        self.notes_text.tag_configure("h1_tag", font=(self.notes_default_font_family, self.notes_default_font_size + 5, "bold"))
        self.notes_text.tag_configure("h2_tag", font=(self.notes_default_font_family, self.notes_default_font_size + 3, "bold"))
        
        self._apply_markdown_formatting()


        self.relevant_files_label = tk.Label(bottom_pane_content, text=f"Relevant Files (copied to: {self.current_session_data['files_path']}):", font=("Ubuntu", 14, "bold"), bg="#2F3136", fg="white")
        self.relevant_files_label.pack(anchor="w", pady=(15, 5), padx=10)
        tk.Button(bottom_pane_content, text="Copy Relevant Files", command=lambda s=self: s.copy_relevant_files(), font=("Ubuntu", 12), bg="#4CAF50", fg="black", activebackground="#45a049", activeforeground="black").pack(pady=10, padx=10, anchor="w")

        bottom_buttons_frame = tk.Frame(self.dashboard_frame, bg="#2F3136")
        bottom_buttons_frame.pack(fill="x", pady=(10, 0))

        tk.Button(bottom_buttons_frame, text="Export Notes (JIRA Markdown)", command=lambda s=self: s.export_notes(), font=("Ubuntu", 12), bg="#FF9800", fg="black", activebackground="#FB8C00", activeforeground="black").pack(side="left", padx=10, expand=True)
        
        self.export_session_button = tk.Button(bottom_buttons_frame, text="Export Session", command=lambda s=self: s.export_current_session(), font=("Ubuntu", 12), bg="#607D8B", fg="black", activebackground="#455A64", activeforeground="black").pack(side="left", padx=10, expand=True) 

        tk.Button(bottom_buttons_frame, text="Back to Main Menu", command=lambda s=self: s.create_main_menu(), font=("Ubuntu", 12), bg="#F44336", fg="black", activebackground="#D32F2F", activeforeground="black").pack(side="right", padx=10, expand=True)

        # FIX: Defer sashpos calls to after the window is fully drawn
        self.master.after(0, lambda: self.master_pane.sashpos(0, 500))
        self.master.after(0, lambda: self.top_horizontal_pane.sashpos(0, 300))

        # Initial selection of stack trace after dashboard loads
        if self.current_session_data["stack_traces_data"]: 
            current_selected_stack_trace_content_from_session = self.current_session_data.get("current_selected_stack_trace_content")
            if current_selected_stack_trace_content_from_session and current_selected_stack_trace_content_from_session in self.current_session_data["stack_traces_data"]:
                 self.select_stack_trace(current_selected_stack_trace_content_from_session)
            else:
                sorted_traces_content = sorted(self.current_session_data["stack_traces_data"].keys(),
                                               key=lambda k: (self.current_session_data["stack_traces_data"][k]['weight'], self.current_session_data["stack_traces_data"][k]['count']), reverse=True)
                if sorted_traces_content:
                    self.select_stack_trace(sorted_traces_content[0])
            self.define_button.config(state=tk.NORMAL)
        else:
            self.current_stack_trace_title.config(text="No Stack Traces Found in Log")
            self.define_button.config(state=tk.DISABLED)

        # After dashboard is fully loaded, perform initial search based on an empty term
        self._perform_search() 


    def select_stack_trace(self, trace_content):
        global current_selected_stack_trace_content
        current_selected_stack_trace_content = trace_content

        data = self.current_session_data["stack_traces_data"].get(trace_content)
        
        self.current_session_data["current_selected_stack_trace_content"] = trace_content
        self.save_current_session_data()

        if data:
            self.stack_trace_code_block.config(state="normal")
            self.stack_trace_code_block.delete("1.0", tk.END)
            self.stack_trace_code_block.insert(tk.END, trace_content)
            self._apply_search_highlight_to_current_trace()
            self.stack_trace_code_block.config(state="disabled")

            self.current_stack_trace_title.config(text=f"{data['exception_name']} (Count: {data['count']}, Weight: {data['weight']})")

            for tr_content, btn_widget in self.trace_buttons.items():
                self._update_trace_button_color(tr_content, btn_widget) 
            
            if self.define_button:
                self.define_button.config(state=tk.NORMAL)

    def _update_trace_button_color(self, trace_content, button_widget):
        # FIX: Declare current_selected_stack_trace_content as global
        global current_selected_stack_trace_content 

        search_term = self.search_term_var.get().strip().lower()
        is_selected = (trace_content == current_selected_stack_trace_content)
        
        if is_selected:
            button_widget.config(relief="sunken", bg="#BBDEFB", fg="black")
        elif search_term and search_term in trace_content.lower():
            button_widget.config(relief="raised", bg="yellow", fg="black")
        else:
            button_widget.config(relief="raised", bg="#E0E0E0", fg="black")


    def _apply_search_highlight_to_current_trace(self):
        self.stack_trace_code_block.tag_remove("search_highlight", "1.0", tk.END)
        search_term = self.search_term_var.get().strip()

        if search_term:
            start_pos = "1.0"
            while True:
                start_pos = self.stack_trace_code_block.search(search_term, start_pos, tk.END, nocase=1)
                if not start_pos:
                    break
                end_pos = self.stack_trace_code_block.index(f"{start_pos}+{len(search_term)}c")
                self.stack_trace_code_block.tag_add("search_highlight", start_pos, end_pos)
                start_pos = end_pos

    def _perform_search(self, event=None):
        self._apply_search_highlight_to_current_trace()

        for trace_content, btn_widget in self.trace_buttons.items():
            self._update_trace_button_color(trace_content, btn_widget)


    def increase_stack_trace_font_size(self):
        max_font_size = 24
        if self.stack_trace_font_size < max_font_size:
            self.stack_trace_font_size += 2
            current_font = font.Font(font=self.stack_trace_code_block['font'])
            current_font.config(size=self.stack_trace_font_size)
            self.stack_trace_code_block.config(font=current_font)

    def decrease_stack_trace_font_size(self):
        min_font_size = 6
        if self.stack_trace_font_size > min_font_size:
            self.stack_trace_font_size -= 2
            current_font = font.Font(font=self.stack_trace_code_block['font'])
            current_font.config(size=self.stack_trace_font_size)
            self.stack_trace_code_block.config(font=current_font)
            
    def insert_code_block(self):
        self.notes_text.insert(tk.INSERT, "{{code}}\n\n{{code}}")
        current_index = self.notes_text.index(tk.INSERT)
        line, char = map(int, current_index.split('.'))
        self.notes_text.mark_set(tk.INSERT, f"{line-1}.0")
        self.notes_text.see(tk.INSERT)
        self._on_notes_change()

    def insert_trace_name(self):
        if current_selected_stack_trace_content:
            trace_data = self.current_session_data["stack_traces_data"].get(current_selected_stack_trace_content)
            if trace_data and 'exception_name' in trace_data:
                self.notes_text.insert(tk.INSERT, trace_data['exception_name'])
                self._on_notes_change()
            else:
                messagebox.showinfo("Info", "No specific stack trace selected to reference.")
        else:
            messagebox.showinfo("Info", "Please select a stack trace on the left to reference its name.")

    def _on_notes_change(self, event=None):
        self.save_notes()
        self._apply_markdown_formatting()

    def _apply_markdown_formatting(self):
        content = self.notes_text.get("1.0", tk.END)

        for tag_name in ["code_block_tag", "h1_tag", "h2_tag"]:
            self.notes_text.tag_remove(tag_name, "1.0", tk.END)

        code_block_pattern = re.compile(r"\{\{code\}\}(.*?)\{\{code\}\}", re.DOTALL)
        for match in code_block_pattern.finditer(content):
            start_index = self.notes_text.index(f"1.0 + {match.start()}c")
            end_index = self.notes_text.index(f"1.0 + {match.end()}c")
            self.notes_text.tag_add("code_block_tag", start_index, end_index)

        h1_pattern = re.compile(r"^h1\.(.*)", re.MULTILINE)
        for match in h1_pattern.finditer(content):
            start_index = self.notes_text.index(f"1.0 + {match.start()}c")
            end_index = self.notes_text.index(f"1.0 + {match.end()}c")
            self.notes_text.tag_add("h1_tag", start_index, end_index)

        h2_pattern = re.compile(r"^h2\.(.*)", re.MULTILINE)
        for match in h2_pattern.finditer(content):
            start_index = self.notes_text.index(f"1.0 + {match.start()}c")
            end_index = self.notes_text.index(f"1.0 + {match.end()}c")
            self.notes_text.tag_add("h2_tag", start_index, end_index)


    def _get_combined_definition_text(self, exception_class_key, log_package_key):
        """Helper to combine definitions from exception class and log package."""
        combined_definition_parts = []

        if exception_class_key and exception_class_key in exception_definitions:
            exc_def = exception_definitions[exception_class_key].get("definition")
            if exc_def:
                combined_definition_parts.append(exc_def)

        if log_package_key and log_package_key in exception_definitions:
            pkg_def = exception_definitions[log_package_key].get("definition")
            if pkg_def:
                combined_definition_parts.append(pkg_def)

        tooltip_text = " ".join(combined_definition_parts).strip()
        if not tooltip_text:
            tooltip_text = "No specific definition available for this stack trace."
        return tooltip_text

    def open_definition_popup(self):
        if not current_selected_stack_trace_content:
            messagebox.showinfo("Info", "Please select a stack trace first to view its definition.")
            return

        trace_data = self.current_session_data["stack_traces_data"].get(current_selected_stack_trace_content)

        if not trace_data:
            messagebox.showerror("Error", "Selected stack trace data not found in current session data.")
            return

        exception_class_key = trace_data.get('exception_class_key')
        log_package_key = trace_data.get('log_package_key')

        definition_text = self._get_combined_definition_text(exception_class_key, log_package_key)

        popup_window = tk.Toplevel(self.master)
        popup_window.title("Definition Details")
        popup_window.geometry("600x400")
        popup_window.transient(self.master)
        popup_window.grab_set()
        popup_window.focus_set()

        tk.Label(popup_window, text="Definition:", font=("Ubuntu", 12, "bold")).pack(padx=10, pady=(10, 5), anchor="w")
        definition_scrolled_text = scrolledtext.ScrolledText(popup_window, height=10, wrap="word", font=("Ubuntu", 10), relief="sunken", bd=1,
                                                            insertbackground="blue", selectbackground="#A0C8F0", selectforeground="black")
        definition_scrolled_text.insert(tk.END, definition_text)
        definition_scrolled_text.config(state="disabled")
        definition_scrolled_text.pack(padx=10, pady=5, fill="both", expand=True)

        button_frame = tk.Frame(popup_window)
        button_frame.pack(pady=10)

        copy_button = tk.Button(button_frame, text="Copy", command=lambda: self.copy_definition_to_clipboard(definition_text),
                                font=("Ubuntu", 10), bg="#607D8B", fg="black", activebackground="#455A64", activeforeground="black")
        copy_button.pack(side="left", padx=5)

        close_button = tk.Button(button_frame, text="Close", command=popup_window.destroy,
                                 font=("Ubuntu", 10), bg="#F44336", fg="black", activebackground="#D32F2F", activeforeground="black")
        close_button.pack(side="left", padx=5)

        popup_window.update_idletasks()
        x = self.master.winfo_x() + (self.master.winfo_width() // 2) - (popup_window.winfo_width() // 2)
        y = self.master.winfo_y() + (self.master.winfo_height() // 2) - (popup_window.winfo_height() // 2)
        popup_window.geometry(f"+{x}+{y}")

    def copy_definition_to_clipboard(self, text_to_copy):
        self.master.clipboard_clear()
        self.master.clipboard_append(text_to_copy)

    def copy_stack_trace_to_clipboard(self):
        """Copies the full content of the displayed stack trace to the clipboard."""
        stack_trace_content = self.stack_trace_code_block.get("1.0", tk.END).strip()
        if stack_trace_content:
            self.master.clipboard_clear()
            self.master.clipboard_append(stack_trace_content)
        else:
            messagebox.showinfo("Info", "No stack trace to copy.")

    def _apply_escalation_template(self):
        global escalation_template_content
        if not current_session_name:
            messagebox.showinfo("Info", "Please start or continue a troubleshooting session first.")
            return

        notes_to_insert = self.notes_text.get("1.0", tk.END).strip()
        
        placeholder_line = "# Place contents of Note Here after clicking \"Escalation Template\""
        
        templated_output_lines = []
        lines = escalation_template_content.split('\n')
        
        inserted_notes_and_skipping_placeholder = False
        
        for line in lines:
            stripped_line = line.strip()

            if not inserted_notes_and_skipping_placeholder:
                if stripped_line == placeholder_line:
                    templated_output_lines.append(notes_to_insert)
                    inserted_notes_and_skipping_placeholder = True
                    continue
                elif stripped_line.startswith("## ") and stripped_line.endswith(":"):
                    templated_output_lines.append(stripped_line[3:])
                else:
                    templated_output_lines.append(line)
            else:
                templated_output_lines.append(line)

        final_templated_content = "\n".join(templated_output_lines)

        self.notes_text.delete("1.0", tk.END)
        self.notes_text.insert(tk.END, final_templated_content)
        self._on_notes_change()

        messagebox.showinfo("Template Applied", "Notes have been formatted with the escalation template.")


    def save_notes(self, event=None):
        global current_session_name
        if current_session_name and self.current_session_data:
            session_root_path = troubleshooting_sessions[current_session_name]
            session_data_file = os.path.join(session_root_path, SESSION_DATA_FILENAME)
            
            self.current_session_data["notes"] = self.notes_text.get("1.0", tk.END).strip()

            try:
                with open(session_data_file, 'w', encoding='utf-8') as f:
                    json.dump(self.current_session_data, f, indent=4)
            except Exception as e:
                messagebox.showerror("Error", f"Could not save notes to session file: {e}")

    def save_current_session_data(self):
        """Saves the current_session_data instance attribute to its session.json file.
        This also updates the main session index."""
        if current_session_name and self.current_session_data:
            session_root_path = troubleshooting_sessions[current_session_name]
            session_data_file_path = os.path.join(session_root_path, SESSION_DATA_FILENAME)
            try:
                with open(session_data_file_path, 'w', encoding='utf-8') as f:
                    json.dump(self.current_session_data, f, indent=4)
                self.save_sessions()
            except Exception as e:
                messagebox.showerror("Error", f"Could not save current session data to '{session_data_file_path}': {e}")


    def rename_dashboard(self):
        global current_session_name
        new_name = self.rename_entry.get().strip()

        if not new_name:
            messagebox.showerror("Error", "Dashboard name cannot be empty.")
            return

        old_name = current_session_name
        if new_name == old_name:
            messagebox.showinfo("Info", "Dashboard already has this name.")
            return

        if new_name in troubleshooting_sessions:
            messagebox.showerror("Error", "A dashboard with this name already exists. Please choose a unique name.")
            return

        old_session_root_path = troubleshooting_sessions[old_name]
        new_session_root_path = os.path.join(SESSION_BASE_DIR, new_name)

        try:
            if os.path.exists(old_session_root_path):
                os.rename(old_session_root_path, new_session_root_path)
            
            self.current_session_data["session_name"] = new_name
            self.current_session_data["files_path"] = new_session_root_path

            current_session_name = new_name
            
            del troubleshooting_sessions[old_name]
            troubleshooting_sessions[new_name] = new_session_root_path

            self.save_current_session_data()
            
            self.dashboard_title_var.set(new_name)
            self.rename_entry.delete(0, tk.END)
            self.rename_entry.insert(0, new_name)
            
            if self.relevant_files_label:
                self.relevant_files_label.config(text=f"Relevant Files (copied to: {self.current_session_data['files_path']}):")
            
            messagebox.showinfo("Renamed", f"Dashboard renamed to '{new_name}'")

        except OSError as e:
            messagebox.showerror("Rename Error", f"Could not rename directory from '{os.path.basename(old_name)}' to '{new_name}': {e}\nSession name updated in app, but directory rename failed. Please manually rename it if necessary.")
            self.current_session_data["session_name"] = old_name
            self.current_session_data["files_path"] = old_session_root_path
            troubleshooting_sessions[old_name] = old_session_root_path
            self.dashboard_title_var.set(old_name)
            self.rename_entry.delete(0, tk.END)
            self.rename_entry.insert(0, old_name)
            self.save_sessions()

    def copy_relevant_files(self):
        global current_session_name
        if not current_session_name or not self.current_session_data:
            messagebox.showerror("Error", "No active troubleshooting session to copy files to.")
            return
        
        session_root_path = self.current_session_data["files_path"]
        
        files_to_copy = filedialog.askopenfilenames(title="Select files to copy")
        if files_to_copy:
            destination_dir = session_root_path
            copied_count = 0
            for file_path in files_to_copy:
                try:
                    shutil.copy2(file_path, destination_dir)
                    copied_count += 1
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to copy {os.path.basename(file_path)}: {e}")
            if copied_count > 0:
                messagebox.showinfo("Success", f"Copied {copied_count} file(s) to '{destination_dir}'")
            else:
                messagebox.showinfo("Info", "No files were copied.")

    def export_notes(self):
        global current_session_name
        if not current_session_name or not self.current_session_data:
            messagebox.showinfo("Info", "No active troubleshooting session to export notes from.")
            return

        notes = self.current_session_data["notes"]
        
        selected_trace_content = self.current_session_data.get("current_selected_stack_trace_content", "")
        stack_trace_for_export = "No specific stack trace selected for this export."
        exception_name_for_export = "N/A"

        if selected_trace_content and "stack_traces_data" in self.current_session_data and selected_trace_content in self.current_session_data["stack_traces_data"]:
            trace_data = self.current_session_data["stack_traces_data"].get(selected_trace_content)
            stack_trace_for_export = selected_trace_content
            exception_name_for_export = trace_data.get("exception_name", "N/A")

        session_name_for_export = self.current_session_data.get("session_name", "Unknown Session")

        jira_markdown = f"""
h1. Scope Troubleshooting Notes: {session_name_for_export}

h2. Selected Exception Type
{exception_name_for_export}

h2. Selected Stack Trace
{{code:python}}
{stack_trace_for_export}
{{code}}

h2. Session Notes
{notes if notes else "No notes taken for this session."}

h2. Relevant Files Location
Local Path: {self.current_session_data['files_path']}
(Files copied to this directory)

"""
        output_filename = filedialog.asksaveasfilename(
            defaultextension=".md",
            initialfile=f"Scope_Export_{session_name_for_export}.md",
            filetypes=[("Markdown files", "*.md"), ("All files", "*.*")]
        )

        if output_filename:
            try:
                with open(output_filename, 'w', encoding='utf-8') as f:
                    f.write(jira_markdown)
                messagebox.showinfo("Export Complete", f"Notes exported to {output_filename}")
            except Exception as e:
                messagebox.showerror("Export Error", f"Could not export notes: {e}")

    def export_current_session(self):
        if not current_session_name or not self.current_session_data:
            messagebox.showinfo("Info", "No active session to export.")
            return

        session_root_path = self.current_session_data["files_path"]
        
        default_zip_filename = f"{current_session_name}.zip"

        zip_file_path = filedialog.asksaveasfilename(
            defaultextension=".zip",
            initialfile=default_zip_filename,
            title="Save Session Archive As",
            filetypes=[("Zip files", "*.zip"), ("All files", "*.*")]
        )

        if zip_file_path:
            try:
                shutil.make_archive(os.path.splitext(zip_file_path)[0], 'zip', session_root_path)
                messagebox.showinfo("Export Complete", f"Session '{current_session_name}' exported to:\n{zip_file_path}")
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to export session: {e}")

    def import_session(self):
        zip_file_path = filedialog.askopenfilename(
            title="Select Session Archive (.zip) to Import",
            filetypes=[("Zip files", "*.zip"), ("All files", "*.*")]
        )

        if not zip_file_path:
            return

        temp_extract_dir_base = os.path.splitext(os.path.basename(zip_file_path))[0]
        temp_extract_dir = os.path.join(SESSION_BASE_DIR, f"temp_import_{datetime.datetime.now().strftime('%H%M%S_%f')}")
        
        try:
            os.makedirs(temp_extract_dir, exist_ok=True)
            shutil.unpack_archive(zip_file_path, temp_extract_dir, 'zip')

            extracted_session_root = temp_extract_dir
            if len(os.listdir(temp_extract_dir)) == 1 and os.path.isdir(os.path.join(temp_extract_dir, os.listdir(temp_extract_dir)[0])):
                 extracted_session_root = os.path.join(temp_extract_dir, os.listdir(temp_extract_dir)[0])

            session_json_path_in_temp = os.path.join(extracted_session_root, SESSION_DATA_FILENAME)
            if not os.path.exists(session_json_path_in_temp):
                messagebox.showerror("Import Error", f"The selected zip file does not contain a '{SESSION_DATA_FILENAME}' at its root level or within its primary extracted folder.")
                shutil.rmtree(temp_extract_dir)
                return

            with open(session_json_path_in_temp, 'r', encoding='utf-8') as f:
                imported_session_data = json.load(f)
            
            base_name_from_json = imported_session_data.get("session_name", os.path.basename(extracted_session_root))
            new_session_name = f"{base_name_from_json}_imported_{datetime.datetime.now().strftime('%H%M%S')}"
            i = 1
            while new_session_name in troubleshooting_sessions:
                new_session_name = f"{base_name_from_json}_imported_{datetime.datetime.now().strftime('%H%M%S')}_{i}"
                i += 1

            final_session_root_path = os.path.join(SESSION_BASE_DIR, new_session_name)
            shutil.move(extracted_session_root, final_session_root_path)

            imported_session_data["session_name"] = new_session_name
            imported_session_data["files_path"] = final_session_root_path

            logs_subdir_in_final = os.path.join(final_session_root_path, SESSION_LOGS_SUBDIR)
            full_log_content_for_reanalysis = ""
            if os.path.exists(logs_subdir_in_final) and os.path.isdir(logs_subdir_in_final):
                log_files_in_imported_dir = [os.path.join(logs_subdir_in_final, f) for f in os.listdir(logs_subdir_in_final) if f.endswith((".log", ".txt"))]
                for log_file_path in log_files_in_imported_dir:
                    try:
                        with open(log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            full_log_content_for_reanalysis += f.read() + "\n"
                    except Exception as e:
                        messagebox.showwarning("Import Warning", f"Could not read log file '{os.path.basename(log_file_path)}' during import re-analysis: {e}")
            
            if full_log_content_for_reanalysis.strip():
                unique_stack_traces_raw = self.extract_stack_traces(full_log_content_for_reanalysis)
                counted_traces = Counter(unique_stack_traces_raw)
                reprocessed_stack_traces = self.process_stack_traces_for_dashboard(counted_traces)
                imported_session_data["stack_traces_data"] = reprocessed_stack_traces
            else:
                messagebox.showinfo("Import Info", f"No log files found or readable in '{SESSION_LOGS_SUBDIR}' for re-analysis in imported session '{new_session_name}'. Stack traces will remain as imported or empty.")
                imported_session_data["stack_traces_data"] = imported_session_data.get("stack_traces_data", {})


            with open(os.path.join(final_session_root_path, SESSION_DATA_FILENAME), 'w', encoding='utf-8') as f:
                json.dump(imported_session_data, f, indent=4)

            troubleshooting_sessions[new_session_name] = final_session_root_path
            self.save_sessions()

            messagebox.showinfo("Import Complete", f"Session '{new_session_name}' imported successfully!")
            self.show_continue_troubleshooting_window()
            
        except Exception as e:
            messagebox.showerror("Import Error", f"An error occurred during session import: {e}")
            if 'temp_extract_dir' in locals() and os.path.exists(temp_extract_dir):
                try:
                    shutil.rmtree(temp_extract_dir)
                except Exception as cleanup_e:
                    print(f"Error cleaning up temporary import directory: {cleanup_e}")
            if 'final_session_root_path' in locals() and os.path.exists(final_session_root_path):
                try:
                    shutil.rmtree(final_session_root_path)
                except Exception as cleanup_e:
                    print(f"Error cleaning up final import directory: {cleanup_e}")


    def show_continue_troubleshooting_window(self):
        global current_session_name

        for widget in self.master.winfo_children():
            widget.destroy()

        self.continue_frame = tk.Frame(self.master, bg="#2F3136")
        self.continue_frame.pack(expand=True, fill="both", padx=40, pady=40)

        tk.Label(self.continue_frame, text="Select a Troubleshooting Session:", font=("Ubuntu", 18, "bold"), bg="#2F3136", fg="white").pack(pady=25)

        if not troubleshooting_sessions:
            tk.Label(self.continue_frame, text="No saved sessions found. Start a new one!", font=("Ubuntu", 14), fg="#F44336", bg="#2F3136").pack(pady=30)
        else:
            session_names = sorted(list(troubleshooting_sessions.keys()), reverse=True)

            self.session_listbox = tk.Listbox(self.continue_frame, selectmode=tk.SINGLE, height=15, font=("Ubuntu", 12), borderwidth=2, relief="groove",
                                              bg="white", fg="black", selectbackground="#A0C8F0", selectforeground="black")
            for name in session_names:
                session_root_path = troubleshooting_sessions[name]
                session_data_file = os.path.join(session_root_path, SESSION_DATA_FILENAME)
                notes_preview = "..."
                num_traces = "N/A"
                try:
                    with open(session_data_file, 'r', encoding='utf-8') as f:
                        session_data_preview = json.load(f)
                        notes_preview = session_data_preview.get("notes", "").split('\n')[0][:50]
                        num_traces = len(session_data_preview.get("stack_traces_data", {}))
                except Exception:
                    notes_preview = "Error loading notes"
                    num_traces = "Error"

                display_text = f"{name} ({num_traces} traces, Notes: '{notes_preview}...')".strip()
                self.session_listbox.insert(tk.END, display_text)
                self.session_listbox.item_data = session_names

            self.session_listbox.pack(fill="both", expand=True, pady=15, padx=20)

            self.open_session_button = tk.Button(self.continue_frame, text="Open Selected Session", command=lambda s=self: s.open_selected_session(), font=("Ubuntu", 14), bg="#2196F3", fg="black", activebackground="#1976D2", activeforeground="black")
            self.open_session_button.pack(pady=20)

            self.delete_session_button = tk.Button(self.continue_frame, text="Delete Selected Session", command=lambda s=self: s.delete_selected_session(), font=("Ubuntu", 12), bg="#F44336", fg="black", activebackground="#D32F2F", activeforeground="black")
            self.delete_session_button.pack(pady=10)

            self.import_button = tk.Button(self.continue_frame, text="Import Session", command=lambda s=self: s.import_session(), font=("Ubuntu", 14), bg="#607D8B", fg="black", activebackground="#455A64", activeforeground="black")
            self.import_button.pack(pady=10)


        self.back_button = tk.Button(self.continue_frame, text="Back to Main Menu", command=lambda s=self: s.create_main_menu(), font=("Ubuntu", 12), activeforeground="black")
        self.back_button.pack(pady=20)

    def open_selected_session(self):
        selected_index = self.session_listbox.curselection()
        if selected_index:
            selected_session_name = self.session_listbox.item_data[selected_index[0]]
            
            if selected_session_name in troubleshooting_sessions:
                self.show_troubleshooting_dashboard(selected_session_name)
            else:
                messagebox.showerror("Error", "Selected session not found in data. It might have been deleted externally.")
                self.load_sessions()
                self.show_continue_troubleshooting_window()
        else:
            messagebox.showerror("Error", "No session selected.")

    def delete_selected_session(self):
        selected_index = self.session_listbox.curselection()
        if selected_index:
            selected_session_name = self.session_listbox.item_data[selected_index[0]]
            
            confirm = messagebox.askyesno(
                "Confirm Delete",
                f"Are you sure you want to delete the session '{selected_session_name}' and its associated files?"
            )
            if confirm:
                if selected_session_name in troubleshooting_sessions:
                    session_dir = troubleshooting_sessions.pop(selected_session_name)
                    
                    if os.path.exists(session_dir):
                        try:
                            shutil.rmtree(session_dir)
                            messagebox.showinfo("Deleted", f"Session '{selected_session_name}' and its files deleted.")
                        except OSError as e:
                            messagebox.showerror("Delete Error", f"Could not delete files for session '{selected_session_name}': {e}\nSession record removed, but files may remain.")
                    else:
                        messagebox.showinfo("Deleted", f"Session '{selected_session_name}' record deleted. Associated files directory not found.")
                    self.save_sessions()
                    self.show_continue_troubleshooting_window()
                else:
                    messagebox.showerror("Error", "Selected session not found.")
        else:
            messagebox.showerror("Error", "No session selected to delete.")


if __name__ == "__main__":
    root = tk.Tk()
    app = ScopeApp(root)
    root.protocol("WM_DELETE_WINDOW", app.save_sessions)
    root.mainloop()