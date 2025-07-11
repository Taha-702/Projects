import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk

# Set dark appearance permanently
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

def extended_euclidean(a, b):
    old_r, r = a, b
    old_s, s = 1, 0
    old_t, t = 0, 1
    steps = []

    while r != 0:
        q = old_r // r
        old_r, r = r, old_r - q * r
        old_s, s = s, old_s - q * s
        old_t, t = t, old_t - q * t
        steps.append((q, old_r, r, old_r % r if r != 0 else 0, old_s, s, old_t))
    
    gcd = old_r
    inverse = old_s % b if gcd == 1 else None
    return gcd, inverse, steps

def validate_input(*args):
    a_value = entry_a.get()
    b_value = entry_b.get()
    
    if a_value and b_value:
        try:
            a = int(a_value)
            b = int(b_value)
            calculate_button.configure(state="normal" if a > 0 and b > 0 else "disabled")
        except ValueError:
            calculate_button.configure(state="disabled")
    else:
        calculate_button.configure(state="disabled")

def calculate_gcd_inverse():
    try:
        a = int(entry_a.get())
        b = int(entry_b.get())
        if a <= 0 or b <= 0:
            messagebox.showerror("Error", "Please enter positive integers.", parent=root)
            return
        
        # Clear previous table and results
        for row in tree.get_children():
            tree.delete(row)

        gcd_label.configure(text="")
        inverse_label.configure(text="")
        
        # Calculate
        gcd, inverse, steps = extended_euclidean(a, b)

        # Fill table with animation
        for step in steps:
            tree.insert("", "end", values=step)
            root.update()
            root.after(100)

        # Update results
        gcd_label.configure(text=f"🧮 GCD: {gcd}")
        if gcd == 1 and inverse is not None:
            inverse_label.configure(text=f"🧾 Modular Inverse of {a} mod {b}: {inverse}")
        else:
            inverse_label.configure(text="🚫 Modular Inverse: Does not exist (GCD ≠ 1)")

    except ValueError:
        messagebox.showerror("Error", "Please enter valid integers.", parent=root)
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred: {str(e)}", parent=root)

def clear_inputs():
    entry_a.delete(0, tk.END)
    entry_b.delete(0, tk.END)
    for row in tree.get_children():
        tree.delete(row)
    gcd_label.configure(text="")
    inverse_label.configure(text="")
    calculate_button.configure(state="disabled")

# ---------------- GUI Layout ---------------- #

root = ctk.CTk()
root.title("")
root.geometry("900x700")
root.minsize(800, 600)

main_frame = ctk.CTkFrame(root, corner_radius=10)
main_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
root.columnconfigure(0, weight=1)
root.rowconfigure(0, weight=1)
 
# Header
header_label = ctk.CTkLabel(
    main_frame, 
    text="GCD and Modular Inverse Calculator Using EEA",
    font=ctk.CTkFont(size=26, weight="bold")
)
header_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))

# Input section
input_frame = ctk.CTkFrame(main_frame, corner_radius=10)
input_frame.grid(row=1, column=0, sticky="ew", pady=10, padx=10)

entry_a = ctk.CTkEntry(input_frame, placeholder_text="Enter a", width=200)
entry_a.grid(row=0, column=1, padx=10, pady=5)
entry_a.bind("<KeyRelease>", validate_input)

entry_b = ctk.CTkEntry(input_frame, placeholder_text="Enter b", width=200)
entry_b.grid(row=1, column=1, padx=10, pady=5)
entry_b.bind("<KeyRelease>", validate_input)

ctk.CTkLabel(input_frame, text="a:", font=ctk.CTkFont(size=14)).grid(row=0, column=0, padx=10, pady=5, sticky="w")
ctk.CTkLabel(input_frame, text="b:", font=ctk.CTkFont(size=14)).grid(row=1, column=0, padx=10, pady=5, sticky="w")

# Buttons
button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
button_frame.grid(row=2, column=0, pady=10)

calculate_button = ctk.CTkButton(button_frame, text="Calculate", command=calculate_gcd_inverse, state="disabled", width=160)
calculate_button.grid(row=0, column=0, padx=10)

clear_button = ctk.CTkButton(button_frame, text="Clear", command=clear_inputs, width=160)
clear_button.grid(row=0, column=1, padx=10)

# Table section
table_frame = ctk.CTkFrame(main_frame, corner_radius=10)
table_frame.grid(row=3, column=0, sticky="nsew", pady=10, padx=10)
main_frame.columnconfigure(0, weight=1)
main_frame.rowconfigure(3, weight=1)

columns = ("Q", "A", "B", "R", "T1", "T2", "T")
tree = ttk.Treeview(table_frame, columns=columns, show="headings", style="Treeview")
tree.grid(row=0, column=0, sticky="nsew")
table_frame.columnconfigure(0, weight=1)
table_frame.rowconfigure(0, weight=1)

style = ttk.Style()
style.configure("Treeview", font=("Helvetica", 12), rowheight=30)
style.configure("Treeview.Heading", font=("Helvetica", 12, "bold"))

for col in columns:
    tree.heading(col, text=col)
    tree.column(col, width=100, anchor="center")

scrollbar = ctk.CTkScrollbar(table_frame, command=tree.yview)
scrollbar.grid(row=0, column=1, sticky="ns")
tree.configure(yscrollcommand=scrollbar.set)

# Results section (moved BELOW the table)
result_frame = ctk.CTkFrame(main_frame, corner_radius=10)
result_frame.grid(row=4, column=0, sticky="ew", pady=15, padx=10)

gcd_label = ctk.CTkLabel(
    result_frame, 
    text="", 
    font=ctk.CTkFont(size=18, weight="bold"), 
    text_color="#00ffcc"
)
gcd_label.grid(row=0, column=0, sticky="w", padx=10, pady=5)

inverse_label = ctk.CTkLabel(
    result_frame, 
    text="", 
    font=ctk.CTkFont(size=18, weight="bold"), 
    text_color="#00ccff"
)
inverse_label.grid(row=1, column=0, sticky="w", padx=10, pady=5)

root.mainloop()
