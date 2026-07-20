"""Admin GUI: list help DBs, add and update help."""
import tkinter as tk
from tkinter import messagebox, filedialog, simpledialog
from pathlib import Path
import json
import threading
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.db_manager import list_databases, get_db_path, get_help_source_path
from shared.hbk_extractor import HELP_SOURCES, find_help_archives
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
        self.root.geometry("720x450")

        self.config = load_config()
        self.project_root = get_project_root()
        self.databases_dir = self.project_root / self.config.get("databases_dir", "databases")
        self.databases_dir.mkdir(exist_ok=True)
        self._db_entries: list[dict] = []

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
            command=self._add_help, width=20, bg="#4CAF50", fg="white"
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            btn_frame, text="🔄 Обновить справку",
            command=self._update_help, width=20, bg="#2196F3", fg="white"
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            btn_frame, text="↻ Обновить список",
            command=self._refresh_list, width=18
        ).pack(side=tk.LEFT, padx=5)

    def _refresh_list(self):
        self.listbox.delete(0, tk.END)
        self._db_entries = list_databases(self.databases_dir)
        if not self._db_entries:
            self.listbox.insert(tk.END, "(нет загруженных справок)")
            return
        for db in self._db_entries:
            self.listbox.insert(
                tk.END,
                f"{db['version']}  —  {db['created'][:10] if db.get('created') else '?'}",
            )

    def _selected_db(self) -> dict | None:
        sel = self.listbox.curselection()
        if not sel or not self._db_entries:
            return None
        idx = sel[0]
        if idx >= len(self._db_entries):
            return None
        return self._db_entries[idx]

    def _is_valid_help_root(self, root_path: Path) -> bool:
        if find_help_archives(root_path):
            return True
        return any((root_path / name).is_dir() for name in HELP_SOURCES)

    def _validate_help_root(self, root_path: Path) -> bool:
        if self._is_valid_help_root(root_path):
            return True
        messagebox.showerror(
            "Ошибка",
            "В выбранной папке нет ни архивов (shcntx_ru.hbk, shlang_ru.hbk,\n"
            "shquery_ru.hbk), ни распакованных каталогов с этими именами.\n"
            "Выберите папку со справкой 1С.",
        )
        return False

    def _pick_help_root(self, title: str, initial_dir: str | None = None) -> Path | None:
        kwargs = {"title": title}
        if initial_dir and Path(initial_dir).is_dir():
            kwargs["initialdir"] = initial_dir
        root_path = filedialog.askdirectory(**kwargs)
        if not root_path:
            return None
        root_path = Path(root_path)
        if not self._validate_help_root(root_path):
            return None
        return root_path

    def _resolve_update_root(self, version: str) -> Path | None:
        saved = get_help_source_path(self.databases_dir, version)
        if saved and Path(saved).is_dir() and self._is_valid_help_root(Path(saved)):
            use_saved = messagebox.askyesno(
                "Источник справки",
                f"Обновить из сохранённой папки?\n\n{saved}\n\n"
                "«Да» — использовать её, «Нет» — выбрать другую папку.",
            )
            if use_saved:
                return Path(saved)
        return self._pick_help_root(
            "Выберите папку со справкой 1С (архивы *.hbk или распакованные каталоги)",
            saved if saved and Path(saved).is_dir() else None,
        )

    def _run_import(self, root_path: Path, version: str, action_label: str) -> None:
        if not messagebox.askyesno(
            "Подтверждение",
            f"{action_label} справку {version}?\n\n"
            f"Источник:\n{root_path}\n\n"
            "База будет полностью пересоздана.",
        ):
            return

        def do_import():
            success, msg = import_help(root_path, version, self.databases_dir)
            self.root.after(0, lambda: self._import_done(success, msg))

        self.root.config(cursor="wait")
        threading.Thread(target=do_import, daemon=True).start()

    def _add_help(self):
        root_path = self._pick_help_root(
            "Выберите папку со справкой 1С (архивы *.hbk или распакованные каталоги)"
        )
        if not root_path:
            return

        version = simpledialog.askstring(
            "Версия платформы",
            "Введите версию платформы 1С (например 8.3.27):",
            parent=self.root,
        )
        if not version or not version.strip():
            return
        version = version.strip()

        db_path = get_db_path(self.databases_dir, version)
        if db_path.exists():
            if not messagebox.askyesno(
                "Подтверждение",
                f"Справка {version} уже существует.\n"
                "Для обновления удобнее кнопка «Обновить справку».\n\n"
                "Всё равно добавить (перезаписать)?",
            ):
                return

        self._run_import(root_path, version, "Загрузить")

    def _update_help(self):
        db = self._selected_db()
        if not db:
            messagebox.showwarning("Предупреждение", "Выберите справку в списке")
            return

        version = db.get("version")
        if not version or version == "?":
            messagebox.showerror("Ошибка", "Не удалось определить версию выбранной справки")
            return

        root_path = self._resolve_update_root(version)
        if not root_path:
            return

        self._run_import(root_path, version, "Обновить")

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
