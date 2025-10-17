import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime
import mysql
from styles import setup_modern_styles
from db import db_cursor, init_db_tables, TAX_RATE

# --------------------------- CENTER WINDOW FUNCTION --------------------------- #
def center_window(win, width=None, height=None, resizable=False):
    win.update_idletasks()
    screen_width = win.winfo_screenwidth()
    screen_height = win.winfo_screenheight()
    if width is None or height is None:
        width = win.winfo_reqwidth()
        height = win.winfo_reqheight()
    x = (screen_width // 2) - (width // 2)
    y = (screen_height // 2) - (height // 2)
    win.geometry(f"{width}x{height}+{x}+{y}")
    win.resizable(resizable, resizable)

init_db_tables()

# -------------------- LOGIN / SIGNUP --------------------
class LoginWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("POS Login")
        center_window(self, 500, 400, resizable=True)
        self.configure(bg="#F9FBFC")
        setup_modern_styles(self)
        self._build_ui()

    def _build_ui(self):
        frame = ttk.Frame(self, padding=24)
        frame.pack(expand=True, fill=tk.BOTH)
        ttk.Label(frame, text="POS - COMPUTER PARTS AND SERVICES", style="Header.TLabel").pack(pady=(0, 16))
        ttk.Label(frame, text="Username:").pack(anchor="w", pady=(0,2))
        self.username = ttk.Entry(frame, font=("Segoe UI", 11)); self.username.pack(fill="x", pady=(0,12))
        ttk.Label(frame, text="Password:").pack(anchor="w", pady=(0,2))
        self.password = ttk.Entry(frame, show="*", font=("Segoe UI", 11)); self.password.pack(fill="x", pady=(0,12))
        btnf = ttk.Frame(frame); btnf.pack(pady=14)
        ttk.Button(btnf, text="Login", command=self.check_login, width=12).pack(side="left", padx=8)
        ttk.Button(btnf, text="Sign Up", command=self.open_signup, width=12).pack(side="left", padx=8)
        ttk.Button(btnf, text="Exit", command=self.destroy, width=12).pack(side="left", padx=8)

    def check_login(self):
        u, p = self.username.get().strip(), self.password.get().strip()
        if not u or not p:
            messagebox.showwarning("Input", "Enter username and password.")
            return
        with db_cursor() as cur:
            if not cur: return
            cur.execute("SELECT id FROM users WHERE username=%s AND password=%s", (u,p))
            row = cur.fetchone()
            if row:
                self.destroy()
                app = POSApp(user=u)
                app.mainloop()
            else:
                messagebox.showerror("Login Failed", "Invalid username or password.")

    def open_signup(self):
        win = SignUpWindow(self)
        win.transient(self); win.grab_set(); self.wait_window(win)

class SignUpWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Sign Up - POS")
        center_window(self, 500, 400, resizable=True)
        self.configure(bg="#F9FBFC")
        setup_modern_styles(self)
        self._build_ui()

    def _build_ui(self):
        frame = ttk.Frame(self, padding=24)
        frame.pack(expand=True, fill=tk.BOTH)
        ttk.Label(frame, text="Create New Account", style="Header.TLabel").pack(pady=(0, 16))
        ttk.Label(frame, text="Username:").pack(anchor="w", pady=(0,2))
        self.username = ttk.Entry(frame, font=("Segoe UI", 11)); self.username.pack(fill="x", pady=(0,10))
        ttk.Label(frame, text="Password:").pack(anchor="w", pady=(0,2))
        self.password = ttk.Entry(frame, show="*", font=("Segoe UI", 11)); self.password.pack(fill="x", pady=(0,10))
        ttk.Label(frame, text="Confirm Password:").pack(anchor="w", pady=(0,2))
        self.confirm = ttk.Entry(frame, show="*", font=("Segoe UI", 11)); self.confirm.pack(fill="x", pady=(0,10))
        btn_frame = ttk.Frame(frame); btn_frame.pack(pady=16)
        ttk.Button(btn_frame, text="Create", width=12, command=self.register_user).pack(side="left", padx=8)
        ttk.Button(btn_frame, text="Exit", width=12, command=self.destroy).pack(side="left", padx=8)

    def register_user(self):
        u, p, c = self.username.get().strip(), self.password.get().strip(), self.confirm.get().strip()
        if not u or not p:
            messagebox.showwarning("Input", "Fill all fields.")
            return
        if p != c:
            messagebox.showwarning("Input", "Passwords do not match.")
            return
        with db_cursor() as cur:
            if not cur: return
            try:
                cur.execute("INSERT INTO users (username, password) VALUES (%s,%s)", (u, p))
                messagebox.showinfo("Success", "Account created successfully.")
                self.destroy()
            except mysql.connector.Error as e:
                messagebox.showerror("Error", f"Could not create account:\n{e}")

# -------------------- POS APP --------------------
class POSApp(tk.Tk):
    def __init__(self, user=""):
        super().__init__()
        self.user = user
        self.title("POS - COMPUTER PARTS AND SERVICES")
        center_window(self, 1500, 700, resizable=True)
        self.configure(bg="#F9FBFC")
        setup_modern_styles(self)
        self.cart = []
        self.inventory_cache = []   # will hold tuples (name, price, quantity)
        self.services_cache = []
        self.create_widgets()
        self.refresh_inventory()
        self.refresh_cart()

    def create_widgets(self):
        header = ttk.Frame(self, padding=(16,10))
        header.pack(fill=tk.X)
        ttk.Label(header, text="POS - COMPUTER PARTS AND SERVICES", style="Header.TLabel").pack(side=tk.LEFT)
        ttk.Label(header, text=f"User: {self.user}", font=("Segoe UI", 11)).pack(side=tk.RIGHT)
        ttk.Button(header, text="Logout", command=self.logout).pack(side=tk.RIGHT, padx=12)

        main = ttk.Frame(self, padding=16)
        main.pack(fill=tk.BOTH, expand=True)

        left = ttk.LabelFrame(main, text="Available Items", padding=16)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0,10))

        search_frame = ttk.Frame(left)
        search_frame.pack(fill="x", pady=(2,10))
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=(0,8))
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, font=("Segoe UI", 11))
        search_entry.pack(side=tk.LEFT, fill="x", expand=True)
        self.search_var.trace_add("write", lambda *a: self.apply_inventory_filter())
        ttk.Button(search_frame, text="Clear", width=8, command=lambda: self.search_var.set("")).pack(side=tk.LEFT, padx=(8,0))

        self.tree = ttk.Treeview(left, columns=("Name","Price","Quantity"), show="headings")
        self.tree.heading("Name", text="Item")
        self.tree.heading("Price", text="Price (₱)")
        self.tree.heading("Quantity", text="Quantity")
        self.tree.column("Name", anchor="w")
        self.tree.column("Price", width=120, anchor="center")
        self.tree.column("Quantity", width=80, anchor="center")
        self.tree.pack(fill=tk.BOTH, expand=True)
        self._attach_tree_scrollbars(self.tree, left)

        inv_btns = ttk.Frame(left)
        inv_btns.pack(fill="x", pady=12)
        ttk.Button(inv_btns, text="Add Item", width=14, command=self._open_add_item).pack(side="left", padx=6)
        ttk.Button(inv_btns, text="Update Item", width=14, command=self._open_update_item).pack(side="left", padx=6)
        ttk.Button(inv_btns, text="Remove Item", width=14, command=self.remove_inventory_item).pack(side="left", padx=6)
        ttk.Button(inv_btns, text="Add to Cart →", width=14, command=self.add_to_cart).pack(side="left", padx=6)
        ttk.Button(inv_btns, text="Computer Services", width=16, command=self._open_services).pack(side="left", padx=6)

        right = ttk.LabelFrame(main, text="Cart", padding=16)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10,0))

        self.cart_tree = ttk.Treeview(right, columns=("Name","Price","Qty","Total"), show="headings")
        self.cart_tree.heading("Name", text="Item")
        self.cart_tree.heading("Price", text="Price (₱)")
        self.cart_tree.heading("Qty", text="Qty")
        self.cart_tree.heading("Total", text="Total (₱)")
        self.cart_tree.column("Name", anchor="w")
        self.cart_tree.column("Price", width=100, anchor="center")
        self.cart_tree.column("Qty", width=80, anchor="center")
        self.cart_tree.column("Total", width=120, anchor="center")
        self.cart_tree.pack(fill=tk.BOTH, expand=True)
        self._attach_tree_scrollbars(self.cart_tree, right)

        cart_btns = ttk.Frame(right)
        cart_btns.pack(fill="x", pady=12)
        ttk.Button(cart_btns, text="Edit Cart", width=14, command=self._open_edit_cart).pack(side="left", padx=8)
        ttk.Button(cart_btns, text="Remove from Cart", width=16, command=self.remove_item).pack(side="left", padx=8)
        ttk.Button(cart_btns, text="Checkout", width=12, command=self.checkout).pack(side="left", padx=8)

        totals = ttk.Frame(right)
        totals.pack(fill=tk.X, pady=(8,0))
        self.subtotal_var = tk.StringVar(value="₱0.00")
        self.tax_var = tk.StringVar(value="₱0.00")
        self.total_var = tk.StringVar(value="₱0.00")
        ttk.Label(totals, text="Subtotal:").grid(row=0,column=0,sticky="w")
        ttk.Label(totals, textvariable=self.subtotal_var).grid(row=0,column=1,sticky="e")
        ttk.Label(totals, text="VAT (12%):").grid(row=1,column=0,sticky="w")
        ttk.Label(totals, textvariable=self.tax_var).grid(row=1,column=1,sticky="e")
        ttk.Label(totals, text="Total:", font=("Segoe UI",11,"bold")).grid(row=2,column=0,sticky="w")
        ttk.Label(totals, textvariable=self.total_var, font=("Segoe UI",11,"bold")).grid(row=2,column=1,sticky="e")

        cash_frame = ttk.Frame(right)
        cash_frame.pack(fill=tk.X, pady=(8,0))
        ttk.Label(cash_frame, text="Cash:").pack(side=tk.LEFT)
        self.cash_var = tk.StringVar(value="")
        ttk.Entry(cash_frame, textvariable=self.cash_var, width=12, font=("Segoe UI", 11)).pack(side=tk.LEFT, padx=8)

    def _attach_tree_scrollbars(self, tree, parent):
        vsb = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(parent, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)

    def _open_add_item(self):
        win = ItemWindow(self, "Add New Item")
        win.transient(self); win.grab_set(); self.wait_window(win)

    def _open_update_item(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Select Item", "Select an inventory item to update.")
            return
        name, price, qty = self.tree.item(sel[0])["values"]
        win = ItemWindow(self, "Update Item", name, float(price), int(qty))
        win.transient(self); win.grab_set(); self.wait_window(win)

    def _open_services(self):
        win = ServiceWindow(self)
        win.transient(self); win.grab_set(); self.wait_window(win)

    def _open_edit_cart(self):
        sel = self.cart_tree.selection()
        if not sel:
            return
        name = self.cart_tree.item(sel[0])["values"][0]
        cart_item = next((c for c in self.cart if c["name"] == name), None)
        if not cart_item:
            return
        win = EditCartWindow(self, cart_item)
        win.transient(self); win.grab_set(); self.wait_window(win)

    def remove_inventory_item(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Select Item", "Please select an item to remove from items.")
            return
        name = self.tree.item(sel[0])["values"][0]
        confirm = messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete '{name}' from items?")
        if not confirm:
            return
        try:
            with db_cursor() as cur:
                if not cur:
                    return
                cur.execute("DELETE FROM items WHERE name=%s", (name,))
            messagebox.showinfo("Deleted", f"'{name}' has been removed from items.")
            self.refresh_inventory()
        except mysql.connector.Error as e:
            messagebox.showerror("DB Error", f"Cannot delete item: {e}")

    def apply_inventory_filter(self):
        term = ""
        try:
            term = self.search_var.get().strip().lower()
        except Exception:
            term = ""
        self.tree.delete(*self.tree.get_children())
        for idx, r in enumerate(self.inventory_cache):
            name = r[0]
            if term == "" or term in name.lower():
                tag = "oddrow" if (idx % 2 == 0) else "evenrow"
                self.tree.insert("", "end", values=(r[0], f"{r[1]:.2f}", r[2]), tags=(tag,))
        self.tree.tag_configure("oddrow", background="#ffffff")
        self.tree.tag_configure("evenrow", background="#E9EEF4")

    def logout(self):
        self.destroy()
        LoginWindow().mainloop()

    def refresh_inventory(self):
        with db_cursor() as cur:
            if not cur: return
            cur.execute("SELECT name, price, quantity FROM items ORDER BY name")
            self.inventory_cache = cur.fetchall()
        self.apply_inventory_filter()

    def refresh_cart(self):
        self.cart_tree.delete(*self.cart_tree.get_children())
        subtotal = 0.0
        for idx, it in enumerate(self.cart):
            total = it["price"] * it["qty"]
            subtotal += total
            tag = "oddrow" if (idx % 2 == 0) else "evenrow"
            self.cart_tree.insert("", "end", values=(it["name"], f"{it['price']:.2f}", it["qty"], f"{total:.2f}"), tags=(tag,))
        self.cart_tree.tag_configure("oddrow", background="#ffffff")
        self.cart_tree.tag_configure("evenrow", background="#E9EEF4")
        tax = subtotal * TAX_RATE
        total = subtotal + tax
        self.subtotal_var.set(f"₱{subtotal:.2f}")
        self.tax_var.set(f"₱{tax:.2f}")
        self.total_var.set(f"₱{total:.2f}")

    def add_to_cart(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Error", "Select an item from items list.")
            return
        name, price_str, qty_str = self.tree.item(sel[0])["values"]
        available = int(qty_str)
        if available <= 0:
            messagebox.showinfo("Out of stock", f"{name} is out of stock.")
            return
        qty = simpledialog.askinteger("Quantity", f"Enter quantity for {name} (max {available}):", minvalue=1, maxvalue=available)
        if qty is None:
            return
        try:
            with db_cursor() as cur:
                if not cur: return
                cur.execute("SELECT quantity FROM items WHERE name=%s FOR UPDATE", (name,))
                r = cur.fetchone()
                if not r or r[0] < qty:
                    raise ValueError(f"Not enough quantity for {name}.")
                cur.execute("UPDATE items SET quantity = quantity - %s WHERE name=%s", (qty, name))
        except ValueError as ve:
            messagebox.showerror("Quantity Error", str(ve))
            return
        except mysql.connector.Error as e:
            messagebox.showerror("DB Error", f"Failed to update quantity: {e}")
            return
        price = float(price_str)
        existing = next((c for c in self.cart if c["name"] == name and abs(c["price"] - price) < 1e-6), None)
        if existing:
            existing["qty"] += qty
        else:
            self.cart.append({"name": name, "price": price, "qty": qty})
        self.refresh_inventory()
        self.refresh_cart()

    def remove_item(self):
        sel = self.cart_tree.selection()
        if not sel:
            return
        name = self.cart_tree.item(sel[0])["values"][0]
        cart_item = next((c for c in self.cart if c["name"] == name), None)
        if not cart_item:
            return
        try:
            with db_cursor() as cur:
                if not cur: return
                cur.execute("UPDATE items SET quantity = quantity + %s WHERE name=%s", (cart_item["qty"], name))
        except mysql.connector.Error as e:
            messagebox.showerror("DB Error", f"Cannot restore quantity: {e}")
            return
        self.cart.remove(cart_item)
        self.refresh_inventory()
        self.refresh_cart()

    def checkout(self):
        if not self.cart:
            messagebox.showinfo("Empty Cart", "Cart is empty. Add items before checkout.")
            return

        try:
            cash = float(self.cash_var.get())
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter a valid cash amount.")
            return

        total = float(self.total_var.get().replace("₱", ""))
        if cash < total:
            messagebox.showwarning("Insufficient Cash", f"Total is ₱{total:.2f}. Cash provided (₱{cash:.2f}) is insufficient.")
            return

        confirm = messagebox.askyesno("Confirm Checkout", f"Proceed to checkout?\nCash: ₱{cash:.2f}\nChange: ₱{(cash-total):.2f}")
        if not confirm:
            return

        now = datetime.now()
        change = cash - total

        try:
            with db_cursor() as cur:
                if not cur: return
                for item in self.cart:
                    cur.execute(
                        "INSERT INTO sales (item, price, qty, total, date, cashier) VALUES (%s,%s,%s,%s,%s,%s)",
                        (item["name"], item["price"], item["qty"], round(item["price"] * item["qty"], 2), now, self.user)
                    )
                cur.execute(
                    "INSERT INTO payments (date_time, total_amount, payment_amount, change_amount) VALUES (%s,%s,%s,%s)",
                    (now, round(total, 2), round(cash, 2), round(change, 2))
                )

            messagebox.showinfo("Checkout Successful", f"Transaction completed!\nChange: ₱{(change):.2f}")
            self.cart.clear()
            self.cash_var.set("")
            self.refresh_inventory()
            self.refresh_cart()
        except mysql.connector.Error as e:
            messagebox.showerror("Checkout Error", f"Failed to complete transaction: {e}")

# -------------------- Item Management Window --------------------
class ItemWindow(tk.Toplevel):
    def __init__(self, parent, title, name="", price=0.0, quantity=0):
        super().__init__(parent)
        self.parent = parent
        self.title(title)
        center_window(self, 500, 400, resizable=True)
        setup_modern_styles(self)
        self.name_val = tk.StringVar(value=name)
        self.price_val = tk.DoubleVar(value=price)
        self.quantity_val = tk.IntVar(value=quantity)
        self._build_ui()

    def _build_ui(self):
        frame = ttk.Frame(self, padding=16)
        frame.pack(expand=True, fill=tk.BOTH)
        ttk.Label(frame, text="Item Name:").pack(anchor="w", pady=(0,2))
        ttk.Entry(frame, textvariable=self.name_val, font=("Segoe UI", 11)).pack(fill="x", pady=(0,10))
        ttk.Label(frame, text="Price:").pack(anchor="w", pady=(0,2))
        ttk.Entry(frame, textvariable=self.price_val, font=("Segoe UI", 11)).pack(fill="x", pady=(0,10))
        ttk.Label(frame, text="Quantity:").pack(anchor="w", pady=(0,2))
        ttk.Entry(frame, textvariable=self.quantity_val, font=("Segoe UI", 11)).pack(fill="x", pady=(0,10))
        btn_frame = ttk.Frame(frame); btn_frame.pack(pady=16)
        ttk.Button(btn_frame, text="Save", command=self.save_item, width=12).pack(side="left", padx=8)
        ttk.Button(btn_frame, text="Cancel", command=self.destroy, width=12).pack(side="left", padx=8)

    def save_item(self):
        name = self.name_val.get().strip()
        price = self.price_val.get()
        quantity = self.quantity_val.get()
        if not name or price <= 0 or quantity < 0:
            messagebox.showwarning("Invalid Input", "Check item details and try again.")
            return
        try:
            with db_cursor() as cur:
                if not cur: return
                cur.execute("SELECT id FROM items WHERE name=%s", (name,))
                r = cur.fetchone()
                if r:
                    cur.execute("UPDATE items SET price=%s, quantity=%s WHERE name=%s", (price, quantity, name))
                else:
                    cur.execute("INSERT INTO items (name, price, quantity) VALUES (%s,%s,%s)", (name, price, quantity))
            messagebox.showinfo("Success", "Item saved successfully.")
            self.parent.refresh_inventory()
            self.destroy()
        except mysql.connector.Error as e:
            messagebox.showerror("DB Error", f"Failed to save item: {e}")

# -------------------- Edit Cart Window --------------------
class EditCartWindow(tk.Toplevel):
    def __init__(self, parent, cart_item):
        super().__init__(parent)
        self.parent = parent
        self.cart_item = cart_item
        self.title(f"Edit {cart_item['name']}")
        center_window(self, 500, 400, resizable=True)
        setup_modern_styles(self)
        self._build_ui()

    def _build_ui(self):
        ttk.Label(self, text=f"Edit {self.cart_item['name']}", font=("Segoe UI", 11, "bold")).pack(pady=10)
        self.qty_label = ttk.Label(self, text=f"Quantity: {self.cart_item['qty']}")
        self.qty_label.pack(pady=8)
        btnf = ttk.Frame(self); btnf.pack(pady=12)
        ttk.Button(btnf, text="Increase", width=10, command=self._increase).pack(side="left", padx=8)
        ttk.Button(btnf, text="Decrease", width=10, command=self._decrease).pack(side="left", padx=8)
        ttk.Button(self, text="Close", width=12, command=self.destroy).pack(pady=10)

    def _increase(self):
        name = self.cart_item['name']
        try:
            with db_cursor() as cur:
                if not cur: return
                cur.execute("SELECT quantity FROM items WHERE name=%s FOR UPDATE", (name,))
                r = cur.fetchone()
                if not r or r[0] <= 0:
                    messagebox.showinfo("Out of stock", "No more stock.")
                    return
                cur.execute("UPDATE items SET quantity = quantity - 1 WHERE name=%s", (name,))
        except mysql.connector.Error as e:
            messagebox.showerror("DB Error", f"Cannot update quantity: {e}")
            return
        self.cart_item['qty'] += 1
        self.qty_label.config(text=f"Quantity: {self.cart_item['qty']}")
        self.parent.refresh_inventory()
        self.parent.refresh_cart()

    def _decrease(self):
        if self.cart_item['qty'] <= 1:
            messagebox.showinfo("Notice", "Quantity cannot be less than 1.")
            return
        try:
            with db_cursor() as cur:
                if not cur: return
                cur.execute("UPDATE items SET quantity = quantity + 1 WHERE name=%s", (self.cart_item['name'],))
        except mysql.connector.Error as e:
            messagebox.showerror("DB Error", f"Cannot update quantity: {e}")
            return
        self.cart_item['qty'] -= 1
        self.qty_label.config(text=f"Quantity: {self.cart_item['qty']}")
        self.parent.refresh_inventory()
        self.parent.refresh_cart()

# -------------------- Services Window --------------------
class ServiceWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Computer Services")
        center_window(self, 520, 420, resizable=True)
        setup_modern_styles(self)
        self._build_ui()
        self.load_services()

    def _build_ui(self):
        frame = ttk.Frame(self, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)
        self.tree = ttk.Treeview(frame, columns=("Service","Price"), show="headings")
        self.tree.heading("Service", text="Service")
        self.tree.heading("Price", text="Price (₱)")
        self.tree.column("Service", anchor="w")
        self.tree.column("Price", width=120, anchor="center")
        self.tree.pack(fill=tk.BOTH, expand=True)
        vsb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)

        btn_frame = ttk.Frame(frame); btn_frame.pack(pady=12)
        ttk.Button(btn_frame, text="Add Service to Cart", width=18, command=self.add_service_to_cart).pack(side=tk.LEFT, padx=8)
        ttk.Button(btn_frame, text="Update Services", width=16, command=self.open_manage_services).pack(side=tk.LEFT, padx=8)
        ttk.Button(btn_frame, text="Remove Service", width=14, command=self.remove_service_direct).pack(side=tk.LEFT, padx=8)

    def load_services(self):
        with db_cursor() as cur:
            if not cur: return
            cur.execute("SELECT name, price FROM services ORDER BY name")
            self.services_cache = cur.fetchall()
        self.tree.delete(*self.tree.get_children())
        for idx, s in enumerate(self.services_cache):
            tag = "oddrow" if (idx % 2 == 0) else "evenrow"
            self.tree.insert("", "end", values=(s[0], f"{s[1]:.2f}"), tags=(tag,))
        self.tree.tag_configure("oddrow", background="#ffffff")
        self.tree.tag_configure("evenrow", background="#E9EEF4")

    def add_service_to_cart(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Select Service", "Select a service to add to cart.")
            return
        name, price_str = self.tree.item(sel[0])["values"]
        try:
            price = float(price_str)
        except Exception:
            price = 0.0
        existing = next((c for c in self.parent.cart if c["name"] == name and abs(c["price"] - price) < 1e-6), None)
        if existing:
            existing["qty"] += 1
        else:
            self.parent.cart.append({"name": name, "price": price, "qty": 1})
        self.parent.refresh_cart()
        messagebox.showinfo("Added", f"{name} added to cart.")

    def open_manage_services(self):
        win = ManageServicesWindow(self)
        win.transient(self); win.grab_set(); self.wait_window(win)

    def remove_service_direct(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Select Service", "Select a service to remove.")
            return
        name = self.tree.item(sel[0])["values"][0]
        confirm = messagebox.askyesno("Confirm Delete", f"Delete service '{name}'?")
        if not confirm:
            return
        with db_cursor() as cur:
            if not cur: return
            try:
                cur.execute("DELETE FROM services WHERE name=%s", (name,))
                messagebox.showinfo("Deleted", f"Service '{name}' deleted.")
            except mysql.connector.Error as e:
                messagebox.showerror("DB Error", f"Cannot delete service: {e}")
                return
        self.load_services()
        try:
            self.parent.refresh_inventory()
        except Exception:
            pass
        try:
            self.parent.refresh_cart()
        except Exception:
            pass

# -------------------- Manage Services Window --------------------
class ManageServicesWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Manage Services")
        center_window(self, 560, 480, resizable=True)
        setup_modern_styles(self)
        self._build_ui()
        self.refresh_tree()

    def _build_ui(self):
        ttk.Label(self, text="Manage Services", font=("Segoe UI", 12, "bold")).pack(pady=12)
        tree_frame = ttk.Frame(self); tree_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0,8))
        self.tree = ttk.Treeview(tree_frame, columns=("name","price"), show="headings")
        self.tree.heading("name", text="Service")
        self.tree.heading("price", text="Price (₱)")
        self.tree.column("name", anchor="w")
        self.tree.column("price", width=120, anchor="center")
        self.tree.pack(fill=tk.BOTH, expand=True)
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)

        btn_frame = ttk.Frame(self); btn_frame.pack(pady=14)
        ttk.Button(btn_frame, text="Add Service", width=14, command=self.add_service).pack(side=tk.LEFT, padx=8)
        ttk.Button(btn_frame, text="Edit Service", width=14, command=self.edit_service).pack(side=tk.LEFT, padx=8)
        ttk.Button(btn_frame, text="Delete Service", width=14, command=self.delete_service).pack(side=tk.LEFT, padx=8)
        ttk.Button(btn_frame, text="Close", width=10, command=self.destroy).pack(side=tk.LEFT, padx=8)

    def refresh_tree(self):
        with db_cursor() as cur:
            if not cur: return
            cur.execute("SELECT id, name, price FROM services ORDER BY name")
            self.data = cur.fetchall()
        self.tree.delete(*self.tree.get_children())
        for idx, s in enumerate(self.data):
            tag = "oddrow" if idx % 2 == 0 else "evenrow"
            self.tree.insert("", "end", values=(s[1], f"{s[2]:.2f}"), tags=(tag,))
        self.tree.tag_configure("oddrow", background="#ffffff")
        self.tree.tag_configure("evenrow", background="#E9EEF4")

    def add_service(self):
        self._service_dialog("Add New Service")

    def edit_service(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Select a service to edit.")
            return
        name, price_str = self.tree.item(sel[0])["values"]
        self._service_dialog("Edit Service", name, float(price_str))

    def delete_service(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Select a service to delete.")
            return
        name = self.tree.item(sel[0])["values"][0]
        confirm = messagebox.askyesno("Confirm Delete", f"Delete service '{name}'?")
        if not confirm:
            return
        with db_cursor() as cur:
            if not cur: return
            cur.execute("DELETE FROM services WHERE name=%s", (name,))
        messagebox.showinfo("Deleted", f"'{name}' deleted.")
        self.refresh_tree()
        try:
            self.parent.load_services()
        except Exception:
            pass

    def _service_dialog(self, title, name="", price=0.0):
        win = tk.Toplevel(self)
        win.title(title)
        center_window(win, 500, 420, resizable=True)
        setup_modern_styles(win)
        name_var = tk.StringVar(value=name)
        price_var = tk.DoubleVar(value=price)
        frame = ttk.Frame(win, padding=16)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="Service Name:").pack(anchor="w", pady=(0,2))
        ttk.Entry(frame, textvariable=name_var, font=("Segoe UI", 11)).pack(fill="x", pady=(0,10))
        ttk.Label(frame, text="Price:").pack(anchor="w", pady=(0,2))
        ttk.Entry(frame, textvariable=price_var, font=("Segoe UI", 11)).pack(fill="x", pady=(0,10))

        def save():
            n = name_var.get().strip()
            p = price_var.get()
            if not n or p <= 0:
                messagebox.showwarning("Invalid", "Please fill out fields correctly.")
                return
            with db_cursor() as cur:
                if not cur: return
                cur.execute("SELECT id FROM services WHERE name=%s", (n,))
                r = cur.fetchone()
                if r:
                    cur.execute("UPDATE services SET price=%s WHERE name=%s", (p, n))
                else:
                    cur.execute("INSERT INTO services (name, price) VALUES (%s,%s)", (n, p))
            messagebox.showinfo("Saved", f"Service '{n}' saved.")
            self.refresh_tree()
            try:
                self.parent.load_services()
            except Exception:
                pass
            win.destroy()
        ttk.Button(frame, text="Save", width=12, command=save).pack(pady=10)
        ttk.Button(frame, text="Cancel", width=12, command=win.destroy).pack()
