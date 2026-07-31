import flet as ft
import sqlite3
from datetime import date, datetime
import time
import os
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
#  SHARED UI HELPERS (GLASSMORPHISM UPGRADE)
# ================================================================

CARD_BG = ft.Colors.with_opacity(0.85, "#1E1E1E") 
BANNER_BG = ft.Colors.with_opacity(0.90, "#121212")

def with_space_bg(content):
    """Wraps any screen with the space GIF in the background using the NEW Flet rules."""
    return ft.Container(
        image=ft.DecorationImage(
            src="space.gif",
            fit="cover",
        ),
        expand=True,
        content=content
    )

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
        bgcolor=BANNER_BG,
        padding=16,  
        width=float("inf"),
    )

def home_banner():
    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Text("📋 Digital Attendance", size=28, weight=ft.FontWeight.BOLD,
                        color=ft.Colors.WHITE, text_align=ft.TextAlign.CENTER),
                ft.Text("by Anubhav Yaduvanshi", size=14, color=ft.Colors.GREY_400,
                        italic=True, text_align=ft.TextAlign.CENTER),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=4,
        ),
        bgcolor=BANNER_BG,
        padding=24,  
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
            elif route == "/older_reports":
                page.views.append(older_reports_view(page))
            elif route == "/add_remove":
                page.views.append(add_remove_view(page))
            page.update()
        return handler

    def menu_card(label, icon, color, route, glow_color):
        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(icon, color=ft.Colors.WHITE, size=26),
                    ft.Text(label, size=17, color=ft.Colors.WHITE, weight=ft.FontWeight.W_600, expand=True),
                    ft.Icon(ft.Icons.ARROW_FORWARD_IOS, color=ft.Colors.WHITE70, size=15),
                ],
            ),
            bgcolor=ft.Colors.with_opacity(0.85, color), 
            border_radius=14,
            padding=20,  
            on_click=go(route),
            shadow=ft.BoxShadow(blur_radius=20, spread_radius=2, color=glow_color),
        )

    main_content = ft.Column(
        controls=[
            home_banner(),
            ft.Container(
                padding=20,
                content=ft.Column(
                    spacing=20, 
                    controls=[
                        ft.Text("Choose an option:", size=15, color=ft.Colors.WHITE70),
                        menu_card("Today's Attendance", ft.Icons.HOW_TO_REG, ft.Colors.GREEN_900, "/attendance", ft.Colors.with_opacity(0.4, ft.Colors.GREEN_ACCENT)),
                        menu_card("Older Reports", ft.Icons.HISTORY_EDU, ft.Colors.BLUE_900, "/older_reports", ft.Colors.with_opacity(0.4, ft.Colors.BLUE_ACCENT)),
                        menu_card("Add / Remove Student", ft.Icons.PEOPLE, ft.Colors.PURPLE_900, "/add_remove", ft.Colors.with_opacity(0.4, ft.Colors.PURPLE_ACCENT)),
                    ],
                ),
            ),
        ],
    )

    return ft.View(
        route="/",
        bgcolor="black", # <--- FIX APPLIED
        padding=0,
        controls=[with_space_bg(main_content)],
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
                        ft.Text(f"✅  Present: {present_count}", size=18,
                                weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_400),
                        ft.Text(f"❌  Absent: {absent_count}", size=18,
                                weight=ft.FontWeight.BOLD, color=ft.Colors.RED_400),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_AROUND,
                ),
                bgcolor=CARD_BG,
                border_radius=12,
                padding=16,
            ),
            ft.Text("Attendance is already done for today ✓", italic=True,
                    color=ft.Colors.WHITE70, size=13),
            ft.Divider(color=ft.Colors.GREY_800),
            ft.Container(
                content=ft.Row(controls=[
                    ft.Text("S.NO", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE70, width=35),
                    ft.Text("Student Name", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE70, expand=True),
                    ft.Text("Status", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE70),
                ]),
                padding=10,  
            )
        ]

        for i, (name, status) in enumerate(report):
            bg    = ft.Colors.with_opacity(0.2, ft.Colors.GREEN) if status == "present" else ft.Colors.with_opacity(0.2, ft.Colors.RED)
            icon  = ft.Icons.CHECK_CIRCLE if status == "present" else ft.Icons.CANCEL
            iclr  = ft.Colors.GREEN_400 if status == "present" else ft.Colors.RED_400
            rows.append(
                ft.Container(
                    content=ft.Row(controls=[
                        ft.Text(str(i+1), size=13, color=ft.Colors.WHITE70, width=35),
                        ft.Icon(icon, color=iclr, size=18),
                        ft.Text(name, size=15, color=ft.Colors.WHITE, expand=True, weight=ft.FontWeight.W_500),
                        ft.Text(status.capitalize(), color=iclr, weight=ft.FontWeight.BOLD),
                    ]),
                    bgcolor=bg,
                    border_radius=10,
                    padding=12,  
                )
            )

        content = ft.Column(
            controls=[
                banner(page, "Today's Attendance", show_back=True),
                ft.Container(padding=20, content=ft.Column(spacing=10, controls=rows)),
            ]
        )
        return ft.View(route="/attendance", bgcolor="black", padding=0, controls=[with_space_bg(content)], scroll=ft.ScrollMode.AUTO) # <--- FIX APPLIED

    attendance_data = [{"id": sid, "name": sname, "status": None} for sid, sname in students]
    cards_col = ft.Column(spacing=10)
    msg       = ft.Text("", size=14)

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
                            ft.Text(f"Student Name :- {entry['name']}",
                                    size=16, color=ft.Colors.WHITE, weight=ft.FontWeight.W_500),
                            ft.Row(
                                controls=[
                                    ft.ElevatedButton(
                                        "✅  Present",
                                        bgcolor=ft.Colors.with_opacity(0.8, ft.Colors.GREEN_700) if is_p else ft.Colors.with_opacity(0.3, "#2C2C2C"),
                                        color=ft.Colors.WHITE if is_p else ft.Colors.WHITE70,
                                        on_click=make_present(),
                                    ),
                                    ft.ElevatedButton(
                                        "❌  Absent",
                                        bgcolor=ft.Colors.with_opacity(0.8, ft.Colors.RED_700) if is_a else ft.Colors.with_opacity(0.3, "#2C2C2C"),
                                        color=ft.Colors.WHITE if is_a else ft.Colors.WHITE70,
                                        on_click=make_absent(),
                                    ),
                                ],
                            ),
                        ],
                    ),
                    bgcolor=CARD_BG,
                    border_radius=12,
                    padding=16,
                )
            )

    build_student_cards()

    def submit(e):
        unmarked = [d["name"] for d in attendance_data if d["status"] is None]
        if unmarked:
            msg.value = f"⚠  Mark all students first! ({len(unmarked)} remaining)"
            msg.color = ft.Colors.RED_400
            page.update()
            return

        save_attendance([(d["id"], d["status"]) for d in attendance_data])
        page.views.pop()
        page.views.append(attendance_view(page))
        page.update()

    if not students:
        main_body = ft.Text(
            "No students added yet!\nGo to 'Add / Remove Student' first.",
            color=ft.Colors.WHITE70, italic=True, text_align=ft.TextAlign.CENTER,
        )
        submit_btn = ft.Container()
    else:
        main_body = cards_col
        submit_btn = ft.ElevatedButton(
            "Submit Attendance",
            icon=ft.Icons.DONE_ALL,
            bgcolor=ft.Colors.BLUE_700,
            color=ft.Colors.WHITE,
            on_click=submit,
            width=float("inf"),
        )

    content = ft.Column(
        controls=[
            banner(page, "Today's Attendance", show_back=True),
            ft.Container(
                padding=20,
                content=ft.Column(
                    spacing=16,
                    controls=[main_body, msg, submit_btn],
                ),
            ),
        ]
    )
    return ft.View(route="/attendance", bgcolor="black", padding=0, controls=[with_space_bg(content)], scroll=ft.ScrollMode.AUTO) # <--- FIX APPLIED


# ================================================================
#  SCREEN 3 — OLDER REPORTS
# ================================================================

def older_reports_view(page):
    dates = get_all_dates()

    if not dates:
        body = ft.Container(
            padding=20,
            content=ft.Text("No reports yet. Take attendance first!",
                            color=ft.Colors.WHITE70, italic=True),
        )
    else:
        date_rows = []
        for ds in dates:
            d = datetime.strptime(ds, "%Y-%m-%d")
            display = d.strftime("%d %b %Y")

            def open_report(date_str=ds, disp=display):
                def handler(e):
                    page.views.append(report_detail_view(page, date_str, disp))
                    page.update()
                return handler

            date_rows.append(
                ft.Container(
                    content=ft.Row(controls=[
                        ft.Icon(ft.Icons.CALENDAR_TODAY, color=ft.Colors.BLUE_400),
                        ft.Text(display, size=17, color=ft.Colors.WHITE, expand=True),
                        ft.Icon(ft.Icons.ARROW_FORWARD_IOS, size=14, color=ft.Colors.WHITE70),
                    ]),
                    bgcolor=CARD_BG,
                    border_radius=10,
                    padding=16,  
                    on_click=open_report(),
                )
            )

        body = ft.Container(
            padding=20,
            content=ft.Column(spacing=12, controls=date_rows),
        )

    content = ft.Column(controls=[banner(page, "Older Reports", show_back=True), body])
    return ft.View(route="/older_reports", bgcolor="black", padding=0, controls=[with_space_bg(content)], scroll=ft.ScrollMode.AUTO) # <--- FIX APPLIED


def report_detail_view(page, date_str, display_date):
    report = get_attendance_for_date(date_str)
    present_count = sum(1 for _, s in report if s == "present")
    absent_count  = sum(1 for _, s in report if s == "absent")

    rows = [
        ft.Container(
            content=ft.Row(
                controls=[
                    ft.Text(f"✅  Present: {present_count}", size=18,
                            weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_400),
                    ft.Text(f"❌  Absent: {absent_count}", size=18,
                            weight=ft.FontWeight.BOLD, color=ft.Colors.RED_400),
                ],
                alignment=ft.MainAxisAlignment.SPACE_AROUND,
            ),
            bgcolor=CARD_BG, border_radius=12, padding=16,
        ),
        ft.Divider(color=ft.Colors.GREY_800),
        ft.Container(
            content=ft.Row(controls=[
                ft.Text("S.NO", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE70, width=35),
                ft.Text("Student Name", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE70, expand=True),
                ft.Text("Status", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE70),
            ]),
            padding=10,  
        )
    ]

    for i, (name, status) in enumerate(report):
        bg   = ft.Colors.with_opacity(0.2, ft.Colors.GREEN) if status == "present" else ft.Colors.with_opacity(0.2, ft.Colors.RED)
        icon = ft.Icons.CHECK_CIRCLE if status == "present" else ft.Icons.CANCEL
        iclr = ft.Colors.GREEN_400 if status == "present" else ft.Colors.RED_400
        rows.append(
            ft.Container(
                content=ft.Row(controls=[
                    ft.Text(str(i+1), size=13, color=ft.Colors.WHITE70, width=35),
                    ft.Icon(icon, color=iclr, size=18),
                    ft.Text(name, size=15, color=ft.Colors.WHITE, expand=True, weight=ft.FontWeight.W_500),
                    ft.Text(status.capitalize(), color=iclr, weight=ft.FontWeight.BOLD),
                ]),
                bgcolor=bg, border_radius=10,
                padding=12,  
            )
        )

    content = ft.Column(
        controls=[
            banner(page, f"📅 {display_date}", show_back=True),
            ft.Container(padding=20, content=ft.Column(spacing=10, controls=rows)),
        ]
    )
    return ft.View(route="/report_detail", bgcolor="black", padding=0, controls=[with_space_bg(content)], scroll=ft.ScrollMode.AUTO) # <--- FIX APPLIED


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
        border_color=ft.Colors.GREY_700
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
                        ft.Icon(ft.Icons.PERSON, color=ft.Colors.BLUE_400, size=20),
                        ft.Text(sname, color=ft.Colors.WHITE, expand=True, size=16),
                        ft.IconButton(icon=ft.Icons.DELETE_OUTLINE,
                                      icon_color=ft.Colors.RED_400,
                                      on_click=make_remove()),
                    ]),
                    bgcolor=CARD_BG, border_radius=10,
                    padding=12,  
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
                        ft.Row(controls=[name_input, ft.ElevatedButton("Add", icon=ft.Icons.ADD, on_click=add, bgcolor=ft.Colors.BLUE_700, color=ft.Colors.WHITE)]),
                        msg,
                        ft.Divider(color=ft.Colors.GREY_800),
                        ft.Text("Existing Students:", size=15, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE70),
                        student_list,
                    ],
                ),
            ),
        ]
    )
    return ft.View(route="/add_remove", bgcolor="black", padding=0, controls=[with_space_bg(content)], scroll=ft.ScrollMode.AUTO) # <--- FIX APPLIED


# ================================================================
#  MAIN APP & SPLASH SCREEN LOGIC
# ================================================================

async def main(page: ft.Page):
    setup_database()
    page.title = "Digital Attendance Pro"
    page.window.width = 400
    page.window.height = 700
    page.bgcolor = "black" 

    # ── 1. Splash Screen ───────────────────────────────────────
    logo = ft.Image(src="logo.png", width=220, height=90, fit="contain")
    spinner = ft.ProgressRing(color="white")
    splash_text = ft.Text("Loading Digital Experience...", size=13, color="white70")

    splash_content = ft.Container(
        content=ft.Column(
            controls=[logo, ft.Container(height=10), spinner, ft.Container(height=5), splash_text],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        expand=True,
        alignment=ft.Alignment.CENTER
    )

    page.views.clear()
    page.views.append(
        ft.View(
            route="/splash",
            bgcolor="black", # <--- FIX APPLIED
            padding=0,
            controls=[with_space_bg(splash_content)] 
        )
    )
    page.update()

    # ── 2. The 5-Second Timer ─────────────────────────────────
    await asyncio.sleep(5)

    # ── 3. Transition to App Dashboard ────────────────────────
    page.views.clear()
    page.views.append(home_view(page))
    page.update()

ft.app(main, assets_dir="assets")
