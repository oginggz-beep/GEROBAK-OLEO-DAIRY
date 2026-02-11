import streamlit as st
import pandas as pd
import pytz
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# ================= KONFIGURASI =================
TOKEN_BOT  = "8285539149:AAHQd-_W9aaBGSz3AUPg0oCuxabZUL6yJo4"
ID_OWNER   = "8505488457"
PIN_OWNER  = "8888" 
NAMA_SHEET = "DATABASE_GEROBAK_APP" # Pastikan Nama File Google Sheet SAMA PERSIS

# ================= KONEKSI GOOGLE SHEETS =================
def connect_gsheet():
    """Menghubungkan aplikasi ke Google Sheets via Streamlit Secrets"""
    try:
        # Mengambil kredensial dari Secrets Streamlit
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
        client = gspread.authorize(creds)
        sheet = client.open(NAMA_SHEET)
        return sheet
    except Exception as e:
        st.error(f"❌ Gagal Konek Google Sheet: {e}")
        return None

def get_waktu_wib():
    tz = pytz.timezone('Asia/Jakarta')
    return datetime.now(tz)

def kirim_telegram(pesan):
    try:
        import requests
        url = f"https://api.telegram.org/bot{TOKEN_BOT}/sendMessage"
        requests.post(url, data={"chat_id": ID_OWNER, "text": pesan})
    except: pass

def format_rupiah(angka):
    return f"Rp {int(angka):,}".replace(",", ".")

# ================= FUNGSI BACA/TULIS DATA (CRUD) =================

def load_data_staff():
    """Mengambil data staff dari Sheet STAFF"""
    try:
        sh = connect_gsheet()
        ws = sh.worksheet("STAFF")
        data = ws.get_all_records() # List of Dicts
        # Convert ke format {PIN: NAMA}
        staff_dict = {str(row['PIN']): row['NAMA'] for row in data}
        return staff_dict
    except: return {}

def save_new_staff(pin, nama):
    try:
        sh = connect_gsheet()
        ws = sh.worksheet("STAFF")
        ws.append_row([str(pin), nama])
        return True
    except: return False

def delete_staff_by_pin(pin):
    try:
        sh = connect_gsheet()
        ws = sh.worksheet("STAFF")
        cell = ws.find(str(pin))
        ws.delete_rows(cell.row)
        return True
    except: return False

def load_data_menu():
    """Mengambil Menu dari Sheet MENU"""
    try:
        sh = connect_gsheet()
        ws = sh.worksheet("MENU")
        data = ws.get_all_records()
        # Convert ke format {NAMA: HARGA}
        menu_dict = {row['NAMA_MENU']: int(row['HARGA']) for row in data}
        # Jika kosong, pakai default
        if not menu_dict:
            return {"Kopi Hitam": 5000}
        return menu_dict
    except: return {"Kopi Hitam": 5000}

def save_menu_update(menu_dict):
    """Menimpa ulang Sheet MENU dengan data baru"""
    try:
        sh = connect_gsheet()
        ws = sh.worksheet("MENU")
        ws.clear() # Hapus semua dulu
        ws.append_row(["NAMA_MENU", "HARGA"]) # Header
        for k, v in menu_dict.items():
            ws.append_row([k, v])
        return True
    except: return False

def load_data_cabang():
    """Mengambil Cabang dari Sheet CABANG"""
    try:
        sh = connect_gsheet()
        ws = sh.worksheet("CABANG")
        data = ws.get_all_records()
        cabang_dict = {str(row['ID']): row['NAMA_CABANG'] for row in data}
        if not cabang_dict:
             return {"1": "Gerobak Pusat"}
        return cabang_dict
    except: return {"1": "Gerobak Pusat"}

def save_cabang_update(cabang_dict):
    try:
        sh = connect_gsheet()
        ws = sh.worksheet("CABANG")
        ws.clear()
        ws.append_row(["ID", "NAMA_CABANG"])
        for k, v in cabang_dict.items():
            ws.append_row([k, v])
        return True
    except: return False

def load_shift_active(nama_cabang):
    """Cek apakah ada shift aktif di Sheet SHIFT"""
    try:
        sh = connect_gsheet()
        ws = sh.worksheet("SHIFT")
        records = ws.get_all_records()
        for row in records:
            if row['CABANG'] == nama_cabang:
                # Convert string stok kembali ke dict
                import ast
                stok_dict = ast.literal_eval(row['STOK_AWAL'])
                return {
                    "pic": row['PIC'],
                    "pin_pic": str(row['PIN_PIC']),
                    "jam_masuk": row['JAM_MASUK'],
                    "stok": stok_dict
                }
        return None
    except: return None

def save_shift_opening(cabang, pic, pin, stok_dict):
    """Simpan data opening sementara"""
    try:
        sh = connect_gsheet()
        ws = sh.worksheet("SHIFT")
        # Jika header belum ada
        if not ws.row_values(1):
            ws.append_row(["CABANG", "PIC", "PIN_PIC", "JAM_MASUK", "STOK_AWAL"])
        
        jam = get_waktu_wib().strftime("%H:%M")
        ws.append_row([cabang, pic, str(pin), jam, str(stok_dict)])
        return jam
    except: return None

def delete_shift_closing(cabang):
    """Hapus data shift setelah closing"""
    try:
        sh = connect_gsheet()
        ws = sh.worksheet("SHIFT")
        cell = ws.find(cabang)
        ws.delete_rows(cell.row)
        return True
    except: return False

def save_laporan_final(data_rows):
    """Simpan laporan permanen ke Sheet LAPORAN"""
    try:
        sh = connect_gsheet()
        ws = sh.worksheet("LAPORAN")
        if not ws.row_values(1):
            ws.append_row(["TANGGAL", "JAM_MASUK", "JAM_PULANG", "GEROBAK", "STAFF", "ITEM", "AWAL", "SISA", "TERJUAL", "OMZET"])
        
        for row in data_rows:
            ws.append_row([
                row['TANGGAL'], row['JAM_MASUK'], row['JAM_PULANG'], 
                row['GEROBAK'], row['STAFF'], row['ITEM'], 
                row['AWAL'], row['SISA'], row['TERJUAL'], row['OMZET_ITEM']
            ])
        return True
    except: return False

# ================= APLIKASI WEB UTAMA =================
def main():
    st.set_page_config(page_title="Sistem Gerobak", page_icon="🥤", layout="centered")
    st.title("🥤 Kasir Cloud (Google Sheets)")

    # LOAD DATA REAL-TIME DARI GOOGLE SHEETS
    with st.spinner("Menghubungkan ke Database..."):
        DATA_GEROBAK = load_data_cabang()
        MENU_HARGA = load_data_menu()
        DATA_STAFF = load_data_staff()

    if 'user_nama' not in st.session_state: st.session_state['user_nama'] = None
    if 'user_pin' not in st.session_state: st.session_state['user_pin'] = None

    # --- SIDEBAR ---
    with st.sidebar:
        st.header("🔐 Akses Karyawan")
        if st.session_state['user_nama'] is None:
            mode_akses = st.radio("Menu:", ["Masuk (Login)", "Daftar Baru"])
            if mode_akses == "Masuk (Login)":
                pin_input = st.text_input("Ketik PIN Anda", max_chars=6, key="login")
                if st.button("Masuk"):
                    if pin_input == PIN_OWNER:
                        st.session_state['user_nama'] = "OWNER"
                        st.session_state['user_pin'] = PIN_OWNER
                        st.rerun()
                    elif pin_input in DATA_STAFF:
                        st.session_state['user_nama'] = DATA_STAFF[pin_input]
                        st.session_state['user_pin'] = pin_input
                        st.rerun()
                    else: st.error("PIN Salah / Belum Terdaftar di Sheets.")
            
            elif mode_akses == "Daftar Baru":
                nama_baru = st.text_input("Nama")
                pin_baru = st.text_input("PIN (Angka)", max_chars=6)
                if st.button("Daftar"):
                    if pin_baru in DATA_STAFF:
                        st.error("PIN Sudah Dipakai.")
                    else:
                        if save_new_staff(pin_baru, nama_baru):
                            st.success("Tersimpan di Google Sheets!")
                            st.rerun()
                        else: st.error("Gagal koneksi ke Sheets.")
        else:
            st.success(f"Halo, {st.session_state['user_nama']}")
            if st.button("LOG OUT"):
                st.session_state['user_nama'] = None; st.rerun()

    # --- MAIN CONTENT ---
    if st.session_state['user_nama']:
        user = st.session_state['user_nama']
        pin = st.session_state['user_pin']

        # FITUR OWNER
        if user == "OWNER":
            st.error("🔧 MENU SUPER ADMIN (Google Sheets Mode)")
            t1, t2, t3 = st.tabs(["Cabang", "Staff", "Menu"])
            
            with t1:
                st.write("Daftar Cabang:")
                st.dataframe(pd.DataFrame(list(DATA_GEROBAK.items()), columns=['ID', 'Nama']))
                nama_cab = st.text_input("Nama Cabang Baru")
                if st.button("Tambah Cabang"):
                    ids = [int(k) for k in DATA_GEROBAK.keys() if k.isdigit()]
                    next_id = str(max(ids)+1) if ids else "1"
                    DATA_GEROBAK[next_id] = nama_cab
                    save_cabang_update(DATA_GEROBAK)
                    st.success("Disimpan!"); st.rerun()
                
                hapus_c = st.selectbox("Hapus Cabang", list(DATA_GEROBAK.values()))
                if st.button("Hapus Cabang"):
                    key = next((k for k, v in DATA_GEROBAK.items() if v == hapus_c), None)
                    if key: 
                        del DATA_GEROBAK[key]
                        save_cabang_update(DATA_GEROBAK)
                        st.rerun()

            with t2:
                st.dataframe(pd.DataFrame(list(DATA_STAFF.items()), columns=['PIN', 'NAMA']))
                hapus_s = st.selectbox("Hapus Staff", [f"{v} - {k}" for k,v in DATA_STAFF.items()])
                if st.button("Hapus Staff"):
                    pin_tg = hapus_s.split(" - ")[-1]
                    delete_staff_by_pin(pin_tg)
                    st.rerun()

            with t3:
                st.dataframe(pd.DataFrame(list(MENU_HARGA.items()), columns=['Menu', 'Harga']))
                c1, c2 = st.columns(2)
                nm = c1.text_input("Nama Menu")
                hr = c2.number_input("Harga", step=500)
                if st.button("Simpan Menu"):
                    MENU_HARGA[nm] = int(hr)
                    save_menu_update(MENU_HARGA)
                    st.rerun()
                
                hps_m = st.selectbox("Hapus Menu", list(MENU_HARGA.keys()))
                if st.button("Hapus Menu Item"):
                    del MENU_HARGA[hps_m]
                    save_menu_update(MENU_HARGA)
                    st.rerun()
            st.divider()

        # OPERASIONAL STAFF
        st.subheader("📍 Operasional Harian")
        pilih_cabang = st.selectbox("Pilih Lokasi:", list(DATA_GEROBAK.values()))
        
        # Cek Status Shift dari Sheets
        shift_data = load_shift_active(pilih_cabang)
        
        if shift_data:
            st.info(f"⚠️ SHIFT AKTIF: {shift_data['pic']} (Masuk {shift_data['jam_masuk']})")
        else:
            st.success("✅ GEROBAK KOSONG (Siap Buka)")

        tab_op, tab_cl = st.tabs(["OPENING", "CLOSING"])

        with tab_op:
            if shift_data:
                st.warning("Sudah ada shift berjalan.")
            else:
                with st.form("opening"):
                    st.write("Stok Awal:")
                    stok_awal = {}
                    cols = st.columns(2)
                    for i, (m, h) in enumerate(MENU_HARGA.items()):
                        with cols[i % 2]:
                            stok_awal[m] = st.number_input(f"{m}", min_value=0)
                    
                    if st.form_submit_button("SIMPAN OPENING"):
                        jam = save_shift_opening(pilih_cabang, user, pin, stok_awal)
                        if jam:
                            kirim_telegram(f"☀️ OPENING\n📍 {pilih_cabang}\n👤 {user}\n🕒 {jam}")
                            st.success("Tersimpan di Cloud!"); st.rerun()
                        else: st.error("Gagal simpan ke Sheets.")

        with tab_cl:
            if not shift_data:
                st.warning("Belum Opening.")
            elif shift_data['pin_pic'] != pin:
                st.error("Bukan shift Anda.")
            else:
                with st.form("closing"):
                    st.write("Hitung Sisa:")
                    omzet = 0
                    jual_list = []
                    excel_data = []
                    tgl = get_waktu_wib().strftime("%Y-%m-%d")
                    jam_pulang = get_waktu_wib().strftime("%H:%M")

                    for m, h in MENU_HARGA.items():
                        aw = shift_data['stok'].get(m, 0)
                        ss = st.number_input(f"Sisa {m} (Awal: {aw})", max_value=aw, min_value=0)
                        lk = aw - ss
                        duit = lk * h
                        omzet += duit
                        jual_list.append(f"{m}: {lk}")
                        excel_data.append({
                            "TANGGAL": tgl, "JAM_MASUK": shift_data['jam_masuk'], "JAM_PULANG": jam_pulang,
                            "GEROBAK": pilih_cabang, "STAFF": user, "ITEM": m,
                            "AWAL": aw, "SISA": ss, "TERJUAL": lk, "OMZET_ITEM": duit
                        })

                    st.info(f"💰 Target: {format_rupiah(omzet)}")
                    tunai = st.number_input("Tunai", step=1000)
                    qris = st.number_input("QRIS", step=1000)
                    total_fisik = tunai + qris
                    selisih = total_fisik - omzet
                    
                    st.caption(f"Fisik: {format_rupiah(total_fisik)} | Selisih: {format_rupiah(selisih)}")
                    catatan = st.text_area("Catatan")

                    if st.form_submit_button("KIRIM LAPORAN"):
                        status = "PAS" if selisih == 0 else ("LEBIH" if selisih > 0 else "MINUS")
                        msg = (f"🌙 CLOSING\n📍 {pilih_cabang}\n👤 {user}\n📊 Omzet: {format_rupiah(omzet)}\n"
                               f"💵 Tunai: {format_rupiah(tunai)}\n💳 QRIS: {format_rupiah(qris)}\n"
                               f"Status: {status} ({format_rupiah(selisih)})\n📝 {catatan}")
                        
                        kirim_telegram(msg)
                        
                        # Tambah baris setoran ke Excel data
                        excel_data.append({"TANGGAL": tgl, "JAM_MASUK": shift_data['jam_masuk'], "JAM_PULANG": jam_pulang, "GEROBAK": pilih_cabang, "STAFF": user, "ITEM": "SETOR TUNAI", "AWAL": 0, "SISA": 0, "TERJUAL": 0, "OMZET_ITEM": tunai})
                        excel_data.append({"TANGGAL": tgl, "JAM_MASUK": shift_data['jam_masuk'], "JAM_PULANG": jam_pulang, "GEROBAK": pilih_cabang, "STAFF": user, "ITEM": "SETOR QRIS", "AWAL": 0, "SISA": 0, "TERJUAL": 0, "OMZET_ITEM": qris})
                        
                        save_laporan_final(excel_data) # Simpan Permanen ke Sheet LAPORAN
                        delete_shift_closing(pilih_cabang) # Hapus Shift Sementara
                        
                        st.success("Laporan tersimpan Aman di Google Sheets!"); st.balloons(); st.rerun()

if __name__ == "__main__":
    main()
                        
