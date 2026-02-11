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
SHEET_ID   = "1zDBbDk91VpnBfK4gBkoZAtEkeSBXBFQwFnxqwKH-yyU"
FILE_EXCEL = "LAPORAN_HARIAN_VIP.xlsx"

# ================= KONEKSI & DATA (TURBO MODE) =================

@st.cache_resource
def connect_gsheet():
    """Koneksi dijaga agar tidak putus (Resource Cache)"""
    try:
        if "gcp_service_account" not in st.secrets: return None
        creds = dict(st.secrets["gcp_service_account"])
        client = gspread.service_account_from_dict(creds)
        return client.open_by_key(SHEET_ID)
    except: return None

@st.cache_data(ttl=3600) # Data disimpan di RAM 1 jam
def ambil_semua_data():
    """Ambil data Menu/Staff/Cabang SEKALI SAJA"""
    sh = connect_gsheet()
    if not sh: return {}, {}, {}
    
    def get_df(nama_sheet, cols):
        try: ws = sh.worksheet(nama_sheet)
        except: 
            ws = sh.add_worksheet(nama_sheet, 100, len(cols))
            ws.append_row(cols)
        return ws.get_all_records()

    # Ambil Staff
    d_staff = get_df("STAFF", ["PIN", "NAMA"])
    staff_dict = {str(r['PIN']): r['NAMA'] for r in d_staff}

    # Ambil Menu
    d_menu = get_df("MENU", ["NAMA_MENU", "HARGA"])
    menu_dict = {r['NAMA_MENU']: int(r['HARGA']) for r in d_menu}
    if not menu_dict: menu_dict = {"Kopi Hitam": 5000}

    # Ambil Cabang
    d_cabang = get_df("CABANG", ["ID", "NAMA_CABANG"])
    cabang_dict = {str(r['ID']): r['NAMA_CABANG'] for r in d_cabang}
    if not cabang_dict: cabang_dict = {"1": "Gerobak Pusat"}

    return staff_dict, menu_dict, cabang_dict

def clear_cache_data():
    st.cache_data.clear()

# ================= FUNGSI UPDATE DATA (VERSI CEPAT/BATCH) =================

def simpan_ke_sheet_batch(nama_sheet, data_list):
    """
    RAHASIA ANTI-LAG: 
    Fungsi ini menghapus isi sheet lama, lalu menimpa dengan data baru
    SEKALIGUS dalam 1 kali kirim (append_rows). 
    """
    sh = connect_gsheet()
    if not sh: return

    # 1. Buka Sheet
    try: ws = sh.worksheet(nama_sheet)
    except: ws = sh.add_worksheet(nama_sheet, 100, 5)
    
    # 2. Bersihkan & Kirim Paket
    ws.clear()
    ws.append_rows(data_list) # <-- Ini kuncinya (pakai 's')
    
    # 3. Reset Memori HP Staff
    clear_cache_data()

# ================= FUNGSI TRANSAKSI =================

def get_waktu_wib():
    return datetime.now(pytz.timezone('Asia/Jakarta'))

def format_rupiah(angka):
    return f"Rp {int(angka):,}".replace(",", ".")

def kirim_telegram(pesan):
    try: requests.post(f"https://api.telegram.org/bot{TOKEN_BOT}/sendMessage", data={"chat_id": ID_OWNER, "text": pesan})
    except: pass

def kirim_file_excel():
    try:
        if os.path.exists(FILE_EXCEL):
            with open(FILE_EXCEL, 'rb') as f:
                requests.post(f"https://api.telegram.org/bot{TOKEN_BOT}/sendDocument", 
                              data={'chat_id': ID_OWNER, 'caption': '📊 Excel'}, files={'document': f})
    except: pass

def buat_excel_lokal(data_rows):
    try:
        df = pd.DataFrame(data_rows)
        df.to_excel(FILE_EXCEL, index=False)
        # Style Header Biru
        wb = load_workbook(FILE_EXCEL)
        ws = wb.active
        header_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
        for cell in ws[1]:
            cell.fill = header_fill
            cell.font = Font(bold=True, color="FFFFFF")
        wb.save(FILE_EXCEL)
    except: pass

def load_shift_realtime(cabang):
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
    if not sh: return None
    try: ws = sh.worksheet("SHIFT")
    except: 
        ws = sh.add_worksheet("SHIFT", 100, 5)
        ws.append_row(["CABANG", "PIC", "PIN_PIC", "JAM_MASUK", "STOK_AWAL"])
    
    if not ws.row_values(1): ws.append_row(["CABANG", "PIC", "PIN_PIC", "JAM_MASUK", "STOK_AWAL"])
    jam = get_waktu_wib().strftime("%H:%M")
    ws.append_row([cabang, pic, str(pin), jam, str(stok)])
    return jam

def save_closing(data_rows):
    """VERSI BATCH CLOSING"""
    sh = connect_gsheet()
    if not sh: return
    try: ws = sh.worksheet("LAPORAN")
    except: 
        ws = sh.add_worksheet("LAPORAN", 1000, 10)
        ws.append_row(["TANGGAL", "JAM_MASUK", "JAM_PULANG", "GEROBAK", "STAFF", "ITEM", "AWAL", "SISA", "TERJUAL", "OMZET"])
    
    if not ws.row_values(1): 
        ws.append_row(["TANGGAL", "JAM_MASUK", "JAM_PULANG", "GEROBAK", "STAFF", "ITEM", "AWAL", "SISA", "TERJUAL", "OMZET"])
    
    # Packing Data
    data_paket = []
    for r in data_rows:
        data_paket.append([
            r['TANGGAL'], r['JAM_MASUK'], r['JAM_PULANG'], 
            r['GEROBAK'], r['STAFF'], r['ITEM'], 
            r['AWAL'], r['SISA'], r['TERJUAL'], r['OMZET_ITEM']
        ])
    
    # Kirim Sekaligus
    ws.append_rows(data_paket)
    
    # Hapus Shift
    try:
        ws_shift = sh.worksheet("SHIFT")
        cell = ws_shift.find(data_rows[0]['GEROBAK'])
        ws_shift.delete_rows(cell.row)
    except: pass

# ================= MAIN APP =================
def main():
    st.set_page_config(page_title="Sistem Gerobak Cepat", page_icon="⚡", layout="centered")
    st.title("⚡ Kasir Anti-Lag (Batch)")

    # 1. LOAD DATA (CACHE)
    try:
        DATA_STAFF, DATA_MENU, DATA_CABANG = ambil_semua_data()
    except:
        st.warning("Sedang menghubungkan..."); st.stop()

    if 'user' not in st.session_state: st.session_state.user = None

    # --- SIDEBAR ---
    with st.sidebar:
        st.header("🔐 Login Area")
        if not st.session_state.user:
            mode = st.radio("Pilih:", ["Login", "Daftar"])
            if mode == "Login":
                pin = st.text_input("PIN", type="password")
                if st.button("Masuk"):
                    if pin == PIN_OWNER: 
                        st.session_state.user = "OWNER"; st.session_state.pin = PIN_OWNER; st.rerun()
                    elif pin in DATA_STAFF: 
                        st.session_state.user = DATA_STAFF[pin]; st.session_state.pin = pin; st.rerun()
                    else: st.error("PIN Salah")
            else:
                nm = st.text_input("Nama"); pn = st.text_input("PIN Baru", max_chars=6)
                if st.button("Daftar"):
                    # Siapkan Paket Data Baru
                    new_data = [["PIN", "NAMA"]] + [[k, v] for k,v in DATA_STAFF.items()] + [[pn, nm]]
                    simpan_ke_sheet_batch("STAFF", new_data) # Pakai Batch
                    st.success("Berhasil! Silakan Login."); st.rerun()
        else:
            st.success(f"👤 {st.session_state.user}")
            if st.button("Logout"): st.session_state.user = None; st.rerun()
            st.divider()
            if st.button("🔄 Refresh Data"): 
                clear_cache_data()
                st.rerun()

    # --- HALAMAN UTAMA ---
    if st.session_state.user:
        user = st.session_state.user
        pin = st.session_state.pin

        # OWNER MENU
        if user == "OWNER":
            st.info("🔧 **MENU OWNER (MODE CEPAT)**")
            t1, t2, t3 = st.tabs(["Cabang", "Staff", "Menu"])
            
            with t1:
                st.table(DATA_CABANG)
                nc = st.text_input("Tambah Cabang")
                if st.button("Simpan Cabang"):
                    nid = str(len(DATA_CABANG) + 1)
                    DATA_CABANG[nid] = nc
                    # Format Batch
                    save_data = [["ID", "NAMA_CABANG"]] + [[k, v] for k,v in DATA_CABANG.items()]
                    simpan_ke_sheet_batch("CABANG", save_data)
                    st.success("Disimpan!"); st.rerun()
                
                hc = st.selectbox("Hapus", list(DATA_CABANG.values()))
                if st.button("Hapus Cabang"):
                    key = [k for k,v in DATA_CABANG.items() if v==hc][0]
                    del DATA_CABANG[key]
                    save_data = [["ID", "NAMA_CABANG"]] + [[k, v] for k,v in DATA_CABANG.items()]
                    simpan_ke_sheet_batch("CABANG", save_data)
                    st.rerun()

            with t2:
                st.table(DATA_STAFF)
                hs = st.selectbox("Hapus Staff", [f"{v} ({k})" for k,v in DATA_STAFF.items()])
                if st.button("Hapus User"):
                    k = hs.split("(")[1].replace(")","")
                    del DATA_STAFF[k]
                    save_data = [["PIN", "NAMA"]] + [[k, v] for k,v in DATA_STAFF.items()]
                    simpan_ke_sheet_batch("STAFF", save_data)
                    st.rerun()

            with t3:
                st.table(DATA_MENU)
                c1,c2 = st.columns(2)
                nm = c1.text_input("Menu"); hr = c2.number_input("Harga", step=500)
                if st.button("Update Menu"):
                    DATA_MENU[nm] = int(hr)
                    # Format Batch
                    save_data = [["NAMA_MENU", "HARGA"]] + [[k, v] for k,v in DATA_MENU.items()]
                    simpan_ke_sheet_batch("MENU", save_data)
                    st.rerun()
                
                hm = st.selectbox("Hapus Menu", list(DATA_MENU.keys()))
                if st.button("Hapus Item"):
                    del DATA_MENU[hm]
                    save_data = [["NAMA_MENU", "HARGA"]] + [[k, v] for k,v in DATA_MENU.items()]
                    simpan_ke_sheet_batch("MENU", save_data)
                    st.rerun()

        st.divider()
        st.subheader("📍 Operasional")
        
        if not DATA_CABANG: st.warning("Data Cabang Kosong."); st.stop()
        
        lokasi = st.selectbox("Pilih Lokasi:", list(DATA_CABANG.values()))
        shift = load_shift_realtime(lokasi)

        if shift: st.warning(f"⚠️ SHIFT AKTIF: {shift['pic']} ({shift['jam_masuk']})")
        else: st.success("✅ Outlet Kosong")

        tab_op, tab_cl = st.tabs(["Opening", "Closing"])

        with tab_op:
            if shift: st.error("Sudah ada shift.")
            else:
                with st.form("op"):
                    st.write("Stok Awal:")
                    stok = {}
                    cols = st.columns(2)
                    for i, (m, h) in enumerate(DATA_MENU.items()):
                        with cols[i%2]: stok[m] = st.number_input(f"{m}", min_value=0)
                    if st.form_submit_button("MULAI SHIFT"):
                        jam = save_opening(lokasi, user, pin, stok)
                        kirim_telegram(f"☀️ *OPENING*\n📍 {lokasi}\n👤 {user}\n🕒 {jam}")
                        st.success("Sukses!"); st.rerun()

        with tab_cl:
            if not shift: st.info("Belum Opening.")
            elif shift['pin_pic'] != pin: st.error("Bukan Shift Anda!")
            else:
                with st.form("cl"):
                    st.write("Stok Akhir:")
                    omzet = 0; excel_data = []
                    tgl = get_waktu_wib().strftime("%Y-%m-%d")
                    jam_plg = get_waktu_wib().strftime("%H:%M")

                    for m, h in DATA_MENU.items():
                        aw = shift['stok'].get(m, 0)
                        ss = st.number_input(f"Sisa {m} (Awal: {aw})", 0, aw)
                        lk = aw - ss; duit = lk * h; omzet += duit
                        excel_data.append({"TANGGAL": tgl, "JAM_MASUK": shift['jam_masuk'], "JAM_PULANG": jam_plg, 
                                           "GEROBAK": lokasi, "STAFF": user, "ITEM": m, 
                                           "AWAL": aw, "SISA": ss, "TERJUAL": lk, "OMZET_ITEM": duit})

                    st.info(f"💰 Omzet: {format_rupiah(omzet)}")
                    tunai = st.number_input("Tunai", step=1000)
                    qris = st.number_input("QRIS", step=1000)
                    cat = st.text_area("Catatan")

                    if st.form_submit_button("KIRIM LAPORAN"):
                        selisih = (tunai + qris) - omzet
                        msg = (f"🌙 *CLOSING*\n📍 {lokasi}\n👤 {user}\n📊 Omzet: {format_rupiah(omzet)}\n"
                               f"💵 Cash: {format_rupiah(tunai)}\n💳 QRIS: {format_rupiah(qris)}\n"
                               f"📝 {cat}\nStatus: {'✅ PAS' if selisih==0 else '⚠️ SELISIH'}")
                        kirim_telegram(msg)
                        
                        excel_data.append({"TANGGAL": tgl, "JAM_MASUK": shift['jam_masuk'], "JAM_PULANG": jam_plg, "GEROBAK": lokasi, "STAFF": user, "ITEM": "SETOR TUNAI", "AWAL": 0, "SISA": 0, "TERJUAL": 0, "OMZET_ITEM": tunai})
                        excel_data.append({"TANGGAL": tgl, "JAM_MASUK": shift['jam_masuk'], "JAM_PULANG": jam_plg, "GEROBAK": lokasi, "STAFF": user, "ITEM": "SETOR QRIS", "AWAL": 0, "SISA": 0, "TERJUAL": 0, "OMZET_ITEM": qris})
                        
                        buat_excel_lokal(excel_data)
                        kirim_file_excel()
                        
                        data_db = [x for x in excel_data if "SETOR" not in x['ITEM']]
                        save_closing(data_db)
                        
                        st.success("Terkirim!"); st.balloons(); st.rerun()

if __name__ == "__main__":
    main()
            
