from tkinter import ttk

def setup_modern_styles(root):
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except Exception:
        pass

    style.configure(".", background="#F9FBFC")
    style.configure("TFrame", background="#F9FBFC")
    style.configure("TLabel", background="#F9FBFC", font=("Segoe UI", 11))
    style.configure("TButton", font=("Segoe UI", 11), padding=6)
    style.configure("Header.TLabel", font=("Segoe UI", 16, "bold"), background="#E9EEF4", foreground="#2D425A")
    style.configure("Treeview", font=("Segoe UI", 10), rowheight=28, fieldbackground="#FFFFFF", borderwidth=1)
    style.configure("Treeview.Heading", font=("Segoe UI", 11, "bold"), background="#E9EEF4")
    style.map("TButton",
        background=[('active', '#E9EEF4'), ('!active', '#F4F6F8')],
        relief=[('pressed', 'sunken'), ('!pressed', 'raised')]
    )
