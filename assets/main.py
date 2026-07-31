import flet as ft
import sqlite3
import os
import shutil
import asyncio
from datetime import date, datetime

# ================================================================
#  THE DATABASE & BACKUP SETUP
# ================================================================

DB = "attendance_app.db"
BACKUP_DIR = "Database_Backups"

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

def auto_backup_db():
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
    
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_path = os.path.join(BACKUP_DIR, f"backup_{timestamp}.db")
    latest_path = os.path.join(BACKUP_DIR, "latest_backup.db")
    
    try:
        shutil.copy2(DB, backup_path)
        shutil.copy2(DB, latest_path)
    except Exception as e:
        print(f"Backup failed: {e}")

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
    # 🛡️ SAFE DELETION FIX: We DO NOT delete past attendance anymore! 
    # This ensures accidental student deletions never wipe historical stats.
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


# ================================================================
#  SHARED UI HELPERS
# ================================================================

APP_BG = "#0F1115"
CARD_BG = "#1A1D24"
HOVER_BG = "#262932"
ACCENT_GOLD = "#D4AF37"
TEXT_GREY = "#8A8D93"
GREEN_COLOR = "#66BB6A"
RED_COLOR = "#EF5350"

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
                page.views.append(analytics_view(page))
            page.update()
        return handler

    def dashboard_card(number, title, subtitle, icon, route, is_highlighted=False):
        icon_color = GREEN_COLOR if title == "Today's Attendance" else ACCENT_GOLD
        
        accent_bar = ft.Container(
            width=4,
            bgcolor=ACCENT_GOLD if is_highlighted else ft.Colors.TRANSPARENT,
            border_radius=4
        )

        inner_card = ft.Container(
            content=ft.Row(
                controls=[
                    accent_bar,
                    ft.Container(
                        content=ft.Icon(icon, color=icon_color, size=22),
                        bgcolor="#262932",
                        padding=12,
                        border_radius=8,
                    ),
                    ft.Column(
                        controls=[
                            ft.Text(f"{number}. {title}", size=15, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD),
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
            border_radius=11, 
            padding=12,
        )

        outer_card = ft.Container(
            content=inner_card,
            bgcolor=ft.Colors.TRANSPARENT, 
            padding=1, 
            border_radius=12,
            on_click=go(route),
        )

        def on_hover(e):
            if e.data == "true":
                outer_card.bgcolor = ACCENT_GOLD 
                inner_card.bgcolor = HOVER_BG
                outer_card.shadow = ft.BoxShadow(
                    blur_radius=15, 
                    spread_radius=2, 
                    color=ft.Colors.with_opacity(0.4, ACCENT_GOLD)
                )
            else:
                outer_card.bgcolor = ft.Colors.TRANSPARENT
                inner_card.bgcolor = CARD_BG
                outer_card.shadow = None
            outer_card.update()
            inner_card.update()

        outer_card.on_hover = on_hover
        return outer_card

    # Fetch live stats for summary card
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
                ft.Container(bgcolor=ACCENT_GOLD, height=8, expand=max(p_pct, 1)),
                ft.Container(bgcolor="#31343F", height=8, expand=max(a_pct, 1)),
            ],
            spacing=0,
        ),
        border_radius=4,
    )

    summary_card = ft.Container(
        content=ft.Column(
            controls=[
                ft.Text("Today's Summary", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                ft.Container(height=5),
                ratio_bar,
                ft.Container(height=5),
                ft.Row(
                    controls=[
                        ft.Row([ft.Icon(ft.Icons.CIRCLE, size=10, color=ACCENT_GOLD), ft.Text(f"Present: {present_count} ({p_pct}%)", size=13, color=TEXT_GREY)]),
                        ft.Row([ft.Icon(ft.Icons.CIRCLE, size=10, color="#31343F"), ft.Text(f"Absent: {absent_count} ({a_pct}%)", size=13, color=TEXT_GREY)]),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                )
            ],
            spacing=5,
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
            dashboard_card("1", "Today's Attendance", f"View and take class records for {date.today().strftime('%b %d')}", ft.Icons.CALENDAR_MONTH, "/attendance", is_highlighted=True),
            dashboard_card("2", "Older Records", "Access past daily attendance data", ft.Icons.HISTORY, "/older_records"),
            dashboard_card("3", "Reports & Analytics", "View Monthly/Yearly percentages", ft.Icons.INSERT_CHART, "/analytics"),
            dashboard_card("4", "Add/Remove Student", "Manage the student database and profiles", ft.Icons.PERSON_ADD_ALT_1, "/add_remove"),
        ],
        spacing=12,
    )

    return ft.View(route="/", bgcolor=APP_BG, padding=20, controls=[main_content])


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
                        ft.Text(f"✅ Present: {present_count}", size=16, weight=ft.FontWeight.BOLD, color=GREEN_COLOR),
                        ft.Text(f"❌ Absent: {absent_count}", size=16, weight=ft.FontWeight.BOLD, color=RED_COLOR),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_AROUND,
                ),
                bgcolor=CARD_BG, border_radius=12, padding=16,
            ),
            ft.Divider(color="#262932"),
        ]

        for i, (name, status) in enumerate(report):
            icon  = ft.Icons.CHECK_CIRCLE if status == "present" else ft.Icons.CANCEL
            iclr  = GREEN_COLOR if status == "present" else RED_COLOR
            rows.append(
                ft.Container(
                    content=ft.Row(controls=[
                        ft.Text(str(i+1), size=13, color=TEXT_GREY, width=30),
                        ft.Icon(icon, color=iclr, size=18),
                        ft.Text(name, size=15, color=ft.Colors.WHITE, expand=True),
                        ft.Text(status.capitalize(), color=iclr, weight=ft.FontWeight.BOLD),
                    ]),
                    bgcolor=CARD_BG, border_radius=10, padding=12,  
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
                                    ft.ElevatedButton("Present", bgcolor="#388E3C" if is_p else "#262932", color=ft.Colors.WHITE, on_click=make_present(), expand=True),
                                    ft.ElevatedButton("Absent", bgcolor="#D32F2F" if is_a else "#262932", color=ft.Colors.WHITE, on_click=make_absent(), expand=True),
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
            msg.color = RED_COLOR
            page.update()
            return

        save_attendance([(d["id"], d["status"]) for d in attendance_data])
        
        # 🔄 IMMEDIATE VIEW UPDATE FIX: Replaces view instantly so summary updates right away!
        page.views.pop()
        page.views.append(attendance_view(page))
        # Re-initialize home view in background stack so home summary refreshes immediately on back
        if len(page.views) > 0:
            page.views[0] = home_view(page)
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
            d_obj = datetime.strptime(ds, "%Y-%m-%d")
            display = d_obj.strftime("%d %b %Y")
            
            # Fetch summary stats for this specific past date
            past_report = get_attendance_for_date(ds)
            p_count = sum(1 for _, s in past_report if s == "present")
            a_count = sum(1 for _, s in past_report if s == "absent")

            def open_report(date_str=ds, disp=display):
                def handler(e):
                    page.views.append(report_detail_view(page, date_str, disp))
                    page.update()
                return handler

            date_rows.append(
                ft.Container(
                    content=ft.Row(controls=[
                        ft.Icon(ft.Icons.CALENDAR_TODAY, color=ACCENT_GOLD, size=20),
                        ft.Column([
                            ft.Text(display, size=15, color=ft.Colors.WHITE, weight="bold"),
                            ft.Text(f"✅ {p_count} Present  |  ❌ {a_count} Absent", size=11, color=TEXT_GREY),
                        ], expand=True, spacing=2),
                        ft.Icon(ft.Icons.CHEVRON_RIGHT, size=20, color=TEXT_GREY),
                    ]),
                    bgcolor=CARD_BG, border_radius=10, padding=16, on_click=open_report(),
                )
            )

        body = ft.Container(padding=20, content=ft.Column(spacing=12, controls=date_rows))

    content = ft.Column(controls=[
        banner(page, "Older Records", show_back=True), 
        body
    ])
    return ft.View(route="/older_records", bgcolor=APP_BG, padding=0, controls=[content], scroll=ft.ScrollMode.AUTO)


def report_detail_view(page, date_str, display_date):
    report = get_attendance_for_date(date_str)
    present_count = sum(1 for _, s in report if s == "present")
    absent_count  = sum(1 for _, s in report if s == "absent")

    rows = [
        ft.Container(
            content=ft.Row(
                controls=[
                    ft.Text(f"✅ Present: {present_count}", size=16, weight=ft.FontWeight.BOLD, color=GREEN_COLOR),
                    ft.Text(f"❌ Absent: {absent_count}", size=16, weight=ft.FontWeight.BOLD, color=RED_COLOR),
                ],
                alignment=ft.MainAxisAlignment.SPACE_AROUND,
            ),
            bgcolor=CARD_BG, border_radius=12, padding=16,
        ),
        ft.Divider(color="#262932"),
    ]
    
    for i, (name, status) in enumerate(report):
        iclr = GREEN_COLOR if status == "present" else RED_COLOR
        rows.append(
            ft.Container(
                content=ft.Row(controls=[
                    ft.Text(str(i+1), size=13, color=TEXT_GREY, width=30),
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
#  SCREEN 4 — ANALYTICS (MONTH / YEAR TOGGLE)
# ================================================================

def analytics_view(page):
    
    current_period = ["month"] 
    stats_column = ft.Column(spacing=10)
    info_text = ft.Text("", size=13, color=TEXT_GREY, italic=True)

    def refresh_stats():
        period = current_period[0]
        stats, total_days = get_analytics_stats(period)
        stats_column.controls.clear()
        
        info_text.value = f"Data based on {total_days} recorded attendance days this {period}."
        
        if total_days == 0:
            stats_column.controls.append(ft.Text(f"No attendance data recorded yet for this {period}.", color=TEXT_GREY))
        else:
            for name, pct, p_days, t_days in stats:
                
                if pct >= 75:
                    pct_color = GREEN_COLOR
                elif pct <= 50:
                    pct_color = RED_COLOR
                else:
                    pct_color = ACCENT_GOLD
                    
                mini_bar = ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Container(bgcolor=pct_color, height=5, expand=max(pct, 1)),
                            ft.Container(bgcolor="#31343F", height=5, expand=max(100 - pct, 1)),
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
                                        ft.Text(name, size=15, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD),
                                        ft.Text(f"{pct}%", size=15, color=pct_color, weight=ft.FontWeight.BOLD),
                                    ],
                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                                ),
                                ft.Text(f"Present {p_days} out of {t_days} days", size=11, color=TEXT_GREY),
                                ft.Container(height=2),
                                mini_bar
                            ],
                            spacing=2,
                        ),
                        bgcolor=CARD_BG,
                        border_radius=10,
                        padding=16,
                    )
                )
        page.update()

    def set_period(period):
        def handler(e):
            current_period[0] = period
            btn_month.bgcolor = ACCENT_GOLD if period == "month" else HOVER_BG
            btn_month.color = APP_BG if period == "month" else ft.Colors.WHITE
            
            btn_year.bgcolor = ACCENT_GOLD if period == "year" else HOVER_BG
            btn_year.color = APP_BG if period == "year" else ft.Colors.WHITE
            
            refresh_stats()
        return handler

    btn_month = ft.ElevatedButton("This Month", on_click=set_period("month"), bgcolor=ACCENT_GOLD, color=APP_BG, expand=True)
    btn_year = ft.ElevatedButton("This Year", on_click=set_period("year"), bgcolor=HOVER_BG, color=ft.Colors.WHITE, expand=True)

    toggle_row = ft.Row(controls=[btn_month, btn_year], spacing=10)
    refresh_stats()

    content = ft.Column(
        controls=[
            banner(page, "Reports & Analytics", show_back=True),
            ft.Container(
                padding=20,
                content=ft.Column(
                    spacing=16,
                    controls=[
                        toggle_row,
                        info_text,
                        ft.Divider(color="#262932"),
                        stats_column
                    ],
                ),
            ),
        ]
    )
    return ft.View(route="/analytics", bgcolor=APP_BG, padding=0, controls=[content], scroll=ft.ScrollMode.AUTO)


# ================================================================
#  SCREEN 5 — ADD / REMOVE STUDENT
# ================================================================

def add_remove_view(page):
    student_list = ft.Column(spacing=8)
    msg = ft.Text("", size=13)
    
    name_input = ft.TextField(
        hint_text="Enter student name...",
        expand=True, 
        border_radius=10, 
        bgcolor=CARD_BG,
        color=ft.Colors.WHITE
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
                        ft.Icon(ft.Icons.PERSON, color=TEXT_GREY, size=20),
                        ft.Text(sname, color=ft.Colors.WHITE, expand=True, size=15),
                        ft.IconButton(icon=ft.Icons.DELETE_OUTLINE, icon_color=RED_COLOR, on_click=make_remove()),
                    ]),
                    bgcolor=CARD_BG, border_radius=10, padding=12,  
                )
            )

    refresh()

    def add(e):
        name = name_input.value.strip()
        if not name:
            msg.value = "Please enter a valid name."
            msg.color = RED_COLOR
        else:
            add_student(name)
            name_input.value = ""
            msg.value = f"Added '{name}' successfully!"
            msg.color = GREEN_COLOR
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
                        ft.Text("Existing Students:", size=15, weight=ft.FontWeight.BOLD, color=TEXT_GREY),
                        student_list,
                    ],
                ),
            ),
        ]
    )
    return ft.View(route="/add_remove", bgcolor=APP_BG, padding=0, controls=[content], scroll=ft.ScrollMode.AUTO)


# ================================================================
#  MAIN APP LOGIC & SPLASH SCREEN
# ================================================================

async def main(page: ft.Page):
    setup_database()
    page.title = "Digital Attendance Pro"
    
    # 📱 LOCKED DIMENSIONS 📱
    page.window.width = 400
    page.window.height = 750
    page.window.resizable = False
    page.window.maximizable = False
    
    page.bgcolor = APP_BG 

    # ── 1. Splash Screen ──────────────────────────
    logo = ft.Image(src="logo.png", width=220, height=90, fit="contain")
    spinner = ft.ProgressRing(color=ACCENT_GOLD)
    splash_text = ft.Text("Loading Digital Experience...", size=13, color=TEXT_GREY)

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

    page.views.clear()
    page.views.append(
        ft.View(
            route="/splash",
            bgcolor=APP_BG,
            padding=0,
            controls=[splash_content] 
        )
    )
    page.update()

    # ── 2. The 5-Second Timer ─────────────────────────────────
    await asyncio.sleep(5)

    # ── 3. Transition to App Dashboard ────────────────────────
    page.views.clear()
    page.views.append(home_view(page))
    page.update()

ft.app(target=main, assets_dir="assets")