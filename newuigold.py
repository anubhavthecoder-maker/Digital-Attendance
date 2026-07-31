import flet as ft
import sqlite3
from datetime import date, datetime
import asyncio

# ================================================================
#  THE DATABASE SETUP
# ================================================================

DB = "attendance_app.db"

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
    conn.commit()
    conn.close()

def today():
    return date.today().strftime("%Y-%m-%d")

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
    c.execute("DELETE FROM attendance WHERE student_id = ?", (sid,))
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

def get_attendance_for_date(date_str):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
        SELECT students.name, attendance.status
        FROM attendance
        JOIN students ON attendance.student_id = students.id
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


# ================================================================
#  SHARED UI HELPERS (NEW SLEEK THEME)
# ================================================================

APP_BG = "#0F1115"
CARD_BG = "#1A1D24"
ACCENT_GOLD = "#D4AF37"
TEXT_GREY = "#8A8D93"

def banner(page, title, show_back=False):
    controls = []
    if show_back:
        controls.append(
            ft.IconButton(
                icon=ft.Icons.ARROW_BACK,
                icon_color=ft.Colors.WHITE,
                on_click=lambda e: (page.views.pop(), page.update()),
            )
        )
    controls.append(
        ft.Text(title, size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)
    )
    return ft.Container(
        content=ft.Row(controls=controls),
        bgcolor=APP_BG,
        padding=16,  
        width=float("inf"),
    )

# ================================================================
#  SCREEN 1 — HOME
# ================================================================

def home_view(page):

    def go(route):
        def handler(e):
            if route == "/attendance":
                page.views.append(attendance_view(page))
            elif route == "/older_records":
                page.views.append(older_reports_view(page))
            elif route == "/add_remove":
                page.views.append(add_remove_view(page))
            elif route == "/analytics":
                pass 
            page.update()
        return handler

    def dashboard_card(number, title, subtitle, icon, route, is_highlighted=False):
        border_color = ACCENT_GOLD if is_highlighted else "transparent"
        icon_color = ft.Colors.GREEN_400 if title == "Today's Attendance" else ACCENT_GOLD
        
        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Container(
                        content=ft.Icon(icon, color=icon_color, size=22),
                        bgcolor="#262932",
                        padding=12,
                        border_radius=8,
                    ),
                    ft.Column(
                        controls=[
                            ft.Text(f"{number}. {title}", size=15, color=ft.Colors.WHITE, weight=ft.FontWeight.W_600),
                            ft.Text(subtitle, size=11, color=TEXT_GREY),
                        ],
                        expand=True,
                        spacing=2,
                    ),
                    ft.Icon(ft.Icons.CHEVRON_RIGHT, color=TEXT_GREY, size=20),
                ],
                alignment=ft.MainAxisAlignment.START,
            ),
            bgcolor=CARD_BG, 
            border_radius=12,
            border=ft.border.all(1, border_color),
            padding=16,
            on_click=go(route),
        )

    # Calculate Data for Today's Summary
    report = get_attendance_for_date(today())
    total_students = len(get_all_students())
    
    if total_students > 0 and is_attendance_done_today():
        present_count = sum(1 for _, s in report if s == "present")
        absent_count = sum(1 for _, s in report if s == "absent")
        p_pct = round((present_count / total_students) * 100, 1)
        a_pct = round((absent_count / total_students) * 100, 1)
    else:
        present_count, absent_count, p_pct, a_pct = 0, 0, 0, 0

    # Summary Card Widget - using the native ft.PieChart
    summary_card = ft.Container(
        content=ft.Row(
            controls=[
                ft.Column(
                    controls=[
                        ft.Text("Today's Summary", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                        ft.Row([ft.Icon(ft.Icons.CIRCLE, size=10, color=ft.Colors.GREEN_400), ft.Text(f"Present: {present_count} ({p_pct}%)", size=13, color=TEXT_GREY)]),
                        ft.Row([ft.Icon(ft.Icons.CIRCLE, size=10, color=ft.Colors.RED_400), ft.Text(f"Absent: {absent_count} ({a_pct}%)", size=13, color=TEXT_GREY)]),
                    ],
                    expand=True,
                    spacing=5,
                ),
                ft.Container(
                    width=70, height=70,
                    content=ft.PieChart(
                        sections=[
                            ft.PieChartSection(value=max(p_pct, 1), color=ACCENT_GOLD, radius=10),
                            ft.PieChartSection(value=max(a_pct, 1), color="#31343F", radius=10),
                        ] if (p_pct > 0 or a_pct > 0) else [ft.PieChartSection(value=100, color="#31343F", radius=10)],
                        sections_space=0,
                        center_space_radius=25,
                    )
                )
            ]
        ),
        bgcolor=CARD_BG,
        border_radius=16,
        padding=20,
    )

    main_content = ft.Column(
        controls=[
            ft.Container(height=30), 
            summary_card,
            ft.Container(height=10), 
            dashboard_card("1", "Today's Attendance", f"View and take class records for {date.today().strftime('%b.%d')}", ft.Icons.CALENDAR_MONTH, "/attendance", is_highlighted=True),
            dashboard_card("2", "Older Records", "Access past daily and monthly attendance data", ft.Icons.HISTORY, "/older_records"),
            dashboard_card("3", "Add/Remove Student", "Manage the student database -\nEnroll new students or modify profiles", ft.Icons.PERSON_ADD_ALT_1, "/add_remove"),
            dashboard_card("4", "Reports & Analytics", "Generate detailed attendance reports, view insights", ft.Icons.INSERT_CHART_OUTLINED, "/analytics"),
        ],
        spacing=12,
    )

    return ft.View(
        route="/",
        bgcolor=APP_BG,
        padding=20,
        controls=[main_content],
    )


# ================================================================
#  SCREEN 2 — TODAY'S ATTENDANCE
# ================================================================

def attendance_view(page):
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
                        ft.Text(f"✅  Present: {present_count}", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_400),
                        ft.Text(f"❌  Absent: {absent_count}", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.RED_400),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_AROUND,
                ),
                bgcolor=CARD_BG, border_radius=12, padding=16,
            ),
            ft.Divider(color="#262932"),
        ]

        for i, (name, status) in enumerate(report):
            bg    = ft.Colors.with_opacity(0.1, ft.Colors.GREEN) if status == "present" else ft.Colors.with_opacity(0.1, ft.Colors.RED)
            icon  = ft.Icons.CHECK_CIRCLE if status == "present" else ft.Icons.CANCEL
            iclr  = ft.Colors.GREEN_400 if status == "present" else ft.Colors.RED_400
            rows.append(
                ft.Container(
                    content=ft.Row(controls=[
                        ft.Text(str(i+1), size=13, color=TEXT_GREY, width=30),
                        ft.Icon(icon, color=iclr, size=18),
                        ft.Text(name, size=15, color=ft.Colors.WHITE, expand=True),
                        ft.Text(status.capitalize(), color=iclr, weight=ft.FontWeight.BOLD),
                    ]),
                    bgcolor=bg, border_radius=10, padding=12,  
                )
            )

        content = ft.Column(
            controls=[
                banner(page, "Today's Attendance", show_back=True),
                ft.Container(padding=20, content=ft.Column(spacing=10, controls=rows)),
            ]
        )
        return ft.View(route="/attendance", bgcolor=APP_BG, padding=0, controls=[content], scroll=ft.ScrollMode.AUTO)

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
                            ft.Text(entry['name'], size=16, color=ft.Colors.WHITE, weight=ft.FontWeight.W_500),
                            ft.Row(
                                controls=[
                                    ft.ElevatedButton("Present", bgcolor=ft.Colors.GREEN_700 if is_p else "#262932", color=ft.Colors.WHITE, on_click=make_present(), expand=True),
                                    ft.ElevatedButton("Absent", bgcolor=ft.Colors.RED_700 if is_a else "#262932", color=ft.Colors.WHITE, on_click=make_absent(), expand=True),
                                ],
                            ),
                        ],
                    ),
                    bgcolor=CARD_BG, border_radius=12, padding=16,
                )
            )

    build_student_cards()

    def submit(e):
        unmarked = [d["name"] for d in attendance_data if d["status"] is None]
        if unmarked:
            msg.value = f"⚠ Mark all students first! ({len(unmarked)} remaining)"
            msg.color = ft.Colors.RED_400
            page.update()
            return

        save_attendance([(d["id"], d["status"]) for d in attendance_data])
        page.views.pop()
        page.views.append(attendance_view(page))
        page.update()

    if not students:
        main_body = ft.Text("No students added yet!\nGo to 'Add / Remove Student' first.", color=TEXT_GREY, italic=True, text_align=ft.TextAlign.CENTER)
        submit_btn = ft.Container()
    else:
        main_body = cards_col
        submit_btn = ft.ElevatedButton("Submit Attendance", bgcolor=ACCENT_GOLD, color=APP_BG, on_click=submit, width=float("inf"))

    content = ft.Column(
        controls=[
            banner(page, "Today's Attendance", show_back=True),
            ft.Container(padding=20, content=ft.Column(spacing=16, controls=[main_body, msg, submit_btn])),
        ]
    )
    return ft.View(route="/attendance", bgcolor=APP_BG, padding=0, controls=[content], scroll=ft.ScrollMode.AUTO)


# ================================================================
#  SCREEN 3 — OLDER REPORTS
# ================================================================

def older_reports_view(page):
    dates = get_all_dates()

    if not dates:
        body = ft.Container(padding=20, content=ft.Text("No records yet.", color=TEXT_GREY))
    else:
        date_rows = []
        for ds in dates:
            display = datetime.strptime(ds, "%Y-%m-%d").strftime("%d %b %Y")

            def open_report(date_str=ds, disp=display):
                def handler(e):
                    page.views.append(report_detail_view(page, date_str, disp))
                    page.update()
                return handler

            date_rows.append(
                ft.Container(
                    content=ft.Row(controls=[
                        ft.Icon(ft.Icons.CALENDAR_TODAY, color=ACCENT_GOLD, size=20),
                        ft.Text(display, size=16, color=ft.Colors.WHITE, expand=True),
                        ft.Icon(ft.Icons.CHEVRON_RIGHT, size=20, color=TEXT_GREY),
                    ]),
                    bgcolor=CARD_BG, border_radius=10, padding=16, on_click=open_report(),
                )
            )

        body = ft.Container(padding=20, content=ft.Column(spacing=12, controls=date_rows))

    content = ft.Column(controls=[banner(page, "Older Records", show_back=True), body])
    return ft.View(route="/older_records", bgcolor=APP_BG, padding=0, controls=[content], scroll=ft.ScrollMode.AUTO)

def report_detail_view(page, date_str, display_date):
    report = get_attendance_for_date(date_str)
    
    rows = []
    for i, (name, status) in enumerate(report):
        iclr = ft.Colors.GREEN_400 if status == "present" else ft.Colors.RED_400
        rows.append(
            ft.Container(
                content=ft.Row(controls=[
                    ft.Text(name, size=15, color=ft.Colors.WHITE, expand=True),
                    ft.Text(status.capitalize(), color=iclr, weight=ft.FontWeight.BOLD),
                ]),
                bgcolor=CARD_BG, border_radius=10, padding=12,  
            )
        )

    content = ft.Column(
        controls=[
            banner(page, f"📅 {display_date}", show_back=True),
            ft.Container(padding=20, content=ft.Column(spacing=10, controls=rows)),
        ]
    )
    return ft.View(route="/report_detail", bgcolor=APP_BG, padding=0, controls=[content], scroll=ft.ScrollMode.AUTO)


# ================================================================
#  SCREEN 4 — ADD / REMOVE STUDENT
# ================================================================

def add_remove_view(page):
    student_list = ft.Column(spacing=8)
    msg = ft.Text("", size=13)
    name_input = ft.TextField(
        hint_text="Enter student name...",
        expand=True, 
        border_radius=10, 
        bgcolor=CARD_BG,
        color=ft.Colors.WHITE,
        border_color="#262932"
    )

    def refresh():
        student_list.controls.clear()
        for sid, sname in get_all_students():
            def make_remove(s=sid):
                def h(e):
                    remove_student(s)
                    msg.value = "Student removed."
                    msg.color = ft.Colors.ORANGE_400
                    refresh()
                    page.update()
                return h
            student_list.controls.append(
                ft.Container(
                    content=ft.Row(controls=[
                        ft.Icon(ft.Icons.PERSON, color=TEXT_GREY, size=20),
                        ft.Text(sname, color=ft.Colors.WHITE, expand=True, size=15),
                        ft.IconButton(icon=ft.Icons.DELETE_OUTLINE, icon_color=ft.Colors.RED_400, on_click=make_remove()),
                    ]),
                    bgcolor=CARD_BG, border_radius=10, padding=12,  
                )
            )

    refresh()

    def add(e):
        name = name_input.value.strip()
        if not name:
            msg.value = "Please enter a valid name."
            msg.color = ft.Colors.RED_400
        else:
            add_student(name)
            name_input.value = ""
            msg.value = f"Added '{name}' successfully!"
            msg.color = ft.Colors.GREEN_400
            refresh()
        page.update()

    content = ft.Column(
        controls=[
            banner(page, "Manage Students", show_back=True),
            ft.Container(
                padding=20,
                content=ft.Column(
                    spacing=16,
                    controls=[
                        ft.Row(controls=[name_input, ft.ElevatedButton("Add", bgcolor=ACCENT_GOLD, color=APP_BG, on_click=add)]),
                        msg,
                        ft.Divider(color="#262932"),
                        student_list,
                    ],
                ),
            ),
        ]
    )
    return ft.View(route="/add_remove", bgcolor=APP_BG, padding=0, controls=[content], scroll=ft.ScrollMode.AUTO)


# ================================================================
#  MAIN APP LOGIC
# ================================================================

async def main(page: ft.Page):
    setup_database()
    page.title = "Digital Attendance Pro"
    page.window.width = 400
    page.window.height = 750
    page.bgcolor = APP_BG 

    page.views.clear()
    page.views.append(home_view(page))
    page.update()

ft.app(main, assets_dir="assets")