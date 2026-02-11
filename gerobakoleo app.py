import streamlit as st
import json
import os
import requests
import pandas as pd
from datetime import datetime
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
import openpyxl

# ================= KONFIGURASI UTAMA (EDIT DISINI) =================
# 👇 Masukkan Token Bot Telegram Anda di dalam tanda kutip dibawah ini:
TOKEN_BOT = "8285539149:AAHQd-_W9aaBGSz3AUPg0oCuxabZUL6yJo4" 

# 👇 ID Telegram & PIN Owner (Bisa diganti)
ID_OWNER  = "8505488457"  
PIN_OWNER = "8888"        

# ================= DATABASE & FILE =================
FILE_DB_GEROBAK = "database_gerobak.json"
FILE_DB_STAFF   = "database_staff.json"
FILE_DB_MENU    = "database_menu.json"
FILE_EXCEL_REP  = "LAPORAN_HARIAN_LENGKAP.xlsx"

# Data Master Default
MENU_DEFAULT = {
    "Strawberry Milk": 10000, "Coklat Milk": 12000,
    "Kopi Susu Aren": 15000, "Matcha Latte": 15000
}
DATA_GEROBAK = {"1": "Gerobak Alun-Alun", "2": "Gerobak Stasiun", "3": "Gerobak Pasar"}

# ================= FUNGSI BANTUAN =================
def kirim_telegram(pesan):
    """Kirim pesan teks ke Telegram Owner"""
    if TOKEN_BOT == "PASTE_TOKEN_BOT_ANDA_DISINI": return # Cegah error jika token belum diisi
    try:
        url = f"https://api.telegram.org/bot{TOKEN_BOT}/sendMessage"
        requests.post(url, data={"chat_id": ID_OWNER, "text": pesan})
    except: pass

def kirim_file_excel_telegram():
    """Kirim file Excel ke Telegram"""
    if TOKEN_BOT == "PASTE_TOKEN_BOT_ANDA_DISINI": return
    if os.path.exists(FILE_EXCEL_REP):
        try:
            url = f"https://api.telegram.org/bot{TOKEN_BOT}/sendDocument"
            with open(FILE_EXCEL_REP, 'rb') as f:
                requests.post(url, data={'chat_id': ID_OWNER, 'caption': '📊 Update Laporan Excel'}, files={'document': f})
        except: pass

def format_rupiah(angka):
    return f"Rp {int(angka):,}".replace(",", ".")

def load_json(filename):
    if os.path.exists(filename):
        try:
            with open(filename, 'r') as f: return json.load(f)
        except: return {}
    return {}

def save_json(filename, data):
    with open(filename, 'w') as f: json.dump(data, f, indent=4)

# --- FUNGSI MENU DINAMIS ---
def get_menu_aktif():
    data = load_json(FILE_DB_MENU)
    if not data:
        save_json(FILE_DB_MENU, MENU_DEFAULT)
        return MENU_DEFAULT
    return data

def simpan_menu_baru(nama, harga):
    data = get_menu_aktif()
    data[nama] = int(harga)
    save_json(FILE_DB_MENU, data)

def hapus_menu(nama):
    data = get_menu_aktif()
    if nama in data:
        del data[nama]
        save_json(FILE_DB_MENU, data)

# --- FUNGSI STAFF ---
def simpan_staff_baru(nama, pin):
    data = load_json(FILE_DB_STAFF)
    if pin in data: return False
    data[pin] = nama
    save_json(FILE_DB_STAFF, data)
    return True

def hapus_staff(pin):
    data = load_json(FILE_DB_STAFF)
    if pin in data:
        nama = data[pin]
        del data[pin]
        save_json(FILE_DB_STAFF, data)
        return nama
    return None

# ================= FUNGSI EXCEL PRO (RAPI & CANTIK) =================
def rapikan_excel(filename):
    try:
        wb = openpyxl.load_workbook(filename)
        ws = wb.active

        # Style Header (Biru Tua, Tebal, Putih)
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="203764", end_color="203764", fill_type="solid")
        center = Alignment(horizontal="center", vertical="center")
        thin_border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
        
        # Terapkan ke Header
        for cell in ws[1]:
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = center
            cell.border = thin_border

        # Auto Width & Format Isi
        for col in ws.columns:
            max_len = 0
            col_letter = col[0].column_letter
            for cell in col:
                cell.border = thin_border
                try:
                    if len(str(cell.value)) > max_len: max_len = len(str(cell.value))
                except: pass
                
                # Format Rupiah Otomatis
                header_text = ws[f"{col_letter}1"].value
                if header_text and any(x in str(header_text).upper() for x in ['OMZET', 'HARGA', 'TUNAI', 'QRIS', 'TOTAL']):
                    cell.number_format = '#,##0 "Rp"'

            ws.column_dimensions[col_letter].width = (max_len + 3)
        wb.save(filename)
    except: pass

def simpan_ke_excel_database(data_rows):
    try:
        df_baru = pd.DataFrame(data_rows)
        if os.path.exists(FILE_EXCEL_REP):
            df_lama = pd.read_excel(FILE_EXCEL_REP)
            df_final = pd.concat([df_lama, df_baru], ignore_index=True)
        else:
            df_final = df_baru
        
        # Simpan & Rapikan
        df_final.to_excel(FILE_EXCEL_REP, index=False)
        rapikan_excel(FILE_EXCEL_REP)
        return True
    except Exception as e:
        st.error(f"❌ Gagal Excel: {e}")
        return False

# ================= TAMPILAN APLIKASI =================
def main():
    st.set_page_config(page_title="Sistem Kasir Pro", page_icon="🛍️", layout="centered")
    
    # Cek Token Dulu
    if TOKEN_BOT == "PASTE_TOKEN_BOT_ANDA_DISINI":
        st.error("⚠️ TOKEN BELUM DIISI!")
        st.warning("Buka file app.py, lalu ganti tulisan 'PASTE_TOKEN_BOT_ANDA_DISINI' dengan Token Telegram Anda.")
        st.stop()

    MENU_SEKARANG = get_menu_aktif()
    st.title("🛍️ Kasir & Absensi Gerobak")
    st.caption(f"📅 Tanggal: {datetime.now().strftime('%d-%m-%Y')}")

    if 'user_nama' not in st.session_state: st.session_state['user_nama'] = None
    if 'user_pin' not in st.session_state: st.session_state['user_pin'] = None

    # --- SIDEBAR LOGIN ---
    with st.sidebar:
        st.header("🔐 Login Akses")
        if st.session_state['user_nama'] is None:
            mode = st.radio("Pilih Menu:", ["Login Masuk", "Daftar Staff Baru"])
            
            if mode == "Login Masuk":
                pin = st.text_input("Masukkan PIN", type="password", max_chars=6)
                if st.button("🚀 MASUK"):
                    data_staff = load_json(FILE_DB_STAFF)
                    if pin == PIN_OWNER:
                        st.session_state['user_nama'] = "OWNER"
                        st.session_state['user_pin'] = PIN_OWNER
                        st.rerun()
                    elif pin in data_staff:
                        st.session_state['user_nama'] = data_staff[pin]
                        st.session_state['user_pin'] = pin
                        st.rerun()
                    else: st.error("PIN Salah!")

            elif mode == "Daftar Staff Baru":
                nama = st.text_input("Nama Panggilan")
                pin_baru = st.text_input("Buat PIN (Angka)", max_chars=6)
                if st.button("💾 Simpan Staff"):
                    if nama and pin_baru:
                        if simpan_staff_baru(nama, pin_baru):
                            st.success(f"Staff {nama} Terdaftar!")
                            kirim_telegram(f"🆕 STAFF BARU: {nama} (PIN: {pin_baru})")
                        else: st.error("PIN sudah dipakai!")
        else:
            st.success(f"Halo, {st.session_state['user_nama']}")
            if st.button("🚪 KELUAR"):
                st.session_state['user_nama'] = None; st.session_state['user_pin'] = None; st.rerun()

    # --- MENU UTAMA ---
    if st.session_state['user_nama']:
        user = st.session_state['user_nama']
        pin  = st.session_state['user_pin']

        # === FITUR OWNER ===
        if user == "OWNER":
            st.error("🔧 **MENU ADMIN BOS**")
            t1, t2, t3 = st.tabs(["Gerobak", "Staff", "Menu Harga"])
            
            with t1: # Reset Shift
                st.write("Status Shift:")
                db_gerobak = load_json(FILE_DB_GEROBAK)
                for g_nama in DATA_GEROBAK.values():
                    if g_nama in db_gerobak:
                        st.write(f"🔴 {g_nama} (Aktif: {db_gerobak[g_nama]['pic']})")
                        if st.button(f"Reset {g_nama}", key=g_nama):
                            del db_gerobak[g_nama]
                            save_json(FILE_DB_GEROBAK, db_gerobak); st.rerun()
                    else: st.write(f"🟢 {g_nama} (Kosong)")
            
            with t2: # Hapus Staff
                data_s = load_json(FILE_DB_STAFF)
                st.dataframe(pd.DataFrame(list(data_s.items()), columns=['PIN', 'NAMA']), hide_index=True)
                hapus = st.selectbox("Hapus Staff:", [f"{v} ({k})" for k,v in data_s.items()])
                if st.button("Hapus"): hapus_staff(hapus.split('(')[1][:-1]); st.rerun()

            with t3: # Kelola Menu
                st.dataframe(pd.DataFrame(list(MENU_SEKARANG.items()), columns=['Menu', 'Harga']), hide_index=True)
                c1, c2 = st.columns(2)
                nm = c1.text_input("Nama Menu")
                hrg = c2.number_input("Harga", step=500)
                if st.button("Simpan Menu"): simpan_menu_baru(nm, hrg); st.rerun()
                
                hps = st.selectbox("Hapus Menu:", list(MENU_SEKARANG.keys()))
                if st.button("Hapus Menu Terpilih"): hapus_menu(hps); st.rerun()
            st.divider()

        # === OPERASIONAL ===
        st.subheader("📍 Operasional")
        lokasi = st.selectbox("Pilih Lokasi:", list(DATA_GEROBAK.values()))
        
        db_gerobak = load_json(FILE_DB_GEROBAK)
        shift = db_gerobak.get(lokasi)

        if shift: st.info(f"⚡ Shift Aktif: {shift['pic']} ({shift['jam_masuk']})")
        else: st.success("✅ Gerobak Kosong")

        tab_op, tab_cl = st.tabs(["☀️ OPENING (Stok)", "🌙 CLOSING (Setor)"])

        with tab_op:
            if shift and shift['pin_pic'] != pin: st.error("⛔ Shift orang lain!")
            else:
                with st.form("opening"):
                    st.write("📦 Input Stok Awal:")
                    stok_in = {}
                    cols = st.columns(2)
                    for i, m in enumerate(MENU_SEKARANG):
                        val = shift['stok'].get(m, 0) if shift else 0
                        with cols[i%2]: stok_in[m] = st.number_input(f"{m}", value=int(val), min_value=0)
                    
                    if st.form_submit_button("SIMPAN OPENING"):
                        jam = datetime.now().strftime("%H:%M")
                        data = {"tanggal": datetime.now().strftime("%Y-%m-%d"), "jam_masuk": shift['jam_masuk'] if shift else jam, "pic": user, "pin_pic": pin, "stok": stok_in}
                        db_gerobak[lokasi] = data
                        save_json(FILE_DB_GEROBAK, db_gerobak)
                        kirim_telegram(f"☀️ OPENING {lokasi}\n👤 {user}\n📦 Stok Terisi")
                        st.success("Masuk!"); st.rerun()

        with tab_cl:
            if not shift: st.info("Buka shift dulu.")
            elif shift['pin_pic'] != pin: st.error("⛔ Bukan shift Anda.")
            else:
                with st.form("closing"):
                    st.write("📊 Hitung Sisa:")
                    omzet = 0
                    jual_list = []
                    excel_rows = []
                    tgl = datetime.now().strftime("%Y-%m-%d")
                    jam_plg = datetime.now().strftime("%H:%M")

                    for m, hrg in MENU_SEKARANG.items():
                        awal = int(shift['stok'].get(m, 0))
                        sisa = st.number_input(f"Sisa {m} (Awal: {awal})", max_value=awal, min_value=0)
                        laku = awal - sisa
                        duit = laku * hrg
                        omzet += duit
                        if laku > 0: jual_list.append(f"{m}: {laku}")
                        excel_rows.append({"TANGGAL": tgl, "GEROBAK": lokasi, "STAFF": user, "ITEM": m, "AWAL": awal, "SISA": sisa, "TERJUAL": laku, "OMZET_ITEM": duit, "TIPE": "JUAL"})

                    st.markdown(f"### 💰 Total Sistem: {format_rupiah(omzet)}")
                    tunai = st.number_input("Fisik Tunai", step=500)
                    qris = st.number_input("Bukti QRIS", step=500)
                    note = st.text_area("Catatan")

                    if st.form_submit_button("KIRIM LAPORAN"):
                        selisih = (tunai+qris) - omzet
                        stat = "PAS" if selisih==0 else (f"MINUS {selisih}" if selisih<0 else f"LEBIH {selisih}")
                        
                        excel_rows.append({"TANGGAL": tgl, "GEROBAK": lokasi, "STAFF": user, "ITEM": "SETORAN", "AWAL":0,"SISA":0,"TERJUAL":0, "OMZET_ITEM": (tunai+qris), "TIPE": "SETORAN"})
                        simpan_ke_excel_database(excel_rows)
                        kirim_file_excel_telegram()
                        
                        msg = f"🌙 CLOSING {lokasi}\n👤 {user}\n💰 Target: {format_rupiah(omzet)}\n💵 Setor: {format_rupiah(tunai+qris)}\n📝 Status: {stat}\nCatatan: {note}"
                        kirim_telegram(msg)
                        
                        del db_gerobak[lokasi]
                        save_json(FILE_DB_GEROBAK, db_gerobak)
                        st.success("Laporan Terkirim!"); st.balloons(); st.rerun()
    else:
        st.info("👈 Silakan Login di menu samping.")

if __name__ == "__main__":
    main()
            
