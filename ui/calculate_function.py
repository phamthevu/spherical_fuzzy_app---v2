import tkinter as tk
from tkinter import ttk, messagebox
from core.model import SphericalFuzzyNumber
from PIL import Image, ImageTk
import os
import sys
from tkinter import filedialog
from core.aggregate import spf_swam, spf_swag
import pandas as pd
from core.aggregate import aggregate_sheets

# ==========================================================
# GLOBAL IMAGE STORAGE (FIX pyimageX BUG)
# ==========================================================
IMAGE_REFS = []

# ==========================================================
# Resource path (for PyInstaller)
# ==========================================================
def resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# ==========================================================
# Utils
# ==========================================================
def parse_float_locale(value: str) -> float:
    value = value.strip()
    if "," in value and "." not in value:
        value = value.replace(",", ".")
    return float(value)

def parse_spherical_fuzzy(text: str) -> SphericalFuzzyNumber:
    cleaned = text.strip()
    if not (cleaned.startswith("(") and cleaned.endswith(")")):
        raise ValueError("Sai định dạng")

    parts = cleaned[1:-1].split(";")
    if len(parts) != 3:
        raise ValueError("Sai định dạng")

    mu = parse_float_locale(parts[0])
    nu = parse_float_locale(parts[1])
    pi = parse_float_locale(parts[2])

    sfn = SphericalFuzzyNumber(mu, nu, pi)
    if not sfn.is_valid():
        raise ValueError("μ² + ν² + γ² > 1")

    return sfn

class WeightedItem:
    def __init__(self, fuzzy, weight):
        self.fuzzy = fuzzy
        self.weight = weight
        self.norm_weight = 0.0

def normalize_weights(items):
    total = sum(it.weight for it in items)
    if total == 0:
        raise ValueError("Tổng weight = 0")

    for it in items:
        it.norm_weight = it.weight / total

def import_excel_items(path, items, parse_func):
    df = pd.read_excel(path)

    for _, row in df.iterrows():
        if pd.isna(row[0]) or pd.isna(row[1]):
            continue

        fuzzy = parse_func(str(row[0]))
        weight = float(row[1])

        items.append(WeightedItem(fuzzy, weight))

    normalize_weights(items)


def set_result(entry, a, b, c):
    entry.delete(0, tk.END)
    entry.insert(0, f"({a:.3f}; {b:.3f}; {c:.3f})")

def copy_text(root, text):
    root.clipboard_clear()
    root.clipboard_append(text)
    root.update()

# ==========================================================
# Load formula image (SAFE)
# ==========================================================
def load_formula_image(parent, img_name):
    path = resource_path(os.path.join("assets", "formulas", img_name))
    img = Image.open(path)
    img = img.resize((700, int(img.height * 700 / img.width)))

    photo = ImageTk.PhotoImage(img)
    IMAGE_REFS.append(photo)  # 🔥 FIX pyimageX

    lbl = tk.Label(parent, image=photo)
    lbl.pack(pady=5)

# ==========================================================
# MAIN APP
# ==========================================================
def start_app():
    root = tk.Tk()
    root.title("Spherical Fuzzy Tool")
    root.geometry("900x650")

    notebook = ttk.Notebook(root)
    notebook.pack(expand=True, fill="both")

    FONT_BOLD = ("Segoe UI", 10, "bold")

    # ======================================================
    # TAB MULTISHEET
    # ======================================================

    def create_multi_sheet_ui(parent, method):
        tab = ttk.Frame(parent)
        parent.add(tab, text=method)

        excel_path = None
        sheet_names = []
        weight_map = {}

        # ======================================================
        # TOP
        # ======================================================
        top = tk.Frame(tab)
        top.pack(fill="x", pady=5)

        lbl_file = tk.Label(top, text="No file selected")
        lbl_file.pack(side="left", padx=10)

        def read_weights_simple(path, names):
            k = len(names)
            if k == 0:
                raise ValueError("Không có sheet Ans")

            try:
                df = pd.read_excel(path, sheet_name="Weight", header=None)
                weights = []
                for i in range(len(df)):
                    if pd.isna(df.iat[i, 0]):
                        continue
                    weights.append(float(df.iat[i, 0]))
            except Exception:
                return [1 / k] * k

            if len(weights) != k:
                raise ValueError("Số weight không khớp số sheet Ans")

            s = sum(weights)
            if s == 0:
                raise ValueError("Tổng weight = 0")

            return [w / s for w in weights]

        def load_excel():
            nonlocal excel_path, sheet_names, weight_map

            path = filedialog.askopenfilename(
                filetypes=[("Excel file", "*.xlsx *.xls")]
            )
            if not path:
                return

            excel_path = path
            lbl_file.config(text=path)

            sheet_names.clear()
            weight_map.clear()
            listbox.delete(0, tk.END)
            preview_table.delete(*preview_table.get_children())
            result_table.delete(*result_table.get_children())
            lbl_weight.config(text="Weight: —")

            xls = pd.ExcelFile(path)
            for s in xls.sheet_names:
                if s.lower().startswith("ans"):
                    sheet_names.append(s)
                    listbox.insert(tk.END, s)

            weights = read_weights_simple(path, sheet_names)
            for s, w in zip(sheet_names, weights):
                weight_map[s] = w

        tk.Button(top, text="Import Excel", command=load_excel)\
            .pack(side="left", padx=5)

    # ======================================================
    # PARAM
    # ======================================================
        param = tk.Frame(tab)
        param.pack(fill="x", pady=5)

        tk.Label(param, text="Rows").pack(side="left")
        entry_rows = tk.Entry(param, width=5)
        entry_rows.pack(side="left", padx=5)

        tk.Label(param, text="Cols").pack(side="left")
        entry_cols = tk.Entry(param, width=5)
        entry_cols.pack(side="left", padx=5)

    # ======================================================
    # PANED LAYOUT (FIX CỨNG)
    # ======================================================
        paned = tk.PanedWindow(
            tab,
            orient="horizontal",
            sashrelief="raised"
        )
        paned.pack(fill="both", expand=True)
        paned.pack(fill="both", expand=True)

        left = tk.Frame(paned, width=200)
        center = tk.Frame(paned, width=340)
        right = tk.Frame(paned, width=340)

        paned.add(left, minsize=180)
        paned.add(center, minsize=100)
        paned.add(right, minsize=100)

        def balance_panes():
            total = paned.winfo_width()
            if total <= 1:
                return

            left_width = 200      # chiều rộng pane LEFT
            remaining = total - left_width

            # sash 0: giữa LEFT | CENTER
            paned.sash_place(0, left_width, 0)

            # sash 1: giữa CENTER | RIGHT (chia đôi)
            paned.sash_place(1, left_width + remaining // 2, 0)

        # chờ Tk render xong rồi mới đặt sash
        tab.after(200, balance_panes)

    # ======================================================
    # LEFT – SHEET LIST
    # ======================================================
        tk.Label(left, text="Sheets").pack()
        listbox = tk.Listbox(left, height=10)
        listbox.pack(fill="y")

        lbl_weight = tk.Label(left, text="Weight: —")
        lbl_weight.pack(pady=5)

        def delete_sheet():
            idx = listbox.curselection()
            if not idx:
                messagebox.showwarning("Warning", "Chọn sheet để xoá")
                return

            s = listbox.get(idx[0])
            sheet_names.remove(s)
            del weight_map[s]

            listbox.delete(idx[0])
            preview_table.delete(*preview_table.get_children())
            result_table.delete(*result_table.get_children())
            lbl_weight.config(text="Weight: —")

            if weight_map:
                total = sum(weight_map.values())
                for k in weight_map:
                    weight_map[k] /= total

        tk.Button(left, text="Delete Sheet", command=delete_sheet)\
            .pack(pady=5)

    # ======================================================
    # CENTER – PREVIEW TABLE
    # ======================================================
        tk.Label(center, text="Preview").pack()

        prev_frame = tk.Frame(center)
        prev_frame.pack(fill="both", expand=True)

        prev_sy = tk.Scrollbar(prev_frame, orient="vertical")
        prev_sx = tk.Scrollbar(prev_frame, orient="horizontal")

        preview_table = ttk.Treeview(
            prev_frame,
            show="headings",
            yscrollcommand=prev_sy.set,
            xscrollcommand=prev_sx.set
        )

        prev_sy.config(command=preview_table.yview)
        prev_sx.config(command=preview_table.xview)

        prev_sy.pack(side="right", fill="y")
        prev_sx.pack(side="bottom", fill="x")
        preview_table.pack(fill="both", expand=True)

        def on_resize(event):
            balance_panes()

        tab.bind("<Configure>", on_resize)

        def preview_sheet(event):
            if not excel_path:
                return
            idx = listbox.curselection()
            if not idx:
                return

            sheet = listbox.get(idx[0])
            lbl_weight.config(text=f"Weight: {weight_map[sheet]:.3f}")

            try:
                n_rows = int(entry_rows.get())
                n_cols = int(entry_cols.get())
            except Exception:
                return

            df = pd.read_excel(excel_path, sheet_name=sheet, header=None)

            preview_table.delete(*preview_table.get_children())
            preview_table["columns"] = [f"C{j+1}" for j in range(n_cols)]

            for j in range(n_cols):
                preview_table.heading(f"C{j+1}", text=f"C{j+1}")
                preview_table.column(f"C{j+1}", width=130, anchor="center")

            for i in range(n_rows):
                row_vals = [str(df.iat[i+1, j+1]) for j in range(n_cols)]
                preview_table.insert("", "end", values=row_vals)

        listbox.bind("<<ListboxSelect>>", preview_sheet)

    # ======================================================
    # RIGHT – RESULT + BUTTONS (KHÔNG BAY)
    # ======================================================
        content_frame = tk.Frame(right)
        content_frame.pack(fill="both", expand=True)

        action_frame = tk.Frame(right)
        action_frame.pack(fill="x", pady=5)

        tk.Label(content_frame, text="Aggregate Result").pack()

        res_frame = tk.Frame(content_frame)
        res_frame.pack(fill="both", expand=True)

        res_sy = tk.Scrollbar(res_frame, orient="vertical")
        res_sx = tk.Scrollbar(res_frame, orient="horizontal")

        result_table = ttk.Treeview(
            res_frame,
            show="headings",
            yscrollcommand=res_sy.set,
            xscrollcommand=res_sx.set
        )

        res_sy.config(command=result_table.yview)
        res_sx.config(command=result_table.xview)

        res_sy.pack(side="right", fill="y")
        res_sx.pack(side="bottom", fill="x")
        result_table.pack(fill="both", expand=True)

        def aggregate_all():
            try:
                if not excel_path:
                    raise ValueError("Chưa import Excel")
                if not sheet_names:
                    raise ValueError("Chưa có sheet Ans")

                n_rows = int(entry_rows.get())
                n_cols = int(entry_cols.get())

                all_fuzzies = []
                for s in sheet_names:
                    df = pd.read_excel(excel_path, sheet_name=s, header=None)
                    mat = []
                    for i in range(n_rows):
                        row = []
                        for j in range(n_cols):
                            row.append(parse_spherical_fuzzy(df.iat[i + 1, j + 1]))
                        mat.append(row)
                    all_fuzzies.append(mat)

                result_table.delete(*result_table.get_children())
                result_table["columns"] = [f"C{j+1}" for j in range(n_cols)]

                for j in range(n_cols):
                    result_table.heading(f"C{j+1}", text=f"C{j+1}")
                    result_table.column(f"C{j+1}", width=140, anchor="center")

                for i in range(n_rows):
                    row_vals = []
                    for j in range(n_cols):
                        cell_fuzzies = [mat[i][j] for mat in all_fuzzies]
                        weights = [weight_map[s] for s in sheet_names]

                        res = (
                            spf_swam(cell_fuzzies, weights)
                            if method == "SWAM"
                            else spf_swag(cell_fuzzies, weights)
                        )
                        row_vals.append(str(res))

                    result_table.insert("", "end", values=row_vals)

            except Exception as e:
                messagebox.showerror("Aggregation error", str(e))

        def export_excel():
            rows = result_table.get_children()
            if not rows:
                messagebox.showwarning("Warning", "Chưa có kết quả để export")
                return

            path = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel file", "*.xlsx")]
            )
            if not path:
                return

            n_rows = len(rows)
            n_cols = len(result_table["columns"])

            data = [["" for _ in range(n_cols + 1)] for _ in range(n_rows + 1)]

            for i, rid in enumerate(rows):
                vals = result_table.item(rid, "values")
                for j, v in enumerate(vals):
                    data[i + 1][j + 1] = v

            df = pd.DataFrame(data)
            df.to_excel(path, index=False, header=False)

            messagebox.showinfo("Success", "Xuất Excel thành công")

        tk.Button(right, text=f"Aggregate {method}", command=aggregate_all)\
            .pack(pady=5)

        tk.Button(right, text="Export Excel", command=export_excel)\
            .pack(pady=5)

        return tab

    
    # ======================================================
    # TAB AGGREGATION
    # ======================================================

    def create_aggregation_tab(parent, title, formula_img, aggregate_func):
        tab = ttk.Frame(parent)
        parent.add(tab, text=title)

        items = []

        # ========== LEFT ==========
        left = tk.Frame(tab)
        left.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        tree = ttk.Treeview(
            left,
            columns=("fuzzy", "w", "nw"),
            show="headings",
            height=12
        )
        tree.heading("fuzzy", text="Spherical fuzzy")
        tree.heading("w", text="Weight")
        tree.heading("nw", text="Norm weight")
        tree.pack(fill="both", expand=True)

        def refresh():
            tree.delete(*tree.get_children())
            for it in items:
                tree.insert(
                    "",
                    "end",
                    values=(str(it.fuzzy), round(it.weight, 4), round(it.norm_weight, 4))
                )

        # controls
        ctrl = tk.Frame(left)
        ctrl.pack(pady=5)

        entry_fuzzy = tk.Entry(ctrl, width=25)
        entry_fuzzy.pack(side="left", padx=5)

        entry_weight = tk.Entry(ctrl, width=8)
        entry_weight.pack(side="left", padx=5)

        def add_manual():
            f = parse_spherical_fuzzy(entry_fuzzy.get())
            w = float(entry_weight.get())
            items.append(WeightedItem(f, w))
            normalize_weights(items)
            refresh()
        
        def delete_selected():
            selected = tree.selection()
            if not selected:
                messagebox.showwarning("Warning", "Chọn 1 dòng để xoá")
                return

            index = tree.index(selected[0])
            items.pop(index)

            if items:
                normalize_weights(items)

            refresh()


        tk.Button(ctrl, text="Add", command=add_manual).pack(side="left", padx=5)
        tk.Button(ctrl, text="Delete", command=lambda: delete_selected()).pack(side="left", padx=5)


        def import_file():
            path = filedialog.askopenfilename(
                filetypes=[("Excel", "*.xlsx *.xls")]
            )
            if path:
                items.clear()
                import_excel_items(path, items, parse_spherical_fuzzy)
                refresh()

        tk.Button(ctrl, text="Import Excel", command=import_file).pack(side="left")

        # ========== RIGHT ==========
        right = tk.Frame(tab)
        right.pack(side="right", fill="y", padx=10, pady=10)

        load_formula_image(right, formula_img)

        result_entry = tk.Entry(right, width=35)
        result_entry.pack(pady=5)

        def aggregate():
            fuzzies = [it.fuzzy for it in items]
            weights = [it.norm_weight for it in items]

            res = aggregate_func(fuzzies, weights)
            result_entry.delete(0, tk.END)
            result_entry.insert(0, str(res))

        tk.Button(right, text="Aggregate", command=aggregate).pack(pady=5)
        tk.Button(
            right,
            text="Copy",
            command=lambda: copy_text(root, result_entry.get())
        ).pack()

        return tab

    # ======================================================
    # TAB GET
    # ======================================================
    tab_get = ttk.Frame(notebook)
    notebook.add(tab_get, text="GET")

    frame_input = tk.Frame(tab_get)
    frame_input.pack(pady=10)

    tk.Label(frame_input, text="Spherical fuzzy (μ; ν; γ):").grid(row=0, column=0)
    entry_get = tk.Entry(frame_input, width=30)
    entry_get.grid(row=0, column=1, padx=5)

    frame_copy = tk.Frame(tab_get)
    frame_copy.pack()

    entry_res = tk.Entry(frame_copy, width=40)
    entry_res.pack(side="left", padx=5)

    tk.Button(
        frame_copy,
        text="Copy",
        command=lambda: copy_text(root, entry_res.get())
    ).pack(side="left")

    frame_table = tk.Frame(tab_get, bd=1, relief="solid")
    frame_table.pack(padx=20, pady=10, fill="x")

    def make_row(r, sym, name):
        tk.Label(frame_table, text=sym, width=10, borderwidth=1, relief="solid").grid(row=r, column=0)
        tk.Label(frame_table, text=name, width=25, borderwidth=1, relief="solid").grid(row=r, column=1)
        lbl = tk.Label(frame_table, text="—", width=15, borderwidth=1, relief="solid")
        lbl.grid(row=r, column=2)
        return lbl

    val_a = make_row(1, "α", "Membership")
    val_b = make_row(2, "β", "Non-membership")
    val_c = make_row(3, "γ", "Hesitation")

    def check_get():
        try:
            F = parse_spherical_fuzzy(entry_get.get())
            set_result(entry_res, F.mu, F.nu, F.pi)
            val_a.config(text=f"{F.mu:.3f}")
            val_b.config(text=f"{F.nu:.3f}")
            val_c.config(text=f"{F.pi:.3f}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    tk.Button(frame_input, text="Check", command=check_get).grid(row=0, column=2, padx=10)

    # ======================================================
    # Helper tab
    # ======================================================
    def create_calc_tab(name, img):
        tab = ttk.Frame(notebook)
        notebook.add(tab, text=name)
        load_formula_image(tab, img)

        frame_in = tk.Frame(tab)
        frame_in.pack(pady=5)

        frame_out = tk.Frame(tab)
        frame_out.pack(pady=5)

        entry = tk.Entry(frame_out, width=35)
        entry.pack(side="left", padx=5)

        tk.Button(
            frame_out,
            text="Copy",
            command=lambda: copy_text(root, entry.get())
        ).pack(side="left")

        lbl = tk.Label(tab, text="—", font=FONT_BOLD)
        lbl.pack()

        return tab, frame_in, entry, lbl

    # ==========================================================
    # TAB 1 – SUM
    # ==========================================================
    tab_sum, sum_in, sum_res, sum_lbl = create_calc_tab("SUM", "sum.png")

    tk.Label(sum_in, text="Fuzzy A").grid(row=0, column=0)
    a_sum = tk.Entry(sum_in, width=30)
    a_sum.grid(row=0, column=1)

    tk.Label(sum_in, text="Fuzzy B").grid(row=1, column=0)
    b_sum = tk.Entry(sum_in, width=30)
    b_sum.grid(row=1, column=1)

    def calc_sum():
        try:
            A = parse_spherical_fuzzy(a_sum.get())
            B = parse_spherical_fuzzy(b_sum.get())

            alpha = (A.mu**2 + B.mu**2 - A.mu**2 * B.mu**2) ** 0.5
            beta = A.nu * B.nu
            gamma = (
                (1 - B.mu**2) * A.pi**2 +
                (1 - A.mu**2) * B.pi**2 -
                A.pi**2 * B.pi**2
            ) ** 0.5

            set_result(sum_res, alpha, beta, gamma)
            sum_lbl.config(text=f"α={alpha:.3f}, β={beta:.3f}, γ={gamma:.3f}")

        except Exception as e:
            messagebox.showerror("Error", str(e))

    tk.Button(sum_in, text="Calculate", command=calc_sum).grid(row=2, column=1, pady=5)

    # ==========================================================
    # TAB 2 – MUL
    # ==========================================================
    tab_mul, mul_in, mul_res, mul_lbl = create_calc_tab("MUL", "mul.png")

    tk.Label(mul_in, text="Fuzzy A").grid(row=0, column=0)
    a_mul = tk.Entry(mul_in, width=30)
    a_mul.grid(row=0, column=1)

    tk.Label(mul_in, text="Fuzzy B").grid(row=1, column=0)
    b_mul = tk.Entry(mul_in, width=30)
    b_mul.grid(row=1, column=1)

    def calc_mul():
        try:
            A = parse_spherical_fuzzy(a_mul.get())
            B = parse_spherical_fuzzy(b_mul.get())

            alpha = A.mu * B.mu
            beta = (A.nu**2 + B.nu**2 - A.nu**2 * B.nu**2) ** 0.5
            gamma = (
                (1 - B.nu**2) * A.pi**2 +
                (1 - A.nu**2) * B.pi**2 -
                A.pi**2 * B.pi**2
            ) ** 0.5

            set_result(mul_res, alpha, beta, gamma)
            mul_lbl.config(text=f"α={alpha:.3f}, β={beta:.3f}, γ={gamma:.3f}")

        except Exception as e:
            messagebox.showerror("Error", str(e))

    tk.Button(mul_in, text="Calculate", command=calc_mul).grid(row=2, column=1, pady=5)

    # ==========================================================
    # TAB 3 – COE
    # ==========================================================
    tab_coe, coe_in, coe_res, coe_lbl = create_calc_tab("COE", "coe.png")

    tk.Label(coe_in, text="Fuzzy").grid(row=0, column=0)
    f_coe = tk.Entry(coe_in, width=30)
    f_coe.grid(row=0, column=1)

    tk.Label(coe_in, text="σ").grid(row=1, column=0)
    s_coe = tk.Entry(coe_in, width=10)
    s_coe.grid(row=1, column=1, sticky="w")

    def calc_coe():
        try:
            F = parse_spherical_fuzzy(f_coe.get())
            s = parse_float_locale(s_coe.get())

            alpha = (1 - (1 - F.mu**2) ** s) ** 0.5
            beta = F.nu ** s
            gamma = (
                (1 - F.mu**2) ** s -
                (1 - F.mu**2 - F.pi**2) ** s
            ) ** 0.5

            set_result(coe_res, alpha, beta, gamma)
            coe_lbl.config(text=f"α={alpha:.3f}, β={beta:.3f}, γ={gamma:.3f}")

        except Exception as e:
            messagebox.showerror("Error", str(e))

    tk.Button(coe_in, text="Calculate", command=calc_coe).grid(row=2, column=1, pady=5)

    # ==========================================================
    # TAB 4 – POW
    # ==========================================================
    tab_pow, pow_in, pow_res, pow_lbl = create_calc_tab("POW", "pow.png")

    tk.Label(pow_in, text="Fuzzy").grid(row=0, column=0)
    f_pow = tk.Entry(pow_in, width=30)
    f_pow.grid(row=0, column=1)

    tk.Label(pow_in, text="σ").grid(row=1, column=0)
    s_pow = tk.Entry(pow_in, width=10)
    s_pow.grid(row=1, column=1, sticky="w")

    def calc_pow():
        try:
            F = parse_spherical_fuzzy(f_pow.get())
            s = parse_float_locale(s_pow.get())

            alpha = F.mu ** s
            beta = (1 - (1 - F.nu**2) ** s) ** 0.5
            gamma = (
                (1 - F.nu**2) ** s -
                (1 - F.nu**2 - F.pi**2) ** s
            ) ** 0.5

            set_result(pow_res, alpha, beta, gamma)
            pow_lbl.config(text=f"α={alpha:.3f}, β={beta:.3f}, γ={gamma:.3f}")

        except Exception as e:
            messagebox.showerror("Error", str(e))

    tk.Button(pow_in, text="Calculate", command=calc_pow).grid(row=2, column=1, pady=5)

    # ==========================================================
    # TAB 5 – DEF
    # ==========================================================
    tab_def, def_in, def_res, def_lbl = create_calc_tab("DEF", "def.png")

    tk.Label(def_in, text="Fuzzy").grid(row=0, column=0)
    f_def = tk.Entry(def_in, width=30)
    f_def.grid(row=0, column=1)

    def calc_def():
        try:
            F = parse_spherical_fuzzy(f_def.get())
            score = ((2 * F.mu - F.pi) ** 2) - ((F.nu - F.pi) ** 2)
            def_res.delete(0, tk.END)
            def_res.insert(0, f"{score:.3f}")
            def_lbl.config(text=f"DEF = {score:.3f}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    tk.Button(def_in, text="Calculate", command=calc_def).grid(row=1, column=1, pady=5)

    # ==========================================================
    # TAB 6 – SWAM
    # ==========================================================
    agg_notebook = ttk.Notebook(notebook)
    notebook.add(agg_notebook, text="AGGREGATION")

    create_aggregation_tab(
        agg_notebook,
        "SWAM",
        "swam.png",
        spf_swam
    )

    create_aggregation_tab(
        agg_notebook,
        "SWAG",
        "swag.png",
        spf_swag
    )

    multi_notebook = ttk.Notebook(notebook)
    notebook.add(multi_notebook, text="MULTI-SHEET")

    create_multi_sheet_ui(multi_notebook, method="SWAM")
    create_multi_sheet_ui(multi_notebook, method="SWAG")  # UI hiển thị SWGM


    root.mainloop()
