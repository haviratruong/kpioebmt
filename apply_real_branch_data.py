import sqlite3
from datetime import datetime
import pandas as pd

def apply_real_branch_data():
    conn = sqlite3.connect('D:/OCEAN_EDU_BMT/09_APP_KPI_MANAGEMENT/kpi_app.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    ym = datetime.now().strftime("%Y-%m")
    today = datetime.now().strftime("%Y-%m-%d")

    print(f"=== BẮT ĐẦU CẬP NHẬT DỮ LIỆU THỰC TẾ CHI NHÁNH BMT (Tháng {ym}) ===")

    # 1. Cập nhật danh sách 9 nhân sự chuẩn theo ảnh
    staff_data = [
        (1, 'bm',          'BM Hương (Giám Đốc)',       'Admin', 1),
        (2, 'thuy_atl',    'Trương Thị Thủy (ATL)',     'Admin', 1),
        (3, 'ketoan_hong', 'Ngô Thị Ánh Hồng (BSA/KT)', 'KeToan', 1),
        (4, 'tram_anh',    'Nguyễn Thị Trâm Anh (EC)',  'EC', 1),
        (5, 'yen_nhi',     'Nguyễn Thị Yến Nhi (EC)',   'EC', 1),
        (6, 'anh_duong',   'Hoàng Ánh Dương (EC)',      'EC', 1),
        (7, 'mi_nhon',     'Phạm Thị Mĩ Nhơn (CM)',     'EC', 1),
        (8, 'kim_phung',   'Đoàn Thị Kim Phụng (CM)',   'EC', 1),
        (9, 'ha_thu',      'Phùng Hà Thu (CM)',         'EC', 1),
    ]

    for uid, uname, dname, role, act in staff_data:
        c.execute("""
            INSERT INTO users(id, username, display_name, password, role, is_active)
            VALUES(?,?,?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET
                username=excluded.username,
                display_name=excluded.display_name,
                role=excluded.role,
                is_active=excluded.is_active
        """, (uid, uname, dname, '123456', role, act))

    print("✓ 1. Đã cập nhật chính xác danh sách nhân sự từ ảnh thực tế:")
    for uid, uname, dname, role, _ in staff_data:
        print(f"   [{uid}] {uname:12} | {dname:26} | Role: {role}")

    # 2. Cập nhật chỉ tiêu Doanh thu, Học viên, Cuộc gọi (monthly_targets)
    # Theo ảnh:
    # Trâm Anh: 107M, 5 HV
    # Yến Nhi: 107M, 5 HV
    # Ánh Dương: 107M, 5 HV
    # Ánh Hồng (BSA): 69.55M, 3 HV
    # Mĩ Nhơn (CM): 56.35M, 3 HV
    # Kim Phụng (CM): 56.35M, 3 HV
    # Hà Thu (CM): 56.35M, 3 HV
    # Cuộc gọi: EC = 180, CM = 45, BSA = 45
    targets_data = [
        (4, "EC",  107000, 180, 180, 5, 0, "Chỉ tiêu căn bản T9: 107M (5 HV)"),
        (5, "EC",  107000, 180, 180, 5, 0, "Chỉ tiêu căn bản T9: 107M (5 HV)"),
        (6, "EC",  107000, 180, 180, 5, 0, "Chỉ tiêu căn bản T9: 107M (5 HV)"),
        (3, "BSA",  69550,  45,  45, 3, 0, "Chỉ tiêu căn bản T9: 69.55M (3 HV)"),
        (7, "CM",   56350,  45,  45, 3, 0, "Chỉ tiêu căn bản T9: 56.35M (3 HV)"),
        (8, "CM",   56350,  45,  45, 3, 0, "Chỉ tiêu căn bản T9: 56.35M (3 HV)"),
        (9, "CM",   56350,  45,  45, 3, 0, "Chỉ tiêu căn bản T9: 56.35M (3 HV)"),
    ]

    for uid, pos, dt_k, cg1, cg2, hv, sk, note in targets_data:
        c.execute("""
            INSERT INTO monthly_targets(year_month, user_id, position, target_doanh_thu, target_cuoc_goi_chang1, target_cuoc_goi_chang2, target_checkin_landau, target_checkin_sk, note)
            VALUES(?,?,?,?,?,?,?,?,?)
            ON CONFLICT(year_month, user_id) DO UPDATE SET
                position=excluded.position,
                target_doanh_thu=excluded.target_doanh_thu,
                target_cuoc_goi_chang1=excluded.target_cuoc_goi_chang1,
                target_cuoc_goi_chang2=excluded.target_cuoc_goi_chang2,
                target_checkin_landau=excluded.target_checkin_landau,
                note=excluded.note
        """, (ym, uid, pos, dt_k, cg1, cg2, hv, sk, note))

    print("✓ 2. Đã nạp chỉ tiêu Doanh thu & Cuộc gọi chuẩn từ bảng ảnh.")

    # 3. Phân bổ Ebook: 40 cái chia đều (cả Ánh Hồng cũng có, trừ BM)
    # 7 nhân sự: 40 / 7 = 5.71.
    # Phân bổ: 3 EC (6 cuốn), Ánh Hồng BSA/KT (7 cuốn), 3 CM (5 cuốn) => Tổng = 6*3 + 7 + 5*3 = 40 cuốn tròn!
    # Và Zalo app QR: 70 cái chia đều cho 7 nhân sự => Mỗi người đúng 10 QR!
    ebook_qr_alloc = [
        (4, 6, 10),  # Trâm Anh: 6 Ebook, 10 QR
        (5, 6, 10),  # Yến Nhi: 6 Ebook, 10 QR
        (6, 6, 10),  # Ánh Dương: 6 Ebook, 10 QR
        (3, 7, 10),  # Ánh Hồng (Kế toán/BSA): 7 Ebook, 10 QR
        (7, 5, 10),  # Mĩ Nhơn: 5 Ebook, 10 QR
        (8, 5, 10),  # Kim Phụng: 5 Ebook, 10 QR
        (9, 5, 10),  # Hà Thu: 5 Ebook, 10 QR
    ]

    for uid, eb_tgt, qr_tgt in ebook_qr_alloc:
        c.execute("""
            INSERT INTO ebook_qr_targets(year_month, user_id, target_ebook, target_qr)
            VALUES(?,?,?,?)
            ON CONFLICT(year_month, user_id) DO UPDATE SET
                target_ebook=excluded.target_ebook,
                target_qr=excluded.target_qr
        """, (ym, uid, eb_tgt, qr_tgt))

    print("✓ 3. Đã phân bổ Ebook (40 cuốn) & QR Zalo Game (70 lượt) cho 7 nhân sự:")
    for uid, eb, qr in ebook_qr_alloc:
        name_row = c.execute("SELECT display_name FROM users WHERE id=?", (uid,)).fetchone()
        print(f"   - {name_row['display_name']:26}: Ebook = {eb} | QR Zalo = {qr}")

    # 4. Kế hoạch BOOTH: 6 cái (HỒNG + TRÂM ANH QUẢN LÝ)
    c.execute("DELETE FROM monthly_events WHERE year_month=? AND ten_hoat_dong LIKE '%Booth%'", (ym,))
    c.execute("""
        INSERT INTO monthly_events(year_month, muc_dich, ten_hoat_dong, phong_ban, noi_dung, dia_diem, doi_tuong, so_luong_chi_tieu, so_luong_thuc_te, timeline, trang_thai, assigned_to, created_at)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (ym, "Khai thác Data & Quảng bá thương hiệu", "Kế Hoạch Booth Hiện Diện Chi Nhánh (6 Booth)", "Tuyển sinh & Đào tạo",
          "Triển khai 6 điểm Booth tại TTTM Vincom, Co.opmart, các trường Tiểu học & khu vui chơi BMT. Quét mã QR Zalo game và phát Ebook.",
          "Vincom Plaza BMT, Co.opmart, Trường TH Lê Quý Đôn...", "Phụ huynh & Học sinh 3-16 tuổi",
          6, 0, f"Tháng {ym}", "Đang thực hiện", "Ngô Thị Ánh Hồng (BSA/KT) + Nguyễn Thị Trâm Anh (EC)", today))

    # Gán duty BOOTH_PLAN trong duty_assignments cho Trâm Anh & Ánh Hồng
    c.execute("""
        INSERT INTO duty_assignments(year_month, duty_code, user_id, note)
        VALUES(?,?,?,?)
        ON CONFLICT(year_month, duty_code) DO UPDATE SET user_id=excluded.user_id, note=excluded.note
    """, (ym, "BOOTH_PLAN", 4, "Trâm Anh phối hợp cùng Ánh Hồng quản lý 6 Booth"))

    print("✓ 4. Đã lưu Kế Hoạch 6 Booth: Giao Ngô Thị Ánh Hồng + Nguyễn Thị Trâm Anh đồng quản lý.")

    # 5. Phân công vòng tròn kiểm tra chéo (Peer Check) xoay vòng 7 nhân sự
    # 3 -> 4 -> 5 -> 6 -> 7 -> 8 -> 9 -> 3
    peer_cycle = [
        (3, 4), # Hồng check Trâm Anh
        (4, 5), # Trâm Anh check Yến Nhi
        (5, 6), # Yến Nhi check Ánh Dương
        (6, 7), # Ánh Dương check Mĩ Nhơn
        (7, 8), # Mĩ Nhơn check Kim Phụng
        (8, 9), # Kim Phụng check Hà Thu
        (9, 3), # Hà Thu check Hồng
    ]
    for chk, chkee in peer_cycle:
        c.execute("""
            INSERT INTO peer_assignments(year_month, checker_id, checkee_id)
            VALUES(?,?,?)
            ON CONFLICT(year_month, checker_id) DO UPDATE SET checkee_id=excluded.checkee_id
        """, (ym, chk, chkee))

    print("✓ 5. Đã thiết lập Vòng Tròn Peer Check khép kín 7 nhân sự.")

    # 6. Chia lịch ca làm việc tuần này cho tất cả nhân sự
    d_obj = datetime.now().date()
    monday = d_obj - pd.Timedelta(days=d_obj.weekday())
    shift_assignments = {
        4: "P1", # Trâm Anh: P1 (07:20 - 17:40)
        5: "P2", # Yến Nhi: P2 (09:00 - 19:20)
        6: "P3", # Ánh Dương: P3 (13:00 - 21:40)
        3: "P4", # Ánh Hồng: P4 (08:30 - 18:30)
        7: "P1", # Mĩ Nhơn: P1
        8: "P2", # Kim Phụng: P2
        9: "P4", # Hà Thu: P4
        1: "P1", # BM Hương
        2: "P1", # Thủy ATL
    }
    ca_times = {
        "P1": ("07:20", "17:40"),
        "P2": ("09:00", "19:20"),
        "P3": ("13:00", "21:40"),
        "P4": ("08:30", "18:30"),
        "OFF": ("", "")
    }

    for w_day in range(7):
        cur_date_str = (monday + pd.Timedelta(days=w_day)).strftime("%Y-%m-%d")
        for uid, ca in shift_assignments.items():
            # Ngày Chủ nhật (w_day=6) luân phiên OFF
            actual_ca = "OFF" if w_day == 6 and uid in (6, 7, 8) else ca
            st, et = ca_times[actual_ca]
            c.execute("""
                INSERT INTO work_shifts(shift_date, user_id, ca, start_time, end_time, location, note, created_by, created_at)
                VALUES(?,?,?,?,?,?,?,?,?)
                ON CONFLICT(shift_date, user_id) DO UPDATE SET
                    ca=excluded.ca, start_time=excluded.start_time, end_time=excluded.end_time
            """, (cur_date_str, uid, actual_ca, st, et, "Chi nhánh", "", "Kế Toán Hồng", today))

    print("✓ 6. Đã nạp Lịch Ca tuần chuẩn P1–P4 cho toàn bộ nhân sự.")

    conn.commit()
    conn.close()
    print("\n=== HOÀN TẤT ĐỒNG BỘ 100% DỮ LIỆU THỰC TẾ CHI NHÁNH BMT VÀO APP! ===")

if __name__ == '__main__':
    apply_real_branch_data()
