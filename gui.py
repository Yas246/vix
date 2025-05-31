import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import os
from dotenv import dotenv_values, set_key, load_dotenv

try:
    from app_refactored import initialize_and_process_question
except ImportError:
    def initialize_and_process_question(question_text: str, status_cb_param=None):
        if status_cb_param: status_cb_param("ERROR: app_refactored.py not found.")
        return {"sql_query": None, "result": None, "answer": "Backend module not found.",
                "logs": ["app_refactored.py not found."], "error": "Backend module not found."}

try:
    from ttkthemes import ThemedTk
except ImportError:
    ThemedTk = tk.Tk

TEMP_DB_CONFIGS = {
    "sqlite": {"fields": ["DB_PATH"], "url_template": "sqlite:///{DB_PATH}"},
    "postgresql": {"fields": ["DB_USER", "DB_PASSWORD", "DB_HOST", "DB_PORT", "DB_NAME"], "url_template": "postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"},
    "mysql": {"fields": ["DB_USER", "DB_PASSWORD", "DB_HOST", "DB_PORT", "DB_NAME"], "url_template": "mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"},
    "sqlserver": {"fields": ["DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD", "ODBC_DRIVER"], "url_template": "mssql+pyodbc://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}?driver={ODBC_DRIVER}"},
    "oracle": {"fields": ["DB_USER", "DB_PASSWORD", "DB_HOST", "DB_PORT", "DB_SERVICE_NAME"], "url_template": "oracle+cx_oracle://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/?service_name={DB_SERVICE_NAME}"},
}
ENV_FILE_PATH = ".env"

class SettingsWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Settings")
        self.geometry("600x750")
        self.parent = parent
        if not os.path.exists(ENV_FILE_PATH): open(ENV_FILE_PATH, "w").close()
        self.vars = {}
        self._create_widgets()
        self.load_settings()
        self.on_db_type_change()
        if hasattr(parent, 'get_current_theme_colors'):
             self.apply_theme_settings(*parent.get_current_theme_colors())

    def _create_widgets(self): # Condensed for brevity
        self.settings_frame = ttk.Frame(self, padding="10")
        self.settings_frame.pack(expand=True, fill=tk.BOTH)
        ttk.Label(self.settings_frame, text="GOOGLE_API_KEY:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.vars["GOOGLE_API_KEY"] = tk.StringVar()
        self.google_api_key_entry = ttk.Entry(self.settings_frame, textvariable=self.vars["GOOGLE_API_KEY"], width=50)
        self.google_api_key_entry.grid(row=0, column=1, sticky=tk.EW, pady=2)
        ttk.Label(self.settings_frame, text="DB_TYPE:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.vars["DB_TYPE"] = tk.StringVar()
        self.db_type_combobox = ttk.Combobox(self.settings_frame, textvariable=self.vars["DB_TYPE"], values=list(TEMP_DB_CONFIGS.keys()), state="readonly", width=47)
        self.db_type_combobox.grid(row=1, column=1, sticky=tk.EW, pady=2)
        self.db_type_combobox.bind("<<ComboboxSelected>>", self.on_db_type_change)
        self.db_fields_frame = ttk.Frame(self.settings_frame, padding="5")
        self.db_fields_frame.grid(row=2, column=0, columnspan=2, sticky=tk.EW)
        self.all_db_fields = {}
        possible_fields = ["DATABASE_URL","DB_USER","DB_PASSWORD","DB_HOST","DB_PORT","DB_NAME","DB_PATH","ODBC_DRIVER","DB_SERVICE_NAME"]
        for i, field_name in enumerate(possible_fields):
            label = ttk.Label(self.db_fields_frame, text=f"{field_name}:")
            self.vars[field_name] = tk.StringVar()
            entry = ttk.Entry(self.db_fields_frame, textvariable=self.vars[field_name], width=50, show=('*' if "PASSWORD" in field_name.upper() else None))
            self.all_db_fields[field_name] = (label, entry)
        btn_frame = ttk.Frame(self.settings_frame)
        btn_frame.grid(row=3,column=0,columnspan=2,pady=10,sticky=tk.E)
        self.save_button = ttk.Button(btn_frame, text="Save", command=self.save_settings) # Store as instance var
        self.save_button.pack(side=tk.LEFT, padx=5)
        self.close_button = ttk.Button(btn_frame, text="Close", command=self.destroy) # Store as instance var
        self.close_button.pack(side=tk.LEFT, padx=5)
        self.settings_frame.columnconfigure(1, weight=1)

    def apply_theme_settings(self, bg, fg, entry_bg, text_fg, button_bg, is_themedtk_active):
        self.configure(bg=bg)
        style = ttk.Style(self)
        # General frame style
        style.configure(f"Settings.TFrame", background=bg)
        self.settings_frame.configure(style=f"Settings.TFrame")
        self.db_fields_frame.configure(style=f"Settings.TFrame")

        # Labels
        label_style_name = f"Settings.TLabel"
        style.configure(label_style_name, background=bg, foreground=fg)
        self.google_api_key_label.configure(style=label_style_name)
        self.db_type_label.configure(style=label_style_name)
        for field_label, _ in self.all_db_fields.values():
            field_label.configure(style=label_style_name)

        # Entries
        entry_style_name = f"Settings.TEntry"
        style.configure(entry_style_name, fieldbackground=entry_bg, foreground=text_fg) # fieldbackground for entry area
        self.google_api_key_entry.configure(style=entry_style_name)
        for _, field_entry in self.all_db_fields.values():
            field_entry.configure(style=entry_style_name)

        # Combobox
        combobox_style_name = f"Settings.TCombobox"
        style.map(combobox_style_name,
                  fieldbackground=[('readonly', entry_bg)],
                  selectbackground=[('readonly', entry_bg)],
                  selectforeground=[('readonly', text_fg)],
                  foreground=[('readonly', text_fg)])
        style.configure(combobox_style_name, background=button_bg, bordercolor=fg, lightcolor=entry_bg, darkcolor=entry_bg) # arrow color needs bordercolor
        self.db_type_combobox.configure(style=combobox_style_name)

        # Buttons
        button_style_name = f"Settings.TButton"
        style.configure(button_style_name, background=button_bg, foreground=text_fg)
        self.save_button.configure(style=button_style_name)
        self.close_button.configure(style=button_style_name)


    def on_db_type_change(self, event=None): # Condensed
        selected_db_type = self.vars["DB_TYPE"].get()
        for label, entry in self.all_db_fields.values(): label.grid_remove(); entry.grid_remove()
        if selected_db_type in TEMP_DB_CONFIGS:
            fields_to_show = TEMP_DB_CONFIGS[selected_db_type]["fields"]
            for i, field_name in enumerate(fields_to_show):
                if field_name in self.all_db_fields:
                    lbl, ent = self.all_db_fields[field_name]
                    lbl.grid(row=i, column=0, sticky=tk.W, pady=1, padx=2)
                    ent.grid(row=i, column=1, sticky=tk.EW, pady=1, padx=2)
            self.db_fields_frame.columnconfigure(1, weight=1)

    def load_settings(self): # Condensed
        if not os.path.exists(ENV_FILE_PATH): open(ENV_FILE_PATH, "w").close()
        env_vals = dotenv_values(ENV_FILE_PATH)
        for k, v_var in self.vars.items(): v_var.set(env_vals.get(k, ""))
        if "DB_TYPE" in env_vals and env_vals["DB_TYPE"] in TEMP_DB_CONFIGS: self.vars["DB_TYPE"].set(env_vals["DB_TYPE"])
        elif self.db_type_combobox['values']: self.vars["DB_TYPE"].set(self.db_type_combobox['values'][0])
        self.on_db_type_change()

    def save_settings(self): # Condensed
        for k, v_var in self.vars.items(): set_key(ENV_FILE_PATH, k, v_var.get())
        db_t = self.vars["DB_TYPE"].get()
        if db_t in TEMP_DB_CONFIGS and db_t != "sqlite": # sqlite uses DB_PATH directly for DATABASE_URL
            config_info = TEMP_DB_CONFIGS[db_t]
            url_template = config_info["url_template"]
            url_params = {field: self.vars[field].get() for field in config_info["fields"] if field in self.vars}
            all_params_filled = all(url_params.get(field) for field in config_info["fields"])
            if all_params_filled:
                database_url = url_template.format(**url_params)
                set_key(ENV_FILE_PATH, "DATABASE_URL", database_url)
            else: # Clear if not all params filled for auto-generation
                set_key(ENV_FILE_PATH, "DATABASE_URL", "")
        elif db_t == "sqlite": # For sqlite, DATABASE_URL is derived from DB_PATH
            db_path_val = self.vars.get("DB_PATH", tk.StringVar()).get()
            if db_path_val: set_key(ENV_FILE_PATH, "DATABASE_URL", f"sqlite:///{db_path_val}")
            else: set_key(ENV_FILE_PATH, "DATABASE_URL", "")
        messagebox.showinfo("Settings Saved", "Settings saved.", parent=self)


class App(ThemedTk):
    def __init__(self):
        super().__init__()
        self.llm_bypass_active = os.getenv("VIX_TEST_MODE_NO_LLM") == "true"
        self.current_theme = "light"
        self.themedtk_active = ThemedTk != tk.Tk and hasattr(self, 'set_theme')
        self.style = ttk.Style(self)
        self.title("Vix - SQL AI Assistant")
        self.geometry("900x750") # Increased height for bypass label
        if not os.path.exists(ENV_FILE_PATH): open(ENV_FILE_PATH, "w").close()
        load_dotenv(ENV_FILE_PATH)
        self._create_widgets()
        self.apply_theme()

    def get_current_theme_colors(self):
        if self.current_theme == "light": return ("#F0F0F0", "#000000", "#FFFFFF", "#000000", "#E1E1E1", self.themedtk_active)
        return ("#2b2b2b", "#ffffff", "#3c3c3c", "#ffffff", "#555555", self.themedtk_active)

    def _create_widgets(self):
        self.main_frame = ttk.Frame(self, padding="10")
        self.main_frame.pack(expand=True, fill=tk.BOTH)
        self.main_frame.columnconfigure(1, weight=1)

        # Top buttons (Theme, Settings)
        top_btn_frame = ttk.Frame(self.main_frame)
        top_btn_frame.grid(row=0, column=0, columnspan=3, sticky=tk.EW, pady=(0,5))
        self.theme_button = ttk.Button(top_btn_frame, text="Theme", command=self.toggle_theme)
        self.theme_button.pack(side=tk.LEFT, padx=2)
        self.settings_button = ttk.Button(top_btn_frame, text="Settings", command=self.open_settings_window)
        self.settings_button.pack(side=tk.LEFT, padx=2)

        # Question Area
        self.question_label = ttk.Label(self.main_frame, text="Ask:")
        self.question_label.grid(row=1, column=0, sticky=tk.W, pady=2)
        self.question_entry = ttk.Entry(self.main_frame, width=70)
        self.question_entry.grid(row=1, column=1, sticky=tk.EW, pady=2, padx=2)
        self.question_entry.bind("<Return>", self.handle_question_submission)
        self.ask_button = ttk.Button(self.main_frame, text="Submit", command=self.handle_question_submission)
        self.ask_button.grid(row=1, column=2, sticky=tk.E, pady=2, padx=2)

        # Response Area
        self.response_label = ttk.Label(self.main_frame, text="Response:")
        self.response_label.grid(row=2, column=0, sticky=tk.NW, pady=2)
        resp_frame = ttk.Frame(self.main_frame)
        resp_frame.grid(row=3, column=0, columnspan=3, sticky=tk.NSEW, pady=2)
        resp_frame.rowconfigure(0, weight=1); resp_frame.columnconfigure(0, weight=1)
        self.response_text = scrolledtext.ScrolledText(resp_frame, wrap=tk.WORD, state=tk.DISABLED, height=10)
        self.response_text.grid(row=0, column=0, sticky=tk.NSEW)

        # Status Label (main status)
        self.status_label_var = tk.StringVar()
        initial_status = "Status: Ready"
        if self.llm_bypass_active: initial_status += " (LLM Bypass Mode)"
        self.status_label_var.set(initial_status)
        self.status_label = ttk.Label(self.main_frame, textvariable=self.status_label_var, relief=tk.SUNKEN)
        self.status_label.grid(row=4, column=0, columnspan=3, sticky=tk.EW, pady=(5,0), ipady=2)

        # LLM Bypass Mode Indicator Label (placed below status_label)
        self.bypass_mode_label_var = tk.StringVar()
        if self.llm_bypass_active:
            self.bypass_mode_label_var.set("LLM BYPASS ACTIVE")
        self.bypass_mode_indicator_label = ttk.Label(
            self.main_frame,
            textvariable=self.bypass_mode_label_var,
            font=("Arial", 8, "italic"),
            relief=tk.RAISED,
            padding=(2,1)
        )
        if self.llm_bypass_active: # Only grid if active
            self.bypass_mode_indicator_label.grid(row=5, column=0, columnspan=3, sticky=tk.EW, pady=(2,0), ipady=1)

        self.main_frame.rowconfigure(3, weight=1) # Response text area expansion

    def _update_response_text(self, message, append=False):
        self.response_text.config(state=tk.NORMAL)
        if not append: self.response_text.delete("1.0", tk.END)
        self.response_text.insert(tk.END, message + "\n")
        self.response_text.see(tk.END)
        self.response_text.config(state=tk.DISABLED)
        self.update_idletasks()

    def handle_question_submission(self, event=None):
        question = self.question_entry.get().strip()
        if not question:
            status_msg = "Please enter a question."
            if self.llm_bypass_active: status_msg += " (LLM Bypass)"
            self.status_label_var.set(status_msg)
            return

        self.status_label_var.set("Processing...") # Bypass mode will be appended by callback or final status
        self._update_response_text("Contacting Vix AI Assistant...\n", append=False)

        def gui_status_callback(log_message):
            self._update_response_text(f"[VIX LOG] {log_message}", append=True)

        try:
            load_dotenv(ENV_FILE_PATH, override=True)
            result_dict = initialize_and_process_question(question, status_cb_param=gui_status_callback)

            final_status_message = ""
            if result_dict.get("error"):
                self._update_response_text(f"\n--- ERROR ---", append=True)
                self._update_response_text(result_dict["error"], append=True)
                final_status_message = "Error occurred."
                messagebox.showerror("Processing Error", result_dict["error"], parent=self)
            else:
                self._update_response_text(f"\n--- SQL QUERY ---", append=True)
                self._update_response_text(result_dict.get("sql_query", "No SQL query generated."), append=True)
                self._update_response_text(f"\n--- VIX ANSWER ---", append=True)
                self._update_response_text(result_dict.get("answer", "No answer provided."), append=True)
                final_status_message = "Done."

            if self.llm_bypass_active:
                final_status_message += " (LLM Bypass)"
            self.status_label_var.set(final_status_message)

        except Exception as e:
            crit_err_msg = "Critical GUI error."
            if self.llm_bypass_active: crit_err_msg += " (LLM Bypass)"
            self._update_response_text(f"\n--- CRITICAL GUI ERROR ---", append=True)
            self._update_response_text(str(e), append=True)
            self.status_label_var.set(crit_err_msg)
            import traceback
            self._update_response_text(traceback.format_exc(), append=True)
            messagebox.showerror("Critical Error", str(e), parent=self)

    def open_settings_window(self):
        load_dotenv(ENV_FILE_PATH, override=True)
        settings_win = SettingsWindow(self)
        settings_win.grab_set()

    def apply_theme(self):
        bg, fg, entry_bg, text_fg, btn_bg, themed_active = self.get_current_theme_colors()
        if themed_active:
            try: self.set_theme("arc" if self.current_theme == "light" else "equilux");
            except tk.TclError: self.themedtk_active = False

        self.style.theme_use('default')
        self.configure(bg=bg)
        self.style.configure(".", background=bg, foreground=fg, bordercolor=fg, lightcolor=bg, darkcolor=fg)
        self.style.configure("TFrame", background=bg)
        self.style.configure("TLabel", background=bg, foreground=fg)
        self.style.configure("TButton", background=btn_bg, foreground=text_fg, padding=3)
        self.style.configure("TEntry", fieldbackground=entry_bg, foreground=text_fg, insertcolor=text_fg)
        self.style.map("TCombobox", fieldbackground=[('readonly', entry_bg)], foreground=[('readonly', text_fg)], selectbackground=[('readonly',entry_bg)], selectforeground=[('readonly',text_fg)])
        self.style.configure("TCombobox", padding=2)

        # Apply styles to main widgets
        self.main_frame.configure(style="TFrame")
        self.question_label.configure(style="TLabel")
        self.question_entry.configure(style="TEntry")
        self.ask_button.configure(style="TButton")
        self.response_label.configure(style="TLabel")
        self.status_label.configure(style="TLabel") # Main status label

        # Style for the bypass indicator label
        bypass_label_fg = "#D32F2F" if self.current_theme == "light" else "#FFCDD2" # Reddish text
        bypass_label_bg = bg # Use main background
        self.style.configure("Bypass.TLabel", background=bypass_label_bg, foreground=bypass_label_fg, font=("Arial", 8, "italic"))
        self.bypass_mode_indicator_label.configure(style="Bypass.TLabel")


        self.response_text.config(background=entry_bg, foreground=text_fg, insertbackground=text_fg)
        try:
            self.response_text.tk.call(self.response_text._w, 'configure', '-selectbackground', text_fg if self.current_theme == "dark" else "#0078D4")
            self.response_text.tk.call(self.response_text._w, 'configure', '-selectforeground', entry_bg if self.current_theme == "dark" else "#FFFFFF")
        except tk.TclError: pass

        for win in self.winfo_children(): # Update open Toplevel windows (Settings)
            if isinstance(win, tk.Toplevel) and hasattr(win, 'apply_theme_settings'):
                win.apply_theme_settings(*self.get_current_theme_colors())

    def toggle_theme(self):
        self.current_theme = "dark" if self.current_theme == "light" else "light"
        self.apply_theme()

if __name__ == "__main__":
    # To test LLM Bypass mode visually:
    # 1. Set VIX_TEST_MODE_NO_LLM=true in your environment before running.
    #    Example: export VIX_TEST_MODE_NO_LLM="true" (Linux/macOS)
    #             set VIX_TEST_MODE_NO_LLM="true" (Windows CMD)
    #             $env:VIX_TEST_MODE_NO_LLM="true" (Windows PowerShell)
    # 2. Then run: python gui.py
    app = App()
    app.mainloop()

#finsihed
