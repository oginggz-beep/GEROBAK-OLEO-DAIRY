import streamlit as st
import json
import os
import requests
from datetime import datetime

# ================= KONFIGURASI =================
TOKEN_BOT  = "8285539149:AAHQd-_W9aaBGSz3AUPg0oCuxabZUL6yJo4"
ID_OWNER   = "8505488457"

# File Penyimpanan Database
FILE_DB_GEROBAK = "database_gerobak.json" # Menyimpan Status Shift
FILE_DB_STAFF   = "database_staff.json"   # Menyimpan Akun Staff

# Data Master
DATA_GEROBAK = {"1": "Gerobak Alun-Alun", "2": "Gerobak Stasiun", "3": "Gerobak Pasar"}
MENU_HARGA = {
    "Strawberry Milk": 10000, "Coklat Milk": 12000,
    "Kopi Susu Aren": 15000, "Matcha Latte": 15000
}
PERLENGKAPAN = ["Mesin Press", "Termos Es", "Lap Tangan", "Gunting", "Tempat Sampah"]

# ================= FUNGSI BANTUAN =================
def kirim_telegram(pesan):
    try:
        url = f"https://api.telegram.org/bot{TOKEN_BOT}/sendMessage"
        requests.post(url, data={"chat_id": ID_OWNER, "text": pesan})
    except: pass

def format_rupiah(angka):
    return f"Rp {angka:,}".replace(",", ".")

# --- DATABASE LOAD/SAVE ---
def load_json(filename):
    if os.path.exists(filename):
        try:
            with open(filename, 'r') as f: return json.load(f)
        except: return {}
    return {}

def save_json(filename, data):
    with open(filename, 'w') as f: json.dump(data, f)

def simpan_staff_baru(nama, pin):
    data = load_json(FILE_DB_STAFF)
    if pin in data: return False # Gagal, PIN kembar
    data[pin] = nama
    save_json(FILE_DB_STAFF, data)
    return True

# ================= APLIKASI WEB UTAMA =================
def main():
    st.set_page_config(page_title="Sistem Gerobak", page_icon="🥤", layout="mobile")
    st.title("🥤 Kasir & Absensi")

    # --- SIDEBAR: LOGIN & REGISTER ---
    with st.sidebar:
        st.header("🔐 Akses Karyawan")
        mode_akses = st.radio("Menu:", ["Masuk (Login)", "Daftar Baru"])
        
        # Inisialisasi Session (Biar Login Tidak Hilang saat Klik Tombol)
        if 'user_nama' not in st.session_state: st.session_state['user_nama'] = None
        if 'user_pin' not in st.session_state: st.session_state['user_pin'] = None

        # --- MENU 1: LOGIN ---
        if mode_akses == "Masuk (Login)":
            st.write("Silakan Login:")
            # Pakai text_input biasa biar gak ada ikon mata error
            pin_input = st.text_input("Ketik PIN Anda", max_chars=6, key="login_pin")
            
            if st.button("Masuk"):
                data_staff = load_json(FILE_DB_STAFF)
                
                if pin_input == "9999": # PIN OWNER
                    st.session_state['user_nama'] = "OWNER"
                    st.session_state['user_pin'] = "9999"
                    st.success("Halo BOS OWNER!")
                elif pin_input in data_staff:
                    st.session_state['user_nama'] = data_staff[pin_input]
                    st.session_state['user_pin'] = pin_input
                    st.success(f"Halo, {data_staff[pin_input]}!")
                else:
                    st.error("PIN Tidak Dikenal.")

        # --- MENU 2: DAFTAR BARU ---
        elif mode_akses == "Daftar Baru":
            st.write("Buat Akun Baru:")
            nama_baru = st.text_input("Nama Panggilan")
            pin_baru = st.text_input("Buat PIN (Angka)", max_chars=6)
            
            if st.button("Simpan Data"):
                if nama_baru and pin_baru:
                    if simpan_staff_baru(nama_baru, pin_baru):
                        st.success(f"✅ Sukses! {nama_baru} (PIN: {pin_baru})")
                        kirim_telegram(f"🆕 *STAFF BARU*\nNama: {nama_baru}\nPIN: {pin_baru}")
                    else:
                        st.error("❌ PIN sudah dipakai orang lain.")
                else:
                    st.warning("Isi Nama & PIN dulu.")

    # ================= AREA UTAMA (SETELAH LOGIN) =================
    if st.session_state['user_nama']:
        nama_aktif = st.session_state['user_nama']
        pin_aktif  = st.session_state['user_pin']
        
        st.divider()
        st.write(f"👤 User: **{nama_aktif}**")
        
        # PILIH GEROBAK
        pilihan_gerobak = st.selectbox("📍 Pilih Lokasi:", list(DATA_GEROBAK.values()))
        
        # LOAD DATA GEROBAK
        db_gerobak = load_json(FILE_DB_GEROBAK)
        data_shift = db_gerobak.get(pilihan_gerobak)
        
        # STATUS INFO
        if data_shift:
            st.info(f"⚠️ SHIFT AKTIF: {data_shift['pic']} (Sejak {data_shift['jam_masuk']})")
        else:
            st.success("✅ GEROBAK KOSONG (Siap Buka)")

        # TAB MENU
        tab1, tab2 = st.tabs(["☀️ OPENING", "🌙 CLOSING"])

        # --- TAB OPENING ---
        with tab1:
            if data_shift and data_shift['pin_pic'] != pin_aktif:
                st.error(f"⛔ Gerobak sedang dipakai {data_shift['pic']}. Tidak bisa timpa.")
            else:
                with st.form("form_opening"):
                    st.write("📦 **Stok Awal:**")
                    stok_input = {}
                    for menu in MENU_HARGA:
                        val = data_shift['stok'].get(menu, 0) if data_shift else 0
                        stok_input[menu] = st.number_input(f"{menu}", min_value=0, value=val)
                    
                    if st.form_submit_button("SIMPAN OPENING"):
                        jam_skrg = datetime.now().strftime("%H:%M")
                        data_baru = {
                            "tanggal": datetime.now().strftime("%Y-%m-%d"),
                            "jam_masuk": data_shift['jam_masuk'] if data_shift else jam_skrg,
                            "pic": nama_aktif, "pin_pic": pin_aktif, "stok": stok_input
                        }
                        db_gerobak[pilihan_gerobak] = data_baru
                        save_json(FILE_DB_GEROBAK, db_gerobak)
                        
                        # Format Pesan
                        list_stok = [f"{k}: {v}" for k,v in stok_input.items()]
                        msg = f"☀️ *OPENING WEB*\n📍 {pilihan_gerobak}\n👤 {nama_aktif}\n🕒 {data_baru['jam_masuk']}\n\n📦 {', '.join(list_stok)}"
                        kirim_telegram(msg)
                        st.success("Tersimpan!"); st.rerun()

        # --- TAB CLOSING ---
        with tab2:
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
                    
                    for menu, harga in MENU_HARGA.items():
                        awal = stok_awal.get(menu, 0)
                        sisa = st.number_input(f"Sisa {menu} (Awal: {awal})", min_value=0, max_value=awal)
                        laku = awal - sisa
                        duit = laku * harga
                        omzet += duit
                        txt_jual.append(f"{menu}: {laku}")

                    st.write("💰 **Keuangan:**")
                    st.info(f"Target Sistem: **{format_rupiah(omzet)}**")
                    tunai = st.number_input("Setor Tunai", step=1000)
                    qris = st.number_input("Setor QRIS", step=1000)
                    catatan = st.text_area("Catatan")

                    if st.form_submit_button("KIRIM LAPORAN"):
                        selisih = (tunai + qris) - omzet
                        status = "✅ PAS" if selisih == 0 else (f"⚠️ MINUS {selisih}" if selisih < 0 else f"ℹ️ LEBIH {selisih}")
                        
                        msg = (f"🌙 *CLOSING*\n📍 {pilihan_gerobak}\n👤 {nama_aktif}\n"
                               f"🕒 {data_shift['jam_masuk']} - Selesai\n\n"
                               f"📊 Jualan: {', '.join(txt_jual)}\n"
                               f"💰 Omzet: {format_rupiah(omzet)}\n"
                               f"💵 Tunai: {format_rupiah(tunai)}\n💳 QRIS: {format_rupiah(qris)}\n"
                               f"Status: {status}\n📝 {catatan}")
                        
                        kirim_telegram(msg)
                        del db_gerobak[pilihan_gerobak] # Hapus Data Shift
                        save_json(FILE_DB_GEROBAK, db_gerobak)
                        st.success("Laporan Terkirim!"); st.balloons(); st.rerun()

    else:
        st.info("👈 Silakan Login atau Daftar di menu sebelah kiri.")

if __name__ == "__main__":
    main()
            
