import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

import hashlib
import os as _os0
APP_DIR = _os0.path.dirname(_os0.path.abspath(__file__))
DB_PATH = _os0.path.join(APP_DIR, "kpi_app.db")
QR_PATH = _os0.path.join(APP_DIR, "qr_hong.jfif")

def hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode("utf-8")).hexdigest()

def make_standard_username(full_name: str, role: str) -> str:
    """Tự động sinh username chuẩn dạng <ten>_<vitri> (VD: nhung_ec, mai_ec, phung_cm, hong_kt, thuy_atl)"""
    import unicodedata
    import re
    words = full_name.strip().split()
    first_name = words[-1] if words else "user"
    clean_name = unicodedata.normalize('NFKD', first_name).encode('ASCII', 'ignore').decode('utf-8').lower()
    clean_name = re.sub(r'[^a-z0-9]', '', clean_name)
    if not clean_name:
        clean_name = "user"
    role_suffix = {"EC": "ec", "CM": "cm", "KeToan": "kt", "ATL": "atl", "BM": "bm", "Admin": "admin"}.get(role, role.lower())
    return f"{clean_name}_{role_suffix}"

# ──────────────────────────────────── DB ──────────────────────────────────────

def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE, display_name TEXT,
        password TEXT, role TEXT, fixed_duty TEXT DEFAULT "")''')

    c.execute('''CREATE TABLE IF NOT EXISTS rules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE, rule_name TEXT, deadline_time TEXT,
        frequency TEXT, penalty_amount INTEGER, roles_required TEXT)''')

    c.execute('''CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, rule_code TEXT, report_date TEXT, content TEXT,
        kpi_cuoc_goi INTEGER DEFAULT 0, kpi_doanh_thu REAL DEFAULT 0,
        kpi_checkin INTEGER DEFAULT 0, kpi_cocnho INTEGER DEFAULT 0,
        giai_trinh TEXT DEFAULT "", de_xuat TEXT DEFAULT "",
        submitted_at TEXT, is_late INTEGER DEFAULT 0,
        FOREIGN KEY(user_id) REFERENCES users(id))''')

    c.execute('''CREATE TABLE IF NOT EXISTS khtn_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, record_date TEXT,
        ten_kh TEXT, so_dien_thoai TEXT, lop_hoc TEXT,
        trang_thai TEXT, ghi_chu TEXT, buoc_tiep_theo TEXT,
        ngay_hen TEXT, updated_at TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id))''')

    c.execute('''CREATE TABLE IF NOT EXISTS duty_assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        year_month TEXT, duty_code TEXT, user_id INTEGER, note TEXT DEFAULT "",
        UNIQUE(year_month, duty_code),
        FOREIGN KEY(user_id) REFERENCES users(id))''')

    c.execute('''CREATE TABLE IF NOT EXISTS peer_assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        year_month TEXT, checker_id INTEGER, checkee_id INTEGER,
        UNIQUE(year_month, checker_id),
        FOREIGN KEY(checker_id) REFERENCES users(id),
        FOREIGN KEY(checkee_id) REFERENCES users(id))''')

    c.execute('''CREATE TABLE IF NOT EXISTS peer_checks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        checker_id INTEGER, checkee_id INTEGER,
        check_date TEXT, check_type TEXT,
        result INTEGER DEFAULT 0,
        link_evidence TEXT DEFAULT "", note TEXT DEFAULT "",
        checked_at TEXT,
        UNIQUE(checker_id, checkee_id, check_date, check_type),
        FOREIGN KEY(checker_id) REFERENCES users(id),
        FOREIGN KEY(checkee_id) REFERENCES users(id))''')

    c.execute('''CREATE TABLE IF NOT EXISTS monthly_targets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        year_month TEXT, user_id INTEGER, position TEXT DEFAULT "",
        target_doanh_thu REAL DEFAULT 0,
        target_cuoc_goi_chang1 INTEGER DEFAULT 0,
        target_cuoc_goi_chang2 INTEGER DEFAULT 0,
        target_checkin_landau INTEGER DEFAULT 0,
        target_checkin_sk INTEGER DEFAULT 0,
        target_data_fb INTEGER DEFAULT 0, target_data_zalo INTEGER DEFAULT 0,
        actual_doanh_thu REAL DEFAULT 0, actual_cuoc_goi INTEGER DEFAULT 0,
        actual_checkin_landau INTEGER DEFAULT 0, actual_checkin_sk INTEGER DEFAULT 0,
        note TEXT DEFAULT "",
        UNIQUE(year_month, user_id),
        FOREIGN KEY(user_id) REFERENCES users(id))''')

    c.execute('''CREATE TABLE IF NOT EXISTS monthly_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        year_month TEXT, muc_dich TEXT DEFAULT "", ten_hoat_dong TEXT,
        phong_ban TEXT DEFAULT "", noi_dung TEXT DEFAULT "",
        chi_phi_qua TEXT DEFAULT "", dia_diem TEXT DEFAULT "",
        doi_tuong TEXT DEFAULT "", so_luong_chi_tieu INTEGER DEFAULT 0,
        timeline TEXT DEFAULT "", dieu_kien_nghiem_thu TEXT DEFAULT "",
        trang_thai TEXT DEFAULT "Chua thuc hien",
        so_luong_thuc_te INTEGER DEFAULT 0,
        assigned_to TEXT DEFAULT "", created_at TEXT)''')

    # ── Bảng Lịch Ca Làm Việc ─────────────────────────────────────────────────
    c.execute('''CREATE TABLE IF NOT EXISTS work_shifts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        shift_date TEXT,
        user_id INTEGER,
        ca TEXT DEFAULT "OFF",
        start_time TEXT DEFAULT "",
        end_time TEXT DEFAULT "",
        location TEXT DEFAULT "Chi nhánh",
        note TEXT DEFAULT "",
        created_by TEXT DEFAULT "",
        created_at TEXT DEFAULT "",
        UNIQUE(shift_date, user_id),
        FOREIGN KEY(user_id) REFERENCES users(id))''')

    c.execute('''CREATE TABLE IF NOT EXISTS penalties (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, report_id INTEGER, amount INTEGER,
        reason TEXT, penalty_date TEXT, is_paid INTEGER DEFAULT 0,
        FOREIGN KEY(user_id) REFERENCES users(id))''')

    # ── Bảng Chỉ Tiêu Ebook & QR theo người theo tháng ───────────────────────
    c.execute('''CREATE TABLE IF NOT EXISTS ebook_qr_targets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        year_month TEXT, user_id INTEGER,
        target_ebook INTEGER DEFAULT 0,
        target_qr    INTEGER DEFAULT 0,
        UNIQUE(year_month, user_id),
        FOREIGN KEY(user_id) REFERENCES users(id))''')

    # ── Bảng Ghi Nhận Từng SĐT Ebook/QR ──────────────────────────────────────
    c.execute('''CREATE TABLE IF NOT EXISTS ebook_qr_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, year_month TEXT,
        type TEXT CHECK(type IN ("ebook","qr")),
        phone_number TEXT,
        note TEXT DEFAULT "",
        added_at TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id))''')


    # ── Seed users
    c.execute("SELECT COUNT(*) as cnt FROM users")
    if c.fetchone()["cnt"] == 0:
        default_users = [
            ("bm",          "BM Hương (Giám Đốc)",    "123456", "Admin",  ""),
            ("thuy_atl",    "Thủy (ATL)",              "123456", "Admin",  "STEAM_PLAN,QR_ZALO,BOOTH_PLAN"),
            ("ketoan_hong", "Hồng (Kế Toán)",          "123456", "KeToan", ""),
            ("tram_anh",    "Trâm Anh (EC)",           "123456", "EC",     ""),
            ("dung",        "Dung (EC)",               "123456", "EC",     ""),
            ("ec_3",        "EC 3 (chưa đặt tên)",     "123456", "EC",     ""),
            ("ec_4",        "EC 4 (chưa đặt tên)",     "123456", "EC",     ""),
            ("ec_5",        "EC 5 (chưa đặt tên)",     "123456", "EC",     ""),
            ("ec_6",        "EC 6 (chưa đặt tên)",     "123456", "EC",     ""),
        ]
        c.executemany("INSERT INTO users(username,display_name,password,role,fixed_duty) VALUES(?,?,?,?,?)", default_users)

    # ── Seed rules
    c.execute("SELECT COUNT(*) as cnt FROM rules")
    if c.fetchone()["cnt"] == 0:
        default_rules = [
            ("BC_DAU_CA",        "Báo cáo đầu ca",                          "09:00", "daily",      50000, "EC,Admin"),
            ("CHI_SO_NGAY",      "Điền chỉ số ngày",                        "21:00", "daily",      50000, "EC,Admin"),
            ("BC_CUOI_CA",       "Báo cáo cuối ca",                         "21:00", "daily",      50000, "EC,Admin"),
            ("KHTN_DAILY",       "Cập nhật KHTN chặng",                     "21:00", "daily",      0,     "EC,Admin"),
            ("MT_TUAN",          "Điền mục tiêu tuần mới",                  "21:00", "weekly_sun", 50000, "EC,Admin"),
            ("BC_NHAN_NHAN_TUAN","Báo cáo nhìn nhận tuần + MT tuần mới",   "21:00", "weekly_sun", 50000, "EC,Admin"),
            ("BC_CHANG_2",       "Báo cáo Chặng 2 (mục tiêu T6-T7-CN)",   "21:00", "weekly_thu", 50000, "EC,Admin"),
            ("EBOOK",            "Báo cáo Ebook (7 EB/nhân sự/tháng)",     "23:59", "monthly",    0,     "EC,Admin"),
            ("BOOTH_PLAN",       "Kế hoạch + Báo cáo BOOTH",               "23:59", "monthly",    0,     "EC,Admin"),
            ("QR_ZALO",          "Báo cáo Quét QR Zalo game",               "23:59", "monthly",    0,     "Admin"),
            ("STEAM_PLAN",       "Kế hoạch STEAM hàng tuần",                "21:00", "weekly_sun", 0,     "Admin"),
        ]
        c.executemany("INSERT INTO rules(code,rule_name,deadline_time,frequency,penalty_amount,roles_required) VALUES(?,?,?,?,?,?)", default_rules)

    # ── Bảng chống ghi phạt "không nộp" 2 lần + bảng cấu hình chung
    c.execute("""CREATE TABLE IF NOT EXISTS penalty_sweep (
        user_id INTEGER, rule_code TEXT, period_date TEXT,
        UNIQUE(user_id, rule_code, period_date))""")
    c.execute("CREATE TABLE IF NOT EXISTS app_settings (key TEXT PRIMARY KEY, value TEXT)")
    c.execute("INSERT OR IGNORE INTO app_settings(key,value) VALUES('sweep_start', ?)",
              (datetime.now().strftime("%Y-%m-%d"),))
    c.execute("INSERT OR IGNORE INTO app_settings(key,value) VALUES('has_atl', '1')")
    c.execute("INSERT OR IGNORE INTO app_settings(key,value) VALUES('branch_name', 'Ocean Edu Buôn Ma Thuột')")
    try:
        c.execute("ALTER TABLE users ADD COLUMN is_active INTEGER DEFAULT 1")
    except Exception:
        pass

    # ── Bảng Lịch Sự Kiện STEAM từ Phòng Đào Tạo ──────────────────────────────
    c.execute('''CREATE TABLE IF NOT EXISTS steam_schedule (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_date TEXT,
        start_time TEXT,
        end_time TEXT,
        title TEXT,
        school_name TEXT,
        location TEXT,
        assigned_ec_ids TEXT,
        note TEXT,
        created_by TEXT,
        created_at TEXT)''')

    # ── Migration v10/v11 — quy chế BM chốt & tính năng mở rộng
    ver = c.execute("PRAGMA user_version").fetchone()[0]
    if ver < 10:
        c.execute("UPDATE rules SET deadline_time='THEO_CA' WHERE code='BC_DAU_CA'")
        c.execute("UPDATE rules SET deadline_time='22:00', rule_name='Báo cáo cuối ca (ngay sau ca, muộn nhất 22:00)' WHERE code='BC_CUOI_CA'")
        c.execute("UPDATE rules SET deadline_time='08:30', penalty_amount=50000, rule_name='Cập nhật KHTN (trước 08:30 hằng ngày)' WHERE code='KHTN_DAILY'")
        c.execute("UPDATE rules SET deadline_time='21:30' WHERE code IN ('BC_CHANG_2','MT_TUAN','BC_NHAN_NHAN_TUAN')")
        c.execute("PRAGMA user_version = 10")
    if ver < 11:
        new_rules = [
            ("BC_ATL_DAU_NGAY",  "ATL — Báo cáo team đầu ngày",          "09:00", "daily", 0, "Admin"),
            ("BC_ATL_KHTN_SANG", "ATL — Rà soát KHTN hẹn sáng",          "08:45", "daily", 0, "Admin"),
            ("BC_ATL_CUOI_NGAY", "ATL — Báo cáo kết quả team cuối ngày", "21:15", "daily", 0, "Admin"),
            ("BC_PHAT_SINH",     "Báo cáo phát sinh theo chỉ đạo",       "23:59", "adhoc", 0, "EC,Admin"),
        ]
        for r_code, r_name, r_dl, r_freq, r_pen, r_roles in new_rules:
            c.execute("""INSERT OR IGNORE INTO rules(code, rule_name, deadline_time, frequency, penalty_amount, roles_required)
                         VALUES(?,?,?,?,?,?)""", (r_code, r_name, r_dl, r_freq, r_pen, r_roles))
        c.execute("PRAGMA user_version = 11")

    conn.commit()
    conn.close()

# ──────────────────────────────── TEMPLATES ───────────────────────────────────

def get_template(rule_code, display_name):
    today_str = datetime.now().strftime("%d/%m/%Y")
    t = {
        "BC_DAU_CA": f"""Báo cáo đầu ca ngày {today_str} — {display_name}
Ca LV: P___  |  Vị trí: EC

I/ Phát sinh doanh thu dự kiến:
  - DT hôm nay: ___K  |  Gọi dự kiến: ___ cuộc
  - KH hẹn check-in: ___  |  KH mới tiếp cận: ___

II/ Timeline làm việc:
  ___h - ___h : ___
  ___h - ___h : ___
  ___h - ___h : Telesale, BC + check sổ
  ___h - ___h : ___

III/ Cam kết:
  Cuộc gọi: ___ | DT mục tiêu: ___K | Check-in: ___""",

        "BC_CUOI_CA": f"""Báo cáo cuối ca ngày {today_str} — {display_name}

🎯 CAM KẾT vs KẾT QUẢ:
  Cuộc gọi:  cam kết ___ / thực tế ___
  Doanh số:  cam kết ___K / thực tế ___K
  Check-in:  cam kết ___ / thực tế ___
  Cọc nhổ:  ___

TIMELINE THỰC TẾ:
  ___h - ___h : ___

RÚT KINH NGHIỆM HÔM NAY:
  - ___

CAM KẾT NGÀY MAI:
  Gọi: ___ cuộc | KH trọng tâm: ___

Chúc thầy cô ngủ ngon! Em cam kết lên bill trong tuần.""",

        "CHI_SO_NGAY": f"""Chỉ số ngày {today_str} — {display_name}

  Cuộc gọi >60s    : ___
  Doanh thu mới     : ___K
  KH Check-in tại CN: ___
  Cọc nhổ           : ___
  KH mới tiếp cận   : ___
  Data mới FB/Zalo  : ___""",

        "KHTN_DAILY": f"""Cập nhật KHTN chặng — {display_name} — {today_str}

KH 1:  Tên/SĐT: ___ | Lớp: ___ | Trạng thái: ___ | Bước tiếp: ___ | Hẹn: ___
KH 2:  Tên/SĐT: ___ | Lớp: ___ | Trạng thái: ___ | Bước tiếp: ___ | Hẹn: ___
KH 3:  Tên/SĐT: ___ | Lớp: ___ | Trạng thái: ___ | Bước tiếp: ___ | Hẹn: ___""",

        "BC_CHANG_2": f"""Báo cáo Chặng 2 — {display_name}
🌱 MỤC TIÊU CHẶNG 2: ___K / ___ tháng

Thứ 6 (___/___):
  KH 1: [Tên] — [Tháng dự chốt] — [Số tiền] — [Thông tin]
  KH 2: ___

Thứ 7 (___/___):
  KH 1: ___

Chủ Nhật (___/___):
  KH 1: ___

🌱 GIẢI PHÁP: ___ cuộc/ngày + theo dõi lịch hẹn PH
📌 {display_name} cam kết cố gắng thực hiện mục tiêu 3 ngày cuối tuần.""",

        "BC_NHAN_NHAN_TUAN": f"""Báo cáo tuần ___ tháng ___ — {display_name}

1. KẾT QUẢ TUẦN VỪA:
  + Cuộc gọi: ___  |  PH tiếp cận: ___
  + Cọc phát sinh: ___ tháng  |  DT phát sinh: ___K
  + % DT hiện tại: ___%
  + Vướng mắc: ___  |  Giải pháp: ___
  + Đề xuất hỗ trợ: ___

2. MỤC TIÊU TUẦN TỚI:
  Chặng 1 (T2-T5):
    [Tên KH] — [Số tháng] — [Số tiền] — [Thông tin]
  Chặng 2 (T6-CN):
    [Tên KH] — [Số tháng] — [Số tiền] — [Thông tin]

{display_name} cam kết bổ sung ___ cuộc gọi/ngày.""",

        "MT_TUAN": f"""Mục tiêu tuần ___ tháng ___ — {display_name}

  Chỉ tiêu DT tuần: ___K / ___ tháng
  Chỉ tiêu gọi: ___ cuộc
  KH Chặng 1 (T2-T5):
    1. [Tên] — [Lớp] — [Dự kiến]
    2. ___
  KH Chặng 2 (T6-CN):
    1. ___
    2. ___
  Kế hoạch sự kiện: ___""",

        "EBOOK": f"""Báo cáo Ebook tháng ___ — {display_name}

  Số EB hoàn thành: ___ / 7
  Chi tiết:
    1. ___  2. ___  3. ___
  Màn hình chụp: [link hoặc mô tả]
  Nhân sự còn thiếu: ___""",

        "BOOTH_PLAN": f"""Báo cáo BOOTH — {display_name} — {today_str}

  Địa điểm: ___  |  Thời gian: ___h - ___h
  Nhân sự: ___   |  KH tiếp cận: ___
  QR quét: ___   |  Data thu: ___
  Kết quả: ___   |  Đề xuất lần sau: ___""",

        "QR_ZALO": f"""Báo cáo QR Zalo — Tháng ___ — {display_name}

  Tổng lượt quét: ___ / 70
  Tuần 1: ___  Tuần 2: ___  Tuần 3: ___  Tuần 4: ___
  Kênh: Booth / SK / Tại CN
  Đề xuất tăng SL: ___""",

        "STEAM_PLAN": f"""Kế hoạch STEAM tuần ___ — {display_name}

  Pre School (~3 tuổi): Ngày ___ | Địa điểm ___ | Phụ trách ___ | KH mới: ___
  Kindy (~5 tuổi):      Ngày ___ | Địa điểm ___ | Phụ trách ___ | KH mới: ___
  Kids (~6 tuổi):       Ngày ___ | Địa điểm ___ | Phụ trách ___ | KH mới: ___""",
    }
    return t.get(rule_code, "Điền nội dung báo cáo tại đây...")

# ────────────────────────────────── UTILS ─────────────────────────────────────

def get_today(): return datetime.now().strftime("%Y-%m-%d")
def get_ym():    return datetime.now().strftime("%Y-%m")
def get_now_time(): return datetime.now().strftime("%H:%M")

def get_branch_setting(key, default=""):
    conn = get_conn()
    c = conn.cursor()
    row = c.execute("SELECT value FROM app_settings WHERE key=?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default

def set_branch_setting(key, value):
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT INTO app_settings(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))
    conn.commit()
    conn.close()

# ═══════════════ BỘ LUẬT DEADLINE (quy chế chốt 28/09/2026) ═══════════════
# Báo cáo tuần: gắn với NGÀY HẠN của tuần đó (T5 hoặc CN), bắt buộc kể cả OFF
WEEKLY_DUE = {"BC_CHANG_2": (3, "21:30"), "MT_TUAN": (6, "21:30"), "BC_NHAN_NHAN_TUAN": (6, "21:30")}
# Báo cáo ngày: chỉ bắt buộc khi có đi làm (ca OFF → để trống, không phạt)
DAILY_CODES = ("BC_DAU_CA", "CHI_SO_NGAY", "BC_CUOI_CA", "KHTN_DAILY", "KHTN_PHOTO_1630")
CUOI_CA_HAN_CHOT = "22:00"   # nộp ngay sau ca; hạn phạt muộn nhất 22:00
KHTN_HAN_CHOT    = "08:30"   # KHTN phải xong trước 08:30 mỗi sáng

def _to_date(d):
    if d is None: return datetime.now().date()
    if isinstance(d, str): return datetime.strptime(d, "%Y-%m-%d").date()
    return d

def period_date(code, d=None):
    """Ngày mà báo cáo được tính vào. Báo cáo tuần → ngày hạn của tuần chứa d."""
    d = _to_date(d)
    if code in WEEKLY_DUE:
        monday = d - pd.Timedelta(days=d.weekday())
        return (monday + pd.Timedelta(days=WEEKLY_DUE[code][0])).strftime("%Y-%m-%d")
    return d.strftime("%Y-%m-%d")

def get_shift_ca(uid, date_str):
    conn = get_conn()
    row = conn.execute("SELECT ca FROM work_shifts WHERE shift_date=? AND user_id=?", (date_str, uid)).fetchone()
    conn.close()
    return row["ca"] if row else None

def get_deadline(code, uid, date_str=None):
    """Trả 'HH:MM' nếu việc này bắt buộc với người này vào ngày đó; None nếu không bắt buộc (OFF)."""
    date_str = date_str or get_today()
    if code in WEEKLY_DUE:
        return WEEKLY_DUE[code][1]
    if code in DAILY_CODES:
        ca = get_shift_ca(uid, date_str)
        if ca == "OFF":
            return None
        if code == "BC_DAU_CA":
            return (CA_DEFS.get(ca, ("09:00", ""))[0] or "09:00") if ca else "09:00"
        return {"CHI_SO_NGAY": "21:00", "BC_CUOI_CA": CUOI_CA_HAN_CHOT,
                "KHTN_DAILY": KHTN_HAN_CHOT, "KHTN_PHOTO_1630": "16:30"}[code]
    conn = get_conn()
    row = conn.execute("SELECT deadline_time FROM rules WHERE code=?", (code,)).fetchone()
    conn.close()
    return row["deadline_time"] if row else "23:59"

def is_past_deadline(date_str, deadline, now=None):
    if not deadline or deadline in ("23:59", "N/A", "THEO_CA"):
        return False
    now = now or datetime.now()
    return now > datetime.strptime(f"{date_str} {deadline}", "%Y-%m-%d %H:%M")

def sweep_missing_penalties():
    """Ghi phạt KHÔNG NỘP cho các kỳ đã qua (chỉ ngày trước hôm nay → không trùng với phạt nộp trễ).
    Chạy mỗi lần mở app, không ghi trùng nhờ bảng penalty_sweep. Chỉ áp dụng EC.
    Báo cáo ngày: chỉ xét ngày ĐÃ có lịch ca và không OFF. Báo cáo tuần: xét mọi tuần."""
    conn = get_conn()
    c = conn.cursor()
    start = c.execute("SELECT value FROM app_settings WHERE key='sweep_start'").fetchone()
    if not start:
        conn.close(); return
    d = datetime.strptime(start["value"], "%Y-%m-%d").date()
    today = datetime.now().date()
    ecs = c.execute("SELECT id FROM users WHERE role='EC'").fetchall()
    rules = {r["code"]: r for r in c.execute("SELECT code, rule_name, penalty_amount FROM rules")}
    while d < today:
        dstr = d.strftime("%Y-%m-%d")
        codes = [k for k in ("BC_DAU_CA", "CHI_SO_NGAY", "BC_CUOI_CA", "KHTN_DAILY")]
        codes += [k for k, (wd, _) in WEEKLY_DUE.items() if wd == d.weekday()]
        for u in ecs:
            ca_row = c.execute("SELECT ca FROM work_shifts WHERE shift_date=? AND user_id=?", (dstr, u["id"])).fetchone()
            for code in codes:
                if code in DAILY_CODES and (not ca_row or ca_row["ca"] == "OFF"):
                    continue
                rule = rules.get(code)
                if not rule or (rule["penalty_amount"] or 0) <= 0:
                    continue
                if c.execute("SELECT 1 FROM reports WHERE user_id=? AND rule_code=? AND report_date=?", (u["id"], code, dstr)).fetchone():
                    continue
                try:
                    c.execute("INSERT INTO penalty_sweep(user_id, rule_code, period_date) VALUES(?,?,?)", (u["id"], code, dstr))
                except sqlite3.IntegrityError:
                    continue   # đã ghi phạt kỳ này rồi
                c.execute("INSERT INTO penalties(user_id,report_id,amount,reason,penalty_date) VALUES(?,?,?,?,?)",
                          (u["id"], None, rule["penalty_amount"], f"KHÔNG NỘP — {rule['rule_name']} ({d.strftime('%d/%m/%Y')})", dstr))
        d += pd.Timedelta(days=1)
    conn.commit()
    conn.close()

STATUS_COLORS = {
    "done_ontime": "🟢", "done_late": "🔴",
    "done_partial": "🟡", "pending": "⚪", "overdue": "🔴"
}

def get_report_status(user_id, rule_code, report_date, deadline=None):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT submitted_at, is_late, giai_trinh FROM reports WHERE user_id=? AND rule_code=? AND report_date=?",
              (user_id, rule_code, report_date))
    row = c.fetchone()
    if not row:
        c.execute("SELECT deadline_time FROM rules WHERE code=?", (rule_code,))
        rule = c.fetchone()
        conn.close()
        dl = deadline or (rule["deadline_time"] if rule else None)
        if is_past_deadline(report_date, dl):
            return "overdue"
        return "pending"
    conn.close()
    if row["is_late"] == 1: return "done_late"
    if row["giai_trinh"] and len(row["giai_trinh"]) > 0: return "done_partial"
    return "done_ontime"

def time_until(deadline_str, date_str=None):
    if not deadline_str or deadline_str in ("23:59","N/A","THEO_CA"): return ""
    now = datetime.now()
    deadline_dt = datetime.strptime(f"{date_str or now.strftime('%Y-%m-%d')} {deadline_str}", "%Y-%m-%d %H:%M")
    total_mins = int((deadline_dt - now).total_seconds() / 60)
    if total_mins < 0:
        return f"🔴 QUÁ GIỜ {abs(total_mins)} phút"
    if total_mins < 60:
        return f"⚡ Còn {total_mins} phút"
    if total_mins >= 1440:
        return f"⏳ Hạn {deadline_dt.strftime('%H:%M %d/%m')}"
    return f"⏳ Còn {total_mins//60}h {total_mins%60}p"

def get_duty_assignee(duty_code, ym):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT u.display_name, u.id FROM duty_assignments da JOIN users u ON da.user_id=u.id WHERE da.year_month=? AND da.duty_code=?", (ym, duty_code))
    row = c.fetchone()
    conn.close()
    return row

def is_my_duty(duty_code, user_id, ym):
    assignee = get_duty_assignee(duty_code, ym)
    if assignee and assignee["id"] == user_id:
        return True
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT fixed_duty FROM users WHERE id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    if not row or not row["fixed_duty"]:
        return False
    return duty_code in [d.strip() for d in (row["fixed_duty"] or "").split(",") if d.strip()]

def get_peer_for_checker(checker_id, ym):
    """Lấy người mà checker_id phải check hôm nay"""
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT u.id, u.display_name FROM peer_assignments pa JOIN users u ON pa.checkee_id=u.id WHERE pa.year_month=? AND pa.checker_id=?", (ym, checker_id))
    row = c.fetchone()
    conn.close()
    return row

def get_peer_check_status(checker_id, checkee_id, check_date, check_type):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT result, note, checked_at FROM peer_checks WHERE checker_id=? AND checkee_id=? AND check_date=? AND check_type=?",
              (checker_id, checkee_id, check_date, check_type))
    row = c.fetchone()
    conn.close()
    return row

# ── Màu thương hiệu Ocean Edu (lấy đúng từ logo thật) ────────────────────────
OE_BLUE_DARK  = "#2D3190"   # Xanh tím đậm (huy hiệu hải đăng + chữ EDU)
OE_BLUE_LIGHT = "#00AEEF"   # Xanh trời sáng (chữ OCEAN + vòng nguyệt quế)
OE_WHITE      = "#FFFFFF"

import base64, os as _os

def _img_to_b64(path, mime="png"):
    try:
        with open(path, "rb") as f:
            data = base64.b64encode(f.read()).decode()
        return f"data:image/{mime};base64,{data}"
    except Exception:
        return ""

# Dùng logo JPG chị cung cấp (màu chuẩn, đầy đủ)
_LOGO_SRC = _img_to_b64(_os.path.join(_os.path.dirname(__file__), "logo_oe.jpg"), "jpeg")
# Fallback: logo PNG ngang
if not _LOGO_SRC:
    _LOGO_SRC = _img_to_b64(_os.path.join(_os.path.dirname(__file__), "logo.png"), "png")


st.set_page_config(
    page_title="OE BMT — Hệ Thống KPI",
    layout="wide",
    page_icon="🌊",
    menu_items={"About": "Ocean Edu Buôn Ma Thuột — Hệ thống quản trị KPI nội bộ"}
)


for k, v in [("logged_in",False),("username",""),("role",""),("user_id",None),("display_name","")]:
    if k not in st.session_state:
        st.session_state[k] = v

init_db()
if not st.session_state.get("_swept_" + datetime.now().strftime("%Y-%m-%d")):
    sweep_missing_penalties()
    st.session_state["_swept_" + datetime.now().strftime("%Y-%m-%d")] = True

# ─────────────────────────── LOGIN ────────────────────────────────────────────

def login():
    branch_name = get_branch_setting("branch_name", "Ocean Edu Buôn Ma Thuột")
    branch_pin = get_branch_setting("branch_pin", "OE2026")
    ym = get_ym()

    logo_img_html = f'<div style="background:white; border-radius:12px; padding:12px 20px; display:inline-block; box-shadow:0 4px 12px rgba(0,0,0,0.08); margin-bottom:12px;"><img src="{_LOGO_SRC}" style="max-height:85px; max-width:280px; object-fit:contain;"></div>' if _LOGO_SRC else ''
    st.markdown(f"""
    <div translate="no" style="text-align:center; padding: 20px 0 15px 0;">
        {logo_img_html}
        <h2 style="margin:8px 0 6px 0; font-weight:900; line-height:1.25;">
            <span style="display:block; color:#2D3190; font-size:1.65rem; letter-spacing:1px; white-space:nowrap;">OCEAN EDU</span>
            <span style="display:block; color:#00AEEF; font-size:1.35rem; letter-spacing:0.5px; white-space:nowrap; margin-top:2px;">BUÔN MA THUỘT</span>
        </h2>
        <div style="color:#64748b; font-size:0.95rem; font-weight:600; letter-spacing:0.5px;">HỆ THỐNG QUẢN TRỊ KPI & VẬN HÀNH PTS</div>
    </div>
    """, unsafe_allow_html=True)

    _, col_center, _ = st.columns([1, 1.8, 1])

    with col_center:
        conn_u = get_conn()
        c_u = conn_u.cursor()
        c_u.execute("SELECT id, username, display_name, role FROM users WHERE (is_active=1 OR is_active IS NULL) AND role NOT IN ('CM', 'cm_daotao') ORDER BY id")
        all_u = c_u.fetchall()
        conn_u.close()

        with st.form("clean_login_form"):
            st.markdown("#### 🔐 Đăng Nhập Hệ Thống")
            quick_user = st.selectbox(
                "Tài khoản nhân sự:",
                [u["username"] for u in all_u],
                format_func=lambda x: next((f"{u['display_name']}" for u in all_u if u['username']==x), x)
            )
            password = st.text_input("Mật khẩu:", type="password")

            if st.form_submit_button("Đăng Nhập", use_container_width=True, type="primary"):
                conn = get_conn()
                c = conn.cursor()
                c.execute("SELECT id, role, display_name, password FROM users WHERE username=?", (quick_user,))
                user = c.fetchone()
                if user and (user["password"] == password or user["password"] == hash_pw(password)):
                    is_def = (password == "123456" or user["password"] == "123456" or user["password"] == hash_pw("123456"))
                    if user["password"] == password and password != hash_pw(password):
                        c.execute("UPDATE users SET password=? WHERE id=?", (hash_pw(password), user["id"]))
                        conn.commit()
                    st.session_state.update({
                        "logged_in": True,
                        "user_id": user["id"],
                        "role": user["role"],
                        "username": quick_user,
                        "display_name": user["display_name"],
                        "is_default_password": is_def
                    })
                    conn.close()
                    st.rerun()
                else:
                    conn.close()
                    st.error("Mật khẩu không chính xác!")

# ─────────────────────────── SUBMIT HELPER ────────────────────────────────────

def submit_report(rule_code, rule_name, deadline, content, extra_kpi=None, giai_trinh="", de_xuat=""):
    today = period_date(rule_code)          # báo cáo tuần → ngày hạn T5/CN của tuần này
    now = get_now_time()
    user_id = st.session_state["user_id"]
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id FROM reports WHERE user_id=? AND rule_code=? AND report_date=?", (user_id, rule_code, today))
    if c.fetchone():
        st.warning(f"Bạn đã nộp '{rule_name}' cho kỳ này rồi!")
        conn.close()
        return False
    is_late = 1 if is_past_deadline(today, deadline) else 0
    kpi = extra_kpi or {}
    c.execute("""INSERT INTO reports(user_id,rule_code,report_date,content,kpi_cuoc_goi,kpi_doanh_thu,kpi_checkin,kpi_cocnho,giai_trinh,de_xuat,submitted_at,is_late)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
        (user_id, rule_code, today, content, kpi.get("cuoc_goi",0), kpi.get("doanh_thu",0),
         kpi.get("checkin",0), kpi.get("coc_nho",0), giai_trinh, de_xuat, now, is_late))
    report_id = c.lastrowid
    if is_late:
        c.execute("SELECT penalty_amount, rule_name FROM rules WHERE code=?", (rule_code,))
        rule = c.fetchone()
        if rule and rule["penalty_amount"] > 0:
            c.execute("INSERT INTO penalties(user_id,report_id,amount,reason,penalty_date) VALUES(?,?,?,?,?)",
                      (user_id, report_id, rule["penalty_amount"], f"NỘP TRỄ — {rule['rule_name']} — Nộp {now} {get_today()[8:]}/{get_today()[5:7]}, hạn {deadline}", get_today()))
    conn.commit()
    conn.close()
    if is_late:
        st.error(f"⚠️ Nộp TRỄ {now} (deadline {deadline})! Hệ thống đã ghi vi phạm.")
    else:
        st.success(f"✅ Đã nộp '{rule_name}' lúc {now}!")
    return True

# ─────────────────────────── DEADLINE TICKER ──────────────────────────────────

def render_deadline_ticker():
    uid = st.session_state["user_id"]
    ym = get_ym()
    weekday = datetime.now().weekday()

    today = get_today()
    daily_tasks = []
    for code, label in [("BC_DAU_CA","Đầu ca"),("KHTN_DAILY","KHTN"),("CHI_SO_NGAY","Chỉ số"),("BC_CUOI_CA","Cuối ca")]:
        dl = get_deadline(code, uid, today)
        if dl: daily_tasks.append((code, label, dl))
    for code, (wd, dl) in WEEKLY_DUE.items():
        if wd == weekday:
            daily_tasks.append((code, {"BC_CHANG_2":"Chặng 2","MT_TUAN":"MT Tuần","BC_NHAN_NHAN_TUAN":"Nhìn nhận tuần"}[code], dl))
    if not daily_tasks:
        return

    logo_html = f'<img src="{_LOGO_SRC}" style="height:48px;background:white;border-radius:6px;padding:4px 8px">' if _LOGO_SRC else "🌊"
    st.markdown(f"""<div translate="no" style="background:{OE_BLUE_DARK};padding:10px 20px;border-radius:10px;margin-bottom:12px;display:flex;align-items:center;gap:16px">
{logo_html}
<span style="color:{OE_WHITE};font-size:1rem;font-weight:700" translate="no">
Chi nhánh Buôn Ma Thuột &nbsp;|&nbsp; 📅 {datetime.now().strftime('%A, %d/%m/%Y')} &nbsp;|&nbsp; 🕐 {datetime.now().strftime('%H:%M')}
</span>
</div>""", unsafe_allow_html=True)


    st.markdown("#### ⏰ Lịch Báo Cáo Hôm Nay")
    cols = st.columns(min(len(daily_tasks), 4))
    for i, (code, name, dl) in enumerate(daily_tasks):
        pdate = period_date(code)
        status = get_report_status(uid, code, pdate, dl)
        col = cols[i % 4]
        cd = time_until(dl, pdate)
        if "done" in status:
            bg = "#c6efce" if status == "done_ontime" else "#ffeb9c"
            label = "✅ Đã nộp"
        elif status == "overdue":
            bg = "#ffc7ce"
            label = cd
        else:
            bg = "#f0f8ff"
            label = cd
        col.markdown(f"""<div style="background:{bg};border-radius:8px;padding:8px 10px;margin:3px 0;border-left:4px solid {OE_BLUE_DARK}">
<div style="font-weight:700;font-size:0.82rem">{name}</div>
<div style="font-size:0.73rem;color:#555">Deadline: <b>{dl}</b></div>
<div style="font-size:0.8rem;font-weight:600;color:#d62728">{label}</div>
</div>""", unsafe_allow_html=True)


# ─────────────────────────── MY KPI DASHBOARD ─────────────────────────────────

def render_my_kpi(uid, name, ym):
    st.subheader(f"📊 KPI Của Tôi — {name} — Tháng {datetime.now().strftime('%m/%Y')}")

    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM monthly_targets WHERE year_month=? AND user_id=?", (ym, uid))
    my_target = c.fetchone()

    if not my_target:
        st.warning("Chưa có chỉ tiêu tháng này. BM/ATL vào 'Lập Kế Hoạch Tháng' để nhập.")
    else:
        dt_pct = (my_target["actual_doanh_thu"] / my_target["target_doanh_thu"] * 100) if my_target["target_doanh_thu"] > 0 else 0
        
        # Chỉ tiêu cuộc gọi >60s: chuẩn 488 cuộc/tháng (20 cuộc/ngày trừ 6 ngày OFF)
        goi_target = (my_target["target_cuoc_goi_thang"] if ("target_cuoc_goi_thang" in my_target.keys() and my_target["target_cuoc_goi_thang"]) else None) or 488
        
        # Thực tế cuộc gọi tích lũy từ báo cáo trong tháng
        c.execute("SELECT SUM(kpi_cuoc_goi) as tong FROM reports WHERE user_id=? AND rule_code='CHI_SO_NGAY' AND report_date LIKE ?", (uid, ym + '%'))
        rep_calls = c.fetchone()["tong"] or 0
        actual_calls = max((my_target["actual_cuoc_goi"] if my_target else 0) or 0, rep_calls)
        calls_pct = (actual_calls / goi_target * 100) if goi_target > 0 else 0

        # Đếm số ngày đi làm đã qua trong tháng (trừ những ngày OFF)
        c.execute("SELECT COUNT(*) FROM work_shifts WHERE user_id=? AND shift_date LIKE ? AND shift_date <= ? AND ca != 'OFF'", (uid, ym + '%', get_today()))
        w_days_so_far = c.fetchone()[0] or 0
        exp_calls_so_far = min(goi_target, w_days_so_far * 20)

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Doanh Thu",
                    f"{my_target['actual_doanh_thu']:,.0f}K",
                    f"{dt_pct:.1f}% / Chỉ tiêu {my_target['target_doanh_thu']:,.0f}K")
        col2.metric("Cuộc Gọi >60s Tích Lũy",
                    f"{actual_calls:,} / {goi_target:,}",
                    f"{calls_pct:.1f}% (Cần đạt: {exp_calls_so_far}c)")
        is_exempt_kpi = (dt_pct >= 90.0)
        if is_exempt_kpi:
            st.caption(f"🎉 **BẠN ĐÃ ĐƯỢC MIỄN ĐỊNH MỨC CUỘC GỌI:** Doanh thu tháng đã đạt **{dt_pct:.1f}%** (≥90%). Bạn không bị phạt hay kiểm soát định mức cuộc gọi.")
        else:
            st.caption(f"📌 **Quy chế Cuộc Gọi >60s:** Định mức **20 cuộc/ngày đi làm** (Tổng **{goi_target} cuộc/tháng** trừ 6 ngày OFF). Lũy kế đến hôm nay ({w_days_so_far} ngày làm): **{exp_calls_so_far} cuộc**. *Miễn định mức cuộc gọi khi đạt ≥90% doanh số.*")
        col3.metric("Check-in Lần Đầu",
                    f"{my_target['actual_checkin_landau']}",
                    f"/ Chỉ tiêu {my_target['target_checkin_landau']}")
        col4.metric("Check-in Sự Kiện",
                    f"{my_target['actual_checkin_sk']}",
                    f"/ Chỉ tiêu {my_target['target_checkin_sk']}")

        # Progress bar
        st.markdown("---")
        st.markdown(f"**Tiến độ Doanh Thu:** {dt_pct:.1f}%")
        st.progress(min(dt_pct / 100, 1.0))
        if dt_pct < 50:
            st.error("🚨 Dưới 50% — Cần hành động ngay!")
        elif dt_pct < 80:
            st.warning("⚠️ Dưới 80% — Cần đẩy mạnh!")
        elif dt_pct >= 100:
            st.success("🏆 Đạt chỉ tiêu! Xuất sắc!")
        else:
            st.info(f"✅ Đang tiến triển tốt — Còn {100-dt_pct:.1f}% nữa là đạt!")

    st.markdown("---")

    # ── BẢNG SO SÁNH TOÀN TEAM ─────────────────────────────────────────────────
    st.subheader("📋 So Sánh Toàn Team (Chỉ số tháng này)")
    c.execute("""SELECT mt.*, u.display_name FROM monthly_targets mt
                 JOIN users u ON mt.user_id=u.id WHERE mt.year_month=? AND u.role NOT IN ('CM', 'cm_daotao')
                 ORDER BY mt.actual_doanh_thu DESC""", (ym,))
    all_targets = c.fetchall()
    conn.close()

    if all_targets:
        rows = []
        for t in all_targets:
            dt_p = (t["actual_doanh_thu"] / t["target_doanh_thu"] * 100) if t["target_doanh_thu"] > 0 else 0
            warn = "🚨 <50%" if dt_p < 50 else ("⚠️ <80%" if dt_p < 80 else "🏆 Đạt!")
            is_me = " 👈" if t["user_id"] == uid else ""
            rows.append({
                "Nhân sự": t["display_name"] + is_me,
                "Vị trí": t["position"],
                "Chỉ tiêu DT (K)": f"{t['target_doanh_thu']:,.0f}",
                "Thực tế DT (K)": f"{t['actual_doanh_thu']:,.0f}",
                "% DT": f"{dt_p:.1f}%",
                "Cảnh báo": warn,
                "Gọi thực tế": t["actual_cuoc_goi"],
                "Check-in LD": f"{t['actual_checkin_landau']}/{t['target_checkin_landau']}",
            })
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
        st.caption("👈 = bạn | Dữ liệu do BM/ATL cập nhật theo tuần")
    else:
        st.info("Chưa có dữ liệu chỉ tiêu tháng này.")

    st.markdown("---")

    # ── LỊCH SỬ CHỈ SỐ NGÀY ───────────────────────────────────────────────────
    st.subheader("📅 Lịch Sử Chỉ Số 7 Ngày Gần Nhất Của Tôi")
    conn2 = get_conn()
    c2 = conn2.cursor()
    c2.execute("""SELECT report_date, kpi_cuoc_goi, kpi_doanh_thu, kpi_checkin, giai_trinh
                  FROM reports WHERE user_id=? AND rule_code='CHI_SO_NGAY'
                  ORDER BY report_date DESC LIMIT 7""", (uid,))
    history = c2.fetchall()
    conn2.close()

    if history:
        df_hist = pd.DataFrame([dict(r) for r in history])
        df_hist.columns = ["Ngày", "Cuộc gọi", "Doanh thu (K)", "Check-in", "Giải trình (nếu thiếu KPI)"]
        st.dataframe(df_hist, hide_index=True, use_container_width=True)
    else:
        st.info("Chưa có dữ liệu chỉ số ngày.")

# ─────────────────────────── PEER CHECKIN ─────────────────────────────────────

def render_peer_checkin(uid, name):
    ym = get_ym()
    today = get_today()

    st.markdown("---")
    st.subheader("🔄 Vòng Tròn Kiểm Tra Đồng Đội")
    peer = get_peer_for_checker(uid, ym)

    if not peer:
        st.info("Chưa được phân công kiểm tra ai tháng này. Admin vào 'Cấu Hình → Vòng Tròn Kiểm Tra' để thiết lập.")
        return

    st.markdown(f"""<div style="background:#e8f4fd;border-radius:10px;padding:14px 18px;margin-bottom:16px;border-left:5px solid #0070C0">
<b>🔍 Tháng này bạn kiểm tra:</b> <span style="font-size:1.1rem;color:#0070C0;font-weight:700">{peer['display_name']}</span><br>
<span style="color:#555;font-size:0.85rem">Điền kết quả kiểm tra của bạn bên dưới. Bạn không thể tự kiểm tra cho chính mình.</span>
</div>""", unsafe_allow_html=True)

    check_types = [
        ("MKT_FB_ZALO",  "Đăng bài FB + Zalo (1 bài/ngày)",      "Có link bài / chụp màn hình không?"),
        ("TUONG_TAC",    "Tương tác nhóm (Like + phản hồi chỉ đạo)", "Có thả tim + phản hồi đầy đủ không?"),
        ("BC_DAU_CA",    "Báo cáo đầu ca trước giờ vào ca",             "Có báo cáo đúng giờ không?"),
        ("BC_CUOI_CA",   "Báo cáo cuối ca trước 21:00",           "Có báo cáo đúng giờ không?"),
    ]

    for check_type, check_name, hint in check_types:
        existing = get_peer_check_status(uid, peer["id"], today, check_type)
        st.markdown(f"**{check_name}**")
        st.caption(hint)
        if existing:
            result_icon = "✅ ĐẠT" if existing["result"] == 1 else "❌ CHƯA ĐẠT"
            st.success(f"Đã kiểm tra lúc {existing['checked_at']}: **{result_icon}** — {existing['note']}")
        else:
            with st.form(f"peer_check_{check_type}_{uid}"):
                result = st.radio("Kết quả kiểm tra:", ["✅ ĐẠT — Đã thực hiện đúng quy định",
                                                          "❌ CHƯA ĐẠT — Chưa thực hiện / Trễ / Thiếu"],
                                  horizontal=True)
                link_ev = st.text_input("Link bằng chứng (link bài đăng, ảnh chụp...)", placeholder="Có thể bỏ trống")
                note_ev = st.text_input("Ghi chú thêm (Trễ mấy phút? Thiếu gì?)", placeholder="")
                if st.form_submit_button(f"Xác Nhận Kiểm Tra — {check_name}"):
                    result_val = 1 if result.startswith("✅") else 0
                    conn = get_conn()
                    cur = conn.cursor()
                    cur.execute("""INSERT INTO peer_checks
                        (checker_id, checkee_id, check_date, check_type, result, link_evidence, note, checked_at)
                        VALUES(?,?,?,?,?,?,?,?)
                        ON CONFLICT(checker_id, checkee_id, check_date, check_type) DO UPDATE SET
                        result=excluded.result, link_evidence=excluded.link_evidence,
                        note=excluded.note, checked_at=excluded.checked_at""",
                        (uid, peer["id"], today, check_type, result_val, link_ev, note_ev,
                         datetime.now().strftime("%H:%M")))
                    conn.commit()
                    conn.close()
                    st.success("Đã ghi nhận kết quả kiểm tra!")
                    st.rerun()

# ─────────────────────────── FORM HELPER ──────────────────────────────────────

def make_form(rule_code, rule_name, deadline, uid, name, extra_fields=None):
    today = period_date(rule_code)
    status = get_report_status(uid, rule_code, today, deadline)
    icon = STATUS_COLORS.get(status, "⚪")
    cd = time_until(deadline, today)
    st.markdown(f"**{icon} {rule_name}** — Deadline: `{deadline}` {cd}")

    if "done" in status:
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT content, submitted_at, is_late FROM reports WHERE user_id=? AND rule_code=? AND report_date=?",
                  (uid, rule_code, today))
        row = c.fetchone()
        conn.close()
        if row:
            tag = "🔴 Nộp trễ" if row["is_late"] else "🟢 Đúng hạn"
            st.success(f"Đã nộp lúc {row['submitted_at']} — {tag}")
            with st.expander("Xem nội dung đã nộp"):
                st.text(row["content"])
        return

    with st.form(f"form_{rule_code}_{uid}"):
        st.caption("📋 Điền vào chỗ ___ theo số liệu thực tế — mẫu đã có sẵn:")
        content = st.text_area("Nội dung báo cáo:", value=get_template(rule_code, name), height=260)

        giai_trinh, de_xuat, extra_kpi = "", "", {}

        if extra_fields == "kpi":
            st.caption("Điền nhanh chỉ số để hệ thống tính KPI:")
            c1, c2, c3, c4 = st.columns(4)
            cuoc_goi = c1.number_input("Cuộc gọi >60s", min_value=0, step=1)
            doanh_thu = c2.number_input("Doanh thu (K)", min_value=0, step=100)
            checkin = c3.number_input("KH Check-in", min_value=0, step=1)
            coc_nho = c4.number_input("Cọc nhổ", min_value=0, step=1)
            extra_kpi = {"cuoc_goi": cuoc_goi, "doanh_thu": doanh_thu, "checkin": checkin, "coc_nho": coc_nho}
            if st.checkbox("Tôi CHƯA hoàn thành chỉ tiêu hôm nay"):
                giai_trinh = st.text_area("Giải trình (BẮT BUỘC):", placeholder="Vì sao chưa đạt?")
                de_xuat = st.text_area("Đề xuất bù:", placeholder="Ngày mai tôi sẽ...")

        if st.form_submit_button(f"Gửi — {rule_name}", use_container_width=True):
            submit_report(rule_code, rule_name, deadline, content, extra_kpi, giai_trinh, de_xuat)
            st.rerun()

# ─────────────────────────── EBOOK & QR TRACKER ───────────────────────────────

def get_ebook_qr_stats(uid, ym):
    """Lấy chỉ tiêu + thực tế Ebook và QR của 1 người trong tháng"""
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT target_ebook, target_qr FROM ebook_qr_targets WHERE year_month=? AND user_id=?", (ym, uid))
    tgt = c.fetchone()
    c.execute("SELECT COUNT(*) as cnt FROM ebook_qr_records WHERE user_id=? AND year_month=? AND type='ebook'", (uid, ym))
    actual_ebook = c.fetchone()["cnt"]
    c.execute("SELECT COUNT(*) as cnt FROM ebook_qr_records WHERE user_id=? AND year_month=? AND type='qr'", (uid, ym))
    actual_qr = c.fetchone()["cnt"]
    conn.close()
    target_ebook = tgt["target_ebook"] if tgt else 0
    target_qr    = tgt["target_qr"]    if tgt else 0
    return target_ebook, target_qr, actual_ebook, actual_qr


def render_ebook_qr_tracker(uid, name, ym):
    """Card Ebook & QR trong trang daily của EC"""
    target_ebook, target_qr, actual_ebook, actual_qr = get_ebook_qr_stats(uid, ym)

    if target_ebook == 0 and target_qr == 0:
        st.warning("⚠️ Chưa có chỉ tiêu Ebook/QR tháng này — liên hệ BM hoặc ATL để phân bổ.")
        return

    remaining_ebook = max(0, target_ebook - actual_ebook)
    remaining_qr    = max(0, target_qr - actual_qr)
    ebook_done = actual_ebook >= target_ebook
    qr_done    = actual_qr    >= target_qr

    # ── Thẻ tổng quan ──────────────────────────────────────────────────────────
    col1, col2 = st.columns(2)

    for col, label, emoji, actual, target, remaining, done, typ in [
        (col1, "Ebook", "📚", actual_ebook, target_ebook, remaining_ebook, ebook_done, "ebook"),
        (col2, "QR Zalo", "📲", actual_qr, target_qr, remaining_qr, qr_done, "qr"),
    ]:
        color = OE_BLUE_DARK if done else "#D32F2F"
        bg    = "#f0f4ff" if done else "#fff5f5"
        pct   = min(actual / target * 100, 100) if target > 0 else 0
        bar_w = int(pct)
        status_txt = "✅ Hoàn thành!" if done else f"🔴 Còn thiếu <b>{remaining}</b> — Phạt <b>{remaining*50000:,}đ</b> nếu không xong"
        col.markdown(f"""<div style="background:{bg};border-left:5px solid {color};border-radius:10px;padding:14px 18px;margin-bottom:6px">
<span style="font-size:0.9rem;font-weight:700;color:#333">{emoji} {label} Tháng Này</span><br>
<span style="font-size:2.4rem;font-weight:900;color:{color}">{actual}</span>
<span style="color:#666;font-size:0.95rem"> / {target}</span><br>
<div style="background:#e0e0e0;border-radius:4px;height:7px;margin:6px 0">
  <div style="background:{color};border-radius:4px;height:7px;width:{bar_w}%"></div>
</div>
<small>{status_txt}</small>
</div>""", unsafe_allow_html=True)

    # ── Lịch sử SĐT đã nhập ────────────────────────────────────────────────────
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT type, phone_number, note, added_at FROM ebook_qr_records WHERE user_id=? AND year_month=? ORDER BY added_at DESC LIMIT 20", (uid, ym))
    recent = c.fetchall()
    conn.close()

    if recent:
        with st.expander(f"📋 Danh sách SĐT đã nộp ({len(recent)} gần nhất)"):
            for r in recent:
                icon = "📚" if r["type"] == "ebook" else "📲"
                st.markdown(f"`{r['added_at'][:10]}` {icon} **{r['phone_number']}** {('— ' + r['note']) if r['note'] else ''}")

    # ── Form nhập SĐT mới ──────────────────────────────────────────────────────
    st.markdown("**Nhập SĐT mới hoàn thành hôm nay:**")
    col_f1, col_f2 = st.columns([1, 1])

    with col_f1:
        with st.form("add_ebook_sdt"):
            st.caption("📚 Thêm SĐT Ebook")
            sdt_e = st.text_input("SĐT (Ebook)", placeholder="0901234567", label_visibility="collapsed")
            note_e = st.text_input("Ghi chú", placeholder="Tên PH, tên trường...", label_visibility="collapsed")
            if st.form_submit_button("➕ Thêm Ebook", use_container_width=True, type="primary" if not ebook_done else "secondary"):
                sdt_e = sdt_e.strip()
                if not sdt_e:
                    st.error("Nhập SĐT!")
                elif not sdt_e.replace(" ","").isdigit() or len(sdt_e.replace(" ","")) < 9:
                    st.error("SĐT không hợp lệ!")
                else:
                    conn2 = get_conn()
                    c2 = conn2.cursor()
                    c2.execute("SELECT u.display_name FROM ebook_qr_records r JOIN users u ON r.user_id=u.id WHERE r.type=? AND REPLACE(r.phone_number,' ','')=?", ("ebook", sdt_e.replace(" ","")))
                    _dup = c2.fetchone()
                    if _dup:
                        conn2.close()
                        st.error(f"SĐT này đã được ghi nhận trước đó bởi {_dup['display_name']} — không tính trùng.")
                    else:
                        c2.execute("INSERT INTO ebook_qr_records(user_id,year_month,type,phone_number,note,added_at) VALUES(?,?,?,?,?,?)",
                                   (uid, ym, "ebook", sdt_e, note_e, datetime.now().strftime("%Y-%m-%d %H:%M")))
                        conn2.commit()
                        conn2.close()
                        st.success(f"✅ Đã ghi nhận Ebook — {sdt_e}!")
                        st.rerun()

    with col_f2:
        with st.form("add_qr_sdt"):
            st.caption("📲 Thêm SĐT QR Zalo")
            sdt_q = st.text_input("SĐT (QR)", placeholder="0901234567", label_visibility="collapsed")
            note_q = st.text_input("Ghi chú", placeholder="Booth, SK, tại CN...", label_visibility="collapsed")
            if st.form_submit_button("➕ Thêm QR Zalo", use_container_width=True, type="primary" if not qr_done else "secondary"):
                sdt_q = sdt_q.strip()
                if not sdt_q:
                    st.error("Nhập SĐT!")
                elif not sdt_q.replace(" ","").isdigit() or len(sdt_q.replace(" ","")) < 9:
                    st.error("SĐT không hợp lệ!")
                else:
                    conn3 = get_conn()
                    c3 = conn3.cursor()
                    c3.execute("SELECT u.display_name FROM ebook_qr_records r JOIN users u ON r.user_id=u.id WHERE r.type=? AND REPLACE(r.phone_number,' ','')=?", ("qr", sdt_q.replace(" ","")))
                    _dup = c3.fetchone()
                    if _dup:
                        conn3.close()
                        st.error(f"SĐT này đã được ghi nhận trước đó bởi {_dup['display_name']} — không tính trùng.")
                    else:
                        c3.execute("INSERT INTO ebook_qr_records(user_id,year_month,type,phone_number,note,added_at) VALUES(?,?,?,?,?,?)",
                                   (uid, ym, "qr", sdt_q, note_q, datetime.now().strftime("%Y-%m-%d %H:%M")))
                        conn3.commit()
                        conn3.close()
                        st.success(f"✅ Đã ghi nhận QR — {sdt_q}!")
                        st.rerun()


# ─────────────────────────── DAILY CHECKLIST ──────────────────────────────────

# ── Links Google Sheets quan trọng ────────────────────────────────────────────
KHTN_SHEET_URL  = "https://docs.google.com/spreadsheets/d/1Y1gqXndsZHrnp5HbiREZrMcmDAGiCzwe6rBq0lzvxvM/edit?gid=2096388166#gid=2096388166"
STEAM_SHEET_URL = "https://docs.google.com/spreadsheets/d/15nKA3esX2kAdP9TBT4oWTNr9-Kef7SrmHQfB1zfQSyg/edit?gid=591678775#gid=591678775"


DAILY_TASKS_ALL = [
    # (rule_code, tên hiển thị, deadline, ghi chú bắt buộc, nhóm)
    # BC_DAU_CA dùng "DYN_SHIFT" → deadline được tra động theo ca làm việc của từng người
    ("BC_DAU_CA",       "Báo cáo Đầu Ca (Timeline + Cam kết)",        "DYN_SHIFT", True, "🌅 Đầu Ca"),
    ("CHI_SO_NGAY",     "Điền Chỉ Số Ngày (Cuộc gọi, DT, Check-in)", "21:00",     True, "📊 Chỉ Số"),
    ("BC_CUOI_CA",      "Báo cáo Cuối Ca (Kết quả + Rút kinh nghiệm)", "DYN_END", True, "🌙 Cuối Ca"),
    ("KHTN_DAILY",      "Cập nhật KHTN (trước 08:30 sáng)",            "08:30",     True, "👥 KH"),
    ("KHTN_PHOTO_1630", "📸 16h30 — Chụp ảnh KHTN → Báo cáo nhóm Zalo OE", "16:30", True, "👥 KH"),
]

WEEKLY_TASKS_MAP = {
    3: [("BC_CHANG_2", "Báo cáo Chặng 2 (Mục tiêu T6-T7-CN)", "21:30", True, "📅 Thứ 5")],
    6: [
        ("MT_TUAN",           "Mục tiêu Tuần Mới",                 "21:30", True, "📅 Chủ Nhật — bắt buộc cả khi OFF"),
        ("BC_NHAN_NHAN_TUAN", "Nhìn nhận Tuần cũ + MT Tuần mới",  "21:30", True, "📅 Chủ Nhật — bắt buộc cả khi OFF"),
    ],
}

PEER_TASKS_ALL = [
    ("MKT_BAIDANG_CHECK", "Kiểm tra đồng đội: Đăng bài FB + Zalo",      "23:59", "🔄 Peer"),
    ("TUONG_TAC_CHECK",   "Kiểm tra đồng đội: Tương tác nhóm (Like...)", "23:59", "🔄 Peer"),
]


def get_penalty_for_rule(rule_code):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT penalty_amount, deadline_time FROM rules WHERE code=?", (rule_code,))
    row = c.fetchone()
    conn.close()
    if row:
        return row["penalty_amount"], row["deadline_time"]
    return 0, "N/A"


def render_task_card(rule_code, task_name, deadline, is_mandatory, group_label, uid, name, extra_fields=None):
    """Render 1 card checklist với trạng thái + form bên trong"""
    today = period_date(rule_code)
    status = get_report_status(uid, rule_code, today, deadline)
    cd = time_until(deadline, today)
    penalty_amt, _ = get_penalty_for_rule(rule_code)

    # Màu card theo trạng thái
    if "done" in status:
        border_color = "#00B050"
        status_icon = "✅"
        status_label = "Đã nộp"
        bg = "#f0fff4"
    elif status == "overdue":
        border_color = "#FF0000"
        status_icon = "🔴"
        status_label = "Trễ hạn!"
        bg = "#fff5f5"
    else:
        now_h = int(datetime.now().strftime("%H"))
        dl_h = int(deadline.split(":")[0]) if ":" in deadline else 23
        if today == get_today() and dl_h - now_h <= 2 and status == "pending":
            border_color = "#FF6600"
            status_icon = "⚡"
            status_label = "Sắp deadline"
            bg = "#fff8f0"
        else:
            border_color = "#0070C0"
            status_icon = "⬜"
            status_label = "Chờ nộp"
            bg = "white"

    mandatory_tag = '<span style="background:#c00;color:white;font-size:0.68rem;padding:2px 6px;border-radius:3px;margin-left:6px">BẮT BUỘC</span>' if is_mandatory else ""
    penalty_tag = f'<span style="background:#ff6600;color:white;font-size:0.68rem;padding:2px 6px;border-radius:3px;margin-left:4px">Trễ: Phạt {penalty_amt:,}đ</span>' if penalty_amt > 0 else '<span style="background:#888;color:white;font-size:0.68rem;padding:2px 6px;border-radius:3px;margin-left:4px">Không phạt tiền</span>'

    # Header card (luôn hiện)
    st.markdown(f"""<div style="background:{bg};border-left:5px solid {border_color};border-radius:8px;padding:10px 16px;margin:6px 0">
<span style="font-size:1.05rem;font-weight:700">{status_icon} {task_name}</span>{mandatory_tag}{penalty_tag}<br>
<small>🏷️ {group_label} &nbsp;|&nbsp; ⏰ Deadline: <b>{deadline}</b> &nbsp;|&nbsp; {cd if "done" not in status else "✅ " + status_label}</small>
</div>""", unsafe_allow_html=True)

    # Nội dung form (mở khi chưa nộp, hiện kết quả khi đã nộp)
    if "done" in status:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT content, submitted_at, is_late, giai_trinh FROM reports WHERE user_id=? AND rule_code=? AND report_date=?",
                    (uid, rule_code, today))
        row = cur.fetchone()
        conn.close()
        if row:
            late_tag = "🔴 Nộp trễ" if row["is_late"] else "🟢 Đúng hạn"
            with st.expander(f"Xem nội dung đã nộp lúc {row['submitted_at']} — {late_tag}"):
                st.text(row["content"])
                if row["giai_trinh"]:
                    st.caption(f"Giải trình: {row['giai_trinh']}")
    else:
        # Hiện form nhập liệu trong expander
        with st.expander(f"📝 Nhấn để điền {task_name}", expanded=(status == "overdue")):
            if status == "overdue":
                st.warning(f"⏰ Đã quá hạn {deadline} — Vi phạm trễ hạn: {penalty_amt:,}đ. Vui lòng hoàn thành ngay:")

            with st.form(f"checklist_form_{rule_code}_{uid}"):
                content = st.text_area("Nội dung báo cáo:", value=get_template(rule_code, name), height=220)

                giai_trinh = ""
                de_xuat = ""
                extra_kpi = {}

                if extra_fields == "kpi":
                    st.markdown("**Điền nhanh chỉ số (hệ thống dùng để tổng hợp KPI):**")
                    
                    # Kiểm tra liên kết doanh số tháng để tự động miễn cuộc gọi
                    conn_ex = get_conn()
                    c_ex = conn_ex.cursor()
                    c_ex.execute("SELECT target_doanh_thu, actual_doanh_thu, target_cuoc_goi_thang FROM monthly_targets WHERE user_id=? AND year_month=?", (uid, get_ym()))
                    ex_tgt = c_ex.fetchone()
                    conn_ex.close()
                    
                    user_tgt_dt = ex_tgt["target_doanh_thu"] if ex_tgt else 0
                    user_act_dt = ex_tgt["actual_doanh_thu"] if ex_tgt else 0
                    user_dt_pct = (user_act_dt / user_tgt_dt * 100) if user_tgt_dt > 0 else 0
                    user_is_exempt = (user_dt_pct >= 90.0)

                    if user_is_exempt:
                        st.success(f"🎉 **BẠN ĐÃ HOÀN THÀNH {user_dt_pct:.1f}% DOANH SỐ THÁNG!** Theo quy chế chi nhánh, bạn được **TỰ ĐỘNG MIỄN ĐỊNH MỨC CUỘC GỌI** (Không bắt buộc gọi ≥20 cuộc, không tính trễ/thiếu).")
                    else:
                        st.caption(f"📌 **Định mức:** 20 cuộc >60s/ngày đi làm (Tháng 488 cuộc trừ 6 ngày OFF; BSA 120 cuộc). Đạt ≥90% Doanh số ➔ Tự động miễn gọi.")

                    c1, c2, c3, c4 = st.columns(4)
                    cuoc_goi = c1.number_input("Cuộc gọi >60s", min_value=0, step=1, help="Quy định tối thiểu 20 cuộc >60s/ngày đi làm (Miễn nếu đạt ≥90% doanh số)")
                    doanh_thu = c2.number_input("Doanh thu (K)", min_value=0, step=100)
                    checkin = c3.number_input("KH Check-in", min_value=0, step=1)
                    coc_nho = c4.number_input("Cọc nhỏ", min_value=0, step=1)
                    extra_kpi = {"cuoc_goi": cuoc_goi, "doanh_thu": doanh_thu, "checkin": checkin, "coc_nho": coc_nho}

                    ca_today = get_shift_ca(uid, today)
                    if ca_today != "OFF" and cuoc_goi < 20 and not user_is_exempt:
                        st.warning(f"⚠️ Hôm nay bạn gọi {cuoc_goi}/20 cuộc (chưa đạt định mức 20 cuộc >60s). Vui lòng điền giải trình và kế hoạch gọi bù bên dưới!")

                    st.markdown("---")
                    chua_dat = st.checkbox("⚠️ Hôm nay CHƯA hoàn thành chỉ tiêu")
                    if chua_dat:
                        giai_trinh = st.text_area("Giải trình (BẮT BUỘC khi tick ô trên):",
                                                   placeholder="Vì sao chưa đạt? Vướng mắc cụ thể?")
                        de_xuat = st.text_area("Cam kết bù / Đề xuất hỗ trợ:",
                                               placeholder="Ngày mai tôi sẽ... / Cần hỗ trợ...")

                if st.form_submit_button(f"✅ Xác Nhận Nộp — {task_name}", use_container_width=True, type="primary"):
                    if extra_fields == "kpi" and not content.strip():
                        st.error("Nội dung không được để trống!")
                    else:
                        ok = submit_report(rule_code, task_name, deadline, content, extra_kpi, giai_trinh, de_xuat)
                        if ok:
                            st.rerun()


def render_ec_daily(uid, name, ym):
    today = get_today()
    weekday = datetime.now().weekday()

    # ── Thanh tiến độ tổng quan ────────────────────────────────────────────────
    all_codes = [t[0] for t in DAILY_TASKS_ALL]
    weekly_extra = WEEKLY_TASKS_MAP.get(weekday, [])
    all_codes += [t[0] for t in weekly_extra]

    _is_off = get_shift_ca(uid, today) == "OFF"
    if _is_off:
        all_codes = [t[0] for t in weekly_extra]
    done_count = sum(1 for code in all_codes if "done" in get_report_status(uid, code, period_date(code)))
    total = len(all_codes)
    pct = done_count / total if total > 0 else 0

    if done_count == total:
        bar_color = "🏆 Hoàn thành tất cả!"
        bar_bg = "#00B050"
    elif pct >= 0.5:
        bar_color = f"⚡ {done_count}/{total} — Tiếp tục!"
        bar_bg = "#FF6600"
    else:
        bar_color = f"⬜ {done_count}/{total} — Cần hoàn thành!"
        bar_bg = "#0070C0"

    st.markdown(f"""<div style="background:{bar_bg};border-radius:10px;padding:10px 18px;margin-bottom:14px;color:white">
<b>📋 CHECKLIST HÔM NAY: {bar_color}</b>
<div style="background:rgba(255,255,255,0.3);border-radius:4px;height:8px;margin-top:6px">
<div style="background:white;border-radius:4px;height:8px;width:{int(pct*100)}%"></div>
</div>
</div>""", unsafe_allow_html=True)



    # ── Banner thông báo nhiệm vụ STEAM hôm nay ──────────────────────────────
    conn_st = get_conn()
    c_st = conn_st.cursor()
    c_st.execute("SELECT * FROM steam_schedule WHERE event_date=?", (today,))
    st_today = c_st.fetchall()
    conn_st.close()
    for s in st_today:
        a_ids = [x.strip() for x in (s["assigned_ec_ids"] or "").split(",") if x.strip()]
        if str(uid) in a_ids or "all" in a_ids:
            st.markdown(f"""
            <div style="background:#f3e5f5; border-left:6px solid #7b1fa2; border-radius:10px; padding:12px 18px; margin-bottom:14px;">
                <b style="color:#7b1fa2; font-size:1.05rem">🔬 HÔM NAY BẠN CÓ NHIỆM VỤ STEAM!</b><br>
                <span style="font-size:1rem; font-weight:700">{s['title']}</span> &nbsp;|&nbsp; 🕐 <b>{s['start_time']} – {s['end_time']}</b><br>
                📍 Địa điểm: <b>{s['location'] or s['school_name'] or 'Chi nhánh'}</b><br>
                📝 Ghi chú: {s['note'] or 'Vui lòng chuẩn bị giáo cụ và hỗ trợ học sinh đúng giờ.'}
            </div>
            """, unsafe_allow_html=True)

    # ── Tra ca hôm nay → resolve DYN deadline ─────────────────────────────────
    today = get_today()
    conn_ca = get_conn()
    cc = conn_ca.cursor()
    cc.execute("SELECT ca, start_time, end_time FROM work_shifts WHERE shift_date=? AND user_id=?",
               (today, uid))
    today_shift = cc.fetchone()
    conn_ca.close()

    dyn_ca   = today_shift["ca"]        if today_shift else None
    dyn_st   = (today_shift["start_time"] or CA_DEFS.get(dyn_ca,("09:00",""))[0]) if today_shift else None
    dyn_end  = (today_shift["end_time"]   or CA_END_TIME.get(dyn_ca,"21:00"))     if today_shift else None

    # Banner hiển thị ca hôm nay
    if today_shift and dyn_ca != "OFF":
        ca_color = {"P1":"#1B5E20","P2":"#0D47A1","P3":"#4A148C","P4":"#E65100"}.get(dyn_ca, "#2D3190")
        st.markdown(f"""<div style="background:{ca_color};color:white;border-radius:8px;padding:10px 18px;margin-bottom:10px;font-weight:700">
📅 Hôm nay: <span style="font-size:1.2rem">{dyn_ca}</span> &nbsp;|&nbsp;
⏰ Vào ca: {dyn_st} &nbsp;|&nbsp; Kết ca: {dyn_end} &nbsp;|&nbsp;
🔔 Deadline BC đầu ca: <u>{dyn_st}</u>
</div>""", unsafe_allow_html=True)
    elif today_shift and dyn_ca == "OFF":
        st.info("🏖️ Hôm nay bạn nghỉ (OFF) — không cần báo cáo ngày. Chúc bạn nghỉ ngơi vui vẻ!"
                + (" Riêng **báo cáo tuần hôm nay vẫn bắt buộc** (hạn 21:30)." if weekly_extra else ""))
        for rule_code, task_name, deadline, is_mandatory, group in weekly_extra:
            render_task_card(rule_code, task_name, deadline, is_mandatory, group, uid, name)
        return
    else:
        st.warning("⚠️ Chưa có lịch ca hôm nay — liên hệ Kế Toán để sắp lịch. Deadline BC Đầu Ca tạm tính: **09:00**")
        dyn_st  = "09:00"
        dyn_end = "?"

    # ── Checklist báo cáo ngày (BẮT BUỘC tất cả) ─────────────────────────────
    st.markdown("### 📋 Báo Cáo Ngày (Bắt Buộc Mọi Người)")
    for rule_code, task_name, deadline, is_mandatory, group in DAILY_TASKS_ALL:
        # Resolve deadline động
        if deadline == "DYN_SHIFT":
            real_deadline = dyn_st
        elif deadline == "DYN_END":
            real_deadline = CUOI_CA_HAN_CHOT
            group = f"🌙 Cuối Ca — nộp ngay sau kết ca {dyn_end} (hạn chót 22:00)"
        else:
            real_deadline = deadline
        render_task_card(rule_code, task_name, real_deadline, is_mandatory, group, uid, name,
                        extra_fields="kpi" if rule_code == "CHI_SO_NGAY" else None)

    # ── Checklist báo cáo theo thứ (T5, CN) ───────────────────────────────────
    if weekly_extra:
        st.markdown("---")
        st.markdown(f"### 📅 Báo Cáo Đặc Biệt Hôm Nay ({WEEKDAY_VN[weekday]})")
        for rule_code, task_name, deadline, is_mandatory, group in weekly_extra:
            render_task_card(rule_code, task_name, deadline, is_mandatory, group, uid, name)

    # ── Peer Check (kiểm tra đồng đội) ─────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 🔄 Kiểm Tra Đồng Đội (Peer Check)")
    render_peer_checkin(uid, name)

    # ── Duty tasks (nếu được phân công) ─────────────────────────────────────────
    duty_tasks = []
    if is_my_duty("EBOOK", uid, ym):
        duty_tasks.append(("EBOOK", "📚 Báo cáo Ebook (7 EB/nhân sự/tháng)", "23:59", False, "📚 Duty tháng"))
    if is_my_duty("BOOTH_PLAN", uid, ym):
        duty_tasks.append(("BOOTH_PLAN", "🏪 Báo cáo BOOTH", "23:59", False, "🏪 Duty tháng"))
    if is_my_duty("QR_ZALO", uid, ym):
        duty_tasks.append(("QR_ZALO", "📲 Báo cáo QR Zalo", "23:59", False, "📲 Duty tháng"))
    if is_my_duty("STEAM_PLAN", uid, ym):
        duty_tasks.append(("STEAM_PLAN", "🔬 Kế hoạch STEAM", "21:00", False, "🔬 Duty tuần"))

    if duty_tasks:
        st.markdown("---")
        st.markdown("### 🎯 Nhiệm Vụ Được Phân Công Tháng Này")
        for rule_code, task_name, deadline, is_mandatory, group in duty_tasks:
            render_task_card(rule_code, task_name, deadline, is_mandatory, group, uid, name)

    # ── Ebook & QR Tracker (chỉ tiêu cá nhân tháng) ───────────────────────────
    st.markdown("---")
    st.markdown("### 📚📲 Chỉ Tiêu Ebook & QR Tháng Này")
    render_ebook_qr_tracker(uid, name, ym)

    # ── Banner STEAM — luôn hiển thị trong checklist ngày ─────────────────────
    st.markdown("---")
    st.markdown(f"""
<div style="background:#f3f0ff;border:2px solid #7c4dff;border-radius:10px;
    padding:14px 18px;margin-top:8px">
<b style="color:#4a148c;font-size:1rem">🔬 Theo Dõi Lịch STEAM Tuần Này</b><br>
<span style="color:#555;font-size:.9rem">
Xem lịch STEAM từ phòng đào tạo — Nếu có tên bạn thì chuẩn bị ngay!</span><br>
<a href="{STEAM_SHEET_URL}" target="_blank"
   style="color:#4a148c;font-weight:700;font-size:.95rem">
🔗 Mở Lịch STEAM Google Sheets &rarr;</a>
</div>
""", unsafe_allow_html=True)

    # ── Báo cáo phát sinh theo chỉ đạo BM ────────────────────────────────────
    st.markdown("---")
    with st.expander("📢 Nộp Báo Cáo Phát Sinh Theo Chỉ Đạo Của BM"):
        st.caption("Dành cho các báo cáo đột xuất theo yêu cầu của BM / Hội sở.")
        with st.form("form_bc_phat_sinh"):
            tieu_de = st.text_input("Tiêu đề / Nội dung chỉ đạo:")
            noi_dung = st.text_area("Nội dung báo cáo thực hiện:")
            link_bc = st.text_input("Link tài liệu / Hình ảnh minh chứng (nếu có):")
            if st.form_submit_button("Nộp Báo Cáo Phát Sinh", use_container_width=True):
                if not tieu_de.strip() or not noi_dung.strip():
                    st.error("Vui lòng nhập đầy đủ tiêu đề và nội dung báo cáo!")
                else:
                    full_c = f"CHỈ ĐẠO: {tieu_de}\n\nNỘI DUNG:\n{noi_dung}\n\nLINK MINH CHỨNG: {link_bc}"
                    submit_report("BC_PHAT_SINH", f"Báo cáo phát sinh: {tieu_de}", "23:59", full_c)
                    st.rerun()

# ─────────────────────────── EC WEEKLY ────────────────────────────────────────

def render_ec_weekly(uid, name, ym):
    st.markdown("---")
    st.caption("Báo cáo tuần tính theo TUẦN: Chặng 2 hạn 21:30 Thứ 5, Mục tiêu tuần + Nhìn nhận tuần hạn 21:30 Chủ Nhật. Nộp sang tuần sau = không nộp tuần trước.")
    make_form("MT_TUAN", "Điền Mục Tiêu Tuần Mới", "21:30", uid, name)
    st.markdown("---")
    make_form("BC_NHAN_NHAN_TUAN", "Báo cáo Nhìn nhận Tuần cũ + Mục tiêu Tuần mới", "21:30", uid, name)
    st.markdown("---")
    make_form("BC_CHANG_2", "Báo cáo Chặng 2 (Mục tiêu T6-T7-CN)", "21:30", uid, name)
    st.markdown("---")

    if is_my_duty("EBOOK", uid, ym):
        st.markdown("#### 📚 Nhiệm vụ tháng: Báo cáo Ebook")
        make_form("EBOOK", "Báo cáo Ebook (7 EB/nhân sự/tháng)", "23:59", uid, name)
        st.markdown("---")
    if is_my_duty("BOOTH_PLAN", uid, ym):
        st.markdown("#### 🏪 Nhiệm vụ tháng: Báo cáo BOOTH")
        make_form("BOOTH_PLAN", "Kế hoạch + Báo cáo BOOTH", "23:59", uid, name)
        st.markdown("---")
    if is_my_duty("QR_ZALO", uid, ym):
        st.markdown("#### 📲 Nhiệm vụ tháng: Báo cáo QR Zalo")
        make_form("QR_ZALO", "Báo cáo Quét QR Zalo game", "23:59", uid, name)
        st.markdown("---")
    if is_my_duty("STEAM_PLAN", uid, ym):
        st.markdown("#### 🔬 Nhiệm vụ tuần: Kế hoạch STEAM")
        make_form("STEAM_PLAN", "Kế hoạch STEAM hàng tuần", "21:00", uid, name)

# ─────────────────────────── KHTN TAB ─────────────────────────────────────────

def render_khtn_tab(uid, name):
    st.subheader(f"👥 KHTN Của Tôi — {name}")

    # ── Banner link KHTN Google Sheets tổng hợp ─────────────────────────────
    KHTN_SHEET_URL = "https://docs.google.com/spreadsheets/d/1Y1gqXndsZHrnp5HbiREZrMcmDAGiCzwe6rBq0lzvxvM/edit?gid=2096388166#gid=2096388166"
    st.markdown(f"""
<div style="background:#e8f5e9;border:1px solid #a5d6a7;border-radius:10px;
    padding:12px 18px;margin-bottom:12px;display:flex;align-items:center;gap:12px">
<span style="font-size:1.4rem">📊</span>
<div>
<b>KHTN Tổng Hợp Toàn Team — Google Sheets</b><br>
<a href="{KHTN_SHEET_URL}" target="_blank" style="color:#1B5E20;font-weight:600">
🔗 Mở Google Sheets KHTN &rarr;</a>
<span style="color:#555;font-size:.85rem;margin-left:12px">
(Xem toàn bộ dữ liệu KH, lọc theo EC, trạng thái, tháng)</span>
</div>
</div>
""", unsafe_allow_html=True)

    # ── Nhắc chụp ảnh KHTN 16h30 báo nhóm OE ────────────────────────────────
    from datetime import datetime as _dt
    now_h = _dt.now().hour
    if 14 <= now_h < 21:
        st.warning("""📸 **Nhắc việc 16h30:** Chụp ảnh danh sách KHTN → gửi báo cáo lên **nhóm Zalo OE**.
Nội dung ảnh: Danh sách KH hôm nay + trạng thái + bước tiếp theo của từng KH.""")

    st.caption("Chỉ hiển thị dữ liệu khách hàng tiềm năng của bạn.")

    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM khtn_records WHERE user_id=? ORDER BY updated_at DESC", (uid,))
    records = c.fetchall()
    conn.close()

    if records:
        df = pd.DataFrame([dict(r) for r in records])
        st.dataframe(df[["ten_kh","so_dien_thoai","lop_hoc","trang_thai","ghi_chu","buoc_tiep_theo","ngay_hen"]].rename(columns={
            "ten_kh":"Tên KH","so_dien_thoai":"SĐT","lop_hoc":"Lớp","trang_thai":"Trạng thái",
            "ghi_chu":"Ghi chú","buoc_tiep_theo":"Bước tiếp theo","ngay_hen":"Ngày hẹn"
        }), hide_index=True, use_container_width=True)
        with st.expander("📄 Xuất Mẫu Báo Cáo KHTN Của Tôi"):
            lines = [f"Cập nhật KHTN — {name} — {datetime.now().strftime('%d/%m/%Y')}\n"]
            for i, r in enumerate(records, 1):
                lines.append(f"KH {i}: {r['ten_kh']} | SĐT: {r['so_dien_thoai']} | Lớp: {r['lop_hoc']}")
                lines.append(f"  Trạng thái: {r['trang_thai']} | Bước tiếp: {r['buoc_tiep_theo']} | Hẹn: {r['ngay_hen']}")
                lines.append(f"  Ghi chú: {r['ghi_chu']}\n")
            st.text("\n".join(lines))

    st.markdown("---")
    st.subheader("Thêm / Cập nhật KH Tiềm Năng")
    with st.form("add_khtn"):
        c1, c2, c3 = st.columns(3)
        ten_kh = c1.text_input("Tên Khách Hàng / Phụ Huynh")
        sdt = c2.text_input("Số Điện Thoại")
        lop = c3.selectbox("Lớp dự kiến", ["Pre School (~3 tuổi)","Kindy (~5 tuổi)","Kids (~6 tuổi)","Primary","IELTS","TOEIC","Khác"])
        trang_thai = st.selectbox("Trạng thái", ["Mới tiếp cận","Đã giới thiệu SP","Đang cân nhắc","Đã lên lịch test","Đã test — chờ chốt","Đã đóng cọc","Đã đóng HT","Từ chối"])
        c4, c5 = st.columns(2)
        buoc = c4.text_input("Bước tiếp theo")
        ngay_hen = c5.text_input("Ngày hẹn tiếp")
        ghi_chu = st.text_area("Ghi chú thêm về KH")
        if st.form_submit_button("Lưu KH Tiềm Năng", use_container_width=True):
            if not ten_kh.strip():
                st.error("Nhập tên KH!")
            else:
                conn2 = get_conn()
                c2_cur = conn2.cursor()
                c2_cur.execute("INSERT INTO khtn_records(user_id,record_date,ten_kh,so_dien_thoai,lop_hoc,trang_thai,ghi_chu,buoc_tiep_theo,ngay_hen,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
                    (uid, get_today(), ten_kh, sdt, lop, trang_thai, ghi_chu, buoc, ngay_hen, datetime.now().strftime("%Y-%m-%d %H:%M")))
                conn2.commit()
                conn2.close()
                st.success(f"Đã lưu KH: {ten_kh}!")
                st.rerun()

# ─────────────────────────── EC DASHBOARD ─────────────────────────────────────

# ─────────────────────────── SCHEDULE MODULE ──────────────────────────────────


# ── Định nghĩa ca thực tế Ocean Edu (4 ca: P1–P4) ───────────────────────────
CA_DEFS = {
    "P1":  ("07:20", "17:40"),   # 07:20–11:40 & 14:00–17:40
    "P2":  ("09:00", "19:20"),   # 09:00–11:40 & 14:00–19:20
    "P3":  ("13:00", "21:40"),   # 13:00–16:30 & 17:10–21:40
    "P4":  ("08:30", "18:30"),   # 08:30–11:40 & 13:40–18:30
    "OFF": ("",      ""),
}

# Giờ nhắc check mail
CA_MAIL_REMINDER = {
    "P1": "07:50", "P2": "09:30", "P3": "13:30", "P4": "09:00",
}

# Giờ kết ca
CA_END_TIME = {
    "P1": "17:40", "P2": "19:20", "P3": "21:40", "P4": "18:30", "OFF": "21:00",
}


def get_dau_ca_deadline(user_id, date_str=None):
    """
    Tra deadline BC Đầu Ca = giờ bắt đầu ca của người đó trong ngày.
    Nếu chưa có lịch ca → trả None.
    """
    if date_str is None:
        date_str = get_today()
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT ca, start_time FROM work_shifts WHERE shift_date=? AND user_id=?",
              (date_str, user_id))
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    ca = row["ca"]
    if ca == "OFF":
        return "OFF"
    st = row["start_time"] or CA_DEFS.get(ca, ("09:00", ""))[0]
    return st or "09:00"


FIXED_TASKS_BY_CA = {
    "P1": [  # 07:20-11:40 & 14:00-17:40
        ("07:15", "📋 Điền BC Đầu Ca (Hạn chót 07:20 — Trước khi vào ca)"),
        ("07:20", "Check mail + Zalo nhóm + Like/phản hồi chỉ đạo"),
        ("08:00", "Vệ sinh + Setup văn phòng chuẩn bị tiếp khách"),
        ("08:30", "Telesale Chặng 1 — Gọi KH theo kịch bản"),
        ("11:00", "Tiếp KH hẹn / Tư vấn trực tiếp / Demo lớp"),
        ("11:40", "Nghỉ trưa"),
        ("14:00", "Telesale tiếp — Follow KHTN chặng chiều"),
        ("15:30", "Tiếp KH hẹn chiều / Tư vấn"),
        ("16:30", "📸 Chụp ảnh KHTN báo nhóm Zalo OE"),
        ("17:00", "Cập nhật KHTN + CRM + Chỉ số KPI"),
        ("17:40", "📋 BC Cuối Ca + Chỉ số + KHTN — Nộp ngay kết ca P1 (Hạn 22:00)"),
    ],
    "P2": [  # 09:00-11:40 & 14:00-19:20
        ("08:50", "📋 Điền BC Đầu Ca (Hạn chót 09:00 — Trước khi vào ca)"),
        ("09:00", "Check mail + Zalo nhóm + Like/phản hồi chỉ đạo"),
        ("09:30", "Telesale Chặng 1 — Gọi KH theo danh sách"),
        ("11:00", "Tiếp KH hẹn sáng / Tư vấn"),
        ("11:40", "Nghỉ trưa"),
        ("14:00", "Telesale Chặng 2 — Follow KH"),
        ("15:30", "Tiếp KH hẹn chiều / Demo lớp"),
        ("16:30", "📸 Chụp ảnh KHTN báo nhóm Zalo OE"),
        ("17:30", "Cập nhật KHTN + CRM + Chỉ số KPI"),
        ("18:00", "Đăng bài MKT (FB + Zalo cá nhân)"),
        ("19:20", "📋 BC Cuối Ca + Chỉ số + KHTN — Nộp ngay kết ca P2 (Hạn 22:00)"),
    ],
    "P3": [  # 13:00-16:30 & 17:10-21:40
        ("12:50", "📋 Điền BC Đầu Ca (Hạn chót 13:00 — Trước khi vào ca)"),
        ("13:00", "Check mail + Zalo nhóm + Like/phản hồi chỉ đạo"),
        ("13:30", "Telesale — Gọi KH buổi chiều"),
        ("16:00", "Tiếp KH hẹn chiều / Tư vấn"),
        ("16:30", "📸 Chụp ảnh KHTN báo nhóm Zalo OE & Nghỉ giải lao"),
        ("17:10", "Telesale Chặng 2 tối — Gọi phụ huynh tan sở về nhà"),
        ("18:30", "Tiếp KH hẹn tối / Demo lớp / Trải nghiệm"),
        ("20:30", "Cập nhật CRM + Chỉ số KPI ngày"),
        ("21:00", "Đăng bài MKT (FB + Zalo) trước 23:59"),
        ("21:40", "📋 BC Cuối Ca + Chỉ số + KHTN — Nộp ngay kết ca P3 (Hạn 22:00)"),
    ],
    "P4": [  # 08:30-11:40 & 13:40-18:30
        ("08:20", "📋 Điền BC Đầu Ca (Hạn chót 08:30 — Trước khi vào ca)"),
        ("08:30", "Check mail + Zalo nhóm + Like/phản hồi chỉ đạo"),
        ("09:00", "Telesale Chặng 1 — Gọi theo kịch bản"),
        ("11:00", "Tiếp KH / Xử lý hồ sơ học viên"),
        ("11:40", "Nghỉ trưa"),
        ("13:40", "Telesale tiếp — Follow KHTN"),
        ("15:00", "Tiếp KH hẹn chiều / Demo lớp"),
        ("16:30", "📸 Chụp ảnh KHTN báo nhóm Zalo OE"),
        ("17:00", "Cập nhật KHTN + CRM"),
        ("18:00", "Đăng bài MKT (FB + Zalo)"),
        ("18:30", "📋 BC Cuối Ca + Chỉ số + KHTN — Nộp ngay kết ca P4 (Hạn 22:00)"),
    ],
    "OFF": [],
}

WEEKDAY_VN = ["Thứ 2","Thứ 3","Thứ 4","Thứ 5","Thứ 6","Thứ 7","Chủ Nhật"]
WEEK_TAG   = {0:"T2",1:"T3",2:"T4",3:"T5",4:"T6",5:"T7",6:"CN"}


def get_week_dates(ref_date=None):
    """Trả về list 7 ngày từ T2 đến CN của tuần chứa ref_date"""
    d = ref_date or datetime.now().date()
    start = d - pd.Timedelta(days=d.weekday())
    return [start + pd.Timedelta(days=i) for i in range(7)]


def get_month_dates(year, month):
    """Trả về list tất cả ngày trong tháng"""
    import calendar
    num_days = calendar.monthrange(year, month)[1]
    return [datetime(year, month, d).date() for d in range(1, num_days + 1)]


def auto_mix_day(uid, date_obj, ym):
    """
    Tự động mix lịch ngày từ:
    1. Ca làm việc (từ work_shifts)
    2. Việc cố định theo ca
    3. Sự kiện tháng được phân công
    4. Báo cáo đặc biệt theo thứ trong tuần
    """
    conn = get_conn()
    c = conn.cursor()
    date_str = date_obj.strftime("%Y-%m-%d")
    weekday = date_obj.weekday()

    # Lấy ca
    c.execute("SELECT ca, location, note FROM work_shifts WHERE shift_date=? AND user_id=?", (date_str, uid))
    shift_row = c.fetchone()
    ca = shift_row["ca"] if shift_row else "?"
    location = shift_row["location"] if shift_row else ""
    shift_note = shift_row["note"] if shift_row else ""

    # Lấy sự kiện tháng trong ngày (dựa theo timeline chứa ngày này)
    c.execute("SELECT ten_hoat_dong, dia_diem, assigned_to FROM monthly_events WHERE year_month=?", (ym,))
    events = c.fetchall()

    # Lấy sự kiện STEAM phân công cho nhân sự này
    c.execute("SELECT * FROM steam_schedule WHERE event_date=?", (date_str,))
    steam_events = c.fetchall()
    conn.close()

    tasks = list(FIXED_TASKS_BY_CA.get(ca, []))
    for s in steam_events:
        a_ids = [x.strip() for x in (s["assigned_ec_ids"] or "").split(",") if x.strip()]
        if str(uid) in a_ids or "all" in a_ids:
            tasks.append((s["start_time"] or "08:00", f"🔬 Nhiệm vụ STEAM: {s['title']} ({s['location'] or s['school_name'] or 'Chi nhánh'})"))

    # Thêm việc theo thứ
    if weekday == 3:  # Thứ 5
        tasks.append(("21:30", "📋 BC Chặng 2 (deadline 21:30)"))
    if weekday == 6:  # Chủ Nhật
        tasks.append(("21:30", "📋 Mục tiêu tuần + Nhìn nhận tuần (deadline 21:30)"))
    if ca in ("P1","P2","P3","P4"):
        tasks.append(("08:30", "📋 Hạn cập nhật KHTN (trước 08:30)"))
    if weekday in (5, 6):  # T7, CN — Chặng 2
        tasks.append(("09:00", "🎯 Chặng 2: Ưu tiên gọi KH có gia đình ở nhà"))

    # Sort theo giờ
    tasks.sort(key=lambda x: x[0])

    return {
        "ca": ca, "location": location, "note": shift_note,
        "tasks": tasks,
        "events": [(e["ten_hoat_dong"], e["dia_diem"]) for e in events]
    }


def render_schedule_admin(is_ketoan=False):
    """Admin/Kế Toán quản lý lịch ca"""
    ym = get_ym()
    now = datetime.now()

    st.subheader(f"📅 Quản Lý Lịch Làm Việc — {now.strftime('%m/%Y')}")
    st.caption("Kế toán / BM chia ca từng tuần. Nhân sự có thể tự cập nhật ca của mình sau khi nhận phân công.")

    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id, display_name FROM users WHERE role IN ('EC','Admin') ORDER BY display_name")
    staff_all = c.fetchall()
    conn.close()

    tab_w, tab_m, tab_edit, tab_steam = st.tabs(["📋 Chia Ca Theo Tuần", "🗓️ Lịch Tháng (Toàn Team)", "✏️ Nhập Ca Hàng Loạt", "🔬 Lịch Sự Kiện STEAM"])

    with tab_w:
        st.markdown("### Chọn Tuần Để Chia Ca")
        week_options = []
        # Tuần luôn bắt đầu Thứ 2; cho chọn từ tuần trước đến 5 tuần tới (xếp lịch trước sang tháng sau)
        this_monday = now.date() - pd.Timedelta(days=now.weekday())
        for w in range(-1, 6):
            week_start = this_monday + pd.Timedelta(days=7*w)
            week_end = week_start + pd.Timedelta(days=6)
            tag = " (tuần này)" if w == 0 else ""
            week_options.append((f"{week_start.strftime('%d/%m')} — {week_end.strftime('%d/%m/%Y')}{tag}", week_start))

        sel_week_label = st.selectbox("Chọn tuần:", [w[0] for w in week_options], index=1)
        sel_week_start = next(w[1] for w in week_options if w[0] == sel_week_label)
        week_dates = [sel_week_start + pd.Timedelta(days=i) for i in range(7)]

        st.markdown(f"**{sel_week_label}**")
        st.caption("Chọn ca cho từng người — hệ thống sẽ tự sinh lịch chi tiết.")

        conn2 = get_conn()
        c2 = conn2.cursor()

        with st.form("assign_week_schedule"):
            cols_header = st.columns([2] + [1]*7)
            cols_header[0].markdown("**Nhân sự**")
            for i, d in enumerate(week_dates):
                cols_header[i+1].markdown(f"**{WEEK_TAG[i]}**\n{d.strftime('%d/%m')}")

            all_inputs = {}
            for staff in staff_all:
                row_cols = st.columns([2] + [1]*7)
                row_cols[0].write(staff["display_name"])
                for i, d in enumerate(week_dates):
                    date_str = d.strftime("%Y-%m-%d")
                    c2.execute("SELECT ca FROM work_shifts WHERE shift_date=? AND user_id=?", (date_str, staff["id"]))
                    ex = c2.fetchone()
                    cur_ca = ex["ca"] if ex else "OFF"
                    ca_opts = list(CA_DEFS.keys())
                    sel = row_cols[i+1].selectbox("",
                        ca_opts, index=ca_opts.index(cur_ca) if cur_ca in ca_opts else ca_opts.index("OFF"),
                        key=f"ca_{staff['id']}_{date_str}", label_visibility="collapsed")
                    all_inputs[(staff["id"], date_str)] = sel

            creator = st.session_state.get("display_name","")
            if st.form_submit_button("💾 Lưu Lịch Tuần Này", use_container_width=True):
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                for (sid, dstr), ca_val in all_inputs.items():
                    s_t, e_t = CA_DEFS.get(ca_val, ("",""))
                    c2.execute("""INSERT INTO work_shifts(shift_date, user_id, ca, start_time, end_time, created_by, created_at)
                                  VALUES(?,?,?,?,?,?,?)
                                  ON CONFLICT(shift_date, user_id) DO UPDATE SET
                                  ca=excluded.ca, start_time=excluded.start_time,
                                  end_time=excluded.end_time, created_by=excluded.created_by,
                                  created_at=excluded.created_at""",
                               (dstr, sid, ca_val, s_t, e_t, creator, now_str))
                conn2.commit()
                st.success("Đã lưu lịch ca tuần này!")
                st.rerun()
        conn2.close()

    with tab_m:
        st.markdown("### Lịch Tháng Toàn Team")
        sel_staff_id = st.selectbox("Xem lịch của:", [s["id"] for s in staff_all],
                                    format_func=lambda x: next(s["display_name"] for s in staff_all if s["id"]==x))

        month_dates = get_month_dates(now.year, now.month)
        conn3 = get_conn()
        c3 = conn3.cursor()
        c3.execute("SELECT shift_date, ca FROM work_shifts WHERE user_id=? AND shift_date LIKE ?",
                   (sel_staff_id, f"{ym}%"))
        shifts_map = {r["shift_date"]: r["ca"] for r in c3.fetchall()}
        conn3.close()

        # Vẽ calendar HTML
        CA_COLORS = {
            "P1": "#d5e8d4", "P2": "#dae8fc", "P3": "#e1d5e7", "P4": "#fff2cc",
            "OFF": "#f5f5f5", "?": "#efefef"
        }

        cal_html = """<style>
        .cal-grid{display:grid;grid-template-columns:repeat(7,1fr);gap:4px;margin:8px 0}
        .cal-hdr{text-align:center;font-weight:700;font-size:0.78rem;padding:4px;background:#0070C0;color:white;border-radius:4px}
        .cal-day{border-radius:6px;padding:6px 4px;min-height:56px;font-size:0.78rem;border:1px solid #ddd}
        .cal-day .dn{font-weight:700;font-size:0.85rem}
        .cal-day .ca-tag{font-size:0.7rem;margin-top:3px;padding:2px 4px;border-radius:3px;background:rgba(0,0,0,0.1)}
        .today-border{border:2px solid #1B3A8C!important;box-shadow:0 0 5px rgba(27,58,140,.2)}
        </style>
        <div class="cal-grid">"""

        # Header thứ
        for wd in WEEKDAY_VN:
            cal_html += f'<div class="cal-hdr">{wd[:4]}</div>'

        # Padding trước ngày đầu tháng
        first_weekday = month_dates[0].weekday()
        for _ in range(first_weekday):
            cal_html += '<div style="min-height:56px"></div>'

        today_str = datetime.now().strftime("%Y-%m-%d")
        for d in month_dates:
            dstr = d.strftime("%Y-%m-%d")
            ca = shifts_map.get(dstr, "?")
            color = CA_COLORS.get(ca, "#efefef")
            is_today = "today-border" if dstr == today_str else ""
            weekend_bg = "background:#fafafa;" if d.weekday() >= 5 else ""
            cal_html += f"""<div class="cal-day {is_today}" style="background:{color};{weekend_bg}">
                <div class="dn">{d.day}</div>
                <div class="ca-tag">{ca.replace('Ca ','').replace('Hành Chính','HC').replace('(Sáng)','S').replace('(Chiều)','C').replace('(Tối)','T').replace('Toàn Phần','Full')}</div>
            </div>"""

        cal_html += "</div>"
        cal_html += "<small>🟢P1 07:20–17:40 &nbsp; 🔵P2 09:00–19:20 &nbsp; 🟣P3 13:00–21:40 &nbsp; 🟡P4 08:30–18:30 &nbsp; ⬜OFF &nbsp; ?=Chưa xếp</small>"
        st.markdown(cal_html, unsafe_allow_html=True)

    with tab_edit:
        st.markdown("### ✏️ Nhập / Chỉnh Sửa Ca Đơn Lẻ")
        with st.form("manual_shift"):
            c1, c2, c3, c4 = st.columns([2, 2, 2, 2])
            sel_staff = c1.selectbox("Nhân sự:", [s["id"] for s in staff_all], format_func=lambda x: next(s["display_name"] for s in staff_all if s["id"]==x))
            sel_date = c2.date_input("Ngày:", value=datetime.now().date())
            sel_ca = c3.selectbox("Ca:", list(CA_DEFS.keys()))
            location = c4.text_input("Địa điểm:", value="Chi nhánh")
            note = st.text_input("Ghi chú:", placeholder="Thay ca, sự kiện, STEAM...")
            if st.form_submit_button("💾 Lưu Ca Này", use_container_width=True):
                s_t, e_t = CA_DEFS[sel_ca]
                conn4 = get_conn()
                c4_cur = conn4.cursor()
                c4_cur.execute("""INSERT INTO work_shifts(shift_date, user_id, ca, start_time, end_time, location, note, created_by, created_at)
                              VALUES(?,?,?,?,?,?,?,?,?)
                              ON CONFLICT(shift_date, user_id) DO UPDATE SET
                              ca=excluded.ca, start_time=excluded.start_time, end_time=excluded.end_time,
                              location=excluded.location, note=excluded.note, created_by=excluded.created_by, created_at=excluded.created_at""",
                             (sel_date.strftime("%Y-%m-%d"), sel_staff, sel_ca, s_t, e_t, location, note,
                              st.session_state.get("display_name",""), datetime.now().strftime("%Y-%m-%d %H:%M")))
                conn4.commit()
                conn4.close()
                st.success("Đã lưu ca!")
                st.rerun()

    with tab_steam:
        st.markdown("### 🔬 Quản Lý Lịch Sự Kiện STEAM (Từ Phòng Đào Tạo)")
        st.caption("Nhập lịch STEAM từ phòng đào tạo. Hệ thống sẽ tự động ghép vào lịch làm việc hàng ngày của các EC được phân công.")

        conn_st = get_conn()
        c_st = conn_st.cursor()
        c_st.execute("SELECT * FROM steam_schedule ORDER BY event_date DESC, start_time ASC")
        steam_list = c_st.fetchall()
        conn_st.close()

        if steam_list:
            st.markdown("#### 📋 Danh Sách Sự Kiện STEAM Đã Lên Lịch")
            for item in steam_list:
                with st.container():
                    col_s1, col_s2, col_s3, col_s4 = st.columns([2, 3, 3, 1])
                    col_s1.markdown(f"📅 **{item['event_date']}**<br>🕐 {item['start_time']} – {item['end_time']}", unsafe_allow_html=True)
                    col_s2.markdown(f"**{item['title']}**<br>🏫 {item['school_name'] or '—'}<br>📍 {item['location'] or 'Chi nhánh'}", unsafe_allow_html=True)
                    
                    assigned_ids = [x.strip() for x in (item['assigned_ec_ids'] or '').split(',') if x.strip()]
                    assigned_names = [s['display_name'] for s in staff_all if str(s['id']) in assigned_ids]
                    assigned_str = ", ".join(assigned_names) if assigned_names else ("Toàn team" if "all" in assigned_ids else "Chưa gán")
                    col_s3.markdown(f"👥 **EC phụ trách:** {assigned_str}<br>📝 *{item['note'] or 'Không có ghi chú'}*", unsafe_allow_html=True)

                    if col_s4.button("🗑️ Xóa", key=f"del_steam_{item['id']}"):
                        conn_del = get_conn()
                        conn_del.execute("DELETE FROM steam_schedule WHERE id=?", (item['id'],))
                        conn_del.commit()
                        conn_del.close()
                        st.success("Đã xóa sự kiện STEAM!")
                        st.rerun()
                    st.divider()
        else:
            st.info("Chưa có sự kiện STEAM nào được lưu. Bạn có thể nhập thêm bên dưới.")

        st.markdown("#### ➕ Thêm Sự Kiện STEAM Mới")
        with st.form("add_steam_event"):
            c1, c2 = st.columns(2)
            st_date = c1.date_input("Ngày diễn ra sự kiện:", value=datetime.now().date())
            st_title = c2.text_input("Tên sự kiện / Nội dung:", placeholder="VD: Khám phá STEAM Khoa học vui")
            
            c3, c4 = st.columns(2)
            st_start = c3.text_input("Giờ bắt đầu (HH:MM):", value="08:00")
            st_end = c4.text_input("Giờ kết thúc (HH:MM):", value="11:00")
            
            c5, c6 = st.columns(2)
            st_school = c5.text_input("Trường học đối tác:", placeholder="VD: TH Lê Quý Đôn")
            st_location = c6.text_input("Địa điểm tổ chức:", placeholder="VD: Sân trường TH Lê Quý Đôn")

            st_assigned = st.multiselect("Phân công nhân sự phụ trách (EC):", 
                                         options=[s['id'] for s in staff_all], 
                                         format_func=lambda x: next((s['display_name'] for s in staff_all if s['id']==x), str(x)))
            st_note = st.text_area("Ghi chú bổ sung (giáo cụ, nhiệm vụ, yêu cầu):")

            if st.form_submit_button("💾 Lưu Sự Kiện STEAM", use_container_width=True):
                if not st_title.strip():
                    st.error("Vui lòng nhập tên sự kiện!")
                else:
                    assigned_str = ",".join(str(x) for x in st_assigned)
                    conn_add = get_conn()
                    conn_add.execute("""
                        INSERT INTO steam_schedule(event_date, start_time, end_time, title, school_name, location, assigned_ec_ids, note, created_by, created_at)
                        VALUES(?,?,?,?,?,?,?,?,?,?)
                    """, (st_date.strftime("%Y-%m-%d"), st_start, st_end, st_title, st_school, st_location, assigned_str, st_note,
                          st.session_state.get("display_name",""), datetime.now().strftime("%Y-%m-%d %H:%M")))
                    conn_add.commit()
                    conn_add.close()
                    st.success(f"Đã lưu sự kiện STEAM: {st_title}!")
                    st.rerun()


def render_my_schedule(uid, name, ym):
    """EC xem lịch tháng của mình + lịch tuần chi tiết auto-mix"""
    now = datetime.now()

    st.subheader(f"📅 Lịch Làm Việc Của Tôi — {name}")

    # ── Sự kiện STEAM được phân công ──────────────────────────────────────────
    conn_mys = get_conn()
    c_mys = conn_mys.cursor()
    c_mys.execute("SELECT * FROM steam_schedule WHERE event_date >= ? ORDER BY event_date ASC LIMIT 10", (get_today(),))
    my_steam = []
    for s in c_mys.fetchall():
        a_ids = [x.strip() for x in (s["assigned_ec_ids"] or "").split(",") if x.strip()]
        if str(uid) in a_ids or "all" in a_ids:
            my_steam.append(s)
    conn_mys.close()
    if my_steam:
        with st.expander(f"🔬 Sự Kiện STEAM Bạn Được Phân Công ({len(my_steam)} sự kiện)", expanded=True):
            for ms in my_steam:
                st.markdown(f"• 📅 **{ms['event_date']}** ({ms['start_time']}–{ms['end_time']}): **{ms['title']}** tại *{ms['location'] or ms['school_name'] or 'Chi nhánh'}* — Ghi chú: {ms['note'] or 'Chuẩn bị giáo cụ'}")

    tab_w, tab_m = st.tabs(["📋 Lịch Tuần Này (Chi Tiết)", "🗓️ Lịch Tháng Của Tôi"])

    with tab_w:
        week_dates = get_week_dates()
        conn = get_conn()
        c = conn.cursor()

        st.markdown("### Lịch Tuần Này — Tự Động Mix")
        st.caption("Hệ thống mix: Ca làm việc + Việc cố định theo ca + Báo cáo deadline + Sự kiện tháng")

        for d in week_dates:
            dstr = d.strftime("%Y-%m-%d")
            mixed = auto_mix_day(uid, d, ym)
            ca = mixed["ca"]
            is_today = dstr == now.strftime("%Y-%m-%d")

            # Card header
            bg = "#e8f0fb" if is_today else ("#f5f5f5" if ca == "OFF" else "white")
            border = OE_BLUE_DARK if is_today else OE_BLUE_LIGHT
            today_badge = " 🔵 HÔM NAY" if is_today else ""
            ca_color_map = {"P1":"#d5e8d4","P2":"#dae8fc","P3":"#e1d5e7","P4":"#fff2cc","OFF":"#f5f5f5","?":"#efefef"}


            st.markdown(f"""<div style="background:{bg};border-left:4px solid {border};border-radius:8px;padding:12px 16px;margin:8px 0">
<b>{WEEKDAY_VN[d.weekday()]} — {d.strftime('%d/%m/%Y')}{today_badge}</b>
&nbsp;&nbsp; <span style="background:{ca_color_map.get(ca,'#eee')};padding:3px 8px;border-radius:4px;font-size:0.82rem"><b>{ca}</b>{f' | 📍 {mixed["location"]}' if mixed["location"] and mixed["location"]!="Chi nhánh" else ""}</span>
{f'&nbsp;&nbsp;<span style="color:#888;font-size:0.78rem">📝 {mixed["note"]}</span>' if mixed["note"] else ""}
</div>""", unsafe_allow_html=True)

            if ca == "OFF":
                st.caption("&nbsp;&nbsp;&nbsp;🏠 Ngày nghỉ")
            elif ca == "?":
                st.caption("&nbsp;&nbsp;&nbsp;⚠️ Chưa có lịch ca — liên hệ kế toán Hồng")
            else:
                if mixed["tasks"]:
                    with st.expander(f"Xem kế hoạch chi tiết {d.strftime('%d/%m')} ({len(mixed['tasks'])} việc)"):
                        for task_time, task_name in mixed["tasks"]:
                            report_icon = "📋" if "📋" in task_name else "·"
                            st.markdown(f"&nbsp;&nbsp; `{task_time}` {task_name}")
                        if mixed["events"]:
                            st.markdown("---")
                            st.caption("🎯 Sự kiện tháng cần chú ý:")
                            for ev_name, ev_place in mixed["events"]:
                                st.markdown(f"&nbsp;&nbsp; 🎪 **{ev_name}** — {ev_place}")

        conn.close()

        # Form tự nhập ca (nếu chưa có)
        st.markdown("---")
        with st.expander("✏️ Tự Nhập Ca Của Tôi (chỉ ngày tương lai chưa được xếp)"):
            with st.form("self_shift"):
                c1, c2, c3 = st.columns(3)
                sel_date = c1.date_input("Ngày:", value=now.date())
                sel_ca = c2.selectbox("Ca của tôi:", list(CA_DEFS.keys()))
                note_s = c3.text_input("Ghi chú (VD: STEAM, Booth...)")
                _locked_msg = None
                if sel_date <= now.date():
                    _locked_msg = "Chỉ được tự nhập ca cho ngày từ NGÀY MAI trở đi. Ca hôm nay/đã qua → liên hệ Kế Toán Hồng."
                elif get_shift_ca(uid, sel_date.strftime("%Y-%m-%d")) is not None:
                    _locked_msg = "Ngày này Kế Toán đã xếp ca — không tự sửa được. Cần đổi ca → liên hệ Kế Toán Hồng."
                if st.form_submit_button("Lưu Ca", use_container_width=True):
                    if _locked_msg:
                        st.error(_locked_msg)
                    else:
                        s_t, e_t = CA_DEFS[sel_ca]
                        conn2 = get_conn()
                        c2_cur = conn2.cursor()
                        c2_cur.execute("""INSERT INTO work_shifts(shift_date,user_id,ca,start_time,end_time,note,created_by,created_at)
                                         VALUES(?,?,?,?,?,?,?,?)
                                         ON CONFLICT(shift_date,user_id) DO UPDATE SET ca=excluded.ca,
                                         start_time=excluded.start_time, end_time=excluded.end_time, note=excluded.note""",
                                       (sel_date.strftime("%Y-%m-%d"), uid, sel_ca, s_t, e_t, note_s, name,
                                        now.strftime("%Y-%m-%d %H:%M")))
                        conn2.commit()
                        conn2.close()
                        st.success(f"Đã lưu ca {sel_ca} ngày {sel_date.strftime('%d/%m')}!")
                        st.rerun()

    with tab_m:
        st.markdown(f"### Lịch Tháng {now.strftime('%m/%Y')} Của Tôi")
        month_dates = get_month_dates(now.year, now.month)
        conn3 = get_conn()
        c3 = conn3.cursor()
        c3.execute("SELECT shift_date, ca FROM work_shifts WHERE user_id=? AND shift_date LIKE ?",
                   (uid, f"{ym}%"))
        shifts_map = {r["shift_date"]: r["ca"] for r in c3.fetchall()}
        conn3.close()

        CA_COLORS = {
            "P1": "#d5e8d4", "P2": "#dae8fc", "P3": "#e1d5e7", "P4": "#fff2cc",
            "OFF": "#f5f5f5", "?": "#efefef"
        }
        today_str = now.strftime("%Y-%m-%d")

        cal_html = """<style>
        .cal-g{display:grid;grid-template-columns:repeat(7,1fr);gap:5px;margin:8px 0}
        .cal-h{text-align:center;font-weight:700;font-size:0.8rem;padding:5px;background:#0070C0;color:white;border-radius:5px}
        .cal-d{border-radius:7px;padding:7px 5px;min-height:62px;font-size:0.8rem;border:1px solid #ddd;position:relative}
        .cal-d .dn{font-weight:700;font-size:0.9rem}
        .cal-d .ca-lbl{font-size:0.68rem;margin-top:3px;opacity:.85}
        .cal-d .bc-dot{width:6px;height:6px;border-radius:50%;background:#1B3A8C;display:inline-block;margin:1px}
        .today-b{border:2.5px solid #1B3A8C!important;box-shadow:0 0 6px rgba(27,58,140,.25)}
        </style>
        <div class="cal-g">"""

        for wd in WEEKDAY_VN:
            cal_html += f'<div class="cal-h">{wd[:4]}</div>'

        first_wd = month_dates[0].weekday()
        for _ in range(first_wd):
            cal_html += '<div style="min-height:62px"></div>'

        for d in month_dates:
            dstr = d.strftime("%Y-%m-%d")
            ca = shifts_map.get(dstr, "?")
            bg = CA_COLORS.get(ca, "#efefef")
            is_td = "today-b" if dstr == today_str else ""
            wknd = "opacity:.85" if d.weekday() >= 5 else ""

            # Check if any reports submitted
            conn_r = get_conn()
            cr = conn_r.cursor()
            cr.execute("SELECT COUNT(*) as cnt FROM reports WHERE user_id=? AND report_date=?", (uid, dstr))
            rpt_cnt = cr.fetchone()["cnt"]
            conn_r.close()
            dots = "".join(['<span class="bc-dot"></span>' for _ in range(min(rpt_cnt, 5))])

            short_ca = ca.replace("Ca Hành Chính","HC").replace("Ca 1 (Sáng)","S").replace("Ca 2 (Chiều)","C").replace("Ca 3 (Tối)","T").replace("Ca Toàn Phần","Full").replace("OFF","OFF")
            cal_html += f"""<div class="cal-d {is_td}" style="background:{bg};{wknd}">
                <div class="dn">{d.day}</div>
                <div class="ca-lbl">{short_ca}</div>
                <div style="margin-top:3px">{dots}</div>
            </div>"""

        cal_html += "</div>"
        cal_html += "<small>Chú thích Ca: P1 07:20–17:40 | P2 09:00–19:20 | P3 13:00–21:40 | P4 08:30–18:30 | ?=Chưa có lịch<br>🔵 Chấm xanh = số báo cáo đã nộp trong ngày đó</small>"
        st.markdown(cal_html, unsafe_allow_html=True)


def render_my_profile_tab():
    uid = st.session_state["user_id"]
    name = st.session_state["display_name"]
    username = st.session_state["username"]
    role = st.session_state["role"]

    st.subheader("👤 Quản Lý Tài Khoản Cá Nhân")
    st.caption("Cập nhật họ tên hiển thị và đổi mật khẩu bảo mật của riêng bạn tại đây.")

    col1, col2 = st.columns([1, 1])
    with col1:
        st.markdown(f"""
        <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:10px; padding:18px 22px; margin-bottom:16px;">
            <h4 style="margin:0 0 10px; color:#2D3190;">📋 Thông Tin Hiện Tại</h4>
            <p style="margin:4px 0; font-size:0.95rem;">• <b>Họ tên hiển thị:</b> {name}</p>
            <p style="margin:4px 0; font-size:0.95rem;">• <b>Tên đăng nhập:</b> <code>{username}</code></p>
            <p style="margin:4px 0; font-size:0.95rem;">• <b>Vai trò hệ thống:</b> <span style="background:#e0f2fe; color:#0369a1; padding:2px 8px; border-radius:4px; font-weight:700;">{role}</span></p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        with st.form("form_center_profile_update"):
            st.markdown("#### ⚙️ Đổi Tên Hiển Thị & Mật Khẩu:")
            up_name = st.text_input("Họ tên hiển thị mới:", value=name)
            up_pass1 = st.text_input("Mật khẩu mới (bỏ trống nếu không muốn đổi):", type="password")
            up_pass2 = st.text_input("Xác nhận lại mật khẩu mới:", type="password")

            if st.form_submit_button("💾 Lưu Thay Đổi Tài Khoản", use_container_width=True, type="primary"):
                conn_p = get_conn()
                c_p = conn_p.cursor()
                if up_pass1.strip():
                    if up_pass1.strip() != up_pass2.strip():
                        st.error("Xác nhận mật khẩu mới không khớp!")
                    elif len(up_pass1.strip()) < 4:
                        st.error("Mật khẩu phải từ 4 ký tự trở lên!")
                    else:
                        c_p.execute("UPDATE users SET display_name=?, password=? WHERE id=?", 
                                    (up_name.strip(), hash_pw(up_pass1.strip()), uid))
                        conn_p.commit()
                        st.session_state["display_name"] = up_name.strip()
                        st.session_state["is_default_password"] = False
                        st.success("🎉 Đã cập nhật họ tên và đổi mật khẩu thành công!")
                        conn_p.close()
                        st.rerun()
                else:
                    c_p.execute("UPDATE users SET display_name=? WHERE id=?", 
                                (up_name.strip(), uid))
                    conn_p.commit()
                    st.session_state["display_name"] = up_name.strip()
                    st.success("🎉 Đã cập nhật họ tên hiển thị thành công!")
                    conn_p.close()
                    st.rerun()
                conn_p.close()


def render_ec():
    uid = st.session_state["user_id"]
    name = st.session_state["display_name"]
    ym = get_ym()

    render_deadline_ticker()

    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT COUNT(*), SUM(amount) FROM penalties WHERE user_id=? AND is_paid=0", (uid,))
    row = c.fetchone()
    conn.close()
    if row and row[0] > 0:
        st.markdown(f"""
        <div style="background-color:#ffebee; border-left:6px solid #d32f2f; padding:15px; border-radius:5px; margin-bottom:15px;">
            <h4 style="color:#c62828; margin-top:0;">🚨 CẢNH BÁO: BẠN CÓ KHOẢN PHẠT CHƯA NỘP!</h4>
            <p style="color:#d32f2f; margin-bottom:0; font-weight:500;">
                Bạn đang có <b>{row[0]}</b> vi phạm chưa nộp phạt (Tổng: <b>{row[1]:,}đ</b>).<br>
                App sẽ nhắc việc chuyển khoản <b>liên tục 3 lần/ngày</b> cho đến khi nộp xong.<br>
                👉 Vui lòng vào tab <b>💵 Vi Phạm</b> để quét mã QR chuyển khoản cho Kế toán Hồng.
            </p>
        </div>
        """, unsafe_allow_html=True)

    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "📝 Báo Cáo Ngày",
        "📅 Lịch Của Tôi",
        "📊 KPI Của Tôi",
        "👥 KHTN Của Tôi",
        "📅 Báo Cáo Tuần / Tháng",
        "💵 Vi Phạm",
        "👤 Tài Khoản Của Tôi"
    ])
    with tab1: render_ec_daily(uid, name, ym)
    with tab2: render_my_schedule(uid, name, ym)
    with tab3: render_my_kpi(uid, name, ym)
    with tab4: render_khtn_tab(uid, name)
    with tab5: render_ec_weekly(uid, name, ym)
    with tab6: render_penalty_table(admin_view=False)
    with tab7: render_my_profile_tab()



# ─────────────────────────── ATL WORKSPACE ───────────────────────────────────

def render_atl_workspace(uid, name):
    branch_name = get_branch_setting("branch_name", "Ocean Edu Buôn Ma Thuột")
    has_atl = get_branch_setting("has_atl", "1") == "1"

    if has_atl:
        st.subheader(f"👩‍💼 Góc Làm Việc & Báo Cáo ATL — {name}")
        st.caption(f"Báo cáo điều hành toàn team và rà soát KHTN gửi Ban Giám Đốc.")
    else:
        st.subheader(f"📋 Báo Cáo Điều Hành Chi Nhánh (BM Kiêm Nhiệm ATL) — {name}")
        st.caption(f"Chi nhánh {branch_name} vận hành tinh gọn: BM trực tiếp rà soát số liệu team và lập báo cáo nhanh gửi Ban Giám Đốc Vùng / Hội sở.")

    today = get_today()
    ym = get_ym()

    tab_sang, tab_khtn, tab_toi, tab_his = st.tabs([
        "🌅 1. Báo Cáo Team Đầu Ngày (09:00)",
        "🔍 2. Rà Soát KHTN Hẹn Sáng (08:45)",
        "🌙 3. Báo Cáo Team Cuối Ngày (21:15)",
        "📋 Lịch Sử Báo Cáo ATL"
    ])

    conn = get_conn()
    c = conn.cursor()

    # ── TAB 1: BC Team Đầu Ngày ───────────────────────────────────────────────
    with tab_sang:
        st.markdown("### 🌅 Báo Cáo Công Việc & Mục Tiêu Team Đầu Ngày")
        st.caption("Quy định nộp trước 09:00 sáng. Báo cáo này gửi cho BM Hương.")

        c.execute("SELECT * FROM reports WHERE rule_code='BC_ATL_DAU_NGAY' AND report_date=?", (today,))
        rep_sang = c.fetchone()

        if rep_sang:
            st.success(f"✅ Đã nộp báo cáo đầu ngày lúc **{rep_sang['submitted_at']}**.")
            st.markdown(f"**Nội dung đã nộp:**\n```\n{rep_sang['content']}\n```")
        else:
            c.execute("SELECT u.display_name, ws.ca, ws.start_time, ws.end_time FROM work_shifts ws JOIN users u ON ws.user_id=u.id WHERE ws.shift_date=?", (today,))
            shift_today = c.fetchall()

            c.execute("SELECT u.display_name, r.content FROM reports r JOIN users u ON r.user_id=u.id WHERE r.rule_code='BC_DAU_CA' AND r.report_date=?", (today,))
            ec_dau_ca = c.fetchall()

            ca_count = {"P1": 0, "P2": 0, "P3": 0, "P4": 0, "OFF": 0}
            working_staff = []
            off_staff = []
            for s in shift_today:
                ca = s["ca"]
                if ca in ca_count:
                    ca_count[ca] += 1
                if ca == "OFF":
                    off_staff.append(s["display_name"])
                else:
                    working_staff.append(f"{s['display_name']} ({ca})")

            default_template = f"""BÁO CÁO CÔNG VIỆC TEAM ĐẦU NGÀY — {datetime.now().strftime('%d/%m/%Y')}
Người báo cáo: {name} (ATL)

I/ TÌNH HÌNH NHÂN SỰ & CA LÀM VIỆC:
- Tổng nhân sự đi làm: {len(working_staff)} người
  • Phân bổ ca: P1: {ca_count['P1']} | P2: {ca_count['P2']} | P3: {ca_count['P3']} | P4: {ca_count['P4']}
  • Danh sách: {', '.join(working_staff) if working_staff else 'Chưa xếp ca'}
  • Nhân sự OFF: {', '.join(off_staff) if off_staff else 'Không'}

II/ MỤC TIÊU & CAM KẾT HOẠT ĐỘNG TOÀN TEAM:
- EC đã nộp BC đầu ca: {len(ec_dau_ca)}/{len(working_staff)} nhân sự
- Mục tiêu tổng cuộc gọi toàn team hôm nay: ___ cuộc
- Mục tiêu doanh số dự kiến phát sinh: ___ K
- Mục tiêu KH hẹn check-in tại chi nhánh: ___ lượt

III/ TRỌNG TÂM ĐIỀU HÀNH & HỖ TRỢ CỦA ATL:
- Đôn đốc các cô gọi telesale theo kịch bản Back to School / Thi thử.
- Trực tiếp hỗ trợ chốt bill cho các case KH tiềm năng của: ___
- Giám sát việc chụp ảnh KHTN lúc 16h30 và đăng bài MKT cá nhân."""

            with st.form("form_atl_dau_ngay"):
                content_sang = st.text_area("Nội dung báo cáo gửi BM:", value=default_template, height=320)
                if st.form_submit_button("🚀 Gửi Báo Cáo Đầu Ngày Cho BM", use_container_width=True):
                    if submit_report("BC_ATL_DAU_NGAY", "ATL — Báo cáo team đầu ngày", "09:00", content_sang):
                        st.rerun()

    # ── TAB 2: Rà Soát KHTN Sáng ───────────────────────────────────────────────
    with tab_khtn:
        st.markdown("### 🔍 Rà Soát KH Hẹn Lên Chi Nhánh Hôm Nay")
        st.caption("Quy định: Tối thiểu 1 KH/vị trí EC. Hạn hoàn thành rà soát trước 08:45 sáng.")

        c.execute("SELECT * FROM reports WHERE rule_code='BC_ATL_KHTN_SANG' AND report_date=?", (today,))
        rep_khtn = c.fetchone()
        if rep_khtn:
            st.success(f"✅ Đã xác nhận rà soát KHTN sáng lúc **{rep_khtn['submitted_at']}**.")
            st.markdown(f"**Ghi chú rà soát:**\n```\n{rep_khtn['content']}\n```")

        c.execute("""
            SELECT u.display_name as ec_name, u.id as ec_id, k.ten_kh, k.so_dien_thoai, k.lop_hoc, k.trang_thai, k.buoc_tiep_theo, k.ngay_hen
            FROM users u
            LEFT JOIN khtn_records k ON u.id = k.user_id AND (k.ngay_hen LIKE ? OR k.ngay_hen = ?)
            WHERE u.role = 'EC'
            ORDER BY u.display_name
        """, (f"%{today}%", today))
        khtn_today_all = c.fetchall()

        ec_khtn_map = {}
        for r in khtn_today_all:
            ec_name = r["ec_name"]
            ec_khtn_map.setdefault(ec_name, []).append(r)

        rows_khtn_summary = []
        alert_missing_khtn = []
        for ec_name, kh_list in ec_khtn_map.items():
            valid_kh = [k for k in kh_list if k["ten_kh"] is not None]
            count = len(valid_kh)
            status_str = "🟢 Đạt (>=1 KH)" if count >= 1 else "🔴 Chưa có KH hẹn"
            if count == 0:
                alert_missing_khtn.append(ec_name)
            kh_details = "; ".join([f"{k['ten_kh']} ({k['so_dien_thoai'] or '—'}, Lớp {k['lop_hoc'] or '—'})" for k in valid_kh]) if valid_kh else "—"
            rows_khtn_summary.append({
                "Tư vấn viên (EC)": ec_name,
                "Số KH hẹn hôm nay": count,
                "Đánh giá": status_str,
                "Danh sách KH hẹn": kh_details
            })

        st.dataframe(pd.DataFrame(rows_khtn_summary), hide_index=True, use_container_width=True)

        if alert_missing_khtn:
            st.warning(f"⚠️ Các cô chưa có KH hẹn lên hôm nay: **{', '.join(alert_missing_khtn)}** — ATL cần đôn đốc gọi ngay đầu giờ sáng!")

        if not rep_khtn:
            with st.form("form_atl_khtn_sang"):
                khtn_note = st.text_area("Ghi chú rà soát & Chỉ đạo cho EC trong ngày:",
                                         value=f"Đã rà soát KHTN sáng {datetime.now().strftime('%d/%m/%Y')}. Có {len(rows_khtn_summary) - len(alert_missing_khtn)} cô có KH hẹn. Đã đôn đốc {', '.join(alert_missing_khtn)} đẩy mạnh gọi tiếp cận.", height=120)
                if st.form_submit_button("✅ Xác Nhận Đã Rà Soát KHTN Sáng", use_container_width=True):
                    full_content = f"RÀ SOÁT KHTN SÁNG {today}\n\n{khtn_note}"
                    if submit_report("BC_ATL_KHTN_SANG", "ATL — Rà soát KHTN hẹn sáng", "08:45", full_content):
                        st.rerun()

    # ── TAB 3: BC Team Cuối Ngày ───────────────────────────────────────────────
    with tab_toi:
        st.markdown("### 🌙 Báo Cáo Kết Quả Team Cuối Ngày")
        st.caption("Quy định nộp trước 21:15 tối. Báo cáo này gửi cho BM Hương.")

        c.execute("SELECT * FROM reports WHERE rule_code='BC_ATL_CUOI_NGAY' AND report_date=?", (today,))
        rep_toi = c.fetchone()

        if rep_toi:
            st.success(f"✅ Đã nộp báo cáo cuối ngày lúc **{rep_toi['submitted_at']}**.")
            st.markdown(f"**Nội dung đã nộp:**\n```\n{rep_toi['content']}\n```")
        else:
            c.execute("""
                SELECT u.display_name, r.kpi_cuoc_goi, r.kpi_doanh_thu, r.kpi_checkin, r.kpi_cocnho, r.giai_trinh, r.de_xuat
                FROM reports r JOIN users u ON r.user_id=u.id
                WHERE r.rule_code='CHI_SO_NGAY' AND r.report_date=?
            """, (today,))
            chiso_list = c.fetchall()

            total_calls = sum(r["kpi_cuoc_goi"] or 0 for r in chiso_list)
            total_rev = sum(r["kpi_doanh_thu"] or 0 for r in chiso_list)
            total_ci = sum(r["kpi_checkin"] or 0 for r in chiso_list)
            total_coc = sum(r["kpi_cocnho"] or 0 for r in chiso_list)

            good_staff = [r["display_name"] for r in chiso_list if (r["kpi_cuoc_goi"] or 0) >= 30]
            low_staff = [f"{r['display_name']} ({r['kpi_cuoc_goi']} cuộc — {r['giai_trinh'] or 'chưa giải trình'})" for r in chiso_list if (r["kpi_cuoc_goi"] or 0) < 20]

            default_template_toi = f"""BÁO CÁO KẾT QUẢ TEAM CUỐI NGÀY — {datetime.now().strftime('%d/%m/%Y')}
Người báo cáo: {name} (ATL)

I/ TỔNG KẾT SỐ LIỆU TOÀN TEAM:
- Tổng số cuộc gọi đạt được: {total_calls} cuộc (TB: {round(total_calls/max(1, len(chiso_list)), 1)} cuộc/người)
- Doanh thu thực tế phát sinh: {total_rev:,} đ
- Check-in học viên: {total_ci} lượt | Cọc nhỏ: {total_coc}

II/ ĐÁNH GIÁ CHI TIẾT TỪNG NHÂN SỰ:
- Nhân sự đạt kết quả tốt (>=30 cuộc): {', '.join(good_staff) if good_staff else 'Chưa có'}
- Nhân sự chưa đạt (<20 cuộc) & Nguyên nhân:
  {chr(10).join(['• ' + x for x in low_staff]) if low_staff else '• Không có (Toàn team đều đạt)'}

III/ GIẢI PHÁP & KẾ HOẠCH BÙ ĐẮP NGÀY MAI:
- Bù cuộc gọi còn thiếu cho chặng: ___
- Phương án follow lại các case từ chối hoặc bận máy: ___
- Đề xuất BM hỗ trợ: ___"""

            with st.form("form_atl_cuoi_ngay"):
                content_toi = st.text_area("Nội dung báo cáo gửi BM:", value=default_template_toi, height=340)
                if st.form_submit_button("🚀 Gửi Báo Cáo Cuối Ngày Cho BM", use_container_width=True):
                    if submit_report("BC_ATL_CUOI_NGAY", "ATL — Báo cáo team cuối ngày", "21:15", content_toi):
                        st.rerun()

    # ── TAB 4: Lịch Sử Báo Cáo ATL ────────────────────────────────────────────
    with tab_his:
        st.markdown("### 📋 Lịch Sử Các Báo Cáo Của ATL")
        c.execute("""
            SELECT rule_code, report_date, submitted_at, content
            FROM reports
            WHERE rule_code LIKE 'BC_ATL_%'
            ORDER BY report_date DESC, submitted_at DESC
            LIMIT 20
        """)
        his_atl = c.fetchall()
        if his_atl:
            for h in his_atl:
                r_label = {"BC_ATL_DAU_NGAY": "🌅 BC Đầu Ngày", "BC_ATL_KHTN_SANG": "🔍 Rà Soát KHTN", "BC_ATL_CUOI_NGAY": "🌙 BC Cuối Ngày"}.get(h["rule_code"], h["rule_code"])
                with st.expander(f"{r_label} — Ngày {h['report_date']} (nộp {h['submitted_at']})"):
                    st.text(h["content"])
        else:
            st.info("Chưa có lịch sử báo cáo ATL nào.")

    conn.close()


# ─────────────────────────── ADMIN DASHBOARD ─────────────────────────────────

def render_admin():
    branch_name = get_branch_setting("branch_name", "Ocean Edu Buôn Ma Thuột")
    has_atl = get_branch_setting("has_atl", "1") == "1"
    tab_atl_title = "👩‍💼 Báo Cáo ATL" if has_atl else "📋 Báo Cáo Điều Hành (Kiêm ATL)"

    st.title(f"📊 Dashboard Quản Trị — {branch_name}")
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        "🗺️ Tổng Quan Ngày", "📅 Lịch & STEAM", tab_atl_title,
        "📆 Lập Kế Hoạch Tháng", "📈 Tiến Độ Tháng",
        "⚙️ Cấu Hình & Nhân Sự", "💰 Quỹ Vi Phạm", "📋 Báo Cáo Chi Tiết"
    ])
    with tab1: render_admin_overview()
    with tab2: render_schedule_admin()
    with tab3: render_atl_workspace(st.session_state["user_id"], st.session_state["display_name"])
    with tab4: render_monthly_planning()
    with tab5: render_monthly_progress()
    with tab6: render_admin_settings()
    with tab7: render_penalty_table(admin_view=True)
    with tab8: render_all_reports()



def render_admin_overview():
    today     = get_today()
    today_fmt = datetime.now().strftime("%d/%m/%Y — %A")
    ym        = get_ym()
    now_h     = datetime.now().hour

    # ── Header Bản Tin Sáng ────────────────────────────────────────────────────
    st.markdown(f"""
<div style="background:linear-gradient(135deg,#2D3190,#00AEEF);color:white;
    border-radius:12px;padding:18px 28px;margin-bottom:16px">
<h2 style="margin:0;font-size:1.4rem">{"🌅 BẢN TIN SÁNG" if now_h < 12 else "🌆 BẢN TIN CHIỀU" if now_h < 17 else "🌙 BẢN TIN TỐI"} — BM Hương</h2>
<p style="margin:4px 0 0;opacity:.9;font-size:.95rem">{today_fmt} &nbsp;|&nbsp; Cập nhật lúc {datetime.now().strftime("%H:%M")}</p>
</div>
""", unsafe_allow_html=True)

    conn = get_conn()
    c    = conn.cursor()

    # ══════════════════════════════════════════════════════════════════════════
    # MỤC 1 — KH TIỀM NĂNG SẮP CHỐT TRONG THÁNG
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown("### 1️⃣ Khách Hàng Tiềm Năng Dự Chốt Tháng Này")
    st.caption("Từ KHTN của toàn team — trạng thái gần chốt, sắp xếp theo ngày hẹn gần nhất")

    c.execute("""
        SELECT k.ten_kh, k.so_dien_thoai, k.lop_hoc, k.trang_thai,
               k.ngay_hen, k.buoc_tiep_theo, k.ghi_chu,
               u.display_name as ec_name
        FROM khtn_records k
        JOIN users u ON k.user_id = u.id
        WHERE k.trang_thai IN (
            'Đã giới thiệu SP','Đang cân nhắc',
            'Đã lên lịch test','Đã test — chờ chốt','Đã đóng cọc'
        )
        ORDER BY
            CASE k.trang_thai
                WHEN 'Đã đóng cọc'        THEN 1
                WHEN 'Đã test — chờ chốt' THEN 2
                WHEN 'Đã lên lịch test'   THEN 3
                WHEN 'Đang cân nhắc'      THEN 4
                ELSE 5
            END,
            k.ngay_hen ASC
    """)
    kh_list = c.fetchall()

    if kh_list:
        # Phân nhóm theo trạng thái + màu cơ hội
        co_hoi_map = {
            "Đã đóng cọc":        ("🔥 90%", "#1B5E20"),
            "Đã test — chờ chốt": ("⚡ 70%", "#2D3190"),
            "Đã lên lịch test":   ("📅 50%", "#E65100"),
            "Đang cân nhắc":      ("🤔 30%", "#F57F17"),
            "Đã giới thiệu SP":   ("👋 15%", "#555"),
        }
        rows_kh = []
        for k in kh_list:
            co_hoi, _ = co_hoi_map.get(k["trang_thai"], ("—", "#999"))
            rows_kh.append({
                "EC phụ trách":       k["ec_name"],
                "Tên KH":             k["ten_kh"],
                "SĐT":               k["so_dien_thoai"] or "—",
                "Lớp":               k["lop_hoc"],
                "Trạng thái":        k["trang_thai"],
                "% Cơ hội":          co_hoi,
                "Ngày hẹn":          k["ngay_hen"] or "Chưa đặt",
                "Bước tiếp theo":    k["buoc_tiep_theo"] or "—",
            })
        df_kh = pd.DataFrame(rows_kh)
        st.dataframe(df_kh, hide_index=True, use_container_width=True)

        # Đếm theo nhóm
        col_a, col_b, col_c, col_d = st.columns(4)
        col_a.metric("🔥 Cọc — sắp đóng HT",
                     sum(1 for k in kh_list if k["trang_thai"]=="Đã đóng cọc"))
        col_b.metric("⚡ Đã test — chờ chốt",
                     sum(1 for k in kh_list if k["trang_thai"]=="Đã test — chờ chốt"))
        col_c.metric("📅 Đã lên lịch test",
                     sum(1 for k in kh_list if k["trang_thai"]=="Đã lên lịch test"))
        col_d.metric("📋 Tổng KH đang follow",  len(kh_list))
    else:
        st.warning("⚠️ Chưa có KH tiềm năng nào được cập nhật trạng thái gần chốt. Nhắc EC cập nhật KHTN!")

    st.divider()

    # ══════════════════════════════════════════════════════════════════════════
    # MỤC 2 — KH THAM GIA SỰ KIỆN HÔM NAY
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown("### 2️⃣ Khách Hàng Tham Gia Sự Kiện Hôm Nay")
    st.caption("Từ kế hoạch sự kiện tháng + KH check-in thực tế")

    # Sự kiện tháng này
    c.execute("""SELECT ten_hoat_dong, so_luong_chi_tieu, so_luong_thuc_te,
                        doi_tuong, dia_diem, timeline, trang_thai, assigned_to
               FROM monthly_events WHERE year_month=?
               ORDER BY timeline""", (ym,))
    events = c.fetchall()

    # KH check-in hôm nay (từ chỉ số ngày)
    c.execute("""SELECT u.display_name, r.kpi_checkin, r.kpi_cuoc_goi, r.kpi_doanh_thu
               FROM reports r JOIN users u ON r.user_id=u.id
               WHERE r.rule_code='CHI_SO_NGAY' AND r.report_date=?""", (today,))
    checkin_today = c.fetchall()

    if events:
        for ev in events:
          da = ev["so_luong_thuc_te"] or 0
          ct = ev["so_luong_chi_tieu"] or 0
          pct = int(da / ct * 100) if ct > 0 else 0
          mau = "🟢" if pct >= 100 else "🟡" if pct >= 60 else "🔴"
          st.markdown(f"""<div style="background:white;border:1px solid #e0e0e0;border-radius:10px;
              padding:12px 18px;margin-bottom:8px;border-left:5px solid
              {'#1B5E20' if pct>=100 else '#F57F17' if pct>=60 else '#C62828'}">
<b>{ev['ten_hoat_dong']}</b> &nbsp;|&nbsp; 🕐 {ev['timeline'] or 'Chưa rõ giờ'} &nbsp;|&nbsp;
📍 {ev['dia_diem'] or 'Chưa xác định'}<br>
{mau} Chỉ tiêu: <b>{ct}</b> KH &nbsp;|&nbsp; Thực tế: <b>{da}</b> KH &nbsp;|&nbsp; {pct}%
&nbsp;|&nbsp; Phân công: {ev['assigned_to'] or '—'}
</div>""", unsafe_allow_html=True)
    else:
        st.info("Chưa có sự kiện nào được lập kế hoạch tháng này. Vào tab Lập KH Tháng để thêm.")

    if checkin_today:
        total_ci = sum(r["kpi_checkin"] or 0 for r in checkin_today)
        st.markdown(f"**Check-in thực tế hôm nay từ báo cáo EC:** `{total_ci}` lượt")
        no_ci = [r["display_name"] for r in checkin_today if (r["kpi_checkin"] or 0) == 0]
        if no_ci:
            st.error(f"⚠️ Các cô chưa có check-in hôm nay: **{', '.join(no_ci)}** — cần giải pháp ngay!")
    else:
        st.caption("Chưa có EC nào điền chỉ số hôm nay.")

    st.divider()

    # ══════════════════════════════════════════════════════════════════════════
    # MỤC 3 — CHỈ SỐ CUỘC GỌI >60S (ĐỊNH MỨC 20 CUỘC/NGÀY — THÁNG 488 CUỘC TRỪ 6 NGÀY OFF)
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown("### 3️⃣ Chỉ Số Cuộc Gọi >60s — Định Mức 20 Cuộc/Ngày (Tháng 488 Cuộc)")
    st.caption("📌 **Quy chế chính thức:** Định mức **20 cuộc >60s/ngày đi làm** (Tổng **488 cuộc/tháng** trừ 6 ngày OFF; BSA: 120 cuộc/tháng). Ngày OFF: 0 cuộc. **ĐẶC BIỆT: Hoàn thành ≥90% Doanh Số ➔ TỰ ĐỘNG LIÊN KẾT MIỄN ĐỊNH MỨC CUỘC GỌI.**")

    # Lấy danh sách nhân sự Tuyển Sinh & BSA (Bao gồm cả Ngô Thị Ánh Hồng)
    c.execute("""SELECT u.id, u.display_name, u.role,
                        COALESCE(mt.target_cuoc_goi_thang, 488) as tgt_thang,
                        COALESCE(mt.target_doanh_thu, 0) as tgt_dt,
                        COALESCE(mt.actual_doanh_thu, 0) as act_dt
               FROM users u
               LEFT JOIN monthly_targets mt ON mt.user_id=u.id AND mt.year_month=?
               WHERE (u.role = 'EC' OR u.username = 'ketoan_hong' OR u.role = 'KeToan')
                 AND u.role NOT IN ('CM', 'cm_daotao')
                 AND (u.is_active=1 OR u.is_active IS NULL)
               ORDER BY (CASE WHEN u.role='EC' THEN 1 ELSE 2 END), u.display_name""", (ym,))
    all_users = c.fetchall()

    # Chỉ số ngày hôm nay
    c.execute("""SELECT user_id, kpi_cuoc_goi, giai_trinh, de_xuat
               FROM reports WHERE rule_code='CHI_SO_NGAY' AND report_date=?""", (today,))
    kpi_today_map = {r["user_id"]: dict(r) for r in c.fetchall()}

    rows_goi = []
    alert_chua_dat_today = []

    for u in all_users:
        uid2 = u["id"]
        tgt_m = u["tgt_thang"] or 488
        tgt_dt = u["tgt_dt"] or 0
        act_dt = u["act_dt"] or 0
        dt_pct = (act_dt / tgt_dt * 100) if tgt_dt > 0 else 0
        is_exempt = (dt_pct >= 90.0)
        
        # Ca làm việc hôm nay
        ca_today = get_shift_ca(uid2, today) or "OFF"
        is_off = (ca_today == "OFF")
        dinh_muc_chuan = 20 if tgt_m >= 400 else max(1, round(tgt_m / 24))
        dinh_muc_today = 0 if is_off else dinh_muc_chuan

        goi_hom_nay = kpi_today_map.get(uid2, {}).get("kpi_cuoc_goi", 0) or 0
        da_dien = "✅" if uid2 in kpi_today_map else "⚪"

        # Đánh giá hôm nay (Có xét miễn khi đạt >=90% doanh số)
        if is_exempt:
            danh_gia_ngay = f"🎉 Miễn gọi (Đạt {dt_pct:.0f}% DT)"
            dinh_muc_display = "🎉 Miễn (≥90% DT)"
        elif is_off:
            danh_gia_ngay = "🏖️ OFF (0c)"
            dinh_muc_display = "0 (OFF)"
        elif uid2 not in kpi_today_map:
            danh_gia_ngay = "⚪ Chưa nộp BC"
            dinh_muc_display = f"{dinh_muc_today} cuộc"
        elif goi_hom_nay >= dinh_muc_today:
            danh_gia_ngay = f"🟢 Đạt ({goi_hom_nay}c)"
            dinh_muc_display = f"{dinh_muc_today} cuộc"
        else:
            danh_gia_ngay = f"🔴 Thiếu ({goi_hom_nay}/{dinh_muc_today}c)"
            dinh_muc_display = f"{dinh_muc_today} cuộc"
            alert_chua_dat_today.append(f"{u['display_name']} (gọi {goi_hom_nay}/{dinh_muc_today}c)")

        # Tính tổng cuộc gọi trong tháng đến hiện tại
        c.execute("SELECT SUM(kpi_cuoc_goi) as tong FROM reports WHERE user_id=? AND rule_code='CHI_SO_NGAY' AND report_date LIKE ?", (uid2, ym + '%'))
        goi_thang = c.fetchone()["tong"] or 0

        # Đếm số ngày đi làm (khác OFF) tính đến hôm nay
        c.execute("SELECT COUNT(*) as cnt FROM work_shifts WHERE user_id=? AND shift_date LIKE ? AND shift_date <= ? AND ca != 'OFF'", (uid2, ym + '%', today))
        working_days_so_far = c.fetchone()["cnt"] or 0
        luy_ke_can_dat = min(tgt_m, working_days_so_far * dinh_muc_chuan)

        pct_m = (goi_thang / tgt_m * 100) if tgt_m > 0 else 0

        if is_exempt:
            tinh_trang_thang = f"🟢 Miễn gọi (Đạt {dt_pct:.0f}% DT)"
            giai_phap = f"🏆 Hoàn thành {dt_pct:.1f}% chỉ tiêu doanh thu"
        elif working_days_so_far == 0:
            tinh_trang_thang = "— Chưa có ca"
            giai_phap = kpi_today_map.get(uid2, {}).get("de_xuat", "") or kpi_today_map.get(uid2, {}).get("giai_trinh", "") or "—"
        elif goi_thang >= luy_ke_can_dat:
            tinh_trang_thang = "🟢 Đúng tiến độ"
            giai_phap = kpi_today_map.get(uid2, {}).get("de_xuat", "") or kpi_today_map.get(uid2, {}).get("giai_trinh", "") or "—"
        elif goi_thang >= luy_ke_can_dat * 0.8:
            tinh_trang_thang = "🟡 Hơi chậm"
            giai_phap = kpi_today_map.get(uid2, {}).get("de_xuat", "") or kpi_today_map.get(uid2, {}).get("giai_trinh", "") or "—"
        else:
            tinh_trang_thang = f"🔴 Chậm (thiếu {luy_ke_can_dat - goi_thang}c)"
            giai_phap = kpi_today_map.get(uid2, {}).get("de_xuat", "") or kpi_today_map.get(uid2, {}).get("giai_trinh", "") or "—"

        rows_goi.append({
            "Nhân sự (EC & BSA)":      u["display_name"],
            "Ca hôm nay":              f"🏖️ OFF" if is_off else f"💼 {ca_today}",
            "Đã điền":                 da_dien,
            "Hôm nay gọi":             f"{goi_hom_nay} cuộc" if not is_off else "0 (OFF)",
            "Định mức ngày":           dinh_muc_display,
            "Đánh giá hôm nay":        danh_gia_ngay,
            "Tổng gọi tháng":          f"{goi_thang:,} / {tgt_m:,}",
            "% Đạt tháng":             f"{pct_m:.1f}%",
            "Lũy kế cần đạt":          f"{luy_ke_can_dat} cuộc ({working_days_so_far} ngày làm)",
            "Tiến độ tháng":           tinh_trang_thang,
            "Giải pháp gọi bù":        giai_phap[:35] + "…" if len(giai_phap) > 35 else giai_phap,
        })

    df_goi = pd.DataFrame(rows_goi)
    st.dataframe(df_goi, hide_index=True, use_container_width=True)

    if alert_chua_dat_today:
        st.error(f"🚨 Cuộc gọi hôm nay chưa đạt định mức: **{', '.join(alert_chua_dat_today)}** — cần theo dõi gọi bù vào chặng kế tiếp!")
    chua_dien = [u["display_name"] for u in all_users if u["id"] not in kpi_today_map and get_shift_ca(u["id"], today) != "OFF" and not ((u["tgt_dt"] or 0) > 0 and (u["act_dt"] or 0) / (u["tgt_dt"] or 1) >= 0.9)]
    if chua_dien:
        st.warning(f"⚠️ Các cô đi làm hôm nay chưa điền chỉ số ngày: **{', '.join(chua_dien)}**")

    st.divider()

    # ══════════════════════════════════════════════════════════════════════════
    # MỤC 3B — THEO DÕI CHỈ TIÊU PHÒNG ĐÀO TẠO (CM — TÁI PHÍ & CHĂM SÓC)
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown("### 🎓 Chỉ Tiêu Phòng Đào Tạo (CM — Tái Phí & Chăm Sóc)")
    st.caption("Do BM trực tiếp theo dõi chỉ tiêu tái phí & học viên — Không thuộc diện báo cáo tác chiến hằng ngày của EC Tuyển Sinh.")
    c.execute("""SELECT u.display_name, mt.position, mt.target_doanh_thu, mt.target_checkin_landau, mt.actual_doanh_thu, mt.note
               FROM monthly_targets mt
               JOIN users u ON mt.user_id=u.id
               WHERE u.role='CM' AND mt.year_month=?
               ORDER BY u.display_name""", (ym,))
    cm_targets = c.fetchall()
    if cm_targets:
        cm_rows = []
        for r in cm_targets:
            cm_rows.append({
                "Nhân sự Đào Tạo": r["display_name"],
                "Vị trí": r["position"],
                "Chỉ tiêu Doanh thu": f"{r['target_doanh_thu']:,.0f}K",
                "Chỉ tiêu Học viên": f"{r['target_checkin_landau']} HV",
                "Thực tế DT": f"{r['actual_doanh_thu']:,.0f}K",
                "Ghi chú nhiệm vụ": r["note"] or "Tái phí & Chăm sóc học viên"
            })
        st.dataframe(pd.DataFrame(cm_rows), hide_index=True, use_container_width=True)
        col_cm1, col_cm2 = st.columns(2)
        total_cm_dt = sum(r["target_doanh_thu"] for r in cm_targets)
        total_cm_hv = sum(r["target_checkin_landau"] for r in cm_targets)
        col_cm1.metric("Tổng Chỉ Tiêu DT Đào Tạo", f"{total_cm_dt:,.0f}K ({total_cm_dt/1000:,.1f} Triệu)")
        col_cm2.metric("Tổng Học Viên Phụ Trách", f"{total_cm_hv} HV")
    else:
        st.info("Chưa có chỉ tiêu cho Phòng Đào Tạo.")

    st.divider()

    # ══════════════════════════════════════════════════════════════════════════
    # MỤC 4 — KẾ HOẠCH BOOTH HIỆN DIỆN
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown("### 4️⃣ Kế Hoạch Hiện Diện Booth Tháng Này")
    st.caption("Từ bảng kế hoạch sự kiện — lọc theo BOOTH")

    c.execute("""SELECT ten_hoat_dong, timeline, dia_diem, so_luong_chi_tieu,
                        so_luong_thuc_te, assigned_to, trang_thai, noi_dung
               FROM monthly_events
               WHERE year_month=? AND (
                   LOWER(ten_hoat_dong) LIKE '%booth%'
                   OR LOWER(noi_dung) LIKE '%booth%'
                   OR LOWER(doi_tuong) LIKE '%booth%'
               )
               ORDER BY timeline""", (ym,))
    booths = c.fetchall()

    # Cũng lấy báo cáo BOOTH_PLAN nếu có
    c.execute("""SELECT u.display_name, r.content, r.submitted_at
               FROM reports r JOIN users u ON r.user_id=u.id
               WHERE r.rule_code='BOOTH_PLAN'
               AND r.report_date LIKE ?
               ORDER BY r.submitted_at DESC LIMIT 5""", (ym + "%",))
    booth_reports = c.fetchall()

    if booths:
        for b in booths:
            da2 = b["so_luong_thuc_te"] or 0
            ct2 = b["so_luong_chi_tieu"] or 0
            mau2 = "🟢" if da2 >= ct2 else "🔴"
            st.markdown(f"""<div style="background:#f3f4ff;border-radius:8px;padding:10px 16px;margin-bottom:6px">
📍 <b>{b['ten_hoat_dong']}</b> | 🕐 {b['timeline'] or '—'} | 📌 {b['dia_diem'] or '—'}<br>
{mau2} KH: {da2}/{ct2} | Phụ trách: {b['assigned_to'] or '—'} | Trạng thái: {b['trang_thai']}
</div>""", unsafe_allow_html=True)
    elif booth_reports:
        for br in booth_reports:
            st.markdown(f"📋 **{br['display_name']}** — {br['submitted_at'][:10]}: {br['content'][:120]}…")
    else:
        st.info("Chưa có kế hoạch Booth. Vào tab Lập KH Tháng → Thêm sự kiện loại Booth.")

    st.divider()

    # ══════════════════════════════════════════════════════════════════════════
    # MỤC 5 — EBOOK & QR CODE ĐẢM BẢO CHƯA
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown("### 5️⃣ Chỉ Số Ebook & QR Code — Đảm Bảo Chưa?")

    c.execute("""SELECT u.id, u.display_name,
                        COALESCE(t.target_ebook,0) as tgt_e,
                        COALESCE(t.target_qr,0)    as tgt_q,
                        COALESCE((SELECT COUNT(*) FROM ebook_qr_records
                                  WHERE user_id=u.id AND year_month=? AND type='ebook'),0) as done_e,
                        COALESCE((SELECT COUNT(*) FROM ebook_qr_records
                                  WHERE user_id=u.id AND year_month=? AND type='qr'),0)    as done_q
               FROM users u
               LEFT JOIN ebook_qr_targets t ON t.user_id=u.id AND t.year_month=?
               WHERE (u.is_active=1 OR u.is_active IS NULL) AND (t.target_ebook>0 OR t.target_qr>0)
               ORDER BY u.display_name""", (ym, ym, ym))
    eq_rows = c.fetchall()
    conn.close()

    if eq_rows:
        chua_du_ebook = []
        chua_du_qr    = []
        rows_eq = []
        for r in eq_rows:
            thieu_e = max(0, r["tgt_e"] - r["done_e"])
            thieu_q = max(0, r["tgt_q"] - r["done_q"])
            pct_e = int(r["done_e"]/r["tgt_e"]*100) if r["tgt_e"]>0 else 100
            pct_q = int(r["done_q"]/r["tgt_q"]*100) if r["tgt_q"]>0 else 100
            if thieu_e > 0: chua_du_ebook.append(f"{r['display_name']} (còn thiếu {thieu_e})")
            if thieu_q > 0: chua_du_qr.append(f"{r['display_name']} (còn thiếu {thieu_q})")
            rows_eq.append({
                "Nhân sự":      r["display_name"],
                "Ebook đã làm": f"{r['done_e']}/{r['tgt_e']}",
                "Ebook %":      f"{'✅' if pct_e>=100 else '🔴'} {pct_e}%",
                "QR đã làm":    f"{r['done_q']}/{r['tgt_q']}",
                "QR %":         f"{'✅' if pct_q>=100 else '🔴'} {pct_q}%",
                "Phạt Ebook":   f"{thieu_e*50000:,}đ" if thieu_e else "—",
                "Phạt QR":      f"{thieu_q*50000:,}đ" if thieu_q else "—",
            })
        st.dataframe(pd.DataFrame(rows_eq), hide_index=True, use_container_width=True)
        if chua_du_ebook:
            st.error(f"📚 Ebook chưa đủ: **{' | '.join(chua_du_ebook)}**")
        if chua_du_qr:
            st.error(f"📲 QR chưa đủ: **{' | '.join(chua_du_qr)}**")
        if not chua_du_ebook and not chua_du_qr:
            st.success("✅ Toàn team đã đảm bảo chỉ tiêu Ebook & QR tháng này!")
    else:
        st.info("Chưa phân bổ chỉ tiêu Ebook/QR tháng này. Vào tab Lập KH Tháng → Phân Bổ Ebook & QR.")

    # ══════════════════════════════════════════════════════════════════════════
    # BẢNG TRẠNG THÁI BÁO CÁO (giữ nguyên — tiện kiểm tra nhanh)
    # ══════════════════════════════════════════════════════════════════════════
    st.divider()
    st.markdown("### 📋 Trạng Thái Báo Cáo Hôm Nay (Toàn Team)")
    st.caption("🟢 Đúng hạn | 🔴 Trễ/Chưa nộp quá giờ | 🟡 Có giải trình | ⚪ Chưa đến deadline")
    conn4 = get_conn()
    c4    = conn4.cursor()
    c4.execute("SELECT id, display_name, role FROM users WHERE role IN ('EC','Admin') ORDER BY role DESC, display_name")
    users4 = c4.fetchall()
    c4.execute("SELECT code, rule_name FROM rules WHERE frequency IN ('daily','weekly_thu','weekly_sun')")
    rules4 = c4.fetchall()
    conn4.close()

    cols_bc = ["Nhân sự"] + [r["rule_name"][:16]+"…" if len(r["rule_name"])>16 else r["rule_name"] for r in rules4]
    rows_bc = []
    for user in users4:
        row = [f"{'🟠' if user['role']=='Admin' else '🔵'} {user['display_name']}"]
        for rule in rules4:
            _dl = get_deadline(rule["code"], user["id"], today)
            if _dl is None:
                row.append("OFF"); continue
            _pd = period_date(rule["code"])
            row.append(STATUS_COLORS.get(get_report_status(user["id"], rule["code"], _pd, _dl), "⚪"))
        rows_bc.append(row)
    st.dataframe(pd.DataFrame(rows_bc, columns=cols_bc), hide_index=True, use_container_width=True)

    # ══════════════════════════════════════════════════════════════════════════
    # MỤC 6 — VÒNG TRÒN KIỂM TRA ĐỒNG ĐỘI (PEER CHECK) HÔM NAY
    # ══════════════════════════════════════════════════════════════════════════
    st.divider()
    st.markdown("### 6️⃣ Giám Sát Vòng Tròn Kiểm Tra Đồng Đội (Peer Check) Hôm Nay")
    st.caption("Admin/BM theo dõi việc EC kiểm tra bài đăng FB/Zalo và tương tác nhóm lẫn nhau.")

    conn_pc = get_conn()
    c_pc = conn_pc.cursor()
    c_pc.execute("""
        SELECT pa.checker_id, u1.display_name as checker_name,
               pa.checkee_id, u2.display_name as checkee_name
        FROM peer_assignments pa
        JOIN users u1 ON pa.checker_id = u1.id
        JOIN users u2 ON pa.checkee_id = u2.id
        WHERE pa.year_month=?
        ORDER BY u1.display_name
    """, (ym,))
    peer_pairs = c_pc.fetchall()

    if not peer_pairs:
        st.info("Chưa thiết lập cặp kiểm tra chéo tháng này. Vào tab 'Cấu Hình → Vòng Tròn Kiểm Tra' để thiết lập.")
        conn_pc.close()
    else:
        pc_rows = []
        penalties_to_give = []
        for pair in peer_pairs:
            cid, kid = pair["checker_id"], pair["checkee_id"]
            c_pc.execute("SELECT check_type, result, link_evidence, note, checked_at FROM peer_checks WHERE checker_id=? AND checkee_id=? AND check_date=?", (cid, kid, today))
            checks = {r["check_type"]: r for r in c_pc.fetchall()}
            
            mkt = checks.get("MKT_FB_ZALO")
            mkt_st = "✅ Đạt" if mkt and mkt["result"]==1 else ("❌ Chưa đạt" if mkt else "⚪ Chưa check")
            if mkt and mkt["result"] == 0:
                penalties_to_give.append((kid, pair["checkee_name"], "MKT_FB_ZALO", mkt.get("note", "")))
                
            tt = checks.get("TUONG_TAC")
            tt_st = "✅ Đạt" if tt and tt["result"]==1 else ("❌ Chưa đạt" if tt else "⚪ Chưa check")
            if tt and tt["result"] == 0:
                penalties_to_give.append((kid, pair["checkee_name"], "TUONG_TAC", tt.get("note", "")))

            bc_d = checks.get("BC_DAU_CA")
            bc_d_st = "✅ Đạt" if bc_d and bc_d["result"]==1 else ("❌ Chưa đạt" if bc_d else "⚪ Chưa check")

            bc_c = checks.get("BC_CUOI_CA")
            bc_c_st = "✅ Đạt" if bc_c and bc_c["result"]==1 else ("❌ Chưa đạt" if bc_c else "⚪ Chưa check")

            pc_rows.append({
                "Người KT": pair["checker_name"],
                "Người được KT": pair["checkee_name"],
                "Đăng bài FB+Zalo": mkt_st,
                "Tương tác nhóm": tt_st,
                "BC Đầu Ca": bc_d_st,
                "BC Cuối Ca": bc_c_st,
                "Link bằng chứng": (mkt.get("link_evidence", "") if mkt else "") or "—"
            })
        conn_pc.close()
        st.dataframe(pd.DataFrame(pc_rows), hide_index=True, use_container_width=True)

        if penalties_to_give:
            st.warning(f"⚠️ Phát hiện {len(penalties_to_give)} hạng mục vi phạm do đồng đội báo Chưa Đạt.")
            for p_kid, p_kname, p_ctype, p_note in penalties_to_give:
                col_p1, col_p2 = st.columns([3, 1])
                col_p1.write(f"🔴 **{p_kname}** — Lỗi: {p_ctype} ({p_note or 'Đồng đội báo Chưa Đạt'})")
                if col_p2.button(f"Ghi Phạt 50K", key=f"pen_peer_{p_kid}_{p_ctype}"):
                    _cp = get_conn()
                    _c_cur = _cp.cursor()
                    _reason = f"Vi phạm kỷ luật (Đồng đội kiểm tra chưa đạt): {p_ctype} ({p_note})"
                    _c_cur.execute("INSERT INTO penalties(user_id,report_id,amount,reason,penalty_date) VALUES(?,?,?,?,?)",
                                   (p_kid, None, 50000, _reason, today))
                    _cp.commit()
                    _cp.close()
                    st.success(f"Đã ghi phạt {p_kname} 50.000đ!")
                    st.rerun()




# ─────────────────────────── QUẢN LÝ NHÂN SỰ CHUNG (BM & HỒNG) ─────────────────

def render_staff_management(is_ketoan=False):
    ym = get_ym()
    conn = get_conn()
    c = conn.cursor()

    actor = "Kế Toán Hồng" if is_ketoan else "BM Hương / Admin"
    st.markdown(f"### 👥 Quản Lý & Thêm Nhân Sự Chi Nhánh (Quyền Quản Trị: {actor})")
    st.caption("Cả Kế Toán Hồng và BM Hương đều có quyền tạo tài khoản nhân sự mới theo chuẩn `<ten>_<vitri>` và mật khẩu mặc định `123456`. Nhân sự khi nhận tài khoản sẽ bắt buộc đổi mật khẩu riêng khi đăng nhập lần đầu.")

    # Thống kê nhanh
    c.execute("SELECT COUNT(*) as total, SUM(CASE WHEN role='EC' AND (is_active=1 OR is_active IS NULL) THEN 1 ELSE 0 END) as total_ec, SUM(CASE WHEN is_active=1 OR is_active IS NULL THEN 1 ELSE 0 END) as active FROM users")
    stat_u = c.fetchone()
    col_u1, col_u2, col_u3 = st.columns(3)
    col_u1.metric("Tổng tài khoản", stat_u["total"] or 0)
    col_u2.metric("Đang hoạt động", stat_u["active"] or 0)
    col_u3.metric("Tư vấn viên (EC) hoạt động", stat_u["total_ec"] or 0)

    # ── Form Thêm Nhân Sự Mới ─────────────────────────────────────────────
    with st.expander("➕ Thêm Nhân Sự Mới Vào Chi Nhánh (Tự Động Tạo Tên <ten>_<vitri> & Pass 123456)", expanded=False):
        with st.form(f"form_add_new_staff_{'kt' if is_ketoan else 'admin'}"):
            col_a1, col_a2 = st.columns(2)
            new_display_name = col_a1.text_input("Họ và tên nhân sự:", placeholder="VD: Lê Thị Hồng Nhung")
            new_role = col_a2.selectbox("Vị trí công tác:", ["EC", "KeToan", "ATL"],
                                        format_func=lambda x: {
                                            "EC": "EC — Chuyên viên tư vấn tuyển sinh",
                                            "KeToan": "KeToan — Kế toán chi nhánh & BSA",
                                            "ATL": "ATL — Trợ lý trưởng nhóm"
                                        }.get(x, x))

            st.caption("Tên đăng nhập chuẩn: `<ten>_<vitri>`, mật khẩu mặc định `123456` (bắt buộc đổi khi nhận tài khoản).")

            if st.form_submit_button("🚀 Lưu & Tạo Tài Khoản Cho Nhân Sự Mới", use_container_width=True, type="primary"):
                clean_name = new_display_name.strip()
                if not clean_name:
                    st.error("Vui lòng nhập họ và tên nhân sự!")
                else:
                    std_user = make_standard_username(clean_name, new_role)
                    # Kiểm tra trùng username
                    c.execute("SELECT id FROM users WHERE username=?", (std_user,))
                    if c.fetchone():
                        std_user = f"{std_user}2"

                    full_display = f"{clean_name} ({new_role})"
                    c.execute("""
                        INSERT INTO users(username, display_name, password, role, is_active)
                        VALUES(?,?,?,?,1)
                    """, (std_user, full_display, hash_pw("123456"), new_role))
                    new_id = c.lastrowid

                    # Cấp chỉ tiêu mặc định nếu là EC
                    if new_role == "EC":
                        c.execute("""
                            INSERT OR IGNORE INTO monthly_targets(year_month, user_id, position, target_doanh_thu, target_cuoc_goi_thang, target_checkin_landau)
                            VALUES(?,?,?,107000,488,5)
                        """, (ym, new_id, "EC"))
                        c.execute("""
                            INSERT OR IGNORE INTO ebook_qr_targets(year_month, user_id, target_ebook, target_qr)
                            VALUES(?,?,10,17)
                        """, (ym, new_id))

                    conn.commit()
                    st.success(f"🎉 ĐÃ TẠO TÀI KHOẢN THÀNH CÔNG!\n\n• **Tên đăng nhập:** `{std_user}`\n• **Mật khẩu khởi tạo:** `123456`\n• **Họ tên:** {full_display}\n\n👉 Bạn hãy gửi tên đăng nhập `{std_user}` và mật khẩu `123456` cho nhân sự mới. Khi vào app lần đầu, hệ thống sẽ tự động yêu cầu họ đổi mật khẩu riêng!")
                    conn.close()
                    st.rerun()

    st.markdown("---")
    st.markdown("#### 📋 Danh Sách Nhân Sự Hiện Có")

    c.execute("SELECT id, username, display_name, role, is_active FROM users WHERE role NOT IN ('CM', 'cm_daotao') ORDER BY is_active DESC, role, display_name")
    all_staff = c.fetchall()

    role_badge = {"Admin": "🔴 BM/Admin", "BM": "🔴 Giám Đốc (BM)", "ATL": "🟠 Trợ Lý (ATL)", "KeToan": "🔵 Kế Toán", "EC": "🟢 Tuyển Sinh (EC)", "CM": "🎓 Đào Tạo (CM)"}

    for u in all_staff:
        uid_cur = u["id"]
        is_act = (u["is_active"] == 1 or u["is_active"] is None)
        act_badge = "🟢 Đang làm việc" if is_act else "⚪ Đã nghỉ việc (Khóa)"
        role_label = role_badge.get(u["role"], u["role"])

        with st.expander(f"{'✅' if is_act else '⛔'} {u['display_name']} — User: `{u['username']}` — {role_label} — {act_badge}"):
            with st.form(f"edit_staff_form_{'kt' if is_ketoan else 'admin'}_{uid_cur}"):
                c_e1, c_e2 = st.columns(2)
                edit_name = c_e1.text_input("Họ tên hiển thị:", value=u["display_name"])
                
                role_options = ["EC", "CM", "KeToan", "ATL", "BM", "Admin"]
                cur_role_idx = role_options.index(u["role"]) if u["role"] in role_options else 0
                edit_role = c_e2.selectbox("Vai trò:", role_options, index=cur_role_idx,
                                          format_func=lambda x: {"EC": "EC — Tuyển sinh", "CM": "CM — Đào tạo", "KeToan": "KeToan — Kế toán", "ATL": "ATL — Trợ lý", "BM": "BM — Giám đốc", "Admin": "Admin"}.get(x, x))

                c_e3, c_e4 = st.columns(2)
                reset_pass = c_e3.checkbox("Đặt lại mật khẩu về mặc định 123456", key=f"rst_{'kt' if is_ketoan else 'ad'}_{uid_cur}")
                edit_status = c_e4.selectbox("Trạng thái làm việc:", ["Đang làm việc", "Đã nghỉ việc / Khóa tài khoản"],
                                            index=0 if is_act else 1)

                col_btn1, col_btn2 = st.columns([3, 1])
                if col_btn1.form_submit_button("💾 Cập Nhật Thông Tin", use_container_width=True):
                    act_val = 1 if edit_status == "Đang làm việc" else 0
                    if reset_pass:
                        c.execute("UPDATE users SET display_name=?, role=?, password=?, is_active=? WHERE id=?",
                                  (edit_name.strip(), edit_role, hash_pw("123456"), act_val, uid_cur))
                        st.info("Đã đặt lại mật khẩu về 123456 (Nhân viên sẽ được yêu cầu đổi mật khẩu khi đăng nhập).")
                    else:
                        c.execute("UPDATE users SET display_name=?, role=?, is_active=? WHERE id=?",
                                  (edit_name.strip(), edit_role, act_val, uid_cur))
                    conn.commit()
                    st.success(f"Đã cập nhật thông tin cho {edit_name}!")
                    conn.close()
                    st.rerun()

            col_del_info, col_del_btn = st.columns([3, 1])
            c.execute("SELECT COUNT(*) FROM reports WHERE user_id=?", (uid_cur,))
            has_reports = c.fetchone()[0] > 0
            if not has_reports:
                if col_del_btn.button("🗑️ Xóa Vĩnh Viễn", key=f"del_u_{'kt' if is_ketoan else 'ad'}_{uid_cur}"):
                    c.execute("DELETE FROM users WHERE id=?", (uid_cur,))
                    conn.commit()
                    st.success(f"Đã xóa vĩnh viễn tài khoản {u['username']}!")
                    conn.close()
                    st.rerun()
            else:
                col_del_info.caption("*(Tài khoản đã có báo cáo lịch sử — hệ thống chuyển sang 'Đã nghỉ việc' để bảo toàn dữ liệu đối soát kế toán)*")
    conn.close()


def render_admin_settings():
    ym = get_ym()
    conn = get_conn()
    c = conn.cursor()

    st.subheader("⚙️ Cấu Hình Vận Hành PTS & Quản Lý Nhân Sự")

    tab_s1, tab_s2, tab_s3, tab_s4 = st.tabs([
        "👥 Quản Lý Nhân Sự & Tài Khoản",
        "🏛️ Mô Hình Vận Hành PTS",
        "🔄 Vòng Tròn Peer Check",
        "🎯 Phân Công Nhiệm Vụ Tháng & Quy Chế"
    ])

    # ── TAB S1: QUẢN LÝ NHÂN SỰ & TÀI KHOẢN ──────────────────────────────────
    with tab_s1:
        render_staff_management(is_ketoan=False)

    # ── TAB S2: MÔ HÌNH VẬN HÀNH PTS ─────────────────────────────────────────
    with tab_s2:
        st.markdown("### 🏛️ Cấu Hình Cơ Cấu Vận Hành PTS")
        st.caption("Thiết lập chi nhánh vận hành theo mô hình có vị trí ATL hay BM kiêm nhiệm toàn bộ.")

        cur_branch = get_branch_setting("branch_name", "Ocean Edu Buôn Ma Thuột")
        cur_has_atl = get_branch_setting("has_atl", "1") == "1"

        with st.form("form_branch_config"):
            set_bname = st.text_input("Tên chi nhánh:", value=cur_branch)
            
            cur_pin = get_branch_setting("branch_pin", "OE2026")
            set_pin = st.text_input("Mã xác thực nội bộ (cho nhân sự mới tự đăng ký):", value=cur_pin, help="Mã này cung cấp cho nhân viên mới để họ tự đăng ký tài khoản")
            st.caption("📌 *Đổi mã này bất cứ lúc nào nếu muốn ngăn người ngoài tự tạo tài khoản.*")

            st.markdown("#### Cơ Cấu Vị Trí Quản Lý Tuyển Sinh:")
            mode_choice = st.radio(
                "Chọn mô hình áp dụng cho chi nhánh:",
                [
                    "Có vị trí ATL (Trợ lý trưởng nhóm điều hành tác chiến team, BM quản lý chiến lược & đối ngoại)",
                    "BM kiêm nhiệm toàn bộ (Chi nhánh tinh gọn, chưa có ATL — BM trực tiếp điều hành và báo cáo Vùng)"
                ],
                index=0 if cur_has_atl else 1
            )

            st.markdown(f"""
            <div style="background:#e8f4fd; border-radius:8px; padding:12px 16px; margin:10px 0; font-size:0.88rem">
            <b>💡 Ý nghĩa vận hành của 2 chế độ:</b><br>
            • <b>Chế độ Có ATL:</b> App sẽ có riêng Tab <b>👩‍💼 Báo Cáo ATL</b> để bạn ATL điền 3 báo cáo (KHTN sáng, BC đầu ngày, BC cuối ngày) gửi cho BM duyệt.<br>
            • <b>Chế độ BM kiêm nhiệm:</b> Tab sẽ tự đổi tên thành <b>📋 Báo Cáo Điều Hành (Kiêm ATL)</b>. BM trực tiếp rà soát số liệu team và bấm gửi báo cáo lên Vùng / Hội sở. Hệ thống không ghi lỗi phạt thiếu ATL.
            </div>
            """, unsafe_allow_html=True)

            if st.form_submit_button("💾 Lưu Cấu Hình Chi Nhánh", use_container_width=True):
                new_has_atl_val = "1" if "Có vị trí ATL" in mode_choice else "0"
                set_branch_setting("branch_name", set_bname.strip())
                set_branch_setting("branch_pin", set_pin.strip())
                set_branch_setting("has_atl", new_has_atl_val)
                st.success("Đã lưu cấu hình chi nhánh & mã xác thực thành công!")
                conn.close()
                st.rerun()

    # ── TAB S3: VÒNG TRÒN PEER CHECK ──────────────────────────────────────────
    with tab_s3:
        st.markdown("### 🔄 Vòng Tròn Kiểm Tra Đồng Đội (Peer Check) — Tháng Này")
        st.caption("Mỗi người sẽ được phân công kiểm tra 1 đồng đội về: Đăng bài MKT, Tương tác nhóm, Báo cáo đầu/cuối ca. Không ai tự chấm điểm cho mình.")

        c.execute("SELECT id, display_name FROM users WHERE (is_active=1 OR is_active IS NULL) AND role IN ('EC','Admin','BM','ATL') ORDER BY display_name")
        users_ec = c.fetchall()
        user_opts = {u["id"]: u["display_name"] for u in users_ec}
        user_ids = list(user_opts.keys())

        c.execute("""SELECT pa.*, u1.display_name as checker_name, u2.display_name as checkee_name
                     FROM peer_assignments pa
                     JOIN users u1 ON pa.checker_id=u1.id
                     JOIN users u2 ON pa.checkee_id=u2.id
                     WHERE pa.year_month=?""", (ym,))
        existing_peers = c.fetchall()
        if existing_peers:
            df_peers = pd.DataFrame([{"Người kiểm tra": r["checker_name"], "Người được kiểm tra": r["checkee_name"]} for r in existing_peers])
            st.dataframe(df_peers, hide_index=True, use_container_width=True)

        with st.expander("Thiết lập / Thay đổi phân công Peer Check tháng này"):
            with st.form("peer_assign_form"):
                st.caption("Chọn từng cặp: Người A sẽ kiểm tra Người B")
                pairs = []
                for i, uid_c in enumerate(user_ids):
                    col_c, col_e = st.columns(2)
                    col_c.write(f"**{user_opts[uid_c]}** kiểm tra:")
                    default_idx = (i + 1) % len(user_ids)
                    _opts = [uid for uid in user_ids if uid != uid_c]
                    _cur = next((p["checkee_id"] for p in existing_peers if p["checker_id"] == uid_c), user_ids[default_idx])
                    checkee = col_e.selectbox("Người được kiểm tra", _opts,
                                              format_func=lambda x: user_opts.get(x,"?"),
                                              index=_opts.index(_cur) if _cur in _opts else 0,
                                              key=f"pair_{uid_c}", label_visibility="collapsed")
                    pairs.append((uid_c, checkee))

                if st.form_submit_button("💾 Lưu Phân Công Vòng Tròn", use_container_width=True):
                    for checker_id, checkee_id in pairs:
                        if checker_id != checkee_id:
                            c.execute("""INSERT INTO peer_assignments(year_month, checker_id, checkee_id)
                                         VALUES(?,?,?)
                                         ON CONFLICT(year_month, checker_id) DO UPDATE SET checkee_id=excluded.checkee_id""",
                                      (ym, checker_id, checkee_id))
                    conn.commit()
                    st.success("Đã lưu phân công vòng tròn kiểm tra!")
                    conn.close()
                    st.rerun()

    # ── TAB S4: DUTY THÁNG & QUY CHẾ ─────────────────────────────────────────
    with tab_s4:
        st.markdown("### 🎯 Phân Công Xoay Vòng Nhiệm Vụ Tháng")
        c.execute("SELECT id, display_name FROM users WHERE (is_active=1 OR is_active IS NULL) AND role IN ('EC','Admin','BM','ATL') ORDER BY display_name")
        users_duty = c.fetchall()
        user_opts_d = {u["id"]: u["display_name"] for u in users_duty}
        user_ids_d = list(user_opts_d.keys())

        duty_list = [
            ("EBOOK",      "Theo dõi & Đôn đốc Ebook (7 EB/nhân sự/tháng)"),
            ("BOOTH_PLAN", "Kế hoạch + Báo cáo BOOTH"),
            ("KHTN_DAILY", "Phụ trách điền KHTN Chặng"),
            ("QR_ZALO",    "Báo cáo Quét QR Zalo game"),
            ("STEAM_PLAN", "Kế hoạch STEAM hàng tuần"),
        ]
        for duty_code, duty_name in duty_list:
            c.execute("SELECT user_id FROM duty_assignments WHERE year_month=? AND duty_code=?", (ym, duty_code))
            ex = c.fetchone()
            current = ex["user_id"] if ex else (user_ids_d[0] if user_ids_d else None)
            col_a, col_b, col_c = st.columns([3, 2, 1])
            col_a.write(f"**{duty_name}**")
            sel = col_b.selectbox("", user_ids_d, format_func=lambda x: user_opts_d.get(x,"?"),
                                  index=user_ids_d.index(current) if current in user_ids_d else 0,
                                  key=f"duty_{duty_code}")
            if col_c.button("Lưu", key=f"save_duty_{duty_code}"):
                c.execute("""INSERT INTO duty_assignments(year_month, duty_code, user_id) VALUES(?,?,?)
                             ON CONFLICT(year_month, duty_code) DO UPDATE SET user_id=excluded.user_id""",
                          (ym, duty_code, sel))
                conn.commit()
                st.success(f"Đã phân công '{duty_name}' cho {user_opts_d[sel]}!")
                conn.close()
                st.rerun()

        st.markdown("---")
        st.markdown("### 📜 Bảng Quy Chế Báo Cáo & Mức Phạt Chi Nhánh")
        c.execute("SELECT code, rule_name, deadline_time, frequency, penalty_amount FROM rules ORDER BY frequency, deadline_time")
        rules = c.fetchall()
        if rules:
            st.dataframe(pd.DataFrame([dict(r) for r in rules]).rename(columns={
                "code":"Mã","rule_name":"Tên Quy Tắc","deadline_time":"Deadline","frequency":"Tần suất","penalty_amount":"Phạt (VNĐ)"}),
                hide_index=True, use_container_width=True)

    conn.close()


def render_monthly_planning():
    ym = get_ym()
    st.subheader(f"📆 Lập Kế Hoạch Tháng {datetime.now().strftime('%m/%Y')}")
    tab_a, tab_b, tab_ebook = st.tabs([
        "👤 Chỉ Tiêu Từng Nhân Sự",
        "🎯 Kế Hoạch Sự Kiện / Hoạt Động",
        "📚 Phân Bổ Ebook & QR"
    ])

    with tab_a:
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT id, display_name FROM users WHERE role IN ('EC','Admin') ORDER BY display_name")
        users = c.fetchall()
        c.execute("SELECT mt.*, u.display_name as name FROM monthly_targets mt JOIN users u ON mt.user_id=u.id WHERE mt.year_month=?", (ym,))
        existing = c.fetchall()
        conn.close()

        if existing:
            df_ex = pd.DataFrame([dict(r) for r in existing])
            st.dataframe(df_ex[["name","position","target_doanh_thu","target_cuoc_goi_chang1","target_cuoc_goi_chang2","target_checkin_landau"]].rename(columns={
                "name":"Nhân sự","position":"Vị trí","target_doanh_thu":"DT (K)",
                "target_cuoc_goi_chang1":"Gọi C1","target_cuoc_goi_chang2":"Gọi C2","target_checkin_landau":"Check-in LD"}),
                hide_index=True, use_container_width=True)

        st.markdown("---")
        sel_uid = st.selectbox("Chọn nhân sự:", [u["id"] for u in users], format_func=lambda x: next(u["display_name"] for u in users if u["id"]==x))
        conn2 = get_conn()
        c2 = conn2.cursor()
        c2.execute("SELECT * FROM monthly_targets WHERE year_month=? AND user_id=?", (ym, sel_uid))
        ex = c2.fetchone()
        conn2.close()

        with st.form(f"target_{sel_uid}"):
            col1, col2 = st.columns(2)
            with col1:
                pos_opts = ["ATL","EC 1","EC 2","EC 3","CM","BSA","SAB"]
                position = st.selectbox("Vị trí", pos_opts, index=pos_opts.index(ex["position"]) if ex and ex["position"] in pos_opts else 1)
                t_dt = st.number_input("Chỉ tiêu DT tháng (K)", min_value=0, step=1000, value=int(ex["target_doanh_thu"]) if ex else 0)
                t_goi_c1 = st.number_input("Cuộc gọi Chặng 1", min_value=0, step=10, value=ex["target_cuoc_goi_chang1"] if ex else 180)
                t_goi_c2 = st.number_input("Cuộc gọi Chặng 2", min_value=0, step=10, value=ex["target_cuoc_goi_chang2"] if ex else 180)
            with col2:
                t_ci_ld = st.number_input("Check-in Lần đầu", min_value=0, step=1, value=ex["target_checkin_landau"] if ex else 44)
                t_ci_sk = st.number_input("Check-in Sự kiện", min_value=0, step=1, value=ex["target_checkin_sk"] if ex else 44)
                t_fb = st.number_input("Data FB mới", min_value=0, step=10, value=ex["target_data_fb"] if ex else 0)
                t_zalo = st.number_input("Data Zalo mới", min_value=0, step=10, value=ex["target_data_zalo"] if ex else 0)
            note = st.text_area("Ghi chú / Điều kiện miễn phạt", value=ex["note"] if ex else "")
            if st.form_submit_button("💾 Lưu Chỉ Tiêu", use_container_width=True):
                conn3 = get_conn()
                c3 = conn3.cursor()
                c3.execute("""INSERT INTO monthly_targets(year_month,user_id,position,target_doanh_thu,
                    target_cuoc_goi_chang1,target_cuoc_goi_chang2,target_checkin_landau,
                    target_checkin_sk,target_data_fb,target_data_zalo,note)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(year_month,user_id) DO UPDATE SET
                    position=excluded.position, target_doanh_thu=excluded.target_doanh_thu,
                    target_cuoc_goi_chang1=excluded.target_cuoc_goi_chang1,
                    target_cuoc_goi_chang2=excluded.target_cuoc_goi_chang2,
                    target_checkin_landau=excluded.target_checkin_landau,
                    target_checkin_sk=excluded.target_checkin_sk,
                    target_data_fb=excluded.target_data_fb, target_data_zalo=excluded.target_data_zalo, note=excluded.note""",
                    (ym, sel_uid, position, t_dt, t_goi_c1, t_goi_c2, t_ci_ld, t_ci_sk, t_fb, t_zalo, note))
                conn3.commit()
                conn3.close()
                st.success("Đã lưu!")
                st.rerun()

    with tab_b:
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT * FROM monthly_events WHERE year_month=? ORDER BY muc_dich, id", (ym,))
        events = c.fetchall()
        conn.close()
        if events:
            ev_rows = []
            for e in events:
                pct = (e["so_luong_thuc_te"]/e["so_luong_chi_tieu"]*100) if e["so_luong_chi_tieu"]>0 else 0
                icon = "✅" if pct>=100 else ("⚠️" if pct>=50 else "🔴")
                ev_rows.append({"Mục đích":e["muc_dich"],"Hoạt động":e["ten_hoat_dong"],"Phòng ban":e["phong_ban"],
                                "Chỉ tiêu":e["so_luong_chi_tieu"],"Thực tế":e["so_luong_thuc_te"],
                                "% Đạt":f"{pct:.0f}%","Trạng thái":f"{icon} {e['trang_thai']}",
                                "Timeline":e["timeline"],"Phân công":e["assigned_to"]})
            st.dataframe(pd.DataFrame(ev_rows), hide_index=True, use_container_width=True)

        st.markdown("---")
        with st.expander("➕ Thêm Hoạt Động / Sự Kiện Mới"):
            with st.form("add_event"):
                c1, c2 = st.columns(2)
                muc_dich = c1.text_input("Mục đích")
                ten_hd = c1.text_input("Tên hoạt động")
                phong_ban = c1.text_input("Phòng ban phụ trách")
                noi_dung = c1.text_area("Nội dung triển khai")
                dia_diem = c2.text_input("Địa điểm")
                doi_tuong = c2.text_input("Đối tượng")
                so_luong = c2.number_input("Chỉ tiêu SL", min_value=0, step=1)
                timeline = c2.text_input("Timeline")
                assigned = c2.text_input("Phân công cho")
                if st.form_submit_button("Thêm Sự Kiện", use_container_width=True):
                    conn4 = get_conn()
                    c4 = conn4.cursor()
                    c4.execute("INSERT INTO monthly_events(year_month,muc_dich,ten_hoat_dong,phong_ban,noi_dung,dia_diem,doi_tuong,so_luong_chi_tieu,timeline,assigned_to,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                        (ym, muc_dich, ten_hd, phong_ban, noi_dung, dia_diem, doi_tuong, so_luong, timeline, assigned, datetime.now().strftime("%Y-%m-%d %H:%M")))
                    conn4.commit()
                    conn4.close()
                    st.success(f"Đã thêm: {ten_hd}!")
                    st.rerun()


    with tab_ebook:
        st.subheader("📚📲 Phân Bổ Chỉ Tiêu Ebook & QR — Đầu Tháng")
        st.caption("BM / ATL nhập chỉ tiêu cho từng nhân sự. EC sẽ thấy ngay trên checklist ngày.")

        conn_e = get_conn()
        ce = conn_e.cursor()
        ce.execute("SELECT id, display_name FROM users WHERE role IN ('EC','Admin') ORDER BY display_name")
        staff_list = ce.fetchall()
        conn_e.close()

        # ── Bảng tổng hợp hiện tại ────────────────────────────────────────────
        overview_rows = []
        for s in staff_list:
            te, tq, ae, aq = get_ebook_qr_stats(s["id"], ym)
            re = max(0, te - ae)
            rq = max(0, tq - aq)
            overview_rows.append({
                "Nhân sự":     s["display_name"],
                "📚 CT Ebook":  te,
                "📚 Đã làm":    ae,
                "📚 Còn thiếu": re,
                "📚 Phạt":      f"{re*50000:,}đ" if re > 0 else "✅",
                "📲 CT QR":     tq,
                "📲 Đã làm":    aq,
                "📲 Còn thiếu": rq,
                "📲 Phạt":      f"{rq*50000:,}đ" if rq > 0 else "✅",
            })
        st.dataframe(pd.DataFrame(overview_rows), hide_index=True, use_container_width=True)

        st.markdown("---")
        st.markdown("### Thiết Lập / Cập Nhật Chỉ Tiêu Từng Người")
        st.caption("Nhập chỉ tiêu Ebook và QR cho từng nhân sự. Bấm Lưu từng người.")

        for s in staff_list:
            te, tq, ae, aq = get_ebook_qr_stats(s["id"], ym)
            with st.expander(f"{'✅' if (ae>=te and aq>=tq and te>0) else '🔴'} {s['display_name']} — Ebook: {ae}/{te}  |  QR: {aq}/{tq}"):
                with st.form(f"ebook_tgt_{s['id']}"):
                    c1, c2 = st.columns(2)
                    new_te = c1.number_input("Chỉ tiêu Ebook / tháng", min_value=0, step=1, value=te, key=f"te_{s['id']}")
                    new_tq = c2.number_input("Chỉ tiêu QR Zalo / tháng", min_value=0, step=1, value=tq, key=f"tq_{s['id']}")
                    if st.form_submit_button("💾 Lưu Chỉ Tiêu", use_container_width=True):
                        conn_s = get_conn()
                        cs = conn_s.cursor()
                        cs.execute("""INSERT INTO ebook_qr_targets(year_month,user_id,target_ebook,target_qr)
                                      VALUES(?,?,?,?)
                                      ON CONFLICT(year_month,user_id) DO UPDATE SET
                                      target_ebook=excluded.target_ebook, target_qr=excluded.target_qr""",
                                   (ym, s["id"], new_te, new_tq))
                        conn_s.commit()
                        conn_s.close()
                        st.success(f"✅ Đã lưu: {s['display_name']} — Ebook: {new_te} | QR: {new_tq}")
                        st.rerun()

                # Xem danh sách SĐT đã nộp
                conn_r = get_conn()
                cr = conn_r.cursor()
                cr.execute("SELECT type, phone_number, note, added_at FROM ebook_qr_records WHERE user_id=? AND year_month=? ORDER BY type, added_at",
                           (s["id"], ym))
                recs = cr.fetchall()
                conn_r.close()
                if recs:
                    st.markdown(f"**Danh sách SĐT đã nộp ({len(recs)}):**")
                    for r in recs:
                        icon = "📚" if r["type"] == "ebook" else "📲"
                        st.markdown(f"- `{r['added_at'][:10]}` {icon} {r['phone_number']} {('— ' + r['note']) if r['note'] else ''}")

        st.markdown("---")

        # ── Tính phạt cuối tháng ──────────────────────────────────────────────
        st.markdown("### ⚡ Tính Phạt Ebook & QR (Cuối Tháng)")
        st.caption("Kiểm tra và ghi phạt cho những nhân sự chưa hoàn thành chỉ tiêu.")
        for s in staff_list:
            te, tq, ae, aq = get_ebook_qr_stats(s["id"], ym)
            re = max(0, te - ae)
            rq = max(0, tq - aq)
            total_pen = (re + rq) * 50000
            if total_pen > 0:
                col_a, col_b = st.columns([3, 1])
                col_a.warning(f"🔴 **{s['display_name']}** — Thiếu {re} Ebook + {rq} QR = **Phạt {total_pen:,}đ**")
                _cp0 = get_conn()
                _already = _cp0.execute("SELECT COUNT(*) FROM penalties WHERE user_id=? AND reason LIKE ? AND penalty_date LIKE ?",
                                        (s["id"], "Ebook thiếu%", ym + "%")).fetchone()[0]
                _cp0.close()
                if _already:
                    col_b.caption("Đã ghi phạt tháng này")
                elif col_b.button("Ghi Phạt", key=f"pen_ebook_{s['id']}"):
                    conn_p = get_conn()
                    cp = conn_p.cursor()
                    reason = f"Ebook thiếu {re} SĐT ({re*50000:,}đ) + QR thiếu {rq} SĐT ({rq*50000:,}đ)"
                    cp.execute("INSERT INTO penalties(user_id,report_id,amount,reason,penalty_date) VALUES(?,?,?,?,?)",
                               (s["id"], None, total_pen, reason, get_today()))
                    conn_p.commit()
                    conn_p.close()
                    st.success(f"Đã ghi phạt {total_pen:,}đ cho {s['display_name']}!")
                    st.rerun()


def render_monthly_progress():
    ym = get_ym()
    st.subheader(f"📈 Bảng Tổng Hợp Tiến Độ Doanh Thu Tháng {datetime.now().strftime('%m/%Y')}")
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT mt.*, u.display_name, u.role
        FROM monthly_targets mt
        JOIN users u ON mt.user_id=u.id
        WHERE mt.year_month=?
        ORDER BY mt.target_doanh_thu DESC
    """, (ym,))
    targets = c.fetchall()
    conn.close()

    if not targets:
        st.warning("Chưa có chỉ tiêu. Vào 'Lập Kế Hoạch Tháng' để nhập.")
        return

    ts_targets = [t for t in targets if t["role"] != "CM"]
    cm_targets = [t for t in targets if t["role"] == "CM"]

    total_tgt_all = sum(t["target_doanh_thu"] for t in targets)
    total_act_all = sum(t["actual_doanh_thu"] for t in targets)
    pct_all = (total_act_all/total_tgt_all*100) if total_tgt_all>0 else 0

    total_tgt_ts = sum(t["target_doanh_thu"] for t in ts_targets)
    total_act_ts = sum(t["actual_doanh_thu"] for t in ts_targets)

    total_tgt_cm = sum(t["target_doanh_thu"] for t in cm_targets)
    total_act_cm = sum(t["actual_doanh_thu"] for t in cm_targets)

    col1, col2, col3 = st.columns(3)
    col1.metric("Doanh Thu Toàn Chi Nhánh", f"{total_act_all:,.0f}K / {total_tgt_all:,.0f}K", f"{pct_all:.1f}%")
    col2.metric("DT Phòng Tuyển Sinh (EC+BSA)", f"{total_act_ts:,.0f}K / {total_tgt_ts:,.0f}K")
    col3.metric("DT Phòng Đào Tạo (Tái Phí CM)", f"{total_act_cm:,.0f}K / {total_tgt_cm:,.0f}K")

    st.markdown("---")
    st.markdown("#### 1️⃣ Phòng Tuyển Sinh (EC & Hỗ Trợ Tuyển Sinh)")
    rows_ts = []
    for t in ts_targets:
        dt_p = (t["actual_doanh_thu"]/t["target_doanh_thu"]*100) if t["target_doanh_thu"]>0 else 0
        warn = "🚨 <50%" if dt_p<50 else ("⚠️ <80%" if dt_p<80 else "🏆 Đạt!")
        rows_ts.append({
            "Nhân sự": t["display_name"],
            "Vị trí": t["position"],
            "Chỉ tiêu DT(K)": f"{t['target_doanh_thu']:,.0f}K",
            "Thực tế DT(K)": f"{t['actual_doanh_thu']:,.0f}K",
            "% Đạt DT": f"{dt_p:.1f}%",
            "Tình trạng": warn,
            "Chỉ tiêu Học viên": f"{t['target_checkin_landau']} HV",
            "Cuộc gọi đã thực hiện": t["actual_cuoc_goi"]
        })
    st.dataframe(pd.DataFrame(rows_ts), hide_index=True, use_container_width=True)

    st.markdown("#### 2️⃣ Phòng Đào Tạo (CM — Quản Trị Lớp & Tái Phí — BM Quản Lý)")
    rows_cm = []
    for t in cm_targets:
        dt_p = (t["actual_doanh_thu"]/t["target_doanh_thu"]*100) if t["target_doanh_thu"]>0 else 0
        warn = "🚨 <50%" if dt_p<50 else ("⚠️ <80%" if dt_p<80 else "🏆 Đạt!")
        rows_cm.append({
            "Nhân sự Đào Tạo": t["display_name"],
            "Vị trí": t["position"],
            "Chỉ tiêu Tái Phí(K)": f"{t['target_doanh_thu']:,.0f}K",
            "Thực tế Tái Phí(K)": f"{t['actual_doanh_thu']:,.0f}K",
            "% Đạt DT": f"{dt_p:.1f}%",
            "Tình trạng": warn,
            "Chỉ tiêu Học viên": f"{t['target_checkin_landau']} HV",
            "Ghi chú": t["note"] or "Tái phí & Chăm sóc"
        })
    st.dataframe(pd.DataFrame(rows_cm), hide_index=True, use_container_width=True)

    st.markdown("---")
    st.markdown("### Cập Nhật Thực Tế")
    sel_uid = st.selectbox("Chọn nhân sự:", [t["user_id"] for t in targets], format_func=lambda x: next(t["display_name"] for t in targets if t["user_id"]==x))
    cur = next(t for t in targets if t["user_id"]==sel_uid)
    with st.form(f"upd_{sel_uid}"):
        c1, c2, c3 = st.columns(3)
        new_dt = c1.number_input("DT thực tế (K)", min_value=0.0, step=100.0, value=float(cur["actual_doanh_thu"]))
        new_goi = c2.number_input("Cuộc gọi thực tế", min_value=0, step=1, value=cur["actual_cuoc_goi"])
        new_ci = c3.number_input("Check-in LD thực tế", min_value=0, step=1, value=cur["actual_checkin_landau"])
        if st.form_submit_button("Cập Nhật", use_container_width=True):
            conn2 = get_conn()
            c2_cur = conn2.cursor()
            c2_cur.execute("UPDATE monthly_targets SET actual_doanh_thu=?,actual_cuoc_goi=?,actual_checkin_landau=? WHERE year_month=? AND user_id=?",
                       (new_dt, new_goi, new_ci, ym, sel_uid))
            conn2.commit()
            conn2.close()
            st.success("Đã cập nhật!")
            st.rerun()


def render_all_reports():
    today = get_today()
    conn = get_conn()
    c = conn.cursor()
    c.execute("""SELECT u.display_name, r.rule_code, r.submitted_at, r.is_late, r.giai_trinh, r.de_xuat
                 FROM reports r JOIN users u ON r.user_id=u.id
                 WHERE r.report_date=? ORDER BY r.submitted_at DESC""", (today,))
    reports = c.fetchall()
    conn.close()
    if reports:
        df = pd.DataFrame([dict(r) for r in reports])
        df["is_late"] = df["is_late"].map({1:"🔴 Trễ", 0:"🟢 Đúng hạn"})
        df.columns = ["Nhân sự","Mã BC","Nộp lúc","Trễ?","Giải trình","Đề xuất"]
        st.dataframe(df, hide_index=True, use_container_width=True)
    else:
        st.info("Chưa có báo cáo nào hôm nay.")


def render_penalty_table(admin_view=False):
    conn = get_conn()
    c = conn.cursor()
    if admin_view:
        c.execute("SELECT p.id, u.display_name, p.reason, p.amount, p.penalty_date, p.is_paid FROM penalties p JOIN users u ON p.user_id=u.id ORDER BY p.penalty_date DESC")
    else:
        c.execute("SELECT p.id, u.display_name, p.reason, p.amount, p.penalty_date, p.is_paid FROM penalties p JOIN users u ON p.user_id=u.id WHERE p.user_id=? ORDER BY p.penalty_date DESC", (st.session_state["user_id"],))
    pens = c.fetchall()
    conn.close()
    if not pens:
        st.success("Chưa có vi phạm nào!")
        return
    c1, c2, c3 = st.columns(3)
    c1.metric("Tổng", f"{sum(p['amount'] for p in pens):,}đ")
    c2.metric("Đã thu", f"{sum(p['amount'] for p in pens if p['is_paid']==1):,}đ")
    
    unpaid_total = sum(p['amount'] for p in pens if p['is_paid']==0)
    c3.metric("Còn nợ", f"{unpaid_total:,}đ")

    if unpaid_total > 0:
        if not admin_view:
            st.error(f"⚠️ Bạn đang có **{unpaid_total:,}đ** chưa nộp. Vui lòng quét mã QR chuyển khoản cho Kế toán Hồng.")
            (st.image(QR_PATH, width=250) if _os0.path.exists(QR_PATH) else st.warning("Chưa có ảnh QR (qr_hong.jfif) trong thư mục app."))
        else:
            st.warning(f"⚠️ Toàn chi nhánh đang có **{unpaid_total:,}đ** chưa thu. Hãy nhắc nhở các EC!")
            with st.expander("Mã QR Của Kế Toán Hồng (Bấm để xem)"):
                (st.image(QR_PATH, width=250) if _os0.path.exists(QR_PATH) else st.warning("Chưa có ảnh QR (qr_hong.jfif) trong thư mục app."))
    else:
        st.success("Tất cả các khoản vi phạm đã được nộp đầy đủ! 🎉")
        
    st.markdown("---")
    conn2 = get_conn()
    c2_cur = conn2.cursor()
    for pen in pens:
        ca, cb, cc = st.columns([3, 1, 1])
        ca.write(f"**{pen['display_name']}** — {pen['reason']} — *{pen['penalty_date']}*")
        cb.write(f"**{pen['amount']:,}đ**")
        if pen["is_paid"] == 0:
            if admin_view:
                if cc.button("✅ Đã thu", key=f"thu_{pen['id']}"):
                    c2_cur.execute("UPDATE penalties SET is_paid=1 WHERE id=?", (pen["id"],))
                    conn2.commit()
                    st.rerun()
            else:
                cc.error("❌ Chưa nộp")
        else:
            cc.success("✅ Đã thu")
    conn2.close()

# ─────────────────────────── KẾ TOÁN ─────────────────────────────────────────

def render_ketoan():
    uid = st.session_state["user_id"]
    name = st.session_state["display_name"]
    ym = get_ym()

    st.title("💰 Kế Toán & BSA — Quản Lý Chi Nhánh & Chuyên Môn")
    st.caption("Kế toán chi nhánh & Chuyên viên BSA: Điều phối lịch ca, quỹ vi phạm, 6 Booth và chỉ tiêu cá nhân.")

    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "📅 Chia Lịch Ca & STEAM", 
        "💰 Quỹ Vi Phạm (Thu Tiền)", 
        "📝 Báo Cáo Ngày & Ebook / QR Của Tôi",
        "📊 KPI Cá Nhân (BSA)",
        "🏪 Quản Lý 6 Booth (Hồng + Trâm Anh)",
        "👥 Thêm & Quản Lý Nhân Sự (Hồng & BM)",
        "👤 Tài Khoản Của Tôi"
    ])
    with tab1:
        render_schedule_admin(is_ketoan=True)
    with tab2:
        render_penalty_table(admin_view=True)
    with tab3:
        render_ec_daily(uid, name, ym)
    with tab4:
        render_my_kpi(uid, name, ym)
    with tab5:
        st.markdown("### 🏪 Kế Hoạch 6 Điểm Booth (Ngô Thị Ánh Hồng + Nguyễn Thị Trâm Anh)")
        st.caption("Chỉ tiêu: 6 Booth trong tháng tại các TTTM Vincom, Co.opmart, các trường Tiểu học & khu vui chơi BMT.")
        
        conn_b = get_conn()
        c_b = conn_b.cursor()
        c_b.execute("""
            SELECT * FROM monthly_events 
            WHERE year_month=? AND (
                LOWER(ten_hoat_dong) LIKE '%booth%' 
                OR LOWER(noi_dung) LIKE '%booth%' 
                OR LOWER(assigned_to) LIKE '%hồng%'
            )
        """, (ym,))
        booth_events = c_b.fetchall()
        
        if booth_events:
            for b in booth_events:
                st.markdown(f"""
                <div style="background:#fff7ed; border-left:5px solid #f97316; border-radius:10px; padding:14px 18px; margin-bottom:12px;">
                    <b style="color:#c2410c; font-size:1.05rem">🏪 {b['ten_hoat_dong']}</b> &nbsp;|&nbsp; Trạng thái: <b>{b['trang_thai']}</b><br>
                    📍 Địa điểm: <b>{b['dia_diem']}</b> &nbsp;|&nbsp; 🕐 Thời gian: <b>{b['timeline']}</b><br>
                    🎯 Chỉ tiêu: <b>{b['so_luong_chi_tieu']} Booth</b> &nbsp;|&nbsp; Thực tế đã chạy: <b>{b['so_luong_thuc_te'] or 0} Booth</b><br>
                    👥 Quản lý: <b>{b['assigned_to']}</b><br>
                    📝 Nội dung: {b['noi_dung']}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Chưa có kế hoạch Booth nào được lập.")

        with st.expander("➕ Cập Nhật Tiến Độ Hoặc Thêm Điểm Booth Mới"):
            with st.form("form_update_booth"):
                b_name = st.text_input("Tên sự kiện Booth:", value="Booth Tuyển Sinh & Khảo Sát Phụ Huynh")
                b_loc = st.text_input("Địa điểm triển khai:", placeholder="VD: Sảnh TTTM Vincom BMT / Cổng trường TH")
                b_time = st.text_input("Thời gian thực hiện:", value=f"Tháng {ym}")
                b_target = st.number_input("Số lượng Booth chỉ tiêu:", min_value=1, max_value=20, value=6)
                b_actual = st.number_input("Số Booth thực tế đã hoàn thành:", min_value=0, max_value=20, value=0)
                b_status = st.selectbox("Trạng thái:", ["Đang chuẩn bị", "Đang triển khai", "Đã hoàn thành 100%"])
                b_note = st.text_area("Nội dung & Phân công nhân sự đi Booth:")

                if st.form_submit_button("💾 Lưu Kế Hoạch Booth", use_container_width=True):
                    c_b.execute("""
                        INSERT INTO monthly_events(year_month, muc_dich, ten_hoat_dong, dia_diem, timeline, so_luong_chi_tieu, so_luong_thuc_te, trang_thai, assigned_to, noi_dung, created_at)
                        VALUES(?,?,?,?,?,?,?,?,?,?,?)
                    """, (ym, "Khai thác Data", b_name, b_loc, b_time, b_target, b_actual, b_status,
                          "Ngô Thị Ánh Hồng (BSA/KT) + Nguyễn Thị Trâm Anh (EC)", b_note, get_today()))
                    conn_b.commit()
                    st.success("Đã cập nhật kế hoạch Booth!")
                    conn_b.close()
                    st.rerun()
        conn_b.close()

    with tab6:
        render_staff_management(is_ketoan=True)
    with tab7:
        render_my_profile_tab()


# ─────────────────────────── BẮT BUỘC ĐỔI MẬT KHẨU ───────────────────────────

def render_change_password_required():
    uid = st.session_state["user_id"]
    name = st.session_state["display_name"]
    username = st.session_state["username"]

    st.markdown(f"""
    <div style="background:#fff8e1; border-left:5px solid #ffa000; border-radius:10px; padding:18px 22px; margin:20px 0;">
        <h3 style="color:#b78103; margin:0 0 6px;">🔐 Thiết Lập Mật Khẩu Cá Nhân</h3>
        <p style="color:#6d4c00; font-size:0.95rem; margin:0;">
            Chào <b>{name}</b>! Bạn đang sử dụng mật khẩu khởi tạo mặc định. 
            Vui lòng đổi mật khẩu mới để bảo mật dữ liệu công việc trước khi vào hệ thống.
        </p>
    </div>
    """, unsafe_allow_html=True)

    with st.form("form_force_change_password"):
        st.markdown("#### 🔑 Nhập Mật Khẩu Mới:")
        col1, col2 = st.columns(2)
        new_p1 = col1.text_input("Mật khẩu mới (tối thiểu 4 ký tự):", type="password")
        new_p2 = col2.text_input("Xác nhận lại mật khẩu mới:", type="password")

        if st.form_submit_button("💾 Xác Nhận Đổi Mật Khẩu & Bắt Đầu Làm Việc", use_container_width=True, type="primary"):
            p1_clean = new_p1.strip()
            p2_clean = new_p2.strip()
            if not p1_clean:
                st.error("Vui lòng nhập mật khẩu mới!")
            elif len(p1_clean) < 4:
                st.error("Mật khẩu phải từ 4 ký tự trở lên!")
            elif p1_clean == "123456":
                st.error("Không được đặt lại mật khẩu mặc định 123456! Vui lòng chọn mật khẩu khác.")
            elif p1_clean != p2_clean:
                st.error("Mật khẩu xác nhận không khớp!")
            else:
                conn_ch = get_conn()
                conn_ch.execute("UPDATE users SET password=? WHERE id=?", (hash_pw(p1_clean), uid))
                conn_ch.commit()
                conn_ch.close()
                st.session_state["is_default_password"] = False
                st.success("🎉 Đổi mật khẩu thành công! Đang chuyển hướng vào không gian làm việc của bạn...")
                st.rerun()


# ─────────────────────────── PHÒNG ĐÀO TẠO (CM) VIEW ─────────────────────────

def render_cm_view():
    uid = st.session_state["user_id"]
    name = st.session_state["display_name"]
    ym = get_ym()
    st.title(f"🎓 Phòng Đào Tạo — {name}")
    st.caption("Theo dõi chỉ tiêu doanh thu tái phí và chăm sóc học viên chi nhánh.")

    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM monthly_targets WHERE user_id=? AND year_month=?", (uid, ym))
    tgt = c.fetchone()

    # Lịch STEAM
    c.execute("SELECT * FROM steam_schedule WHERE event_date >= ? ORDER BY event_date ASC", (get_today(),))
    steam_list = c.fetchall()
    conn.close()

    if tgt:
        st.markdown("### 🎯 Chỉ Tiêu Tái Phí Tháng Của Bạn")
        c1, c2, c3 = st.columns(3)
        c1.metric("Chỉ Tiêu Doanh Thu Tái Phí", f"{tgt['target_doanh_thu']:,.0f}K ({tgt['target_doanh_thu']/1000:,.1f} Triệu)")
        c2.metric("Chỉ Tiêu Học Viên Tái Phí", f"{tgt['target_checkin_landau']} Học viên")
        c3.metric("Doanh Thu Đã Đạt", f"{tgt['actual_doanh_thu']:,.0f}K")

    st.markdown("---")
    st.markdown("### 🔗 Liên Kết Dữ Liệu Phòng Đào Tạo")
    st.markdown(f"""
    <div style="background:#e8f4fd;border-left:5px solid #0070C0;border-radius:8px;padding:14px 18px;margin-bottom:14px">
    <b>📊 File Quản Lý Phòng Đào Tạo (Danh Sách Học Viên 2026, Tái Phí, Hết Phí):</b><br>
    <a href="https://docs.google.com/spreadsheets/d/15nKA3esX2kAdP9TBT4oWTNr9-Kef7SrmHQfB1zfQSyg/edit?gid=774645173#gid=774645173" target="_blank" style="color:#0070C0;font-weight:700">
    🔗 Mở Google Sheets Đào Tạo BMT &rarr;</a>
    </div>
    """, unsafe_allow_html=True)

    if steam_list:
        with st.expander("🔬 Lịch Sự Kiện STEAM Toàn Chi Nhánh", expanded=True):
            for s in steam_list:
                st.markdown(f"• 📅 **{s['event_date']}** ({s['start_time']}–{s['end_time']}): **{s['title']}** tại *{s['school_name'] or s['location']}*")



# ─────────────────────────── ROUTER ───────────────────────────────────────────

# CSS Global — màu Ocean Edu
st.markdown(f"""<style>
/* Ẩn hoàn toàn thanh công cụ Streamlit (Share, Edit, GitHub, Star, Footer, Badge) cho người dùng */
#MainMenu {visibility: hidden; display: none !important;}
header {visibility: hidden; display: none !important;}
footer {visibility: hidden; display: none !important;}
[data-testid="stToolbar"] {visibility: hidden; display: none !important;}
[data-testid="stDecoration"] {visibility: hidden; display: none !important;}
[data-testid="stStatusWidget"] {visibility: hidden; display: none !important;}
[data-testid="stAppDeployButton"] {visibility: hidden; display: none !important;}
.viewerBadge_container__r5tak {display: none !important;}
.viewerBadge_link__qRIco {display: none !important;}
[class*="viewerBadge"] {display: none !important;}
[class*="profileBadge"] {display: none !important;}
[class*="manageApp"] {display: none !important;}

/* Nút chính dùng màu xanh Ocean Edu */
.stButton > button[kind="primary"] {{
    background-color: {OE_BLUE_DARK} !important;
    border-color: {OE_BLUE_DARK} !important;
    color: white !important;
}}
.stButton > button[kind="primary"]:hover {{
    background-color: {OE_BLUE_LIGHT} !important;
    border-color: {OE_BLUE_LIGHT} !important;
}}
/* Tab active */
.stTabs [aria-selected="true"] {{
    border-bottom-color: {OE_BLUE_DARK} !important;
    color: {OE_BLUE_DARK} !important;
    font-weight: 700;
}}
/* Sidebar */
[data-testid="stSidebar"] {{
    background: linear-gradient(180deg, {OE_BLUE_DARK} 0%, #1a1f6e 100%);
}}
[data-testid="stSidebar"] * {{
    color: white !important;
}}
[data-testid="stSidebar"] .stButton > button {{
    background: rgba(255,255,255,0.15) !important;
    border: 1px solid rgba(255,255,255,0.4) !important;
    color: white !important;
}}
[data-testid="stSidebar"] .stButton > button:hover {{
    background: rgba(255,255,255,0.3) !important;
}}
</style>""", unsafe_allow_html=True)

if not st.session_state.get("logged_in", False):
    login()
    st.stop()

# ── Khi đã đăng nhập: Sidebar tinh gọn (CHỈ LOGO & THÔNG TIN CÁ NHÂN & ĐĂNG XUẤT) ─────
with st.sidebar:
    if _LOGO_SRC:
        st.markdown(f"""<div translate="no" style="padding:16px 12px 8px 12px;text-align:center">
<div style="background:white;border-radius:10px;padding:10px 14px;display:inline-block">
<img src="{_LOGO_SRC}" style="max-width:150px;height:auto">
</div>
</div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"""<div translate="no" style="padding:12px;text-align:center;font-size:1.2rem;font-weight:700;color:white">
🌊 OCEAN EDU BMT
</div>""", unsafe_allow_html=True)

    st.markdown(f"""<div translate="no" style="text-align:center;font-size:0.78rem;opacity:.8;padding:4px 0 12px 0;border-bottom:1px solid rgba(255,255,255,0.25)">
Buôn Ma Thuột — Hệ thống KPI nội bộ
</div>""", unsafe_allow_html=True)

    st.markdown(f"""<div style="padding:12px 8px 4px 8px">
<div style="font-weight:700;font-size:0.95rem">👤 {st.session_state.get('display_name', '')}</div>
<div style="font-size:0.78rem;opacity:.8">Vai trò: {st.session_state.get('role', '')}</div>
<div style="font-size:0.75rem;opacity:.7">{datetime.now().strftime('%d/%m/%Y  %H:%M')}</div>
</div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    if st.button("🚪 Đăng Xuất Khỏi Hệ Thống", use_container_width=True):
        for k in ["logged_in", "username", "role", "user_id", "display_name", "is_default_password"]:
            st.session_state[k] = False if k in ("logged_in", "is_default_password") else ""
        st.rerun()

# ── KHÔNG GIAN THAO TÁC CHÍNH (TOÀN BỘ Ở GIỮA MÀN HÌNH) ──────────────────────
if st.session_state.get("is_default_password", False):
    render_change_password_required()
    st.stop()

role = st.session_state.get("role", "")
if role in ("Admin", "BM", "ATL"):
    render_admin()
elif role == "KeToan":
    render_ketoan()
elif role == "EC":
    render_ec()
elif role == "CM":
    render_cm_view()
else:
    render_ec()
