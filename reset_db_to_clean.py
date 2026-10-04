import sqlite3

def clean_database():
    conn = sqlite3.connect('D:/OCEAN_EDU_BMT/09_APP_KPI_MANAGEMENT/kpi_app.db')
    c = conn.cursor()

    tables_to_clear = [
        'reports',
        'khtn_records',
        'work_shifts',
        'penalties',
        'peer_checks',
        'peer_assignments',
        'monthly_targets',
        'monthly_events',
        'ebook_qr_targets',
        'ebook_qr_records',
        'steam_schedule',
        'penalty_sweep'
    ]

    for t in tables_to_clear:
        c.execute(f"DELETE FROM {t}")
        print(f"✓ Đã làm sạch bảng: {t}")

    conn.commit()
    conn.close()
    print("=== ĐÃ LÀM SẠCH HOÀN TOÀN CƠ SỞ DỮ LIỆU ĐỂ BẮT ĐẦU CHẠY THẬT! ===")

if __name__ == '__main__':
    clean_database()
