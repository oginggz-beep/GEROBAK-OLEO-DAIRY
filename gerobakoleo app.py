import streamlit as st
import json
import os
import requests
import pandas as pd
from datetime import datetime

# ================= KONFIGURASI KEAMANAN =================
# Mengambil data rahasia dari file .streamlit/secrets.toml
try:
    TOKEN_BOT = st.secrets["telegram"]["token"]
    ID_OWNER  = st.secrets["telegram"]["owner_id"]
    PIN_OWNER = st.secrets["telegram"]["pin_owner"]
except Exception as e:
    st.error("⚠️ File .streamlit/secrets.toml belum dibuat atau format salah!")
    st.info("Buat folder .streamlit dan file secrets.toml berisi [telegram] token=... terlebih dahulu.")
    st.stop()

# Nama File Database
FILE_DB_GEROBAK = "database_gerobak.json"
FILE_DB_STAFF   = "database_staff.json"
FILE_DB_MENU    = "database_menu.json"
FILE_EXCEL_REP  = "LAPORAN_HARIAN_LENGKAP.xlsx"

# Data Master Default
MENU_DEFAULT = {
    "Strawberry Milk": 10000, 
    "Coklat Milk": 12000,
    "Kopi Susu Aren": 15000, 
    "Matcha Latte": 15000
}
DATA_GEROBAK = {"1": "Gerobak Alun-Alun", "2": "Gerobak Stasiun", "3": "Gerobak Pasar"}

# ================= FUNGSI BANTUAN =================
def kirim_telegram(pesan):
    """Mengirim pesan teks ke Telegram Owner"""
    try:
        url = f"https://api.telegram.org/bot{TOKEN_BOT}/sendMessage"
        requests.post(url, data={"chat_id": ID_OWNER, "text": pesan})
    except Exception as e: 
        print(f"Error Telegram: {e}")

def kirim_file_excel_telegram():
    """Mengirim file Excel ke Telegram Owner"""
    if os.path.exists(FILE_EXCEL_REP):
        try:
            url = f"https://api.telegram.org/bot{TOKEN_BOT}/sendDocument"
            with open(FILE_EXCEL_REP, 'rb') as f:
                data = {'chat_id': ID_OWNER, 'caption': '📊 Update Laporan Excel'}
                files = {'document': f}
                requests.post(url, data=data, files=files)
        except: pass

def format_rupiah(angka):
    return f"Rp {angka:,}".replace(",", ".")

def load_json(filename):
    if os.path.exists(filename):
        try:
            with open(filename, 'r') as f: return json.load(f)
        except: return {}
    return {}

def save_json(filename, data):
    with open(filename, 'w') as f: json.dump(data, f, indent=4)

# --- FUNGSI MENU ---
def get_menu_aktif():
    data = load_json(FILE_DB_MENU)
    if not data:
        save_json(FILE_DB_MENU, MENU_DEFAULT)
        return MENU_DEFAULT
    return data

def simpan_menu_baru(nama_item, harga_item):
    data = get_menu_aktif()
    data[nama_item] = int(harga_item)
    save_json(FILE_DB_MENU, data)

def hapus_menu(nama_item):
    data = get_menu_aktif()
    if nama_item in data:
        del data[nama_item]
        save_json(FILE_DB_MENU, data)

# --- FUNGSI STAFF ---
def simpan_staff_baru(nama, pin):
    data = load_json(FILE_DB_STAFF)
    if pin in data: return False
    data[pin] = nama
    save_json(FILE_DB_STAFF, data)
    return True

def hapus_staff(pin_target):
    data = load_json(FILE_DB_STAFF)
    if pin_target in data:
        nama = data[pin_target]
        del data[pin_target]
        save_json(FILE_DB_STAFF, data)
        return nama
    return None

# ================= FUNGSI EXCEL =================
def simpan_ke_excel_database(data_rows):
    try:
        df_baru = pd.DataFrame(data_rows)
        if os.path.exists(FILE_EXCEL_REP):
            df_lama = pd.read_excel(FILE_EXCEL_REP)
            df_final = pd.concat([df_lama, df_baru], ignore_index=True)
        else:
            df_final = df_baru
        df_final.to_excel(FILE_EXCEL_REP, index=False)
        return True
    except Exception as e:
        st.error(f"❌ Gagal simpan Excel: {e}")
        return False

# ================= APLIKASI WEB UTAMA =================
def main():
    st.set_page_config(page_title="Sistem Gerobak Aman", page_icon="🔒", layout="centered")
    
    MENU_SEKARANG = get_menu_aktif()
    st.title("🥤 Kasir & Absensi (Secure)")
    st.caption(f"📅 {datetime.now().strftime('%d-%m-%Y')}")

    if 'user_nama' not in st.session_state: st.session_state['user_nama'] = None
    if 'user_pin' not in st.session_state: st.session_state['user_pin'] = None

    # --- SIDEBAR ---
    with st.sidebar:
        st.header("🔐 Akses Karyawan")
        
        if st.session_state['user_nama'] is None:
            mode_akses = st.radio("Menu:", ["Masuk (Login)", "Daftar Baru"])
            
            if mode_akses == "Masuk (Login)":
                st.write("Silakan Login:")
                pin_input = st.text_input("Ketik PIN Anda", max_chars=6, type="password", key="login_pin")
                if st.button("Masuk"):
                    data_staff = load_json(FILE_DB_STAFF)
                    # Cek Owner pakai data dari secrets
                    if pin_input == PIN_OWNER:
                        st.session_state['user_nama'] = "OWNER"
                        st.session_state['user_pin'] = PIN_OWNER
                        st.toast("Selamat datang, Bos!", icon="😎")
                        st.rerun()
                    elif pin_input in data_staff:
                        st.session_state['user_nama'] = data_staff[pin_input]
                        st.session_state['user_pin'] = pin_input
                        st.toast(f"Selamat bekerja, {data_staff[pin_input]}!", icon="💪")
                        st.rerun()
                    else: st.error("PIN Tidak Dikenal.")

            elif mode_akses == "Daftar Baru":
                st.write("Buat Akun Baru:")
                nama_baru = st.text_input("Nama Panggilan")
                pin_baru = st.text_input("Buat PIN (Angka)", max_chars=6)
                if st.button("Simpan Data"):
                    if nama_baru and pin_baru:
                        if simpan_staff_baru(nama_baru, pin_baru):
                            st.success(f"✅ Sukses! {nama_baru}")
                            kirim_telegram(f"🆕 *STAFF BARU*\nNama: {nama_baru}\nPIN: {pin_baru}")
                        else: st.error("❌ PIN sudah dipakai.")
                    else: st.warning("Isi Nama & PIN dulu.")
        else:
            st.success(f"👤 Login: **{st.session_state['user_nama']}**")
            if st.button("🚪 LOG OUT"):
                st.session_state['user_nama'] = None
                st.session_state['user_pin'] = None
                st.rerun()

    # --- AREA UTAMA ---
    if st.session_state['user_nama']:
        nama_aktif = st.session_state['user_nama']
        pin_aktif  = st.session_state['user_pin']
        
        # === FITUR OWNER ===
        if nama_aktif == "OWNER":
            st.error("🔧 **MENU SUPER ADMIN**")
            tab_bos1, tab_bos2, tab_bos3 = st.tabs(["🛒 Status Gerobak", "👥 Kelola Staff", "📋 Kelola Menu"])
            
            with tab_bos1:
                st.write("Reset Data Shift:")
                db_gerobak_bos = load_json(FILE_DB_GEROBAK)
                for g_nama in list(DATA_GEROBAK.values()):
                    info_g = db_gerobak_bos.get(g_nama)
                    col_a, col_b = st.columns([3, 1])
                    if info_g:
                        col_a.markdown(f"**{g_nama}** : 🔴 AKTIF ({info_g['pic']})")
                        if col_b.button(f"FORCE CLOSE", key=f"del_{g_nama}"):
                            del db_gerobak_bos[g_nama]
                            save_json(FILE_DB_GEROBAK, db_gerobak_bos)
                            st.rerun()
                    else:
                        col_a.markdown(f"**{g_nama}** : 🟢 KOSONG")
            
            with tab_bos2:
                data_staff_bos = load_json(FILE_DB_STAFF)
                if data_staff_bos:
                    df_staff = pd.DataFrame(list(data_staff_bos.items()), columns=['PIN', 'NAMA'])
                    st.dataframe(df_staff, hide_index=True, use_container_width=True)
                    list_pilihan = [f"{v} (PIN: {k})" for k,v in data_staff_bos.items()]
                    pilih_hapus = st.selectbox("Hapus Staff:", list_pilihan)
                    if st.button("Hapus Staff"):
                        pin_target = pilih_hapus.split("PIN: ")[1].replace(")", "")
                        if hapus_staff(pin_target): st.rerun()
            
            with tab_bos3:
                st.subheader("Daftar Menu & Harga")
                df_menu = pd.DataFrame(list(MENU_SEKARANG.items()), columns=['Nama Menu', 'Harga'])
                st.dataframe(df_menu, hide_index=True, use_container_width=True)
                
                col_m1, col_m2 = st.columns(2)
                with col_m1: input_menu_nama = st.text_input("Nama Menu Baru / Edit")
                with col_m2: input_menu_harga = st.number_input("Harga Jual", min_value=0, step=500)
                
                if st.button("💾 Simpan Menu"):
                    if input_menu_nama and input_menu_harga > 0:
                        simpan_menu_baru(input_menu_nama, input_menu_harga)
                        st.success(f"Menu {input_menu_nama} disimpan!")
                        st.rerun()
                
                st.write("Hapus Menu:")
                pilih_hapus_menu = st.selectbox("Pilih Menu:", list(MENU_SEKARANG.keys()))
                if st.button("🗑️ Hapus Menu"):
                    hapus_menu(pilih_hapus_menu); st.rerun()
            st.divider()

        # === OPERASIONAL STAFF ===
        st.subheader(f"📍 Operasional Toko")
        pilihan_gerobak = st.selectbox("Lokasi:", list(DATA_GEROBAK.values()))
        
        db_gerobak = load_json(FILE_DB_GEROBAK) 
        data_shift = db_gerobak.get(pilihan_gerobak)
        
        if data_shift:
            if data_shift['pin_pic'] == pin_aktif:
                st.info(f"⚡ SHIFT ANDA AKTIF ({data_shift['jam_masuk']})")
            else:
                st.warning(f"⚠️ Shift Aktif: **{data_shift['pic']}**")
        else:
            st.success("✅ Siap Buka Shift")

        tab1, tab2 = st.tabs(["☀️ OPENING", "🌙 CLOSING"])

        with tab1: # OPENING
            if data_shift and data_shift['pin_pic'] != pin_aktif:
                st.error(f"⛔ Shift dipegang {data_shift['pic']}.")
            else:
                with st.form("form_opening"):
                    st.write("📦 **Stok Awal:**")
                    stok_input = {}
                    col1, col2 = st.columns(2)
                    i = 0
                    for menu in MENU_SEKARANG:
                        val = data_shift['stok'].get(menu, 0) if data_shift else 0
                        with (col1 if i % 2 == 0 else col2):
                            stok_input[menu] = st.number_input(f"{menu}", min_value=0, value=int(val))
                        i += 1
                    
                    if st.form_submit_button("SIMPAN OPENING"):
                        jam_skrg = datetime.now().strftime("%H:%M")
                        data_baru = {
                            "tanggal": datetime.now().strftime("%Y-%m-%d"),
                            "jam_masuk": data_shift['jam_masuk'] if data_shift else jam_skrg,
                            "pic": nama_aktif, "pin_pic": pin_aktif, "stok": stok_input
                        }
                        db_gerobak[pilihan_gerobak] = data_baru
                        save_json(FILE_DB_GEROBAK, db_gerobak)
                        
                        list_stok = [f"{k}: {v}" for k,v in stok_input.items()]
                        msg = (f"☀️ *OPENING*\n📍 {pilihan_gerobak}\n👤 {nama_aktif}\n"
                               f"🕒 {data_baru['jam_masuk']}\n📦 Stok: {', '.join(list_stok)}")
                        kirim_telegram(msg)
                        st.success("Tersimpan!"); st.rerun()

        with tab2: # CLOSING
            if not data_shift:
                st.info("Belum ada data Opening.")
            elif data_shift['pin_pic'] != pin_aktif:
                st.error("⛔ Bukan shift Anda!")
            else:
                with st.form("form_closing"):
                    st.write("📊 **Hitung Jualan:**")
                    stok_awal = data_shift['stok']
                    omzet = 0
                    txt_jual = []
                    list_excel_rows = []
                    
                    jam_pulang = datetime.now().strftime("%H:%M")
                    tanggal_ini = datetime.now().strftime("%Y-%m-%d")

                    for menu, harga in MENU_SEKARANG.items():
                        awal = int(stok_awal.get(menu, 0))
                        sisa = st.number_input(f"Sisa {menu} (Awal: {awal})", min_value=0, max_value=awal)
                        laku = awal - sisa
                        omzet += (laku * harga)
                        
                        if laku > 0: txt_jual.append(f"{menu}: {laku}")
                        
                        list_excel_rows.append({
                            "TANGGAL": tanggal_ini, "JAM_MASUK": data_shift['jam_masuk'], 
                            "JAM_PULANG": jam_pulang, "GEROBAK": pilihan_gerobak, 
                            "STAFF": nama_aktif, "ITEM": menu, "AWAL": awal, 
                            "SISA": sisa, "TERJUAL": laku, "OMZET_ITEM": (laku * harga),
                            "TIPE": "TRANSAKSI"
                        })

                    st.info(f"💰 Target Setoran: **{format_rupiah(omzet)}**")
                    col_u1, col_u2 = st.columns(2)
                    with col_u1: tunai = st.number_input("Setor Tunai", step=1000)
                    with col_u2: qris = st.number_input("Setor QRIS", step=1000)
                    catatan = st.text_area("Catatan")

                    if st.form_submit_button("KIRIM LAPORAN"):
                        selisih = (tunai + qris) - omzet
                        status = "✅ PAS" if selisih == 0 else (f"⚠️ MINUS {selisih}" if selisih < 0 else f"ℹ️ LEBIH {selisih}")
                        
                        msg = (f"🌙 *CLOSING*\n📍 {pilihan_gerobak}\n👤 {nama_aktif}\n"
                               f"🕒 Shift: {data_shift['jam_masuk']} - {jam_pulang}\n\n"
                               f"📊 Jualan: {', '.join(txt_jual) if txt_jual else 'ZONK'}\n"
                               f"💰 Target: {format_rupiah(omzet)}\n"
                               f"💵 Tunai: {format_rupiah(tunai)}\n💳 QRIS: {format_rupiah(qris)}\n"
                               f"Status: {status}\n📝 {catatan}")
                        kirim_telegram(msg)
                        
                        list_excel_rows.append({
                            "TANGGAL": tanggal_ini, "JAM_MASUK": data_shift['jam_masuk'], 
                            "JAM_PULANG": jam_pulang, "GEROBAK": pilihan_gerobak, 
                            "STAFF": nama_aktif, "ITEM": "TOTAL SETORAN", 
                            "AWAL": 0, "SISA": 0, "TERJUAL": 0, "OMZET_ITEM": (tunai + qris),
                            "TIPE": "SETORAN"
                        })
                        
                        simpan_ke_excel_database(list_excel_rows)
                        kirim_file_excel_telegram()
                        
                        del db_gerobak[pilihan_gerobak]
                        save_json(FILE_DB_GEROBAK, db_gerobak)
                        st.success("Sukses!"); st.balloons(); st.rerun()
    else:
        st.info("👈 Silakan Login dulu.")

if __name__ == "__main__":
    main()
                        
