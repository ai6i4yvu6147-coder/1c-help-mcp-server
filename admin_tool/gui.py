"""Admin GUI: list help DBs, add new help."""
import tkinter as tk
from tkinter import messagebox, filedialog, simpledialog
from pathlib import Path
import json
import threading
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.db_manager import list_databases, get_db_path
from admin_tool.importer import import_help


def get_project_root():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent.parent
    return Path(__file__).parent.parent


def load_config():
    root = get_project_root()
    config_path = root / "config.json"
    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            return json.load(f)
    return {"databases_dir": "databases", "default_version": None}


class AdminApp:
    def __init__(self, root):
        self.root = root
        self.root.title("1C Help MCP — Администратор")
        self.root.geometry("700x450")

        self.config = load_config()
        self.project_root = get_project_root()
        self.databases_dir = self.project_root / self.config.get("databases_dir", "databases")
        self.databases_dir.mkdir(exist_ok=True)

        self._create_widgets()
        self._refresh_list()

    def _create_widgets(self):
        title = tk.Label(self.root, text="1C Help MCP — Администратор", font=("Arial", 14, "bold"))
        title.pack(pady=15)

        tk.Label(self.root, text="Загруженные справки:", font=("Arial", 10)).pack(anchor=tk.W, padx=20)

        list_frame = tk.Frame(self.root)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)

        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, height=12, font=("Consolas", 10))
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.listbox.yview)

        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=15)

        tk.Button(
            btn_frame, text="➕ Добавить справку",
            command=self._add_help, width=22, bg="#4CAF50", fg="white"
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            btn_frame, text="🔄 Обновить список",
            command=self._refresh_list, width=20
        ).pack(side=tk.LEFT, padx=5)

    def _refresh_list(self):
        self.listbox.delete(0, tk.END)
        dbs = list_databases(self.databases_dir)
        if not dbs:
            self.listbox.insert(tk.END, "(нет загруженных справок)")
            return
        for db in dbs:
            self.listbox.insert(tk.END, f"{db['version']}  —  {db['created'][:10] if db.get('created') else '?'}")

    def _add_help(self):
        root_path = filedialog.askdirectory(
            title="Выберите папку с распакованной справкой (shcntx_ru, shlang_ru)"
        )
        if not root_path:
            return
        root_path = Path(root_path)

        if not (root_path / "shcntx_ru").exists() and not (root_path / "shlang_ru").exists():
            messagebox.showerror(
                "Ошибка",
                "В выбранной папке нет shcntx_ru или shlang_ru.\n"
                "Выберите корневую папку, где лежат эти каталоги."
            )
            return

        version = simpledialog.askstring(
            "Версия платформы",
            "Введите версию платформы 1С (например 8.3.27):",
            parent=self.root
        )
        if not version or not version.strip():
            return
        version = version.strip()

        db_path = get_db_path(self.databases_dir, version)
        if db_path.exists():
            if not messagebox.askyesno("Подтверждение", f"Справка {version} уже существует. Перезаписать?"):
                return

        def do_import():
            success, msg = import_help(root_path, version, self.databases_dir)
            self.root.after(0, lambda: self._import_done(success, msg))

        self.root.config(cursor="wait")
        threading.Thread(target=do_import, daemon=True).start()

    def _import_done(self, success: bool, msg: str):
        self.root.config(cursor="")
        if success:
            messagebox.showinfo("Готово", msg)
            self._refresh_list()
        else:
            messagebox.showerror("Ошибка", msg)


def main():
    root = tk.Tk()
    AdminApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
