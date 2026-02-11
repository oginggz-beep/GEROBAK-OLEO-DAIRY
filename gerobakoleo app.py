import streamlit as st
import pytz
import gspread
import pandas as pd
import requests
import os
from datetime import datetime
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

# ================= KONFIGURASI =================
TOKEN_BOT  = "8285539149:AAHQd-_W9aaBGSz3AUPg0oCuxabZUL6yJo4"
ID_OWNER   = "8505488457"
PIN_OWNER  = "8888" 
# Menggunakan ID yang sudah valid dari link sebelumnya agar koneksi 100% sukses
SHEET_ID   = "1zDBbDk91VpnBfK4gBkoZAtEkeSBXBFQwFnxqwKH-yyU"
FILE_EXCEL = "LAPORAN_HARIAN_VIP.xlsx"

# ================= KONEKSI GOOGLE SHEETS (DENGAN CACHE) =================
# @st.cache_resource membuat koneksi disimpan di memori, mencegah error putus
@st.cache_resource
def connect_gsheet():
    try:
        # Cek Secrets
        if "gcp_service_account" not in st.secrets:
            st.error("❌ Secrets belum disetting di Streamlit!")
            return None
        
        # Login pakai gspread native (Tanpa oauth2client yg sering error)
        creds_dict = dict(st.secrets["gcp_service_account"])
        client = gspread.service_account_from_dict(creds_dict)
        
        # Buka File Pakai ID (Paling Aman)
        return client.open_by_key(SHEET_ID)
    except Exception as e:
        return None

def get_waktu_wib():
    return datetime.now(pytz.timezone('Asia/Jakarta'))

def format_rupiah(angka):
    return f"Rp {int(angka):,}".replace(",", ".")

# ================= FUNGSI TELEGRAM & EXCEL =================
def kirim_telegram(pesan):
    try:
        requests.post(f"https://api.telegram.org/bot{TOKEN_BOT}/sendMessage", data={"chat_id": ID_OWNER, "text": pesan})
    except: pass

def kirim_file_excel():
    try:
        if os.path.exists(FILE_EXCEL):
            with open(FILE_EXCEL, 'rb') as f:
                requests.post(f"https://api.telegram.org/bot{TOKEN_BOT}/sendDocument", 
                              data={'chat_id': ID_OWNER, 'caption': '📊 Laporan Detail (Excel)'}, 
                              files={'document': f})
    except: pass

def rapikan_excel(filename):
    """Mempercantik tampilan Excel (Header Biru, Border, Auto Width)"""
    try:
        wb = load_workbook(filename)
        ws = wb.active
        
        # Style Header
        header_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF", size=11)
        border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
        
        for cell in ws[1]:
            cell.fill = header_fill; cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")
        
        for row in ws.iter_rows(min_row=2):
            for cell in row:
                cell.border = border
                cell.alignment = Alignment(vertical="center", horizontal="center")
                if cell.column == 10: # Kolom Omzet Rata Kanan
                    cell.number_format = '#,##0'; cell.alignment = Alignment(horizontal="right")
        
        # Auto Width Columns
        for col in ws.columns:
            max_len = 0
            col_letter = col[0].column_letter
            for cell in col:
                try:
                    if len(str(cell.value)) > max_len: max_len = len(str(cell.value))
                except: pass
            ws.column_dimensions[col_letter].width = (max_len + 2)
        wb.save(filename)
    except: pass

def buat_excel_lokal(data_rows):
    # Simpan data ke Excel sementara untuk dikirim ke Telegram
    df = pd.DataFrame(data_rows)
    df.to_excel(FILE_EXCEL, index=False)
    rapikan_excel(FILE_EXCEL)

# ================= DATABASE CRUD (GOOGLE SHEETS) =================
# Fungsi Helper untuk Load/Create Sheet dengan Error Handling Kuat
def load_data(sheet_name, default_cols):
    sh = connect_gsheet()
    if sh is None: return []
    try: 
        ws = sh.worksheet(sheet_name)
    except: 
        ws = sh.add_worksheet(title=sheet_name, rows=100, cols=len(default_cols))
        ws.append_row(default_cols)
    return ws.get_all_records()

def save_update(sheet_name, header, data_dict):
    sh = connect_gsheet()
    if sh is None: return False
    try:
        try: ws = sh.worksheet(sheet_name)
        except: ws = sh.add_worksheet(title=sheet_name, rows=100, cols=len(header))
        
        ws.clear()
        ws.append_row(header)
        for k, v in data_dict.items(): ws.append_row([k, v])
        return True
    except: return False

# Load Data Spesifik
def load_staff():
    data = load_data("STAFF", ["PIN", "NAMA"])
    return {str(r['PIN']): r['NAMA'] for r in data}

def load_menu():
    data = load_data("MENU", ["NAMA_MENU", "HARGA"])
    d = {r['NAMA_MENU']: int(r['HARGA']) for r in data}
    return d if d else {"Kopi Hitam": 5000}

def load_cabang():
    data = load_data("CABANG", ["ID", "NAMA_CABANG"])
    d = {str(r['ID']): r['NAMA_CABANG'] for r in data}
    return d if d else {"1": "Gerobak Pusat"}

def load_shift(cabang):
    sh = connect_gsheet()
    if not sh: return None
    try: ws = sh.worksheet("SHIFT")
    except: return None
    for row in ws.get_all_records():
        if row['CABANG'] == cabang:
            import ast
            try: stok = ast.literal_eval(str(row['STOK_AWAL']))
            except: stok = {}
            return {"pic": row['PIC'], "pin_pic": str(row['PIN_PIC']), "jam_masuk": row['JAM_MASUK'], "stok": stok}
    return None

def save_opening(cabang, pic, pin, stok):
    sh = connect_gsheet()
    if sh is None: return None
    try: ws = sh.worksheet("SHIFT")
    except: 
        ws = sh.add_worksheet(title="SHIFT", rows=100, cols=5)
        ws.append_row(["CABANG", "PIC", "PIN_PIC", "JAM_MASUK", "STOK_AWAL"])
    
    if not ws.row_values(1): ws.append_row(["CABANG", "PIC", "PIN_PIC", "JAM_MASUK", "STOK_AWAL"])
    jam = get_waktu_wib().strftime("%H:%M")
    ws.append_row([cabang, pic, str(pin), jam, str(stok)])
    return jam

def save_closing_gsheet(data_rows):
    sh = connect_gsheet()
    if sh is None: return False
    try: ws = sh.worksheet("LAPORAN")
    except: 
        ws = sh.add_worksheet(title="LAPORAN", rows=1000, cols=10)
        ws.append_row(["TANGGAL", "JAM_MASUK", "JAM_PULANG", "GEROBAK", "STAFF", "ITEM", "AWAL", "SISA", "TERJUAL", "OMZET"])
    
    if not ws.row_values(1): 
        ws.append_row(["TANGGAL", "JAM_MASUK", "JAM_PULANG", "GEROBAK", "STAFF", "ITEM", "AWAL", "SISA", "TERJUAL", "OMZET"])
    
    for r in data_rows:
        ws.append_row([
            r['TANGGAL'], r['JAM_MASUK'], r['JAM_PULANG'], r['GEROBAK'], r['STAFF'], 
            r['ITEM'], r['AWAL'], r['SISA'], r['TERJUAL'], r['OMZET_ITEM']
        ])
    
    # Hapus Data Shift
    try:
        ws_shift = sh.worksheet("SHIFT")
        cell = ws_shift.find(data_rows[0]['GEROBAK'])
        ws_shift.delete_rows(cell.row)
    except: pass

# ================= MAIN APP =================
def main():
    st.set_page_config(page_title="Sistem Gerobak Pro", page_icon="💎", layout="centered")
    st.title("💎 Kasir & Absensi (Pro)")

    # Load Data di Awal (Safe Mode)
    DATA_CABANG = {}
    DATA_MENU = {}
    DATA_STAFF = {}
    
    try:
        if connect_gsheet():
            # Tidak pakai Spinner full screen biar lebih cepat
            DATA_CABANG = load_cabang()
            DATA_MENU = load_menu()
            DATA_STAFF = load_staff()
        else:
            st.error("Koneksi Google Sheets Terputus. Coba Refresh halaman.")
            st.stop()
    except:
        st.warning("Sedang memuat ulang data..."); st.stop()

    if 'user' not in st.session_state: st.session_state.user = None

    # --- SIDEBAR LOGIN ---
    with st.sidebar:
        st.header("🔐 Login Staff")
        if not st.session_state.user:
            menu = st.radio("Mode:", ["Masuk", "Daftar"])
            if menu == "Masuk":
                pin = st.text_input("PIN", type="password")
                if st.button("Log In"):
                    if pin == PIN_OWNER: 
                        st.session_state.user = "OWNER"; st.session_state.pin = PIN_OWNER; st.rerun()
                    elif pin in DATA_STAFF: 
                        st.session_state.user = DATA_STAFF[pin]; st.session_state.pin = pin; st.rerun()
                    else: st.error("PIN Salah")
            else:
                nm = st.text_input("Nama"); pn = st.text_input("PIN Baru", max_chars=6)
                if st.button("Daftar"):
                    sh = connect_gsheet()
                    if sh:
                        try: ws = sh.worksheet("STAFF")
                        except: ws = sh.add_worksheet(title="STAFF", rows=100, cols=2)
                        ws.append_row([pn, nm])
                        st.success("Tedaftar! Silakan Login."); st.rerun()
        else:
            st.success(f"👤 {st.session_state.user}"); 
            if st.button("Logout"): st.session_state.user = None; st.rerun()

    # --- HALAMAN UTAMA ---
    if st.session_state.user:
        user = st.session_state.user
        pin = st.session_state.pin

        if user == "OWNER":
            st.info("🔧 **PANEL KENDALI OWNER**")
            t1, t2, t3 = st.tabs(["🏢 Cabang", "👥 Staff", "🍔 Menu"])
            with t1:
                st.table(DATA_CABANG)
                nc = st.text_input("Tambah Cabang")
                if st.button("Simpan Cabang"):
                    nid = str(max([int(k) for k in DATA_CABANG.keys()] or [0]) + 1)
                    DATA_CABANG[nid] = nc; save_update("CABANG", ["ID","NAMA_CABANG"], DATA_CABANG); st.rerun()
                if DATA_CABANG:
                    hc = st.selectbox("Hapus", list(DATA_CABANG.values()))
                    if st.button("Hapus Cabang"):
                        k = [k for k,v in DATA_CABANG.items() if v==hc][0]
                        del DATA_CABANG[k]; save_update("CABANG", ["ID","NAMA_CABANG"], DATA_CABANG); st.rerun()
            with t2:
                st.table(DATA_STAFF)
                if DATA_STAFF:
                    hs = st.selectbox("Hapus Staff", [f"{v} ({k})" for k,v in DATA_STAFF.items()])
                    if st.button("Hapus User"):
                        k = hs.split("(")[1].replace(")","")
                        del DATA_STAFF[k]; save_update("STAFF", ["PIN","NAMA"], DATA_STAFF); st.rerun()
            with t3:
                st.table(DATA_MENU)
                c1,c2 = st.columns(2)
                nm = c1.text_input("Menu"); hr = c2.number_input("Harga", step=500)
                if st.button("Update Menu"):
                    DATA_MENU[nm] = int(hr); save_update("MENU", ["NAMA_MENU","HARGA"], DATA_MENU); st.rerun()
                if DATA_MENU:
                    hm = st.selectbox("Hapus Menu", list(DATA_MENU.keys()))
                    if st.button("Hapus Item"):
                        del DATA_MENU[hm]; save_update("MENU", ["NAMA_MENU","HARGA"], DATA_MENU); st.rerun()

        # AREA KERJA
        st.divider()
        st.subheader("📍 Operasional Outlet")
        if not DATA_CABANG: 
            st.warning("Data Cabang Kosong. Tambah dulu di menu Owner.")
        else:
            lokasi = st.selectbox("Pilih Lokasi:", list(DATA_CABANG.values()))
            shift = load_shift(lokasi)

            if shift: st.warning(f"⚠️ SHIFT AKTIF: {shift['pic']} (Masuk {shift['jam_masuk']})")
            else: st.success("✅ Outlet Kosong")

            tab_op, tab_cl = st.tabs(["☀️ Opening", "🌙 Closing"])

            with tab_op:
                if shift: st.error("Sudah ada shift.")
                else:
                    with st.form("op"):
                        st.write("Input Stok Awal:")
                        stok = {}
                        cols = st.columns(2)
                        for i, (m, h) in enumerate(DATA_MENU.items()):
                            with cols[i%2]: stok[m] = st.number_input(f"{m}", min_value=0)
                        if st.form_submit_button("MULAI SHIFT"):
                            jam = save_opening(lokasi, user, pin, stok)
                            if jam:
                                kirim_telegram(f"☀️ *OPENING*\n📍 {lokasi}\n👤 {user}\n🕒 {jam}")
                                st.success("Shift Dimulai!"); st.rerun()
                            else:
                                st.error("Gagal simpan ke database. Coba lagi.")

            with tab_cl:
                if not shift: st.info("Belum Opening.")
                elif shift['pin_pic'] != pin: st.error("Bukan Shift Anda!")
                else:
                    with st.form("cl"):
                        st.write("Input Sisa Stok:")
                        omzet = 0; excel_data = []
                        tgl = get_waktu_wib().strftime("%Y-%m-%d")
                        jam_plg = get_waktu_wib().strftime("%H:%M")

                        for m, h in DATA_MENU.items():
                            aw = shift['stok'].get(m, 0)
                            ss = st.number_input(f"Sisa {m} (Awal: {aw})", 0, aw)
                            lk = aw - ss; duit = lk * h; omzet += duit
                            
                            excel_data.append({
                                "TANGGAL": tgl, "JAM_MASUK": shift['jam_masuk'], "JAM_PULANG": jam_plg, 
                                "GEROBAK": lokasi, "STAFF": user, "ITEM": m, 
                                "AWAL": aw, "SISA": ss, "TERJUAL": lk, "OMZET_ITEM": duit
                            })

                        st.info(f"💰 Total Omzet: {format_rupiah(omzet)}")
                        tunai = st.number_input("Setor Tunai", step=1000)
                        qris = st.number_input("Setor QRIS", step=1000)
                        fisik = tunai + qris
                        selisih = fisik - omzet
                        
                        st.caption(f"Fisik: {format_rupiah(fisik)} | Selisih: {format_rupiah(selisih)}")
                        cat = st.text_area("Catatan")

                        if st.form_submit_button("KIRIM LAPORAN & EXCEL"):
                            # 1. Kirim Pesan Telegram
                            msg = (f"🌙 *CLOSING*\n📍 {lokasi}\n👤 {user}\n📊 Omzet: {format_rupiah(omzet)}\n"
                                   f"💵 Cash: {format_rupiah(tunai)}\n💳 QRIS: {format_rupiah(qris)}\n"
                                   f"📝 {cat}\n\nStatus: {'✅ PAS' if selisih==0 else '⚠️ SELISIH'}")
                            kirim_telegram(msg)
                            
                            # 2. Excel & Database
                            excel_data.append({"TANGGAL": tgl, "JAM_MASUK": shift['jam_masuk'], "JAM_PULANG": jam_plg, "GEROBAK": lokasi, "STAFF": user, "ITEM": "SETOR TUNAI", "AWAL": 0, "SISA": 0, "TERJUAL": 0, "OMZET_ITEM": tunai})
                            excel_data.append({"TANGGAL": tgl, "JAM_MASUK": shift['jam_masuk'], "JAM_PULANG": jam_plg, "GEROBAK": lokasi, "STAFF": user, "ITEM": "SETOR QRIS", "AWAL": 0, "SISA": 0, "TERJUAL": 0, "OMZET_ITEM": qris})

                            buat_excel_lokal(excel_data)
                            kirim_file_excel()

                            data_db = [x for x in excel_data if "SETOR" not in x['ITEM']]
                            save_closing_gsheet(data_db)
                            
                            st.success("Laporan Lengkap Terkirim!"); st.balloons(); st.rerun()

if __name__ == "__main__":
    main()
            
