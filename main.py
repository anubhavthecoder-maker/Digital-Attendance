import flet as ft
import sqlite3
import os
import shutil
import asyncio
import csv
from datetime import date, datetime

# ================================================================
#  GLOBAL STATE STORAGE & DYNAMIC THEME
# ================================================================
app_state = {
    "selected_date": None,
    "selected_display": None,
    "theme": "dark" # Default theme
}

def get_colors():
    if app_state["theme"] == "light":
        return {
            "bg": "#F5F5F7",
            "card": "#FFFFFF",
            "hover": "#E5E5EA",
            "text": "#1C1C1E",
            "text_muted": "#8E8E93",
            "accent": "#D4AF37", 
            "green": "#34C759",
            "red": "#FF3B30",
            "header_text": "#000000"
        }
    else:
        return {
            "bg": "#0F1115",
            "card": "#1A1D24",
            "hover": "#262932",
            "text": "#FFFFFF",
            "text_muted": "#8A8D93",
            "accent": "#D4AF37",
            "green": "#66BB6A",
            "red": "#EF5350",
            "header_text": "#FFFFFF"
        }

# ================================================================
#  THE DATABASE & BACKUP SETUP
# ================================================================

DB = "attendance_app.db"
BACKUP_DIR = "Database_Backups"
EXPORT_DIR = "Exports"

def setup_database():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id   INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            date       TEXT NOT NULL,
            status     TEXT NOT NULL
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS holidays (
            date TEXT PRIMARY KEY,
            reason TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def auto_backup_db():
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
    
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_path = os.path.join(BACKUP_DIR, f"backup_{timestamp}.db")
    latest_path = os.path.join(BACKUP_DIR, "latest_backup.db")
    
    try:
        shutil.copy2(DB, backup_path)
        shutil.copy2(DB, latest_path)
    except Exception:
        pass

def today():
    return date.today().strftime("%Y-%m-%d")

# --- Export to Excel Feature ---
def export_all_to_csv():
    if not os.path.exists(EXPORT_DIR):
        os.makedirs(EXPORT_DIR)
        
    filename = os.path.join(EXPORT_DIR, f"School_Attendance_Export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
    
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
        SELECT attendance.date, 
               COALESCE(students.name, 'Deleted Student [ID: ' || attendance.student_id || ']'), 
               attendance.status
        FROM attendance
        LEFT JOIN students ON attendance.student_id = students.id
        ORDER BY attendance.date DESC, students.name
    """)
    rows = c.fetchall()
    conn.close()
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["Date", "Student Name", "Status"])
        writer.writerows(rows)
        
    return filename

# --- Holiday Functions ---
def get_all_holidays():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT date, reason FROM holidays ORDER BY date DESC")
    rows = c.fetchall()
    conn.close()
    return rows

def add_holiday(h_date, reason):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO holidays (date, reason) VALUES (?, ?)", (h_date, reason))
    conn.commit()
    conn.close()

def remove_holiday(h_date):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("DELETE FROM holidays WHERE date = ?", (h_date,))
    conn.commit()
    conn.close()

def get_holiday_reason(h_date):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT reason FROM holidays WHERE date = ?", (h_date,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

# --- Student & Attendance Functions ---
def get_all_students():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT id, name FROM students ORDER BY name")
    rows = c.fetchall()
    conn.close()
    return rows

def add_student(name):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("INSERT INTO students (name) VALUES (?)", (name,))
    conn.commit()
    conn.close()

def remove_student(sid):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("DELETE FROM students WHERE id = ?", (sid,))
    conn.commit()
    conn.close()

def is_attendance_done_today():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM attendance WHERE date = ?", (today(),))
    count = c.fetchone()[0]
    conn.close()
    return count > 0

def save_attendance(records):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    for sid, status in records:
        c.execute(
            "INSERT INTO attendance (student_id, date, status) VALUES (?, ?, ?)",
            (sid, today(), status)
        )
    conn.commit()
    conn.close()
    auto_backup_db()

def get_attendance_for_date(date_str):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
        SELECT COALESCE(students.name, 'Deleted Student [ID: ' || attendance.student_id || ']'), attendance.status
        FROM attendance
        LEFT JOIN students ON attendance.student_id = students.id
        WHERE attendance.date = ?
        ORDER BY students.name
    """, (date_str,))
    rows = c.fetchall()
    conn.close()
    return rows

def get_all_dates():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT DISTINCT date FROM attendance ORDER BY date DESC")
    rows = c.fetchall()
    conn.close()
    return [r[0] for r in rows]

def get_analytics_stats(period="month"):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    today_str = today()
    
    if period == "month":
        prefix = today_str[:7] 
    else:
        prefix = today_str[:4] 

    c.execute("SELECT COUNT(DISTINCT date) FROM attendance WHERE date LIKE ?", (f"{prefix}%",))
    total_days = c.fetchone()[0]

    stats = []
    if total_days > 0:
        c.execute("SELECT id, name FROM students ORDER BY name")
        students = c.fetchall()
        for sid, name in students:
            c.execute("SELECT COUNT(*) FROM attendance WHERE student_id = ? AND date LIKE ? AND status = 'present'", (sid, f"{prefix}%"))
            present_days = c.fetchone()[0]
            pct = int((present_days / total_days) * 100)
            stats.append((name, pct, present_days, total_days))
            
    conn.close()
    return stats, total_days

def get_all_months():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT DISTINCT SUBSTR(date, 1, 7) FROM attendance ORDER BY date DESC")
    rows = c.fetchall()
    conn.close()
    return [r[0] for r in rows]

def delete_month_data(month_prefix):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("DELETE FROM attendance WHERE date LIKE ?", (f"{month_prefix}%",))
    conn.commit()
    conn.close()
    auto_backup_db()


# ================================================================
#  SHARED UI HELPERS
# ================================================================

def banner(page, title, show_back=False):
    c = get_colors()
    controls = []
    if show_back:
        controls.append(
            ft.IconButton(
                icon=ft.Icons.ARROW_BACK, 
                icon_color=c["header_text"],
                on_click=lambda e: page.go("/"),
            )
        )
    controls.append(
        ft.Text(title, size=18, weight=ft.FontWeight.BOLD, color=c["header_text"])
    )
    return ft.Container(
        content=ft.Row(controls=controls),
        bgcolor=c["bg"],
        padding=16,
        width=float("inf"),
    )


# ================================================================
#  SCREEN 1 — HOME
# ================================================================

def home_view(page):
    c = get_colors()

    def dashboard_card(number, title, subtitle, icon, route, is_highlighted=False):
        icon_color = c["green"] if title == "Today's Attendance" else c["accent"]
        
        accent_bar = ft.Container(
            width=4,
            bgcolor=c["accent"] if is_highlighted else ft.Colors.TRANSPARENT,
            border_radius=4
        )

        inner_card = ft.Container(
            content=ft.Row(
                controls=[
                    accent_bar,
                    ft.Container(
                        content=ft.Icon(icon, color=icon_color, size=22),
                        bgcolor=c["hover"],
                        padding=12,
                        border_radius=8,
                    ),
                    ft.Column(
                        controls=[
                            ft.Text(f"{number}. {title}", size=15, color=c["text"], weight=ft.FontWeight.BOLD),
                            ft.Text(subtitle, size=11, color=c["text_muted"]),
                        ],
                        expand=True,
                        spacing=2,
                    ),
                    ft.Icon(ft.Icons.CHEVRON_RIGHT, color=c["text_muted"], size=20), 
                ],
                alignment=ft.MainAxisAlignment.START,
            ),
            bgcolor=c["card"], 
            border_radius=11, 
            padding=12,
        )

        outer_card = ft.Container(
            content=inner_card,
            bgcolor=ft.Colors.TRANSPARENT, 
            padding=1, 
            border_radius=12,
            on_click=lambda e: page.go(route),
        )
        return outer_card

    report = get_attendance_for_date(today())
    total_students = len(get_all_students())
    
    if total_students > 0 and is_attendance_done_today():
        present_count = sum(1 for _, s in report if s == "present")
        absent_count = sum(1 for _, s in report if s == "absent")
        p_pct = int((present_count / total_students) * 100)
        a_pct = int((absent_count / total_students) * 100)
    else:
        present_count, absent_count, p_pct, a_pct = 0, 0, 0, 0

    ratio_bar = ft.Container(
        content=ft.Row(
            controls=[
                ft.Container(bgcolor=c["accent"], height=8, expand=max(p_pct, 1)),
                ft.Container(bgcolor=c["hover"], height=8, expand=max(a_pct, 1)),
            ],
            spacing=0,
        ),
        border_radius=4,
    )

    summary_card = ft.Container(
        content=ft.Column(
            controls=[
                ft.Text("Today's Summary", size=16, weight=ft.FontWeight.BOLD, color=c["text"]),
                ft.Container(height=5),
                ratio_bar,
                ft.Container(height=5),
                ft.Row(
                    controls=[
                        ft.Row([ft.Container(width=10, height=10, border_radius=5, bgcolor=c["accent"]), ft.Text(f"Present: {present_count} ({p_pct}%)", size=13, color=c["text_muted"])]),
                        ft.Row([ft.Container(width=10, height=10, border_radius=5, bgcolor=c["hover"]), ft.Text(f"Absent: {absent_count} ({a_pct}%)", size=13, color=c["text_muted"])]),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                )
            ],
            spacing=5,
        ),
        bgcolor=c["card"],
        border_radius=16,
        padding=20,
    )

    top_header = ft.Row(
        controls=[
            ft.IconButton(icon=ft.Icons.SETTINGS, icon_color=c["text_muted"], on_click=lambda e: page.go("/settings")), 
            ft.Text("Dashboard", size=20, weight=ft.FontWeight.BOLD, color=c["header_text"]),
            ft.Container(width=40) 
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN
    )

    beta_credits_note = ft.Container(
        content=ft.Column(
            controls=[
                ft.Container(height=10),
                ft.Text("App is currently in beta version", size=10, color=c["text_muted"], italic=True, text_align=ft.TextAlign.CENTER),
                ft.Text("Developer - Anubhav Yaduwanshi", size=11, color=c["accent"], weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                ft.Container(height=10),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=2
        ),
        width=float("inf")
    )

    main_content = ft.Column(
        controls=[
            ft.Container(height=25), 
            top_header,
            ft.Container(height=10),
            summary_card,
            ft.Container(height=10), 
            dashboard_card("1", "Today's Attendance", f"Take records for {date.today().strftime('%b %d')}", ft.Icons.CALENDAR_MONTH, "/attendance", is_highlighted=True), 
            dashboard_card("2", "Older Records", "Access past daily attendance data", ft.Icons.HISTORY, "/older_records"),
            dashboard_card("3", "Reports & Analytics", "View Monthly/Yearly & Export to Excel", ft.Icons.INSERT_CHART, "/analytics"),
            dashboard_card("4", "Add/Remove Student", "Manage the student database", ft.Icons.PERSON_ADD_ALT_1, "/add_remove"),
            dashboard_card("5", "Manage Holidays", "Set school festivals and off-days", ft.Icons.EVENT, "/holidays"), 
            beta_credits_note
        ],
        spacing=12,
    )

    return ft.View(route="/", bgcolor=c["bg"], padding=20, controls=[main_content], scroll=ft.ScrollMode.AUTO)


# ================================================================
#  SETTINGS & MANAGE DATA SCREENS
# ================================================================

def settings_view(page):
    c = get_colors()
    
    def toggle_theme(e):
        if app_state["theme"] == "dark":
            app_state["theme"] = "light"
        else:
            app_state["theme"] = "dark"
        page.go("/settings") 
        
    theme_icon = ft.Icons.DARK_MODE if app_state["theme"] == "light" else ft.Icons.LIGHT_MODE
    theme_text = "Switch to Dark Mode" if app_state["theme"] == "light" else "Switch to White Mode"

    content = ft.Column(
        controls=[
            ft.Container(height=25), 
            banner(page, "Settings", show_back=True),
            ft.Container(
                padding=20,
                content=ft.Column(
                    spacing=16,
                    controls=[
                        ft.Container(
                            content=ft.Row([
                                ft.Icon(theme_icon, color=c["accent"]),
                                ft.Text(theme_text, color=c["text"], size=15, expand=True),
                                ft.Icon(ft.Icons.SYNC, color=c["text_muted"]) 
                            ]),
                            bgcolor=c["card"], padding=16, border_radius=10,
                            on_click=toggle_theme
                        ),
                        ft.Container(
                            content=ft.Row([
                                ft.Icon(ft.Icons.STORAGE, color=c["accent"]), 
                                ft.Text("Manage Data (Delete Records)", color=c["text"], size=15, expand=True),
                                ft.Icon(ft.Icons.CHEVRON_RIGHT, color=c["text_muted"]) 
                            ]),
                            bgcolor=c["card"], padding=16, border_radius=10,
                            on_click=lambda e: page.go("/manage_data")
                        )
                    ]
                )
            )
        ]
    )
    return ft.View(route="/settings", bgcolor=c["bg"], padding=0, controls=[content], scroll=ft.ScrollMode.AUTO)

# 🛠️ FIXED: Removed the buggy Flet Popup box entirely. 
# Data now deletes instantly when the trash can is clicked, just like the students!
def manage_data_view(page):
    c = get_colors()
    month_list = ft.Column(spacing=10)
    msg = ft.Text("", size=14, weight=ft.FontWeight.BOLD)
    
    def refresh():
        month_list.controls.clear()
        months = get_all_months()
        if not months:
            month_list.controls.append(ft.Text("No data available to delete yet.", color=c["text_muted"], italic=True))
        else:
            for m in months:
                def make_del_btn(month_val=m):
                    def do_delete(e):
                        try:
                            delete_month_data(month_val)
                            msg.value = f"✅ All records for {month_val} deleted successfully."
                            msg.color = c["green"]
                            refresh()
                        except Exception as err:
                            msg.value = f"❌ Error Deleting: {err}"
                            msg.color = c["red"]
                            page.update()
                    return ft.IconButton(
                        icon=ft.Icons.DELETE_FOREVER, 
                        icon_color=c["red"], 
                        on_click=do_delete
                    )
                month_list.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Text(f"Records for: {m}", color=c["text"], size=15, expand=True),
                            make_del_btn()
                        ]),
                        bgcolor=c["card"], padding=12, border_radius=10
                    )
                )
        page.update()

    refresh()

    content = ft.Column(
        controls=[
            ft.Container(height=25),
            banner(page, "Manage Data", show_back=True),
            ft.Container(
                padding=20,
                content=ft.Column([
                    ft.Text("Click the trash icon to permanently delete a month's records.", color=c["text_muted"], italic=True),
                    msg,
                    ft.Container(height=10),
                    month_list
                ])
            )
        ]
    )
    return ft.View(route="/manage_data", bgcolor=c["bg"], padding=0, controls=[content], scroll=ft.ScrollMode.AUTO)


# ================================================================
#  SCREEN 2 — TODAY'S ATTENDANCE
# ================================================================

def attendance_view(page):
    c = get_colors()
    
    if datetime.today().weekday() == 6:
        content = ft.Column(controls=[
            ft.Container(height=25), banner(page, "Today's Attendance", show_back=True),
            ft.Container(padding=20, content=ft.Column([
                ft.Icon(ft.Icons.WEEKEND, color=c["accent"], size=50), 
                ft.Text("It's Sunday!", size=24, weight=ft.FontWeight.BOLD, color=c["text"]),
                ft.Text("This is an automatic holiday. No attendance is required today. Enjoy your day off!", color=c["text_muted"], text_align=ft.TextAlign.CENTER)
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.CENTER))
        ])
        return ft.View(route="/attendance", bgcolor=c["bg"], padding=0, controls=[content], scroll=ft.ScrollMode.AUTO)

    holiday_reason = get_holiday_reason(today())
    if holiday_reason:
        content = ft.Column(controls=[
            ft.Container(height=25), banner(page, "Today's Attendance", show_back=True),
            ft.Container(padding=20, content=ft.Column([
                ft.Icon(ft.Icons.CELEBRATION, color=c["accent"], size=50), 
                ft.Text("School Holiday!", size=24, weight=ft.FontWeight.BOLD, color=c["text"]),
                ft.Text(f"Today is marked as: {holiday_reason}", size=16, color=c["accent"]),
                ft.Text("No attendance is required today.", color=c["text_muted"])
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.CENTER))
        ])
        return ft.View(route="/attendance", bgcolor=c["bg"], padding=0, controls=[content], scroll=ft.ScrollMode.AUTO)

    students = get_all_students()
    done_already = is_attendance_done_today()

    if done_already:
        report = get_attendance_for_date(today())
        present_count = sum(1 for _, s in report if s == "present")
        absent_count  = sum(1 for _, s in report if s == "absent")

        rows = [
            ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Text(f"✅ Present: {present_count}", size=16, weight=ft.FontWeight.BOLD, color=c["green"]),
                        ft.Text(f"❌ Absent: {absent_count}", size=16, weight=ft.FontWeight.BOLD, color=c["red"]),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_AROUND,
                ),
                bgcolor=c["card"], border_radius=12, padding=16,
            ),
            ft.Divider(color=c["hover"]),
        ]

        for i, (name, status) in enumerate(report):
            icon  = ft.Icons.CHECK_CIRCLE if status == "present" else ft.Icons.CANCEL
            iclr  = c["green"] if status == "present" else c["red"]
            rows.append(
                ft.Container(
                    content=ft.Row(controls=[
                        ft.Text(str(i+1), size=13, color=c["text_muted"], width=30),
                        ft.Icon(icon, color=iclr, size=18),
                        ft.Text(name, size=15, color=c["text"], expand=True),
                        ft.Text(status.capitalize(), color=iclr, weight=ft.FontWeight.BOLD),
                    ]),
                    bgcolor=c["card"], border_radius=10, padding=12,  
                )
            )

        content = ft.Column(
            controls=[
                ft.Container(height=25),
                banner(page, "Today's Attendance", show_back=True),
                ft.Container(padding=20, content=ft.Column(spacing=10, controls=rows)),
            ]
        )
        return ft.View(route="/attendance", bgcolor=c["bg"], padding=0, controls=[content], scroll=ft.ScrollMode.AUTO)

    attendance_data = [{"id": sid, "name": sname, "status": None} for sid, sname in students]
    cards_col = ft.Column(spacing=10)
    msg = ft.Text("", size=14)

    def build_student_cards():
        cards_col.controls.clear()
        for entry in attendance_data:
            is_p = entry["status"] == "present"
            is_a = entry["status"] == "absent"

            def make_present(ent=entry):
                def h(e):
                    ent["status"] = "present"
                    build_student_cards()
                    page.update()
                return h

            def make_absent(ent=entry):
                def h(e):
                    ent["status"] = "absent"
                    build_student_cards()
                    page.update()
                return h

            cards_col.controls.append(
                ft.Container(
                    content=ft.Column(
                        spacing=12,
                        controls=[
                            ft.Text(entry['name'], size=16, color=c["text"], weight=ft.FontWeight.W_500),
                            ft.Row(
                                controls=[
                                    ft.ElevatedButton("Present", bgcolor="#388E3C" if is_p else c["hover"], color=ft.Colors.WHITE if is_p else c["text"], on_click=make_present(), expand=True),
                                    ft.ElevatedButton("Absent", bgcolor="#D32F2F" if is_a else c["hover"], color=ft.Colors.WHITE if is_a else c["text"], on_click=make_absent(), expand=True),
                                ],
                            ),
                        ],
                    ),
                    bgcolor=c["card"], border_radius=12, padding=16,
                )
            )

    build_student_cards()

    def submit(e):
        unmarked = [d["name"] for d in attendance_data if d["status"] is None]
        if unmarked:
            msg.value = f"⚠ Mark all students first! ({len(unmarked)} remaining)"
            msg.color = c["red"]
            page.update()
            return

        save_attendance([(d["id"], d["status"]) for d in attendance_data])
        page.go("/")

    if not students:
        main_body = ft.Text("No students added yet!\nGo to 'Add / Remove Student' first.", color=c["text_muted"], italic=True, text_align=ft.TextAlign.CENTER)
        submit_btn = ft.Container()
    else:
        main_body = cards_col
        submit_btn = ft.ElevatedButton("Submit Attendance", bgcolor=c["accent"], color="#000000", on_click=submit, width=float("inf"))

    content = ft.Column(
        controls=[
            ft.Container(height=25), 
            banner(page, "Today's Attendance", show_back=True),
            ft.Container(padding=20, content=ft.Column(spacing=16, controls=[main_body, msg, submit_btn])),
        ]
    )
    return ft.View(route="/attendance", bgcolor=c["bg"], padding=0, controls=[content], scroll=ft.ScrollMode.AUTO)


# ================================================================
#  SCREEN 3 — OLDER REPORTS 
# ================================================================

def older_reports_view(page):
    c = get_colors()
    dates = get_all_dates()

    if not dates:
        body = ft.Container(padding=20, content=ft.Text("No records yet.", color=c["text_muted"]))
    else:
        date_rows = []
        for ds in dates:
            d_obj = datetime.strptime(ds, "%Y-%m-%d")
            display = d_obj.strftime("%d %b %Y")
            
            past_report = get_attendance_for_date(ds)
            p_count = sum(1 for _, s in past_report if s == "present")
            a_count = sum(1 for _, s in past_report if s == "absent")

            def open_report(date_str=ds, disp=display):
                def handler(e):
                    app_state["selected_date"] = date_str
                    app_state["selected_display"] = disp
                    page.go("/report_detail")
                return handler

            date_rows.append(
                ft.Container(
                    content=ft.Row(controls=[
                        ft.Icon(ft.Icons.CALENDAR_TODAY, color=c["accent"], size=20),
                        ft.Column([
                            ft.Text(display, size=15, color=c["text"], weight=ft.FontWeight.BOLD),
                            ft.Text(f"✅ {p_count} Present  |  ❌ {a_count} Absent", size=11, color=c["text_muted"]),
                        ], expand=True, spacing=2),
                        ft.Icon(ft.Icons.CHEVRON_RIGHT, size=20, color=c["text_muted"]),
                    ]),
                    bgcolor=c["card"], border_radius=10, padding=16, on_click=open_report(),
                )
            )

        body = ft.Container(padding=20, content=ft.Column(spacing=12, controls=date_rows))

    content = ft.Column(controls=[
        ft.Container(height=25), 
        banner(page, "Older Records", show_back=True), 
        body
    ])
    return ft.View(route="/older_records", bgcolor=c["bg"], padding=0, controls=[content], scroll=ft.ScrollMode.AUTO)


def report_detail_view(page):
    c = get_colors()
    date_str = app_state.get("selected_date")
    display_date = app_state.get("selected_display")
    
    report = get_attendance_for_date(date_str) if date_str else []
    present_count = sum(1 for _, s in report if s == "present")
    absent_count  = sum(1 for _, s in report if s == "absent")

    rows = [
        ft.Container(
            content=ft.Row(
                controls=[
                    ft.Text(f"✅ Present: {present_count}", size=16, weight=ft.FontWeight.BOLD, color=c["green"]),
                    ft.Text(f"❌ Absent: {absent_count}", size=16, weight=ft.FontWeight.BOLD, color=c["red"]),
                ],
                alignment=ft.MainAxisAlignment.SPACE_AROUND,
            ),
            bgcolor=c["card"], border_radius=12, padding=16,
        ),
        ft.Divider(color=c["hover"]),
    ]
    
    for i, (name, status) in enumerate(report):
        iclr = c["green"] if status == "present" else c["red"]
        rows.append(
            ft.Container(
                content=ft.Row(controls=[
                    ft.Text(str(i+1), size=13, color=c["text_muted"], width=30),
                    ft.Text(name, size=15, color=c["text"], expand=True),
                    ft.Text(status.capitalize(), color=iclr, weight=ft.FontWeight.BOLD),
                ]),
                bgcolor=c["card"], border_radius=10, padding=12,  
            )
        )

    content = ft.Column(
        controls=[
            ft.Container(height=25), 
            banner(page, f"📅 {display_date or 'Record'}", show_back=True),
            ft.Container(padding=20, content=ft.Column(spacing=10, controls=rows)),
        ]
    )
    return ft.View(route="/report_detail", bgcolor=c["bg"], padding=0, controls=[content], scroll=ft.ScrollMode.AUTO)


# ================================================================
#  SCREEN 4 — ANALYTICS & EXPORT
# ================================================================

def analytics_view(page):
    c = get_colors()
    current_period = ["month"] 
    stats_column = ft.Column(spacing=10)
    info_text = ft.Text("", size=13, color=c["text_muted"], italic=True)
    export_msg = ft.Text("", size=13, color=c["green"], weight=ft.FontWeight.BOLD)

    def trigger_export(e):
        try:
            filepath = export_all_to_csv()
            export_msg.value = f"✅ Success! File saved in: App Folder/{EXPORT_DIR}"
        except Exception as err:
            export_msg.value = f"❌ Export failed: {err}"
            export_msg.color = c["red"]
        page.update()

    def refresh_stats():
        period = current_period[0]
        stats, total_days = get_analytics_stats(period)
        stats_column.controls.clear()
        
        info_text.value = f"Total Working Days Recorded: {total_days}\n(Only days with submitted attendance are counted)"
        
        if total_days == 0:
            stats_column.controls.append(ft.Text(f"No attendance data recorded yet for this {period}.", color=c["text_muted"]))
        else:
            for name, pct, p_days, t_days in stats:
                if pct >= 75:
                    pct_color = c["green"]
                elif pct <= 50:
                    pct_color = c["red"]
                else:
                    pct_color = c["accent"]
                    
                mini_bar = ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Container(bgcolor=pct_color, height=5, expand=max(pct, 1)),
                            ft.Container(bgcolor=c["hover"], height=5, expand=max(100 - pct, 1)),
                        ],
                        spacing=0,
                    ),
                    border_radius=2,
                    clip_behavior=ft.ClipBehavior.HARD_EDGE,
                )

                stats_column.controls.append(
                    ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Row(
                                    controls=[
                                        ft.Text(name, size=15, color=c["text"], weight=ft.FontWeight.BOLD),
                                        ft.Text(f"{pct}%", size=15, color=pct_color, weight=ft.FontWeight.BOLD),
                                    ],
                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                                ),
                                ft.Text(f"Present {p_days} out of {t_days} days", size=11, color=c["text_muted"]),
                                ft.Container(height=2),
                                mini_bar
                            ],
                            spacing=2,
                        ),
                        bgcolor=c["card"],
                        border_radius=10,
                        padding=16,
                    )
                )
        page.update()

    def set_period(period):
        def handler(e):
            current_period[0] = period
            btn_month.bgcolor = c["accent"] if period == "month" else c["hover"]
            btn_month.color = "#000000" if period == "month" else c["text"]
            
            btn_year.bgcolor = c["accent"] if period == "year" else c["hover"]
            btn_year.color = "#000000" if period == "year" else c["text"]
            
            refresh_stats()
        return handler

    btn_month = ft.ElevatedButton("This Month", on_click=set_period("month"), bgcolor=c["accent"], color="#000000", expand=True)
    btn_year = ft.ElevatedButton("This Year", on_click=set_period("year"), bgcolor=c["hover"], color=c["text"], expand=True)
    
    export_btn = ft.ElevatedButton("Export All Data to Excel (CSV)", icon=ft.Icons.DOWNLOAD, bgcolor="#2E7D32", color=ft.Colors.WHITE, width=float("inf"), on_click=trigger_export) 

    toggle_row = ft.Row(controls=[btn_month, btn_year], spacing=10)
    refresh_stats()

    content = ft.Column(
        controls=[
            ft.Container(height=25), 
            banner(page, "Reports & Analytics", show_back=True),
            ft.Container(
                padding=20,
                content=ft.Column(
                    spacing=16,
                    controls=[
                        toggle_row,
                        info_text,
                        ft.Divider(color=c["hover"]),
                        stats_column,
                        ft.Divider(color=c["hover"]),
                        export_btn, 
                        export_msg
                    ],
                ),
            ),
        ]
    )
    return ft.View(route="/analytics", bgcolor=c["bg"], padding=0, controls=[content], scroll=ft.ScrollMode.AUTO)


# ================================================================
#  SCREEN 5 — ADD / REMOVE STUDENT
# ================================================================

def add_remove_view(page):
    c = get_colors()
    student_list = ft.Column(spacing=8)
    msg = ft.Text("", size=13)
    
    name_input = ft.TextField(
        hint_text="Enter student name...",
        expand=True, 
        border_radius=10, 
        bgcolor=c["card"],
        color=c["text"]
    )

    def refresh():
        student_list.controls.clear()
        for sid, sname in get_all_students():
            def make_remove(s=sid):
                def h(e):
                    remove_student(s)
                    msg.value = "Student removed (attendance history saved)."
                    msg.color = "#FFA726" 
                    refresh()
                    page.update()
                return h
            student_list.controls.append(
                ft.Container(
                    content=ft.Row(controls=[
                        ft.Icon(ft.Icons.PERSON, color=c["text_muted"], size=20),
                        ft.Text(sname, color=c["text"], expand=True, size=15),
                        ft.IconButton(icon=ft.Icons.DELETE_OUTLINE, icon_color=c["red"], on_click=make_remove()), 
                    ]),
                    bgcolor=c["card"], border_radius=10, padding=12,  
                )
            )

    refresh()

    def add(e):
        name = name_input.value.strip()
        if not name:
            msg.value = "Please enter a valid name."
            msg.color = c["red"]
        else:
            add_student(name)
            name_input.value = ""
            msg.value = f"Added '{name}' successfully!"
            msg.color = c["green"]
            refresh()
        page.update()

    content = ft.Column(
        controls=[
            ft.Container(height=25), 
            banner(page, "Manage Students", show_back=True),
            ft.Container(
                padding=20,
                content=ft.Column(
                    spacing=16,
                    controls=[
                        ft.Row(controls=[name_input, ft.ElevatedButton("Add", bgcolor=c["accent"], color="#000000", on_click=add)]),
                        msg,
                        ft.Divider(color=c["hover"]),
                        ft.Text("Existing Students:", size=15, weight=ft.FontWeight.BOLD, color=c["text_muted"]),
                        student_list
                    ],
                ),
            ),
        ]
    )
    return ft.View(route="/add_remove", bgcolor=c["bg"], padding=0, controls=[content], scroll=ft.ScrollMode.AUTO)


# ================================================================
#  SCREEN 6 — MANAGE HOLIDAYS 
# ================================================================

def holidays_view(page):
    c = get_colors()
    holiday_list = ft.Column(spacing=8)
    msg = ft.Text("", size=13)
    
    date_input = ft.TextField(value=today(), hint_text="YYYY-MM-DD", expand=1, border_radius=10, bgcolor=c["card"], color=c["text"])
    reason_input = ft.TextField(hint_text="e.g. Holi Festival", expand=2, border_radius=10, bgcolor=c["card"], color=c["text"])

    def refresh():
        holiday_list.controls.clear()
        for h_date, reason in get_all_holidays():
            def make_remove(d=h_date):
                def h(e):
                    remove_holiday(d)
                    msg.value = "Holiday removed."
                    msg.color = "#FFA726" 
                    refresh()
                    page.update()
                return h
            holiday_list.controls.append(
                ft.Container(
                    content=ft.Row(controls=[
                        ft.Icon(ft.Icons.EVENT, color=c["accent"], size=20), 
                        ft.Column([
                            ft.Text(reason, color=c["text"], size=15, weight=ft.FontWeight.BOLD),
                            ft.Text(h_date, color=c["text_muted"], size=12),
                        ], expand=True, spacing=2),
                        ft.IconButton(icon=ft.Icons.DELETE_OUTLINE, icon_color=c["red"], on_click=make_remove()), 
                    ]),
                    bgcolor=c["card"], border_radius=10, padding=12,  
                )
            )

    refresh()

    def add(e):
        d_val = date_input.value.strip()
        r_val = reason_input.value.strip()
        
        if not d_val or not r_val:
            msg.value = "Please enter both a date and a reason."
            msg.color = c["red"]
        else:
            add_holiday(d_val, r_val)
            reason_input.value = ""
            msg.value = f"Added holiday for {d_val}!"
            msg.color = c["green"]
            refresh()
        page.update()

    content = ft.Column(
        controls=[
            ft.Container(height=25), 
            banner(page, "Manage Holidays", show_back=True),
            ft.Container(
                padding=20,
                content=ft.Column(
                    spacing=16,
                    controls=[
                        ft.Text("Declare official school holidays. Sundays are automatic.", color=c["text_muted"], italic=True),
                        ft.Row(controls=[date_input, reason_input]),
                        ft.ElevatedButton("Set Holiday", bgcolor=c["accent"], color="#000000", width=float("inf"), on_click=add),
                        msg,
                        ft.Divider(color=c["hover"]),
                        ft.Text("Upcoming & Past Holidays:", size=15, weight=ft.FontWeight.BOLD, color=c["text_muted"]),
                        holiday_list
                    ],
                ),
            ),
        ]
    )
    return ft.View(route="/holidays", bgcolor=c["bg"], padding=0, controls=[content], scroll=ft.ScrollMode.AUTO)


# ================================================================
#  ROUTER & MAIN APP LOGIC
# ================================================================

def get_splash_view():
    c = get_colors()
    logo = ft.Image(src="logo.png", width=220, height=90, fit="contain")  
    spinner = ft.ProgressRing(color=c["accent"])
    splash_text = ft.Text("Loading the app...", size=13, color=c["text_muted"])

    splash_content = ft.Container(
        content=ft.Column(
            controls=[
                logo, 
                ft.Container(height=10), 
                spinner, 
                ft.Container(height=5), 
                splash_text
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        expand=True
    )

    return ft.View(
        route="/splash",
        bgcolor=c["bg"],
        padding=0,
        controls=[splash_content]
    )


async def main(page: ft.Page):
    setup_database()
    page.title = "Digital Attendance Pro"
    
    page.window.width = 400
    page.window.height = 750
    page.window.resizable = False
    page.window.maximizable = False

    def route_change(e):
        try:
            c = get_colors()
            page.bgcolor = c["bg"]

            new_view = None
            if page.route == "/splash":
                new_view = get_splash_view()
            elif page.route == "/":
                new_view = home_view(page)
            elif page.route == "/settings":
                new_view = settings_view(page)
            elif page.route == "/manage_data":
                new_view = manage_data_view(page)
            elif page.route == "/attendance":
                new_view = attendance_view(page)
            elif page.route == "/older_records":
                new_view = older_reports_view(page)
            elif page.route == "/report_detail":
                new_view = report_detail_view(page)
            elif page.route == "/analytics":
                new_view = analytics_view(page)
            elif page.route == "/add_remove":
                new_view = add_remove_view(page)
            elif page.route == "/holidays": 
                new_view = holidays_view(page)
            else:
                new_view = home_view(page)

            # ✨ THE SAFE SWAP 
            if new_view:
                page.views.append(new_view)
            
            old_views = page.views[:-1]
            for old_view in old_views:
                page.views.remove(old_view)
            
            page.update()
            
        except Exception as error:
            error_view = ft.View(
                route="/error", 
                controls=[ft.Text(f"Crash Prevented! Error: {error}", color="red", size=20)]
            )
            page.views.append(error_view)
            
            old_views = page.views[:-1]
            for old_view in old_views:
                page.views.remove(old_view)
                
            page.update()

    def view_pop(view):
        page.views.pop()
        if len(page.views) > 0:
            top_view = page.views[-1]
            page.go(top_view.route)
        else:
            page.go("/")

    page.on_route_change = route_change
    page.on_view_pop = view_pop

    # Boot Sequence
    page.go("/splash")
    await asyncio.sleep(8.0) 
    page.go("/")

ft.app(target=main, assets_dir="assets")