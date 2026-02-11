import streamlit as st
import json
import os
import requests
import pandas as pd
import pytz # Library untuk Zona Waktu WIB
from datetime import datetime
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

# ================= KONFIGURASI =================
TOKEN_BOT  = "8285539149:AAHQd-_W9aaBGSz3AUPg0oCuxabZUL6yJo4"
ID_OWNER   = "8505488457"
PIN_OWNER  = "8888" 

# Nama File
FILE_DB_GEROBAK = "database_gerobak.json"
FILE_DB_STAFF   = "database_staff.json"
FILE_EXCEL_REP  = "LAPORAN_HARIAN_PRO.xlsx" # Nama file excel baru

# Data Master
DATA_GEROBAK = {"1": "Gerobak Alun-Alun", "2": "Gerobak Stasiun", "3": "Gerobak Pasar"}
MENU_HARGA = {
    "Strawberry Milk": 10000, "Coklat Milk": 12000,
    "Kopi Susu Aren": 15000, "Matcha Latte": 15000
}

# ================= FUNGSI BANTUAN =================
def get_waktu_wib():
    """Mengambil waktu sekarang zona Jakarta (WIB)"""
    tz = pytz.timezone('Asia/Jakarta')
    return datetime.now(tz)

def kirim_telegram(pesan):
    try:
        url = f"https://api.telegram.org/bot{TOKEN_BOT}/sendMessage"
        requests.post(url, data={"chat_id": ID_OWNER, "text": pesan})
    except: pass

def kirim_file_excel_telegram():
    if os.path.exists(FILE_EXCEL_REP):
        try:
            url = f"https://api.telegram.org/bot{TOKEN_BOT}/sendDocument"
            with open(FILE_EXCEL_REP, 'rb') as f:
                data = {'chat_id': ID_OWNER, 'caption': '📊 Laporan Excel Profesional'}
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
    with open(filename, 'w') as f: json.dump(data, f)

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

# ================= FUNGSI EXCEL PROFESIONAL =================
def rapikan_excel():
    """Fungsi untuk mempercantik tampilan Excel (Warna, Border, Auto Width)"""
    try:
        wb = load_workbook(FILE_EXCEL_REP)
        ws = wb.active
        
        # 1. Style Header (Biru Tua, Teks Putih)
        header_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF", size=11)
        thin_border = Border(left=Side(style='thin'), right=Side(style='thin'), 
                             top=Side(style='thin'), bottom=Side(style='thin'))

        for cell in ws[1]: # Baris pertama
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")

        # 2. Style Isi Tabel (Border & Alignment)
        for row in ws.iter_rows(min_row=2):
            for cell in row:
                cell.border = thin_border
                cell.alignment = Alignment(vertical="center", horizontal="center")
                
                # Jika kolom Rupiah/Angka (Kolom ke-10 / J), rata kanan
                if cell.column == 10: 
                    cell.number_format = '#,##0'
                    cell.alignment = Alignment(horizontal="right")

        # 3. Auto Width (Lebar Kolom Otomatis)
        for col in ws.columns:
            max_length = 0
            column = col[0].column_letter
            for cell in col:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except: pass
            ws.column_dimensions[column].width = (max_length + 2)

        wb.save(FILE_EXCEL_REP)
    except: pass

def simpan_ke_excel_database(data_rows):
    try:
        if os.path.exists(FILE_EXCEL_REP):
            df_lama = pd.read_excel(FILE_EXCEL_REP)
            df_baru = pd.DataFrame(data_rows)
            df_final = pd.concat([df_lama, df_baru], ignore_index=True)
        else:
            df_final = pd.DataFrame(data_rows)
            
        # Simpan Data Mentah
        df_final.to_excel(FILE_EXCEL_REP, index=False)
        
        # PANGGIL FUNGSI PERCANTIK
        rapikan_excel()
        return True
    except Exception as e:
        return False

# ================= APLIKASI WEB UTAMA =================
def main():
    st.set_page_config(page_title="Sistem Gerobak", page_icon="🥤", layout="centered")
    st.title("🥤 Kasir & Absensi")

    if 'user_nama' not in st.session_state: st.session_state['user_nama'] = None
    if 'user_pin' not in st.session_state: st.session_state['user_pin'] = None

    # --- SIDEBAR ---
    with st.sidebar:
        st.header("🔐 Akses Karyawan")
        
        if st.session_state['user_nama'] is None:
            mode_akses = st.radio("Menu:", ["Masuk (Login)", "Daftar Baru"])
            
            if mode_akses == "Masuk (Login)":
                st.write("Silakan Login:")
                pin_input = st.text_input("Ketik PIN Anda", max_chars=6, key="login_pin")
                if st.button("Masuk"):
                    data_staff = load_json(FILE_DB_STAFF)
                    if pin_input == PIN_OWNER:
                        st.session_state['user_nama'] = "OWNER"
                        st.session_state['user_pin'] = PIN_OWNER
                        st.success("Halo BOS OWNER!")
                        st.rerun()
                    elif pin_input in data_staff:
                        st.session_state['user_nama'] = data_staff[pin_input]
                        st.session_state['user_pin'] = pin_input
                        st.success(f"Halo, {data_staff[pin_input]}!")
                        st.rerun()
                    else: st.error("PIN Tidak Dikenal.")

            elif mode_akses == "Daftar Baru":
                st.write("Buat Akun Baru:")
                nama_baru = st.text_input("Nama Panggilan")
                pin_baru = st.text_input("Buat PIN (Angka)", max_chars=6)
                if st.button("Simpan Data"):
                    if nama_baru and pin_baru:
                        if simpan_staff_baru(nama_baru, pin_baru):
                            st.success(f"✅ Sukses! {nama_baru} (PIN: {pin_baru})")
                            kirim_telegram(f"🆕 *STAFF BARU*\nNama: {nama_baru}\nPIN: {pin_baru}")
                        else: st.error("❌ PIN sudah dipakai.")
                    else: st.warning("Isi Nama & PIN dulu.")
        else:
            st.success(f"👤 User: **{st.session_state['user_nama']}**")
            if st.button("🚪 LOG OUT"):
                st.session_state['user_nama'] = None
                st.session_state['user_pin'] = None
                st.rerun()

    # --- AREA UTAMA ---
    if st.session_state['user_nama']:
        nama_aktif = st.session_state['user_nama']
        pin_aktif  = st.session_state['user_pin']
        
        # MENU OWNER
        if nama_aktif == "OWNER":
            st.error("🔧 **MENU SUPER ADMIN**")
            tab_bos1, tab_bos2 = st.tabs(["🛒 Kelola Gerobak", "👥 Kelola Staff"])
            
            with tab_bos1:
                st.write("Reset Data Shift:")
                db_gerobak_bos = load_json(FILE_DB_GEROBAK)
                for g_id, g_nama in DATA_GEROBAK.items():
                    info_g = db_gerobak_bos.get(g_nama)
                    status_text = f"✅ KOSONG" if not info_g else f"⚠️ AKTIF ({info_g['pic']})"
                    col_a, col_b = st.columns([3, 1])
                    col_a.text(f"{g_nama} -> {status_text}")
                    if info_g and col_b.button(f"🗑️ HAPUS", key=f"del_{g_id}"):
                        del db_gerobak_bos[g_nama]
                        save_json(FILE_DB_GEROBAK, db_gerobak_bos)
                        st.rerun()
            
            with tab_bos2:
                data_staff_bos = load_json(FILE_DB_STAFF)
                if data_staff_bos:
                    df_staff = pd.DataFrame(list(data_staff_bos.items()), columns=['PIN', 'NAMA'])
                    st.dataframe(df_staff, use_container_width=True)
                    st.write("Hapus Akun:")
                    list_pilihan = [f"{v} - {k}" for k,v in data_staff_bos.items()]
                    pilih_hapus = st.selectbox("Pilih Staff:", list_pilihan)
                    if st.button("Hapus Staff Terpilih"):
                        pin_target = pilih_hapus.split(" - ")[-1]
                        if hapus_staff(pin_target): st.rerun()
            st.divider()

        # OPERASIONAL
        st.write(f"📍 **Operasional Harian**")
        pilihan_gerobak = st.selectbox("Pilih Lokasi:", list(DATA_GEROBAK.values()))
        
        db_gerobak = load_json(FILE_DB_GEROBAK) 
        data_shift = db_gerobak.get(pilihan_gerobak)
        
        if data_shift:
            st.info(f"⚠️ SHIFT AKTIF: {data_shift['pic']} (Sejak {data_shift['jam_masuk']})")
        else:
            st.success("✅ GEROBAK KOSONG (Siap Buka)")

        tab1, tab2 = st.tabs(["☀️ OPENING", "🌙 CLOSING"])

        with tab1:
            if data_shift and data_shift['pin_pic'] != pin_aktif:
                st.error(f"⛔ Gerobak dipakai {data_shift['pic']}.")
            else:
                with st.form("form_opening"):
                    st.write("📦 **Stok Awal:**")
                    stok_input = {}
                    col1, col2 = st.columns(2)
                    i = 0
                    for menu in MENU_HARGA:
                        val = data_shift['stok'].get(menu, 0) if data_shift else 0
                        with (col1 if i % 2 == 0 else col2):
                            stok_input[menu] = st.number_input(f"{menu}", min_value=0, value=val)
                        i += 1
                    
                    if st.form_submit_button("SIMPAN OPENING"):
                        # PAKAI JAM WIB
                        jam_skrg = get_waktu_wib().strftime("%H:%M")
                        
                        data_baru = {
                            "tanggal": get_waktu_wib().strftime("%Y-%m-%d"),
                            "jam_masuk": data_shift['jam_masuk'] if data_shift else jam_skrg,
                            "pic": nama_aktif, "pin_pic": pin_aktif, "stok": stok_input
                        }
                        db_gerobak[pilihan_gerobak] = data_baru
                        save_json(FILE_DB_GEROBAK, db_gerobak)
                        
                        list_stok = [f"{k}: {v}" for k,v in stok_input.items()]
                        msg = f"☀️ *OPENING WEB*\n📍 {pilihan_gerobak}\n👤 {nama_aktif}\n🕒 {data_baru['jam_masuk']}\n\n📦 {', '.join(list_stok)}"
                        kirim_telegram(msg)
                        st.success("Tersimpan!"); st.rerun()

        with tab2:
            if not data_shift:
                st.info("Belum ada data Opening. Silakan Opening dulu.")
            elif data_shift['pin_pic'] != pin_aktif:
                st.error("⛔ Bukan shift Anda!")
            else:
                with st.form("form_closing"):
                    st.write("📊 **Hitung Jualan:**")
                    stok_awal = data_shift['stok'] 
                    omzet = 0
                    txt_jual = []
                    list_excel_rows = []
                    
                    # PAKAI JAM WIB
                    jam_pulang = get_waktu_wib().strftime("%H:%M")
                    tanggal_ini = get_waktu_wib().strftime("%Y-%m-%d")

                    for menu, harga in MENU_HARGA.items():
                        awal = stok_awal.get(menu, 0) 
                        sisa = st.number_input(f"Sisa {menu} (Awal: {awal})", min_value=0, max_value=awal)
                        laku = awal - sisa
                        omzet += (laku * harga)
                        txt_jual.append(f"{menu}: {laku}")
                        
                        list_excel_rows.append({
                            "TANGGAL": tanggal_ini,
                            "JAM_MASUK": data_shift['jam_masuk'],
                            "JAM_PULANG": jam_pulang,
                            "GEROBAK": pilihan_gerobak,
                            "STAFF": nama_aktif,
                            "ITEM": menu,
                            "AWAL": awal,
                            "SISA": sisa,
                            "TERJUAL": laku,
                            "OMZET_ITEM": (laku * harga)
                        })

                    st.write("💰 **Keuangan:**")
                    st.info(f"Target Sistem: **{format_rupiah(omzet)}**")
                    tunai = st.number_input("Setor Tunai", step=1000)
                    qris = st.number_input("Setor QRIS", step=1000)
                    catatan = st.text_area("Catatan")

                    if st.form_submit_button("KIRIM LAPORAN"):
                        selisih = (tunai + qris) - omzet
                        status = "✅ PAS" if selisih == 0 else (f"⚠️ MINUS {selisih}" if selisih < 0 else f"ℹ️ LEBIH {selisih}")
                        
                        msg = (f"🌙 *CLOSING*\n📍 {pilihan_gerobak}\n👤 {nama_aktif}\n"
                               f"🕒 {data_shift['jam_masuk']} - {jam_pulang}\n\n"
                               f"📊 Jualan: {', '.join(txt_jual)}\n"
                               f"💰 Omzet: {format_rupiah(omzet)}\n"
                               f"💵 Tunai: {format_rupiah(tunai)}\n💳 QRIS: {format_rupiah(qris)}\n"
                               f"Status: {status}\n📝 {catatan}")
                        kirim_telegram(msg)
                        
                        # Baris Keuangan
                        list_excel_rows.append({
                            "TANGGAL": tanggal_ini, "JAM_MASUK": data_shift['jam_masuk'], "JAM_PULANG": jam_pulang,
                            "GEROBAK": pilihan_gerobak, "STAFF": nama_aktif,
                            "ITEM": "TOTAL SETORAN", "AWAL": 0, "SISA": 0, "TERJUAL": 0, 
                            "OMZET_ITEM": (tunai + qris)
                        })
                        
                        simpan_ke_excel_database(list_excel_rows)
                        kirim_file_excel_telegram()
                        
                        del db_gerobak[pilihan_gerobak]
                        save_json(FILE_DB_GEROBAK, db_gerobak)
                        
                        st.success("Laporan & Excel Terkirim!")
                        st.balloons()
                        st.rerun()
    else:
        st.info("👈 Silakan Login atau Daftar di menu sebelah kiri.")

if __name__ == "__main__":
    main()
                    
