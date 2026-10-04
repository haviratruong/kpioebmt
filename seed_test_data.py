import sqlite3
from datetime import datetime
import pandas as pd

def seed_sample_data():
    conn = sqlite3.connect('D:/OCEAN_EDU_BMT/09_APP_KPI_MANAGEMENT/kpi_app.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    today = datetime.now().strftime("%Y-%m-%d")
    ym = datetime.now().strftime("%Y-%m")
    d_obj = datetime.now().date()
    monday = d_obj - pd.Timedelta(days=d_obj.weekday())

    print(f"=== BẮT ĐẦU NẠP DỮ LIỆU TEST (Hôm nay: {today}, Tháng: {ym}) ===")

    # 1. Cập nhật tên thật nhân sự nếu còn để placeholder
    c.execute("UPDATE users SET display_name='Thảo (EC 3)' WHERE username='ec_3' AND display_name LIKE '%chưa đặt%'")
    c.execute("UPDATE users SET display_name='Huyền (EC 4)' WHERE username='ec_4' AND display_name LIKE '%chưa đặt%'")

    # 2. Lịch ca tuần này (work_shifts)
    shifts = [
        (4, "P1", "07:20", "17:40"),  # Trâm Anh
        (5, "P2", "09:00", "19:20"),  # Dung
        (6, "P3", "13:00", "21:40"),  # Thảo
        (7, "P4", "08:30", "18:30"),  # Huyền
        (8, "P1", "07:20", "17:40"),  # EC 5
        (9, "P2", "09:00", "19:20"),  # EC 6
        (1, "P1", "07:20", "17:40"),  # BM Hương
        (2, "P1", "07:20", "17:40"),  # Thủy ATL
        (3, "P1", "07:20", "17:40"),  # Hồng KT
    ]
    for w_day in range(7):
        cur_d = (monday + pd.Timedelta(days=w_day)).strftime("%Y-%m-%d")
        for uid, ca, st, et in shifts:
            # Cho CN nghỉ (OFF) một số người
            real_ca = "OFF" if w_day == 6 and uid in (6, 7) else ca
            c.execute("""
                INSERT INTO work_shifts(shift_date, user_id, ca, start_time, end_time, location, note, created_by, created_at)
                VALUES(?,?,?,?,?,?,?,?,?)
                ON CONFLICT(shift_date, user_id) DO UPDATE SET ca=excluded.ca, start_time=excluded.start_time, end_time=excluded.end_time
            """, (cur_d, uid, real_ca, st, et, "Chi nhánh", "", "Kế Toán Hồng", today))

    print("✓ Đã nạp Lịch Ca tuần này cho 9 nhân sự.")

    # 3. Lịch sự kiện STEAM (steam_schedule)
    c.execute("DELETE FROM steam_schedule WHERE event_date=?", (today,))
    c.execute("""
        INSERT INTO steam_schedule(event_date, start_time, end_time, title, school_name, location, assigned_ec_ids, note, created_by, created_at)
        VALUES(?,?,?,?,?,?,?,?,?,?)
    """, (today, "08:00", "11:00", "Ngày hội STEAM Khám Phá Khoa Học", "TH Lê Quý Đôn", "Sân trường TH Lê Quý Đôn", "4,5", "Chuẩn bị 50 phần quà trải nghiệm + Standee", "Thủy ATL", today))
    print("✓ Đã nạp Sự Kiện STEAM hôm nay (Trâm Anh & Dung phụ trách).")

    # 4. Chỉ tiêu tháng (monthly_targets)
    targets = [
        (4, "EC", 70000, 180, 180, 15, 5),  # Trâm Anh
        (5, "EC", 60000, 99, 99, 12, 4),    # Dung
        (6, "EC", 50000, 99, 99, 10, 3),    # Thảo
        (7, "EC", 50000, 99, 99, 10, 3),    # Huyền
    ]
    for uid, pos, dt, c1, c2, cild, cisk in targets:
        c.execute("""
            INSERT INTO monthly_targets(year_month, user_id, position, target_doanh_thu, target_cuoc_goi_chang1, target_cuoc_goi_chang2, target_checkin_landau, target_checkin_sk)
            VALUES(?,?,?,?,?,?,?,?)
            ON CONFLICT(year_month, user_id) DO UPDATE SET
                target_doanh_thu=excluded.target_doanh_thu,
                target_cuoc_goi_chang1=excluded.target_cuoc_goi_chang1,
                target_cuoc_goi_chang2=excluded.target_cuoc_goi_chang2
        """, (ym, uid, pos, dt, c1, c2, cild, cisk))

    # Ebook & QR targets
    for uid in (4, 5, 6, 7):
        c.execute("""
            INSERT INTO ebook_qr_targets(year_month, user_id, target_ebook, target_qr)
            VALUES(?,?,?,?)
            ON CONFLICT(year_month, user_id) DO UPDATE SET target_ebook=excluded.target_ebook, target_qr=excluded.target_qr
        """, (ym, uid, 7, 20))

    print("✓ Đã nạp Chỉ Tiêu KPI Tháng (Doanh thu, Cuộc gọi Chặng 1 & 2, Ebook, QR).")

    # 5. Phân công Peer Check tháng
    peers = [(4, 5), (5, 6), (6, 7), (7, 4)]
    for chk, chkee in peers:
        c.execute("""
            INSERT INTO peer_assignments(year_month, checker_id, checkee_id)
            VALUES(?,?,?)
            ON CONFLICT(year_month, checker_id) DO UPDATE SET checkee_id=excluded.checkee_id
        """, (ym, chk, chkee))
    print("✓ Đã nạp Vòng Tròn Phân Cặp Kiểm Tra Đồng Đội (Peer Check).")

    # 6. Khách hàng tiềm năng (khtn_records)
    c.execute("DELETE FROM khtn_records WHERE record_date=?", (today,))
    khtn_samples = [
        (4, "Chị Mai (bé Bảo Nam)", "0912345678", "Primary", "Đã đóng cọc", "Đã cọc 2 triệu, hẹn lên chi nhánh hoàn tất hồ sơ", "Đóng hoàn thiện", today),
        (5, "Anh Tuấn (bé Thảo My)", "0987654321", "Kids (~6 tuổi)", "Đã test — chờ chốt", "Bé đạt Starters 14/15 khiên, PH rất hài lòng", "Tư vấn gói 1 năm", today),
        (4, "Cô Lan (bé Minh Khôi)", "0905123456", "Kindy (~5 tuổi)", "Đã lên lịch test", "Hẹn 15h30 chiều nay đưa bé qua test đầu vào", "Test đầu vào", today),
        (6, "Anh Hùng (bé Gia Bảo)", "0935112233", "Pre School (~3 tuổi)", "Đang cân nhắc", "Đang so sánh với trung tâm khác, cần gửi thêm video lớp", "Gọi chăm sóc lại", today),
    ]
    for uid, tkh, sdt, lop, tt, gc, btt, nh in khtn_samples:
        c.execute("""
            INSERT INTO khtn_records(user_id, record_date, ten_kh, so_dien_thoai, lop_hoc, trang_thai, ghi_chu, buoc_tiep_theo, ngay_hen, updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?)
        """, (uid, today, tkh, sdt, lop, tt, gc, btt, nh, f"{today} 08:30"))
    print("✓ Đã nạp 4 Khách Hàng Tiềm Năng (Có % cơ hội, ngày hẹn hôm nay).")

    # 7. Báo cáo mẫu đã nộp trong ngày (reports)
    c.execute("DELETE FROM reports WHERE report_date=?", (today,))
    # Trâm Anh nộp BC Đầu Ca (P1: 07:15)
    c.execute("""
        INSERT INTO reports(user_id, rule_code, report_date, content, kpi_cuoc_goi, kpi_doanh_thu, kpi_checkin, kpi_cocnho, submitted_at, is_late)
        VALUES(?,?,?,?,?,?,?,?,?,0)
    """, (4, "BC_DAU_CA", today, "BC Đầu Ca Trâm Anh — Cam kết 35 cuộc gọi, DT 15.000K, 2 check-in.", 0, 0, 0, 0, "07:12"))

    # Trâm Anh nộp Chỉ Số Ngày (Đạt 32 cuộc gọi, 15 triệu doanh thu)
    c.execute("""
        INSERT INTO reports(user_id, rule_code, report_date, content, kpi_cuoc_goi, kpi_doanh_thu, kpi_checkin, kpi_cocnho, submitted_at, is_late)
        VALUES(?,?,?,?,?,?,?,?,?,0)
    """, (4, "CHI_SO_NGAY", today, "Chỉ số ngày Trâm Anh: 32 cuộc gọi, thu 15.000K, 2 check-in, 1 cọc.", 32, 15000, 2, 1, "20:45"))

    # Dung nộp BC Đầu Ca (P2: 08:50)
    c.execute("""
        INSERT INTO reports(user_id, rule_code, report_date, content, kpi_cuoc_goi, kpi_doanh_thu, kpi_checkin, kpi_cocnho, submitted_at, is_late)
        VALUES(?,?,?,?,?,?,?,?,?,0)
    """, (5, "BC_DAU_CA", today, "BC Đầu Ca Dung — Cam kết 25 cuộc gọi, DT 5.000K.", 0, 0, 0, 0, "08:45"))

    # Dung nộp Chỉ Số Ngày (Chưa đạt: 16 cuộc gọi, có giải trình)
    c.execute("""
        INSERT INTO reports(user_id, rule_code, report_date, content, kpi_cuoc_goi, kpi_doanh_thu, kpi_checkin, kpi_cocnho, giai_trinh, de_xuat, submitted_at, is_late)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,0)
    """, (5, "CHI_SO_NGAY", today, "Chỉ số ngày Dung: 16 cuộc gọi.", 16, 0, 1, 0, "Nhiều PH bận đón con, máy bận", "Gọi bù 15 cuộc vào chặng tối ngày mai", "20:50"))

    print("✓ Đã nộp Báo Cáo Đầu Ca & Chỉ Số Ngày (Có bạn đạt, bạn cần giải trình).")

    # 8. Kết quả Peer Check hôm nay (peer_checks)
    c.execute("DELETE FROM peer_checks WHERE check_date=?", (today,))
    # Trâm Anh kiểm tra Dung
    c.execute("""
        INSERT INTO peer_checks(checker_id, checkee_id, check_date, check_type, result, link_evidence, note, checked_at)
        VALUES(?,?,?,?,?,?,?,?)
    """, (4, 5, today, "MKT_FB_ZALO", 1, "https://facebook.com/dung.ocean/post/123", "Đã đăng đủ 1 bài FB + 1 bài Zalo", "21:10"))
    c.execute("""
        INSERT INTO peer_checks(checker_id, checkee_id, check_date, check_type, result, link_evidence, note, checked_at)
        VALUES(?,?,?,?,?,?,?,?)
    """, (4, 5, today, "TUONG_TAC", 1, "", "Đã thả tim chỉ đạo nhóm chính", "21:10"))
    print("✓ Đã nạp Kết Quả Peer Check (Trâm Anh kiểm tra Dung ✅ Đạt).")

    # 9. Sự kiện tháng (monthly_events)
    c.execute("DELETE FROM monthly_events WHERE year_month=?", (ym,))
    c.execute("""
        INSERT INTO monthly_events(year_month, muc_dich, ten_hoat_dong, phong_ban, noi_dung, dia_diem, doi_tuong, so_luong_chi_tieu, so_luong_thuc_te, timeline, trang_thai, assigned_to, created_at)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (ym, "Khai thác Data mới", "Booth Activation Vincom Buôn Ma Thuột", "Tuyển sinh", "Tư vấn chương trình học bổng 13M + Quét QR", "TTTM Vincom BMT", "Phụ huynh & Học sinh", 50, 35, f"{today} 16:00 - 20:00", "Đang diễn ra", "Trâm Anh, Thủy ATL", today))
    print("✓ Đã nạp Sự Kiện / Booth tháng.")

    conn.commit()
    conn.close()
    print("=== HOÀN TẤT NẠP DỮ LIỆU TEST! HỆ THỐNG ĐÃ HOẠT ĐỘNG 100% ===")

if __name__ == "__main__":
    seed_sample_data()
