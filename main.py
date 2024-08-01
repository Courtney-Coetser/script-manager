import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox, simpledialog
import subprocess
import threading
import sqlite3
import os
from datetime import datetime

class ScriptMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Python Script Monitor")
        self.root.geometry("800x500")
        self.root.config(bg='#2d2d2d')

        self.scripts = []
        self.processes = {}
        self.create_widgets()
        self.initialize_db()
        self.load_scripts()

        self.monitor_thread = threading.Thread(target=self.monitor_scripts)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()

    def create_widgets(self):
        self.add_script_btn = tk.Button(self.root, text="Add Script", command=self.add_script, bg='#4caf50', fg='white')
        self.add_script_btn.pack(pady=10)

        self.script_listbox = tk.Listbox(self.root, bg='#333333', fg='white', selectbackground='#4caf50', selectmode=tk.MULTIPLE)
        self.script_listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.script_listbox.bind("<<ListboxSelect>>", self.on_script_select)

        self.output_text = scrolledtext.ScrolledText(self.root, bg='#333333', fg='white')
        self.output_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.output_text.config(state=tk.DISABLED)

        self.start_btn = tk.Button(self.root, text="Start Script(s)", command=self.start_scripts, state=tk.DISABLED, bg='#2196f3', fg='white')
        self.start_btn.pack(side=tk.LEFT, padx=10, pady=10)

        self.stop_btn = tk.Button(self.root, text="Stop Script(s)", command=self.stop_scripts, state=tk.DISABLED, bg='#f44336', fg='white')
        self.stop_btn.pack(side=tk.LEFT, padx=10, pady=10)

    def add_script(self):
        filepath = filedialog.askopenfilename(filetypes=[("Python Scripts", "*.py")])
        if filepath:
            title = simpledialog.askstring("Input", "Enter a title for the script:")
            description = simpledialog.askstring("Input", "Enter a description for the script:")
            date_added = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.save_script_to_db(title, description, filepath, date_added)
            self.load_scripts()

    def on_script_select(self, event):
        selected = self.script_listbox.curselection()
        if selected:
            self.output_text.config(state=tk.NORMAL)
            self.output_text.delete('1.0', tk.END)
            for index in selected:
                script_id = self.script_listbox.get(index).split(':')[0]
                script = self.get_script_details(int(script_id))
                self.output_text.insert(tk.END, f"Selected script: {script['title']}\n")
                self.output_text.insert(tk.END, f"Description: {script['description']}\n")
                self.output_text.insert(tk.END, f"Path: {script['path']}\n")
                self.output_text.insert(tk.END, f"Date Added: {script['date_added']}\n\n")
            self.output_text.config(state=tk.DISABLED)
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.NORMAL)

    def start_scripts(self):
        selected = self.script_listbox.curselection()
        for index in selected:
            script_id = int(self.script_listbox.get(index).split(':')[0])
            script = self.get_script_details(script_id)
            script_path = script['path']
            if script_path in self.processes:
                messagebox.showinfo("Info", f"Script '{script['title']}' is already running.")
                continue

            process = subprocess.Popen(["python", script_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            start_time = datetime.now()
            self.processes[script_path] = (process, start_time)
            self.output_text.config(state=tk.NORMAL)
            self.output_text.insert(tk.END, f"Started script: {script['title']}\n")
            self.output_text.config(state=tk.DISABLED)

    def stop_scripts(self):
        selected = self.script_listbox.curselection()
        for index in selected:
            script_id = int(self.script_listbox.get(index).split(':')[0])
            script = self.get_script_details(script_id)
            script_path = script['path']
            if script_path not in self.processes:
                messagebox.showinfo("Info", f"Script '{script['title']}' is not running.")
                continue

            process, start_time = self.processes.pop(script_path)
            process.terminate()
            runtime = datetime.now() - start_time
            self.output_text.config(state=tk.NORMAL)
            self.output_text.insert(tk.END, f"Stopped script: {script['title']}\n")
            self.output_text.insert(tk.END, f"Run time: {runtime}\n\n")
            self.output_text.config(state=tk.DISABLED)

    def monitor_scripts(self):
        while True:
            for script_path, (process, start_time) in list(self.processes.items()):
                if process.poll() is not None:
                    output, error = process.communicate()
                    self.processes.pop(script_path)
                    script = self.get_script_by_path(script_path)
                    self.output_text.config(state=tk.NORMAL)
                    self.output_text.insert(tk.END, f"Script finished: {script['title']}\n")
                    self.output_text.insert(tk.END, f"Run time: {datetime.now() - start_time}\n")
                    if output:
                        self.output_text.insert(tk.END, f"Output: {output}\n")
                    if error:
                        self.output_text.insert(tk.END, f"Error: {error}\n")
                    self.output_text.config(state=tk.DISABLED)

    def load_scripts(self):
        self.script_listbox.delete(0, tk.END)
        self.scripts = self.get_all_scripts()
        for script in self.scripts:
            self.script_listbox.insert(tk.END, f"{script['id']}: {script['title']}")

    def initialize_db(self):
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scripts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                path TEXT NOT NULL,
                date_added TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()

    def get_db_connection(self):
        conn = sqlite3.connect('scripts.db')
        return conn

    def save_script_to_db(self, title, description, path, date_added):
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO scripts (title, description, path, date_added) VALUES (?, ?, ?, ?)",
                       (title, description, path, date_added))
        conn.commit()
        conn.close()

    def get_all_scripts(self):
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM scripts")
        scripts = cursor.fetchall()
        conn.close()
        return [{"id": row[0], "title": row[1], "description": row[2], "path": row[3], "date_added": row[4]} for row in scripts]

    def get_script_details(self, script_id):
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM scripts WHERE id=?", (script_id,))
        script = cursor.fetchone()
        conn.close()
        if script:
            return {"id": script[0], "title": script[1], "description": script[2], "path": script[3], "date_added": script[4]}
        return None

    def get_script_by_path(self, path):
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM scripts WHERE path=?", (path,))
        script = cursor.fetchone()
        conn.close()
        if script:
            return {"id": script[0], "title": script[1], "description": script[2], "path": script[3], "date_added": script[4]}
        return None

if __name__ == "__main__":
    root = tk.Tk()
    app = ScriptMonitorApp(root)
    root.mainloop()
