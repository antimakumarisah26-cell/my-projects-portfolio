import pyodbc
import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
from datetime import datetime, timedelta
import hashlib
import random
import re
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


# ---------- DATABASE SETUP ----------
DB_PASSWORD = 'technomax'
connection_string = (
    "DRIVER={SQL Server};"
    "SERVER=APRACHANASAH;"
    "DATABASE=ExpenseTrackerDB;"
    "UID=sa;"
    f"PWD={DB_PASSWORD};"
)

try:
    cnxn = pyodbc.connect(connection_string)
    cursor = cnxn.cursor()
    print("Database connected")
except Exception as e:
    cnxn = None
    cursor = None
    print(f"Database Connection Failed: {e}")

# Global variable to store logged in user's info
current_user = {'userid': None, 'username': None}

# Global variables for edit windows (ADD THESE)
edit_income_window = None
edit_expense_window = None


def get_totals(start_date=None, end_date=None):
    try:
        if start_date and end_date:
            income_query = "SELECT ISNULL(SUM(Amount), 0) FROM Income WHERE UserID=? AND Date BETWEEN ? AND ?"
            end_date_adj = end_date + timedelta(days=1) - timedelta(seconds=1)
            cursor.execute(income_query, (current_user['userid'], start_date, end_date_adj))
        else:
            cursor.execute("SELECT ISNULL(SUM(Amount), 0) FROM Income WHERE UserID=?", (current_user['userid'],))

        income_row = cursor.fetchone()
        total_income = income_row[0] if income_row[0] is not None else 0

        if start_date and end_date:
            expense_query = "SELECT ISNULL(SUM(Amount), 0) FROM Expense WHERE UserID=? AND Date BETWEEN ? AND ?"
            cursor.execute(expense_query, (current_user['userid'], start_date, end_date_adj))
        else:
            cursor.execute("SELECT ISNULL(SUM(Amount), 0) FROM Expense WHERE UserID=?", (current_user['userid'],))

        expense_row = cursor.fetchone()
        total_expense = expense_row[0] if expense_row[0] is not None else 0

        return float(total_income), float(total_expense)
    except Exception as e:
        messagebox.showerror("DB Error", str(e))
        return 0.0, 0.0


# ---------- CATEGORIES ----------
income_categories = ["salary", "bonus", "freelance", "interest", "gifts", "other"]
expense_categories = ["food", "clothes", "rent", "health", "transport", "entertainment", "other"]


# ---------- SHA-256 ----------
def hash_password_sha(password):
    return hashlib.sha256(password.encode()).hexdigest()


def send_otp_email(receiver_email, otp):
    messagebox.showinfo("OTP Code",
                        f"OTP for {receiver_email}:\n\n"
                        f"🔢 {otp}\n\n"
                        f"Note: In production, this would be sent via email.")
    return True


def validate_password(password):
    if len(password) < 4 or len(password) > 20:
        return "Password must be between 4 and 20 characters long."
    if not re.search(r"[A-Z]", password):
        return "Password must contain at least 1 uppercase letter."
    if not re.search(r"[a-z]", password):
        return "Password must contain at least 1 lowercase letter."
    if not re.search(r"[0-9]", password):
        return "Password must contain at least 1 number."
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return "Password must contain at least 1 special character."
    if re.search(r"\s", password):
        return "Password must not contain spaces."
    return "OK"


# Global variables for OTP
OTP_VALUE = None
OTP_EMAIL = None

# ---------- LOGIN WINDOW ----------
login_window = tk.Tk()
login_window.title("Expense Tracker - Login")
login_window.geometry("400x300")

username_var = tk.StringVar()
password_var = tk.StringVar()

# Login UI
tk.Label(login_window, text="Username").pack(pady=5)
tk.Entry(login_window, textvariable=username_var).pack(pady=5)
tk.Label(login_window, text="Password").pack(pady=5)
tk.Entry(login_window, textvariable=password_var, show="*").pack(pady=5)


# ---------- FORGOT PASSWORD FUNCTIONS ----------
def forgot_password():
    if cursor is None:
        messagebox.showerror("DB Error", "Database not connected. Cannot reset password.")
        return

    fp = tk.Toplevel(login_window)
    fp.title("Forgot Password")
    fp.geometry("350x200")

    tk.Label(fp, text="Enter Email:").pack(pady=10)
    email_entry = tk.Entry(fp, width=30)
    email_entry.pack()

    def send_otp_btn():
        email = email_entry.get().strip()
        if not email:
            messagebox.showerror("Error", "Enter an email")
            return
        try:
            cursor.execute("SELECT * FROM Users WHERE Email=?", (email,))
            if not cursor.fetchone():
                messagebox.showerror("Error", "Email not found!")
                return
        except Exception as e:
            messagebox.showerror("Error", f"DB error: {e}")
            return

        global OTP_VALUE, OTP_EMAIL
        OTP_EMAIL = email
        OTP_VALUE = random.randint(100000, 999999)

        send_otp_email(email, OTP_VALUE)
        messagebox.showinfo("Success", "OTP Sent to your email!")
        fp.destroy()
        verify_otp_window()

    tk.Button(fp, text="Send OTP", command=send_otp_btn).pack(pady=20)


def verify_otp_window():
    win = tk.Toplevel(login_window)
    win.title("Verify OTP")
    win.geometry("350x200")

    tk.Label(win, text="Enter OTP").pack(pady=10)
    otp_entry = tk.Entry(win, width=20)
    otp_entry.pack()

    def verify():
        if otp_entry.get() == str(OTP_VALUE):
            messagebox.showinfo("Success", "OTP Verified!")
            win.destroy()
            reset_password_window()
        else:
            messagebox.showerror("Error", "Invalid OTP")

    tk.Button(win, text="Verify", command=verify).pack(pady=20)


def reset_password_window():
    rp = tk.Toplevel(login_window)
    rp.title("Reset Password")
    rp.geometry("350x300")

    tk.Label(rp, text="New Password").pack(pady=10)
    new_pass = tk.Entry(rp, width=25, show="*")
    new_pass.pack()

    tk.Label(rp, text="Confirm Password").pack(pady=10)
    confirm_pass = tk.Entry(rp, width=25, show="*")
    confirm_pass.pack()

    def save_new_password():
        p = new_pass.get().strip()
        cp = confirm_pass.get().strip()

        if not p or not cp:
            messagebox.showerror("Error", "Both password fields are required.")
            return

        if p != cp:
            messagebox.showerror("Error", "Passwords do not match.")
            return

        result = validate_password(p)
        if result != "OK":
            messagebox.showerror("Password Error", result)
            return

        hashed = hashlib.sha256(p.encode()).hexdigest()
        try:
            cursor.execute("UPDATE Users SET Password=? WHERE Email=?", (hashed, OTP_EMAIL))
            cnxn.commit()
        except Exception as e:
            messagebox.showerror("Error", f"DB error: {e}")
            return

        messagebox.showinfo("Success", "Password Updated Successfully!")
        rp.destroy()

    tk.Button(rp, text="Save Password", command=save_new_password).pack(pady=20)


# ---------- LOGIN FUNCTION ----------
def login():
    global current_user
    if cursor is None:
        messagebox.showerror("DB Error", "Database not connected.")
        return

    username = username_var.get().strip()
    password = password_var.get()
    try:
        cursor.execute("SELECT UserID, Password FROM Users WHERE Username=?", (username,))
        row = cursor.fetchone()
        if row:
            userid = row[0]
            stored_hash = row[1]

            if stored_hash == hash_password_sha(password):
                current_user['userid'] = userid
                current_user['username'] = username
                messagebox.showinfo("Success", f"Welcome {username}!")
                login_window.withdraw()
                open_dashboard()
            else:
                messagebox.showerror("Error", "Invalid password!")
        else:
            messagebox.showerror("Error", "Username not found!")
    except Exception as e:
        messagebox.showerror("Error", str(e))


# ---------- SIGNUP FUNCTION ----------
def signup():
    if cursor is None:
        messagebox.showerror("DB Error", "Database not connected.")
        return

    signup_win = tk.Toplevel(login_window)
    signup_win.title("Signup")
    signup_win.geometry("400x350")

    new_username = tk.StringVar()
    new_password = tk.StringVar()
    confirm_password = tk.StringVar()
    new_email = tk.StringVar()

    form_frame = tk.Frame(signup_win)
    form_frame.pack(pady=20)

    tk.Label(form_frame, text="Username:").grid(row=0, column=0, sticky="w", pady=5, padx=5)
    tk.Entry(form_frame, textvariable=new_username, width=25).grid(row=0, column=1, pady=5, padx=5)

    tk.Label(form_frame, text="Email:").grid(row=1, column=0, sticky="w", pady=5, padx=5)
    tk.Entry(form_frame, textvariable=new_email, width=25).grid(row=1, column=1, pady=5, padx=5)

    tk.Label(form_frame, text="Password:").grid(row=2, column=0, sticky="w", pady=5, padx=5)
    tk.Entry(form_frame, textvariable=new_password, show="*", width=25).grid(row=2, column=1, pady=5, padx=5)

    tk.Label(form_frame, text="Confirm Password:").grid(row=3, column=0, sticky="w", pady=5, padx=5)
    tk.Entry(form_frame, textvariable=confirm_password, show="*", width=25).grid(row=3, column=1, pady=5, padx=5)

    def register_user():
        u = new_username.get().strip()
        p = new_password.get().strip()
        cp = confirm_password.get().strip()
        e = new_email.get().strip()

        if not u or not p or not cp or not e:
            messagebox.showerror("Error", "All fields are required!")
            return

        if p != cp:
            messagebox.showerror("Error", "Passwords do not match!")
            return

        result = validate_password(p)
        if result != "OK":
            messagebox.showerror("Password Error", result)
            return

        hashed_pw = hash_password_sha(p)
        try:
            cursor.execute("INSERT INTO Users (Username, Password, Email) VALUES (?, ?, ?)", (u, hashed_pw, e))
            cnxn.commit()
            messagebox.showinfo("Success", "User registered successfully!")
            signup_win.destroy()
        except pyodbc.IntegrityError:
            messagebox.showerror("Error", "Username or Email already exists!")
        except Exception as ex:
            messagebox.showerror("Error", f"DB error: {ex}")

    tk.Button(signup_win, text="Register", command=register_user,
              bg="green", fg="white", width=15).pack(pady=15)


# ---------- LOGIN BUTTONS ----------
tk.Button(login_window, text="Login", command=login,
          bg="blue", fg="white", width=12).pack(pady=10)
tk.Button(login_window, text="Forgot Password?", command=forgot_password,
          fg="red").pack(pady=5)
tk.Button(login_window, text="Signup", command=signup,
          bg="orange", fg="white", width=12).pack(pady=5)


# ---------- DASHBOARD FUNCTIONS ----------
def open_dashboard():
    window = tk.Toplevel()
    window.title(f"Expense Tracker - Welcome {current_user['username']}")
    window.geometry("1100x700")

    # ---------------- GLOBAL VARIABLES ----------------
    global income_start_date_var, income_end_date_var, expense_start_date_var, expense_end_date_var
    global income_tree, expense_tree, total_income_label, total_expense_label
    global ai_category, ai_amount, ai_desc, ae_category, ae_amount, ae_desc
    global chart_container
    global edit_income_window, edit_expense_window  # ADD THIS

    # Initialize StringVars
    income_start_date_var = tk.StringVar()
    income_end_date_var = tk.StringVar()
    expense_start_date_var = tk.StringVar()
    expense_end_date_var = tk.StringVar()
    ai_category = tk.StringVar()
    ai_amount = tk.StringVar()
    ai_desc = tk.StringVar()
    ae_category = tk.StringVar()
    ae_amount = tk.StringVar()
    ae_desc = tk.StringVar()

    # Initialize other variables
    income_tree = None
    expense_tree = None
    total_income_label = None
    total_expense_label = None
    edit_income_window = None  # ADD THIS
    edit_expense_window = None  # ADD THIS

    # ---------------- TOP BAR ----------------
    top_bar = tk.Frame(window, bg="lightgray", height=50)
    top_bar.pack(fill="x")

    welcome_label = tk.Label(top_bar, text=f"Welcome, {current_user['username']}!",
                             font=("Arial", 12, "bold"))
    welcome_label.pack(side="left", padx=10, pady=10)

    def logout():
        global current_user
        current_user = {'userid': None, 'username': None}
        window.destroy()
        login_window.deiconify()
        username_var.set("")
        password_var.set("")

    logout_btn = tk.Button(top_bar, text="Logout", command=logout,
                           bg="orange", fg="white")
    logout_btn.pack(side="right", padx=10, pady=10)

    # ---------------- MENU BAR ----------------
    menu_bar = tk.Frame(window, bg="#e8e8e8", height=40)
    menu_bar.pack(fill="x")

    # ---------------- MAIN CONTAINER FRAME ----------------
    main_container = tk.Frame(window)
    main_container.pack(fill="both", expand=True, padx=10, pady=10)

    # Left frame for chart (40% width)
    chart_container = tk.Frame(main_container, bg="white", relief="groove", bd=2)
    chart_container.pack(side="left", fill="both", expand=True, padx=(0, 5))

    # Right frame for table (60% width)
    table_container = tk.Frame(main_container, bg="white", relief="groove", bd=2)
    table_container.pack(side="right", fill="both", expand=True, padx=(5, 0))

    def show_bar_chart(frame, start_date=None, end_date=None):
        # Default to last 1 month if no dates provided
        if start_date is None or end_date is None:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)

        # Clear previous chart widgets
        for widget in frame.winfo_children():
            widget.destroy()

        # Chart title with date range
        date_range_text = f"({start_date.strftime('%d-%b')} to {end_date.strftime('%d-%b')})"

        # Create title frame
        title_frame = tk.Frame(frame)
        title_frame.pack(pady=10)
        tk.Label(title_frame, text=f"Income vs Expense {date_range_text}",
                 font=("Arial", 14, "bold")).pack()

        # Fetch BOTH income AND expense for the date range
        try:
            # Income query
            income_query = "SELECT ISNULL(SUM(Amount),0) FROM Income WHERE UserID=? AND Date BETWEEN ? AND ?"
            end_date_adj = end_date + timedelta(days=1) - timedelta(seconds=1)
            cursor.execute(income_query, (current_user['userid'], start_date, end_date_adj))
            income = cursor.fetchone()[0]

            # Expense query
            expense_query = "SELECT ISNULL(SUM(Amount),0) FROM Expense WHERE UserID=? AND Date BETWEEN ? AND ?"
            cursor.execute(expense_query, (current_user['userid'], start_date, end_date_adj))
            expense = cursor.fetchone()[0]

        except Exception as e:
            messagebox.showerror("DB Error", str(e))
            income, expense = 0, 0

        # Chart
        fig = Figure(figsize=(5, 4), dpi=100)
        ax = fig.add_subplot(111)

        categories = ["Income", "Expense"]
        values = [income, expense]

        bars = ax.bar(categories, values, color=["green", "red"])
        ax.set_title(f"Income vs Expense {date_range_text}", fontsize=12, fontweight='bold')
        ax.set_ylabel("Amount (₹)", fontsize=10)

        # Remove Y-axis tick labels for cleaner look
        ax.yaxis.set_ticklabels([])

        # Add value labels on top of bars
        for bar, val in zip(bars, values):
            height = bar.get_height()
            if height > 0:
                ax.text(bar.get_x() + bar.get_width() / 2., height,
                        f'₹{val:,.0f}',
                        ha='center', va='bottom', fontweight='bold', fontsize=10)

        chart_canvas = FigureCanvasTkAgg(fig, master=frame)
        chart_canvas.draw()
        chart_canvas.get_tk_widget().pack(fill="both", expand=True, padx=20, pady=20)

    # Initial chart display with last 1 month
    show_bar_chart(chart_container)

    # ---------------- FRAMES FOR DIFFERENT VIEWS ----------------
    Frame_Add_Income = tk.Frame(table_container, bg="white")
    Frame_View_Income = tk.Frame(table_container, bg="white")
    Frame_Add_Expense = tk.Frame(table_container, bg="white")
    Frame_View_Expense = tk.Frame(table_container, bg="white")

    # ---------------- HIDE ALL TABLE FRAMES ----------------
    def hide_all_table_frames():
        Frame_Add_Income.pack_forget()
        Frame_View_Income.pack_forget()
        Frame_Add_Expense.pack_forget()
        Frame_View_Expense.pack_forget()

    # ---------------- SHOW TABLE FRAME FUNCTION ----------------
    def show_table_frame(f):
        hide_all_table_frames()
        f.pack(fill="both", expand=True, padx=10, pady=10)

    # ---------------- MENU BUTTONS ----------------
    tk.Button(menu_bar, text="Add Income", command=lambda: show_table_frame(Frame_Add_Income)).pack(side="left",
                                                                                                    padx=10)
    tk.Button(menu_bar, text="View Income", command=lambda: show_table_frame(Frame_View_Income)).pack(side="left",
                                                                                                      padx=10)
    tk.Button(menu_bar, text="Add Expense", command=lambda: show_table_frame(Frame_Add_Expense)).pack(side="left",
                                                                                                      padx=10)
    tk.Button(menu_bar, text="View Expense", command=lambda: show_table_frame(Frame_View_Expense)).pack(side="left",
                                                                                                        padx=10)

    # ---------- FUNCTIONS ----------
    def get_default_month_range():
        today = datetime.now()
        last_month = today - timedelta(days=30)
        return last_month, today

    # ---------- 1 MONTH FILTER FUNCTIONS ----------
    def load_last_month_income():
        start, end = get_default_month_range()
        income_start_date_var.set(start.strftime("%Y-%m-%d"))
        income_end_date_var.set(end.strftime("%Y-%m-%d"))
        load_income(start, end)

    def load_last_month_expense():
        start, end = get_default_month_range()
        expense_start_date_var.set(start.strftime("%Y-%m-%d"))
        expense_end_date_var.set(end.strftime("%Y-%m-%d"))
        load_expense(start, end)

    # ---------- ADD INCOME / EXPENSE ----------
    def add_income():
        if cursor is None:
            messagebox.showerror("DB Error", "Database not connected.")
            return
        try:
            cat = ai_category.get()
            amt = float(ai_amount.get())
            desc = ai_desc.get()
        except ValueError:
            messagebox.showerror("Error", "Enter a valid amount")
            return
        try:
            cursor.execute(
                "INSERT INTO Income (UserID, Date, Category, Amount, Description) VALUES (?, ?, ?, ?, ?)",
                (current_user['userid'], datetime.now(), cat, amt, desc)
            )
            cnxn.commit()
            messagebox.showinfo("Success", "Income Added")

            # Update chart with current filter
            try:
                start = datetime.strptime(income_start_date_var.get(), "%Y-%m-%d")
                end = datetime.strptime(income_end_date_var.get(), "%Y-%m-%d")
                show_bar_chart(chart_container, start, end)
            except:
                show_bar_chart(chart_container)

            if Frame_View_Income.winfo_ismapped():
                load_last_month_income()

            # Clear fields
            ai_category.set("")
            ai_amount.set("")
            ai_desc.set("")

        except Exception as e:
            messagebox.showerror("Error", str(e))

    def add_expense():
        if cursor is None:
            messagebox.showerror("DB Error", "Database not connected.")
            return
        try:
            cat = ae_category.get()
            amt = float(ae_amount.get())
            desc = ae_desc.get()
        except ValueError:
            messagebox.showerror("Error", "Enter a valid amount")
            return
        try:
            cursor.execute(
                "INSERT INTO Expense (UserID, Date, Category, Amount, Description) VALUES (?, ?, ?, ?, ?)",
                (current_user['userid'], datetime.now(), cat, amt, desc)
            )
            cnxn.commit()
            messagebox.showinfo("Success", "Expense Added")

            # Update chart with current filter
            try:
                start = datetime.strptime(expense_start_date_var.get(), "%Y-%m-%d")
                end = datetime.strptime(expense_end_date_var.get(), "%Y-%m-%d")
                show_bar_chart(chart_container, start, end)
            except:
                show_bar_chart(chart_container)

            if Frame_View_Expense.winfo_ismapped():
                load_last_month_expense()

            # Clear fields
            ae_category.set("")
            ae_amount.set("")
            ae_desc.set("")

        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ---------- LOAD DATA ----------
    def load_income(start_date=None, end_date=None):
        if income_tree is None:
            return
        for row in income_tree.get_children():
            income_tree.delete(row)
        total = 0
        query = "SELECT IncomeID, Date, Category, Amount, Description FROM Income WHERE UserID=?"
        params = (current_user['userid'],)
        if start_date and end_date:
            query += " AND Date BETWEEN ? AND ?"
            end_date_adj = end_date + timedelta(days=1) - timedelta(seconds=1)
            params = (current_user['userid'], start_date, end_date_adj)
        try:
            cursor.execute(query, params)
        except Exception as e:
            messagebox.showerror("Error", f"DB error: {e}")
            return

        for r in cursor.fetchall():
            row_id = r[0]
            if r[1]:
                if isinstance(r[1], datetime):
                    date_str = r[1].strftime("%Y-%m-%d")
                else:
                    date_parts = str(r[1]).split()
                    date_str = date_parts[0] if date_parts else ""
            else:
                date_str = ""

            amount_str = f"{r[3]:.2f}"
            income_tree.insert("", "end", values=(row_id, r[2], amount_str, r[4], date_str))
            total += float(r[3])

        # Show total with date range
        if total_income_label:
            if start_date and end_date:
                total_income_label.config(
                    text=f"Total Income ({start_date.strftime('%d-%b')} to {end_date.strftime('%d-%b')}): ₹{total:,.2f}")
            else:
                total_income_label.config(text=f"Total Income: ₹{total:,.2f}")

        # Update chart with same filter
        if start_date and end_date:
            show_bar_chart(chart_container, start_date, end_date)
        else:
            try:
                start = datetime.strptime(income_start_date_var.get(), "%Y-%m-%d")
                end = datetime.strptime(income_end_date_var.get(), "%Y-%m-%d")
                show_bar_chart(chart_container, start, end)
            except:
                start, end = get_default_month_range()
                show_bar_chart(chart_container, start, end)

    def load_expense(start_date=None, end_date=None):
        if expense_tree is None:
            return
        for row in expense_tree.get_children():
            expense_tree.delete(row)
        total = 0
        query = "SELECT Id, Date, Category, Amount, Description FROM Expense WHERE UserID=?"
        params = (current_user['userid'],)
        if start_date and end_date:
            query += " AND Date BETWEEN ? AND ?"
            end_date_adj = end_date + timedelta(days=1) - timedelta(seconds=1)
            params = (current_user['userid'], start_date, end_date_adj)
        try:
            cursor.execute(query, params)
        except Exception as e:
            messagebox.showerror("Error", f"DB error: {e}")
            return

        for r in cursor.fetchall():
            row_id = r[0]
            if r[1]:
                if isinstance(r[1], datetime):
                    date_str = r[1].strftime("%Y-%m-%d")
                else:
                    date_parts = str(r[1]).split()
                    date_str = date_parts[0] if date_parts else ""
            else:
                date_str = ""

            amount_str = f"{r[3]:.2f}"
            expense_tree.insert("", "end", values=(row_id, r[2], amount_str, r[4], date_str))
            total += float(r[3])

        # Show total with date range
        if total_expense_label:
            if start_date and end_date:
                total_expense_label.config(
                    text=f"Total Expense ({start_date.strftime('%d-%b')} to {end_date.strftime('%d-%b')}): ₹{total:,.2f}")
            else:
                total_expense_label.config(text=f"Total Expense: ₹{total:,.2f}")

        # Update chart with same filter
        if start_date and end_date:
            show_bar_chart(chart_container, start_date, end_date)
        else:
            try:
                start = datetime.strptime(expense_start_date_var.get(), "%Y-%m-%d")
                end = datetime.strptime(expense_end_date_var.get(), "%Y-%m-%d")
                show_bar_chart(chart_container, start, end)
            except:
                start, end = get_default_month_range()
                show_bar_chart(chart_container, start, end)

    # ---------- BUILD UI ----------
    def build_add_income_ui():
        tk.Label(Frame_Add_Income, text="ADD INCOME", font=("Arial", 16, "bold")).pack(pady=10)
        form = tk.Frame(Frame_Add_Income)
        form.pack(pady=10)

        tk.Label(form, text="Category").grid(row=0, column=0, padx=5, pady=5)
        ttk.Combobox(form, textvariable=ai_category, values=income_categories, state="readonly").grid(row=0, column=1,
                                                                                                      padx=5, pady=5)
        tk.Label(form, text="Amount").grid(row=1, column=0, padx=5, pady=5)
        tk.Entry(form, textvariable=ai_amount).grid(row=1, column=1, padx=5, pady=5)
        tk.Label(form, text="Description").grid(row=2, column=0, padx=5, pady=5)
        tk.Entry(form, textvariable=ai_desc).grid(row=2, column=1, padx=5, pady=5)
        tk.Button(Frame_Add_Income, text="Add Income", command=add_income, bg="green", fg="white").pack(pady=10)

    def build_add_expense_ui():
        tk.Label(Frame_Add_Expense, text="ADD EXPENSE", font=("Arial", 16, "bold")).pack(pady=10)
        form = tk.Frame(Frame_Add_Expense)
        form.pack(pady=10)

        tk.Label(form, text="Category").grid(row=0, column=0, padx=5, pady=5)
        ttk.Combobox(form, textvariable=ae_category, values=expense_categories, state="readonly").grid(row=0, column=1,
                                                                                                       padx=5, pady=5)
        tk.Label(form, text="Amount").grid(row=1, column=0, padx=5, pady=5)
        tk.Entry(form, textvariable=ae_amount).grid(row=1, column=1, padx=5, pady=5)
        tk.Label(form, text="Description").grid(row=2, column=0, padx=5, pady=5)
        tk.Entry(form, textvariable=ae_desc).grid(row=2, column=1, padx=5, pady=5)
        tk.Button(Frame_Add_Expense, text="Add Expense", command=add_expense, bg="red", fg="white").pack(pady=10)

    # ---------- VIEW + EDIT INCOME ----------
    def build_view_income_ui():
        tk.Label(Frame_View_Income, text="INCOME RECORDS", font=("Arial", 16, "bold")).pack(pady=10)
        global income_tree, total_income_label

        filter_frame = tk.Frame(Frame_View_Income)
        filter_frame.pack(pady=5)

        tk.Label(filter_frame, text="Start Date (YYYY-MM-DD)").grid(row=0, column=0, padx=5)
        tk.Entry(filter_frame, textvariable=income_start_date_var, width=12).grid(row=0, column=1, padx=5)
        tk.Label(filter_frame, text="End Date (YYYY-MM-DD)").grid(row=0, column=2, padx=5)
        tk.Entry(filter_frame, textvariable=income_end_date_var, width=12).grid(row=0, column=3, padx=5)

        tk.Button(filter_frame, text="1 Month", command=load_last_month_income).grid(row=0, column=4, padx=5)
        tk.Button(filter_frame, text="Apply Filter", command=lambda: apply_income_date_filter()).grid(row=0, column=5,
                                                                                                      padx=5)

        income_tree = ttk.Treeview(Frame_View_Income,
                                   columns=("IncomeID", "Category", "Amount", "Description", "Date"),
                                   show="headings", height=15)

        income_tree.column("IncomeID", width=0, stretch=False, minwidth=0)
        income_tree.heading("Category", text="Category", anchor="center")
        income_tree.column("Category", width=120, anchor="center", minwidth=120)
        income_tree.heading("Amount", text="Amount", anchor="center")
        income_tree.column("Amount", width=100, anchor="center", minwidth=100)
        income_tree.heading("Description", text="Description", anchor="center")
        income_tree.column("Description", width=200, anchor="center", minwidth=200)
        income_tree.heading("Date", text="Date", anchor="center")
        income_tree.column("Date", width=120, anchor="center", minwidth=120)

        income_tree.pack(fill="both", expand=True, padx=10, pady=5)
        income_tree.bind("<Double-1>", lambda event: edit_income())

        total_income_label = tk.Label(Frame_View_Income, text="Total Income: ₹0.00", font=("Arial", 12, "bold"))
        total_income_label.pack(pady=5)
        tk.Button(Frame_View_Income, text="Refresh", command=lambda: apply_income_date_filter()).pack(pady=5)

    def edit_income():
        global edit_income_window
        if edit_income_window is not None and edit_income_window.winfo_exists():
            edit_income_window.lift()  # bring to front if already open
            return

        selected = income_tree.selection()
        if not selected:
            messagebox.showwarning("No selection", "Please select a row")
            return
        item = income_tree.item(selected)
        row_id, old_category, old_amount, old_desc, old_date = item['values']

        if old_date and len(str(old_date)) >= 10:
            date_only = str(old_date)[:10]
        else:
            date_only = datetime.now().strftime("%Y-%m-%d")

        edit_income_window = tk.Toplevel(window)
        edit_income_window.title("Edit Income")
        edit_income_window.geometry("350x300")

        def close_edit_income_window():
            global edit_income_window
            if edit_income_window is not None:
                edit_income_window.destroy()
            edit_income_window = None

        edit_income_window.protocol("WM_DELETE_WINDOW", close_edit_income_window)

        tk.Label(edit_income_window, text="Category").pack(pady=5)
        cat_var = tk.StringVar(value=old_category)
        ttk.Combobox(edit_income_window, textvariable=cat_var, values=income_categories, state="readonly").pack()
        tk.Label(edit_income_window, text="Amount").pack(pady=5)
        amt_var = tk.StringVar(value=str(old_amount))
        tk.Entry(edit_income_window, textvariable=amt_var).pack()
        tk.Label(edit_income_window, text="Description").pack(pady=5)
        desc_var = tk.StringVar(value=old_desc)
        tk.Entry(edit_income_window, textvariable=desc_var).pack()
        tk.Label(edit_income_window, text="Date").pack(pady=5)
        date_var = tk.StringVar(value=date_only)
        DateEntry(edit_income_window, textvariable=date_var, date_pattern="yyyy-mm-dd").pack()

        def save_changes():
            if cursor is None:
                messagebox.showerror("DB Error", "Database not connected.")
                return
            try:
                amt = float(amt_var.get())
            except ValueError:
                messagebox.showerror("Error", "Enter a valid amount")
                return
            try:
                cursor.execute("SELECT UserID FROM Income WHERE IncomeID=?", (int(row_id),))
                income_user = cursor.fetchone()
                if income_user and income_user[0] == current_user['userid']:
                    cursor.execute("""
                        UPDATE Income SET Category=?, Amount=?, Description=?, Date=?
                        WHERE IncomeID=?
                    """, (cat_var.get(), amt, desc_var.get(), date_var.get(), int(row_id)))
                    cnxn.commit()
                    messagebox.showinfo("Success", "Income updated!")
                try:
                    start = datetime.strptime(income_start_date_var.get(), "%Y-%m-%d")
                    end = datetime.strptime(income_end_date_var.get(), "%Y-%m-%d")
                    load_income(start, end)
                except:
                    load_income()
                close_edit_income_window()
            except Exception as e:
                messagebox.showerror("Error", f"Update failed: {e}")

        tk.Button(edit_income_window, text="Save Changes", bg="green", fg="white", command=save_changes).pack(pady=10)
        tk.Button(edit_income_window, text="Cancel", bg="gray", fg="white", command=close_edit_income_window).pack(
            pady=5)

    def apply_income_date_filter():
        try:
            start = datetime.strptime(income_start_date_var.get(), "%Y-%m-%d")
            end = datetime.strptime(income_end_date_var.get(), "%Y-%m-%d")
            load_income(start, end)
        except:
            messagebox.showerror("Invalid Date", "Enter valid YYYY-MM-DD dates")

    # ---------- VIEW + EDIT EXPENSE ----------
    def build_view_expense_ui():
        tk.Label(Frame_View_Expense, text="EXPENSE RECORDS", font=("Arial", 16, "bold")).pack(pady=10)
        global expense_tree, total_expense_label

        filter_frame = tk.Frame(Frame_View_Expense)
        filter_frame.pack(pady=5)

        tk.Label(filter_frame, text="Start Date (YYYY-MM-DD)").grid(row=0, column=0, padx=5)
        tk.Entry(filter_frame, textvariable=expense_start_date_var, width=12).grid(row=0, column=1, padx=5)
        tk.Label(filter_frame, text="End Date (YYYY-MM-DD)").grid(row=0, column=2, padx=5)
        tk.Entry(filter_frame, textvariable=expense_end_date_var, width=12).grid(row=0, column=3, padx=5)

        tk.Button(filter_frame, text="1 Month", command=load_last_month_expense).grid(row=0, column=4, padx=5)
        tk.Button(filter_frame, text="Apply Filter", command=lambda: apply_expense_date_filter()).grid(row=0, column=5,
                                                                                                       padx=5)

        expense_tree = ttk.Treeview(Frame_View_Expense,
                                    columns=("ID", "Category", "Amount", "Description", "Date"),
                                    show="headings", height=15)

        expense_tree.column("ID", width=0, stretch=False, minwidth=0)
        expense_tree.heading("Category", text="Category", anchor="center")
        expense_tree.column("Category", width=120, anchor="center", minwidth=120)
        expense_tree.heading("Amount", text="Amount", anchor="center")
        expense_tree.column("Amount", width=100, anchor="center", minwidth=100)
        expense_tree.heading("Description", text="Description", anchor="center")
        expense_tree.column("Description", width=200, anchor="center", minwidth=200)
        expense_tree.heading("Date", text="Date", anchor="center")
        expense_tree.column("Date", width=120, anchor="center", minwidth=120)

        expense_tree.pack(fill="both", expand=True, padx=10, pady=5)
        expense_tree.bind("<Double-1>", lambda event: edit_expense())

        total_expense_label = tk.Label(Frame_View_Expense, text="Total Expense: ₹0.00", font=("Arial", 12, "bold"))
        total_expense_label.pack(pady=5)
        tk.Button(Frame_View_Expense, text="Refresh", command=lambda: apply_expense_date_filter()).pack(pady=5)

    def edit_expense():
        global edit_expense_window
        if edit_expense_window is not None and edit_expense_window.winfo_exists():
            edit_expense_window.lift()  # bring to front if already open
            return

        selected = expense_tree.selection()
        if not selected:
            messagebox.showwarning("No selection", "Please select a row")
            return
        item = expense_tree.item(selected)
        row_id, old_category, old_amount, old_desc, old_date = item['values']

        if old_date and len(str(old_date)) >= 10:
            date_only = str(old_date)[:10]
        else:
            date_only = datetime.now().strftime("%Y-%m-%d")

        edit_expense_window = tk.Toplevel(window)
        edit_expense_window.title("Edit Expense")
        edit_expense_window.geometry("350x280")

        def close_edit_expense_window():
            global edit_expense_window
            if edit_expense_window is not None:
                edit_expense_window.destroy()
            edit_expense_window = None

        edit_expense_window.protocol("WM_DELETE_WINDOW", close_edit_expense_window)

        tk.Label(edit_expense_window, text="Category").pack(pady=5)
        cat_var = tk.StringVar(value=old_category)
        ttk.Combobox(edit_expense_window, textvariable=cat_var, values=expense_categories, state="readonly").pack()
        tk.Label(edit_expense_window, text="Amount").pack(pady=5)
        amt_var = tk.StringVar(value=str(old_amount))
        tk.Entry(edit_expense_window, textvariable=amt_var).pack()
        tk.Label(edit_expense_window, text="Description").pack(pady=5)
        desc_var = tk.StringVar(value=old_desc)
        tk.Entry(edit_expense_window, textvariable=desc_var).pack()
        tk.Label(edit_expense_window, text="Date").pack(pady=5)
        date_var = tk.StringVar(value=date_only)
        DateEntry(edit_expense_window, textvariable=date_var, date_pattern="yyyy-mm-dd").pack()

        def save_changes():
            if cursor is None:
                messagebox.showerror("DB Error", "Database not connected.")
                return
            try:
                new_date = datetime.strptime(date_var.get(), "%Y-%m-%d")
            except:
                messagebox.showerror("Error", "Invalid date")
                return
            try:
                cursor.execute("SELECT UserID FROM Expense WHERE ID=?", (int(row_id),))
                expense_user = cursor.fetchone()
                if expense_user and expense_user[0] == current_user['userid']:
                    cursor.execute("""
                        UPDATE Expense SET Category=?, Amount=?, Description=?, Date=?
                        WHERE ID=?
                    """, (cat_var.get(), float(amt_var.get()), desc_var.get(), date_var.get(), int(row_id)))
                    cnxn.commit()
                    messagebox.showinfo("Success", "Expense updated!")
                try:
                    start = datetime.strptime(expense_start_date_var.get(), "%Y-%m-%d")
                    end = datetime.strptime(expense_end_date_var.get(), "%Y-%m-%d")
                    load_expense(start, end)
                except:
                    load_expense()
                close_edit_expense_window()
            except Exception as e:
                messagebox.showerror("Error", f"Update failed: {e}")

        tk.Button(edit_expense_window, text="Save Changes", bg="green", fg="white", command=save_changes).pack(pady=10)
        tk.Button(edit_expense_window, text="Cancel", bg="gray", fg="white", command=close_edit_expense_window).pack(
            pady=5)

    def apply_expense_date_filter():
        try:
            start = datetime.strptime(expense_start_date_var.get(), "%Y-%m-%d")
            end = datetime.strptime(expense_end_date_var.get(), "%Y-%m-%d")
            load_expense(start, end)
        except:
            messagebox.showerror("Invalid Date", "Enter valid YYYY-MM-DD dates")

    # ---------- BUILD FRAMES ----------
    build_add_income_ui()
    build_add_expense_ui()
    build_view_income_ui()
    build_view_expense_ui()

    # Initial data load
    load_last_month_income()
    load_last_month_expense()


# ---------- RUN MAIN LOOP ----------
login_window.mainloop()