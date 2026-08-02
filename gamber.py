import flet as ft
import sqlite3
import os
import shutil
import asyncio
import csv
from datetime import date, datetime

# ================================================================
#  GLOBAL STATE & CONFIG
# ================================================================
app_state = {
    "selected_date": None,
    "selected_display": None
}

DB = "attendance_app.db"
BACKUP_DIR = "Database_Backups"
EXPORT_DIR = "Exports"

# Theme Colors
APP_BG = "#0B0C10"
CARD_BG = "#1F2833"
HOVER_BG = "#2C3A47"
ACCENT_BLUE = "#45A29E"
ACCENT_GREEN = "#66FCF1"
TEXT_GREY = "#C5C6C7"
RED_COLOR = "#FF5722"

# ================================================================
#  DATABASE & LOGIC (Upgraded)
# ================================================================

def setup_database():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS students (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL)")
    c.execute("CREATE TABLE IF NOT EXISTS attendance (id INTEGER PRIMARY KEY AUTOINCREMENT, student_id INTEGER NOT NULL, date TEXT NOT NULL, status TEXT NOT NULL)")
    conn.commit()
    conn.close()

def auto_backup_db():
    os.makedirs(BACKUP_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    shutil.copy2(DB, os.path.join(BACKUP_DIR, f"backup_{timestamp}.db"))

def export_to_csv(date_str, data):
    os.makedirs(EXPORT_DIR, exist_ok=True)
    filepath = os.path.join(EXPORT_DIR, f"Attendance_{date_str}.csv")
    with open(filepath, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Student Name", "Status", "Date"])
        for name, status in data:
            writer.writerow([name, status.capitalize(), date_str])
    return filepath

def today():
    return date.today().strftime("%Y-%m-%d")

def get_all_students(search_query=""):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    if search_query:
        c.execute("SELECT id, name FROM students WHERE name LIKE ? ORDER BY name", (f"%{search_query}%",))
    else:
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
        c.execute("INSERT INTO attendance (student_id, date, status) VALUES (?, ?, ?)", (sid, today(), status))
    conn.commit()
    conn.close()
    auto_backup_db()

def get_attendance_for_date(date_str):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
        SELECT COALESCE(students.name, 'Deleted Student'), attendance.status
        FROM attendance LEFT JOIN students ON attendance.student_id = students.id
        WHERE attendance.date = ? ORDER BY students.name
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

def get_analytics_stats():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    prefix = today()[:7] 
    c.execute("SELECT COUNT(DISTINCT date) FROM attendance WHERE date LIKE ?", (f"{prefix}%",))
    total_days = c.fetchone()[0]
    stats = []
    if total_days > 0:
        c.execute("SELECT id, name FROM students ORDER BY name")
        for sid, name in c.fetchall():
            c.execute("SELECT COUNT(*) FROM attendance WHERE student_id = ? AND date LIKE ? AND status = 'present'", (sid, f"{prefix}%"))
            present_days = c.fetchone()[0]
            stats.append((name, int((present_days / total_days) * 100)))
    conn.close()
    return stats, total_days

# ================================================================
#  UI HELPERS
# ================================================================

def show_toast(page, message, color=ACCENT_GREEN):
    page.snack_bar = ft.SnackBar(ft.Text(message, color=APP_BG, weight="bold"), bgcolor=color, duration=2500)
    page.snack_bar.open = True
    page.update()

def header(page, title, show_back=False):
    return ft.Container(
        content=ft.Row([
            *( [ft.IconButton(ft.Icons.ARROW_BACK_IOS_NEW, icon_color=ACCENT_GREEN, on_click=lambda e: page.go("/"))] if show_back else []),
            ft.Text(title, size=24, weight="bold", color=ft.Colors.WHITE)
        ]),
        padding=ft.padding.only(top=40, bottom=20, left=10, right=10)
    )

# ================================================================
#  SCREENS
# ================================================================

def home_view(page):
    def dash_card(title, subtitle, icon, route):
        return ft.Container(
            content=ft.Row([
                ft.Container(content=ft.Icon(icon, color=ACCENT_GREEN, size=28), padding=15, bgcolor=APP_BG, border_radius=12),
                ft.Column([
                    ft.Text(title, size=16, weight="bold", color=ft.Colors.WHITE),
                    ft.Text(subtitle, size=12, color=TEXT_GREY),
                ], expand=True, spacing=2),
                ft.Icon(ft.Icons.ARROW_FORWARD_IOS, color=ACCENT_BLUE, size=16),
            ]),
            bgcolor=CARD_BG, border_radius=16, padding=15, on_click=lambda e: page.go(route),
            shadow=ft.BoxShadow(spread_radius=1, blur_radius=10, color=ft.colors.with_opacity(0.1, ACCENT_GREEN))
        )

    report = get_attendance_for_date(today())
    present_count = sum(1 for _, s in report if s == "present")
    absent_count = sum(1 for _, s in report if s == "absent")
    
    chart = ft.PieChart(
        sections=[
            ft.PieChartSection(present_count, color=ACCENT_GREEN, radius=40, title=f"{present_count} P"),
            ft.PieChartSection(absent_count, color=RED_COLOR, radius=40, title=f"{absent_count} A"),
        ] if present_count or absent_count else [ft.PieChartSection(1, color=HOVER_BG, radius=40, title="No Data")],
        sections_space=2, center_space_radius=30, expand=True
    )

    return ft.View(
        "/", bgcolor=APP_BG, padding=20, scroll="auto",
        controls=[
            header(page, "Dashboard"),
            ft.Container(
                content=ft.Row([
                    ft.Column([ft.Text("Today's Overview", size=18, weight="bold", color=ft.Colors.WHITE), chart], expand=True)
                ]), bgcolor=CARD_BG, border_radius=20, padding=20, height=180
            ),
            ft.Container(height=15),
            dash_card("Take Attendance", "Mark today's records", ft.Icons.HOW_TO_REG, "/attendance"),
            ft.Container(height=10),
            dash_card("Past Records", "View and export history", ft.Icons.HISTORY_EDU, "/older_records"),
            ft.Container(height=10),
            dash_card("Analytics", "Monthly performance stats", ft.Icons.PIE_CHART, "/analytics"),
            ft.Container(height=10),
            dash_card("Manage Roster", "Add or remove students", ft.Icons.PEOPLE_ALT, "/add_remove"),
        ]
    )

def attendance_view(page):
    students = get_all_students()
    done_already = is_attendance_done_today()

    if done_already:
        return ft.View(
            "/attendance", bgcolor=APP_BG, padding=20, scroll="auto",
            controls=[
                header(page, "Today's Attendance", True),
                ft.Container(content=ft.Text("✅ Attendance already submitted for today!", color=ACCENT_GREEN, size=16), padding=20, bgcolor=CARD_BG, border_radius=10)
            ]
        )

    attendance_data = [{"id": sid, "name": sname, "status": None} for sid, sname in students]
    cards_col = ft.Column(spacing=12)

    def build_cards():
        cards_col.controls.clear()
        for entry in attendance_data:
            def set_status(status, ent=entry):
                def h(e):
                    ent["status"] = status
                    build_cards()
                    page.update()
                return h

            p_color = ACCENT_GREEN if entry["status"] == "present" else HOVER_BG
            a_color = RED_COLOR if entry["status"] == "absent" else HOVER_BG

            cards_col.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Text(entry['name'], size=16, color=ft.Colors.WHITE, expand=True, weight="w600"),
                        ft.ElevatedButton("P", bgcolor=p_color, color=APP_BG, on_click=set_status("present"), width=60),
                        ft.ElevatedButton("A", bgcolor=a_color, color=ft.Colors.WHITE, on_click=set_status("absent"), width=60),
                    ]), bgcolor=CARD_BG, border_radius=12, padding=12
                )
            )

    build_cards()

    def submit(e):
        if any(d["status"] is None for d in attendance_data):
            show_toast(page, "Mark ALL students before submitting!", RED_COLOR)
            return
        save_attendance([(d["id"], d["status"]) for d in attendance_data])
        show_toast(page, "Attendance Saved Successfully!")
        page.go("/")

    body = cards_col if students else ft.Text("No students in database.", color=TEXT_GREY)
    btn = ft.ElevatedButton("Submit Records", bgcolor=ACCENT_BLUE, color=APP_BG, height=50, on_click=submit, expand=True) if students else ft.Container()

    return ft.View(
        "/attendance", bgcolor=APP_BG, padding=20, scroll="auto",
        controls=[header(page, "Mark Attendance", True), body, ft.Container(height=20), ft.Row([btn])]
    )

def older_reports_view(page):
    dates = get_all_dates()
    date_rows = ft.Column(spacing=12)
    
    for ds in dates:
        def open_report(date_str=ds):
            def handler(e):
                app_state["selected_date"] = date_str
                page.go("/report_detail")
            return handler
        
        date_rows.controls.append(
            ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.CALENDAR_MONTH, color=ACCENT_BLUE),
                    ft.Text(datetime.strptime(ds, "%Y-%m-%d").strftime("%B %d, %Y"), size=16, color=ft.Colors.WHITE, expand=True),
                    ft.Icon(ft.Icons.ARROW_FORWARD_IOS, size=14, color=TEXT_GREY)
                ]), bgcolor=CARD_BG, border_radius=12, padding=15, on_click=open_report()
            )
        )

    return ft.View(
        "/older_records", bgcolor=APP_BG, padding=20, scroll="auto",
        controls=[header(page, "Past Records", True), date_rows if dates else ft.Text("No records found.", color=TEXT_GREY)]
    )

def report_detail_view(page):
    date_str = app_state.get("selected_date")
    report = get_attendance_for_date(date_str) if date_str else []
    
    def handle_export(e):
        path = export_to_csv(date_str, report)
        show_toast(page, f"Exported to {path}!")

    rows = ft.Column(spacing=10)
    for name, status in report:
        color = ACCENT_GREEN if status == "present" else RED_COLOR
        icon = ft.Icons.CHECK_CIRCLE if status == "present" else ft.Icons.CANCEL
        rows.controls.append(
            ft.Container(content=ft.Row([
                ft.Icon(icon, color=color),
                ft.Text(name, size=16, color=ft.Colors.WHITE, expand=True),
                ft.Text(status.upper(), color=color, weight="bold")
            ]), bgcolor=CARD_BG, padding=12, border_radius=8)
        )

    return ft.View(
        "/report_detail", bgcolor=APP_BG, padding=20, scroll="auto",
        controls=[
            header(page, f"Record: {date_str}", True), 
            ft.ElevatedButton("Export to CSV", icon=ft.Icons.DOWNLOAD, bgcolor=ACCENT_BLUE, color=APP_BG, on_click=handle_export),
            ft.Container(height=10), rows
        ]
    )

def analytics_view(page):
    stats, total = get_analytics_stats()
    chart = ft.BarChart(
        bar_groups=[
            ft.BarChartGroup(x=i, bar_rods=[ft.BarChartRod(from_y=0, to_y=pct, color=ACCENT_GREEN if pct >= 75 else RED_COLOR, width=15)])
            for i, (_, pct) in enumerate(stats)
        ],
        bottom_axis=ft.ChartAxis(labels=[ft.ChartAxisLabel(value=i, label=ft.Text(name[:3], size=10, color=TEXT_GREY)) for i, (name, _) in enumerate(stats)]),
        expand=True, tooltip_bgcolor=CARD_BG
    )

    return ft.View(
        "/analytics", bgcolor=APP_BG, padding=20, scroll="auto",
        controls=[
            header(page, "Monthly Analytics", True),
            ft.Text(f"Based on {total} recorded days this month", color=TEXT_GREY, italic=True),
            ft.Container(content=chart, height=300, bgcolor=CARD_BG, padding=20, border_radius=16) if stats else ft.Text("Not enough data yet.", color=TEXT_GREY)
        ]
    )

def add_remove_view(page):
    student_list = ft.Column(spacing=10)
    search_bar = ft.TextField(hint_text="Search or Add new...", expand=True, bgcolor=CARD_BG, border_radius=10, border_color=ACCENT_BLUE)

    def refresh(e=None):
        student_list.controls.clear()
        for sid, sname in get_all_students(search_bar.value):
            def make_remove(s=sid):
                def h(e):
                    remove_student(s)
                    show_toast(page, "Student removed", RED_COLOR)
                    refresh()
                return h
            student_list.controls.append(
                ft.Container(content=ft.Row([
                    ft.Icon(ft.Icons.PERSON, color=ACCENT_BLUE),
                    ft.Text(sname, color=ft.Colors.WHITE, expand=True, size=16),
                    ft.IconButton(ft.Icons.DELETE, icon_color=RED_COLOR, on_click=make_remove)
                ]), bgcolor=CARD_BG, border_radius=10, padding=5)
            )
        page.update()

    def add(e):
        name = search_bar.value.strip()
        if name:
            add_student(name)
            search_bar.value = ""
            show_toast(page, f"Added {name}!")
            refresh()
        else:
            show_toast(page, "Enter a valid name!", RED_COLOR)

    search_bar.on_change = refresh
    refresh()

    return ft.View(
        "/add_remove", bgcolor=APP_BG, padding=20, scroll="auto",
        controls=[
            header(page, "Manage Roster", True),
            ft.Row([search_bar, ft.FloatingActionButton(icon=ft.Icons.ADD, bgcolor=ACCENT_GREEN, on_click=add)]),
            ft.Container(height=20),
            student_list
        ]
    )

# ================================================================
#  MAIN APP & ROUTER
# ================================================================

async def main(page: ft.Page):
    setup_database()
    page.title = "Attendance Pro Max"
    page.window.width, page.window.height = 400, 750
    page.window.resizable = False
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = APP_BG

    splash = ft.View(
        "/splash", bgcolor=APP_BG,
        controls=[
            ft.Container(
                content=ft.Column([
                    ft.Icon(ft.Icons.FINGERPRINT, size=80, color=ACCENT_GREEN),
                    ft.Text("ATTENDANCE PRO", size=24, weight="bold", color=ft.Colors.WHITE, tracking=2),
                    ft.ProgressBar(width=150, color=ACCENT_BLUE, bgcolor=CARD_BG)
                ], alignment="center", horizontal_alignment="center"), expand=True
            )
        ]
    )

    def route_change(route):
        page.views.clear()
        views = {
            "/splash": splash, "/": home_view(page), "/attendance": attendance_view(page),
            "/older_records": older_reports_view(page), "/report_detail": report_detail_view(page),
            "/analytics": analytics_view(page), "/add_remove": add_remove_view(page)
        }
        page.views.append(views.get(page.route, home_view(page)))
        page.update()

    def view_pop(view):
        page.views.pop()
        page.go(page.views[-1].route if page.views else "/")

    page.on_route_change = route_change
    page.on_view_pop = view_pop
    page.go("/splash")
    
    await asyncio.sleep(1.5) # Shortened splash screen for snappier feel
    page.go("/")

ft.app(target=main)