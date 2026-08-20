#!/usr/bin/env python3
"""Desktop app for generating RANDOM.ORG integers. Intended for client delivery."""

from __future__ import annotations

import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from random_org import format_numbers, generate_integers
from random_org_form import FormError, parse_inputs, zh_error


class RandomOrgApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("随机整数生成器")
        self.minsize(460, 420)
        self.numbers: list[int] = []
        self._busy = False
        self._build()

    def _build(self) -> None:
        pad = {"padx": 12, "pady": 6}
        header = ttk.Label(
            self,
            text="从 RANDOM.ORG 生成真随机整数（非官方客户端）",
        )
        header.pack(anchor="w", **pad)

        form = ttk.Frame(self)
        form.pack(fill="x", **pad)

        self.num_var = tk.StringVar(value="5")
        self.min_var = tk.StringVar(value="1")
        self.max_var = tk.StringVar(value="100")
        self.unique_var = tk.BooleanVar(value=False)

        self._row(form, 0, "个数", self.num_var)
        self._row(form, 1, "最小值", self.min_var)
        self._row(form, 2, "最大值", self.max_var)
        ttk.Checkbutton(form, text="不重复", variable=self.unique_var).grid(
            row=3, column=1, sticky="w", pady=6
        )

        buttons = ttk.Frame(self)
        buttons.pack(fill="x", **pad)
        self.generate_btn = ttk.Button(buttons, text="生成", command=self.start_generate)
        self.generate_btn.pack(side="left")
        ttk.Button(buttons, text="复制结果", command=self.copy_result).pack(side="left", padx=8)
        ttk.Button(buttons, text="保存为文本", command=self.save_result).pack(side="left")

        self.output = tk.Text(self, height=12, wrap="word")
        self.output.pack(fill="both", expand=True, padx=12, pady=6)

        self.status = tk.StringVar(value="请填写范围后点击生成。电脑需要能上网。")
        ttk.Label(self, textvariable=self.status).pack(anchor="w", padx=12, pady=(0, 10))

    def _row(self, parent: ttk.Frame, row: int, label: str, variable: tk.StringVar) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="e", padx=(0, 8), pady=4)
        ttk.Entry(parent, textvariable=variable, width=18).grid(row=row, column=1, sticky="w", pady=4)

    def start_generate(self) -> None:
        if self._busy:
            return
        unique = bool(self.unique_var.get())
        try:
            num, minimum, maximum = parse_inputs(
                self.num_var.get(),
                self.min_var.get(),
                self.max_var.get(),
                unique=unique,
            )
        except FormError as exc:
            messagebox.showerror("输入有误", str(exc))
            return

        self._busy = True
        self.generate_btn.config(state="disabled")
        self.status.set("正在向 RANDOM.ORG 请求，请稍候…")

        def work() -> None:
            try:
                numbers = generate_integers(num, minimum, maximum, unique=unique)
            except Exception as exc:  # noqa: BLE001 — show any request failure in the UI
                err = exc
                self.after(0, lambda: self._fail(err))
                return
            self.after(0, lambda: self._succeed(numbers))

        threading.Thread(target=work, daemon=True).start()

    def _succeed(self, numbers: list[int]) -> None:
        self.numbers = numbers
        self.output.delete("1.0", "end")
        self.output.insert("1.0", format_numbers(numbers, "\n"))
        self.status.set(f"已生成 {len(numbers)} 个数字。")
        self._idle()

    def _fail(self, exc: Exception) -> None:
        self.status.set("生成失败。")
        self._idle()
        messagebox.showerror("生成失败", zh_error(exc))

    def _idle(self) -> None:
        self._busy = False
        self.generate_btn.config(state="normal")

    def copy_result(self) -> None:
        text = self.output.get("1.0", "end").strip()
        if not text:
            messagebox.showinfo("提示", "还没有可复制的结果。")
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        self.status.set("已复制到剪贴板。")

    def save_result(self) -> None:
        text = self.output.get("1.0", "end").strip()
        if not text:
            messagebox.showinfo("提示", "还没有可保存的结果。")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")],
            initialfile="random-numbers.txt",
        )
        if not path:
            return
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text + "\n")
        self.status.set(f"已保存到 {path}")


def main() -> None:
    app = RandomOrgApp()
    app.mainloop()


if __name__ == "__main__":
    main()
