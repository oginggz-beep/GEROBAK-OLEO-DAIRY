import streamlit as st
import json
import os
import requests
import pandas as pd
from datetime import datetime
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
import openpyxl

# ================= KONFIGURASI UTAMA (EDIT DISINI) =================
# 👇 Masukkan Token Bot Telegram Anda di dalam tanda kutip:
TOKEN_BOT = "8285539149:AAHQd-_W9aaBGSz3AUPg0oCuxabZUL6yJo4" 

# 👇 ID Telegram & PIN Owner
ID_OWNER  = "8505488457"  
PIN_OWNER = "8888"        

# ================= DATABASE & FILE =================
FILE_DB_GEROBAK = "database_gerobak.json" # Shift Aktif
FILE_DB_STAFF   = "database_staff.json"   # Data Staff
FILE_DB_MENU    = "database_menu.json"    # Data Menu
FILE_DB_LOKASI  = "database_lokasi.json"  # Data Lokasi (BARU)
FILE_EXCEL_REP  = "LAPORAN_HARIAN_LENGKAP.xlsx"

# Data Master Default (Dipakai jika file belum ada)
MENU_DEFAULT = {
    "Strawberry Milk": 10000, "Coklat Milk": 12000,
    "Kopi Susu Aren": 15000, "Matcha Latte": 15000
}
LOKASI_DEFAULT = {
    "1": "Gerobak Alun-Alun", 
    "2": "Gerobak Stasiun", 
    "3": "Gerobak Pasar"
}

# ================= FUNGSI BANTUAN =================
def kirim_telegram(pesan):
    if TOKEN_BOT == "PASTE_TOKEN_BOT_ANDA_DISINI": return
    try:
        url = f"https://api.telegram.org/bot{TOKEN_BOT}/sendMessage"
        requests.post(url, data={"chat_id": ID_OWNER, "text": pesan})
    except: pass

def kirim_file_excel_telegram():
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

# --- FUNGSI LOKASI (BARU) ---
def get_lokasi_aktif():
    data = load_json(FILE_DB_LOKASI)
    if not data:
        save_json(FILE_DB_LOKASI, LOKASI_DEFAULT)
        return LOKASI_DEFAULT
    return data

def simpan_lokasi_baru(id_lokasi, nama_lokasi):
    data = get_lokasi_aktif()
    data[id_lokasi] = nama_lokasi
    save_json(FILE_DB_LOKASI, data)

def hapus_lokasi(id_lokasi):
    data = get_lokasi_aktif()
    if id_lokasi in data:
        del data[id_lokasi]
        save_json(FILE_DB_LOKASI, data)

# --- FUNGSI MENU ---
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
        del data[pin]
        save_json(FILE_DB_STAFF, data)
        return True
    return False

# ================= FUNGSI EXCEL PRO =================
def rapikan_excel(filename):
    try:
        wb = openpyxl.load_workbook(filename)
        ws = wb.active
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="203764", end_color="203764", fill_type="solid")
        center = Alignment(horizontal="center", vertical="center")
        thin_border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
        
        for cell in ws[1]:
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = center
            cell.border = thin_border

        for col in ws.columns:
            max_len = 0
            col_letter = col[0].column_letter
            for cell in col:
                cell.border = thin_border
                try:
                    if len(str(cell.value)) > max_len: max_len = len(str(cell.value))
                except: pass
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
        df_final.to_excel(FILE_EXCEL_REP, index=False)
        rapikan_excel(FILE_EXCEL_REP)
        return True
    except Exception as e:
        st.error(f"❌ Gagal Excel: {e}")
        return False

# ================= TAMPILAN APLIKASI =================
def main():
    st.set_page_config(page_title="Sistem Gerobak Pro", page_icon="🏪", layout="centered")
    
    if TOKEN_BOT == "PASTE_TOKEN_BOT_ANDA_DISINI":
        st.error("⚠️ TOKEN BELUM DIISI! Buka file app.py dan isi token dulu.")
        st.stop()

    LOKASI_SEKARANG = get_lokasi_aktif()
    MENU_SEKARANG = get_menu_aktif()
    
    st.title("🏪 Kasir & Absensi Gerobak")
    st.caption(f"📅 {datetime.now().strftime('%d-%m-%Y')}")

    if 'user_nama' not in st.session_state: st.session_state['user_nama'] = None
    if 'user_pin' not in st.session_state: st.session_state['user_pin'] = None

    # --- SIDEBAR ---
    with st.sidebar:
        st.header("🔐 Akses")
        if st.session_state['user_nama'] is None:
            mode = st.radio("Menu:", ["Login", "Daftar Staff"])
            if mode == "Login":
                pin = st.text_input("PIN", type="password", max_chars=6)
                if st.button("Masuk"):
                    data_staff = load_json(FILE_DB_STAFF)
                    if pin == PIN_OWNER:
                        st.session_state['user_nama'] = "OWNER"; st.session_state['user_pin'] = PIN_OWNER; st.rerun()
                    elif pin in data_staff:
                        st.session_state['user_nama'] = data_staff[pin]; st.session_state['user_pin'] = pin; st.rerun()
                    else: st.error("PIN Salah")
            elif mode == "Daftar Staff":
                nm = st.text_input("Nama"); pn = st.text_input("PIN Baru", max_chars=6)
                if st.button("Simpan"): 
                    if simpan_staff_baru(nm, pn): st.success("OK!"); kirim_telegram(f"🆕 STAFF: {nm} ({pn})")
                    else: st.error("PIN Terpakai")
        else:
            st.success(f"👤 {st.session_state['user_nama']}")
            if st.button("Keluar"): st.session_state['user_nama']=None; st.rerun()

    # --- KONTEN UTAMA ---
    if st.session_state['user_nama']:
        user = st.session_state['user_nama']
        pin  = st.session_state['user_pin']

        # === FITUR OWNER ===
        if user == "OWNER":
            st.error("🔧 **MENU ADMIN BOS**")
            # Menambah Tab Lokasi
            t1, t2, t3, t4 = st.tabs(["🛒 Status", "👥 Staff", "📋 Menu", "📍 Kelola Lokasi"])
            
            with t1: # Status Shift
                st.write("Pantau Shift Aktif:")
                db_gerobak = load_json(FILE_DB_GEROBAK)
                # Menggunakan LOKASI_SEKARANG agar nama update
                for id_lok, nama_lok in LOKASI_SEKARANG.items():
                    info = db_gerobak.get(nama_lok) # Key DB Gerobak pakai Nama
                    if info:
                        st.write(f"🔴 **{nama_lok}**: {info['pic']}")
                        if st.button(f"Reset {nama_lok}", key=id_lok):
                            del db_gerobak[nama_lok]; save_json(FILE_DB_GEROBAK, db_gerobak); st.rerun()
                    else: st.write(f"🟢 **{nama_lok}**: Kosong")
            
            with t2: # Staff
                ds = load_json(FILE_DB_STAFF)
                st.dataframe(pd.DataFrame(list(ds.items()), columns=['PIN','NAMA']), hide_index=True)
                pilih = st.selectbox("Hapus Staff:", [f"{v} ({k})" for k,v in ds.items()])
                if st.button("Hapus Staff"): hapus_staff(pilih.split('(')[1][:-1]); st.rerun()

            with t3: # Menu
                st.dataframe(pd.DataFrame(list(MENU_SEKARANG.items()), columns=['Menu','Harga']), hide_index=True)
                c1,c2 = st.columns(2)
                nm = c1.text_input("Nama Menu"); hg = c2.number_input("Harga", step=500)
                if st.button("Simpan Menu"): simpan_menu_baru(nm, hg); st.rerun()
                if st.button("Hapus Menu"): hapus_menu(st.selectbox("Hapus:", list(MENU_SEKARANG.keys()))); st.rerun()

            with t4: # Lokasi (BARU)
                st.subheader("Daftar Gerobak / Cabang")
                df_lok = pd.DataFrame(list(LOKASI_SEKARANG.items()), columns=['ID', 'Nama Lokasi'])
                st.dataframe(df_lok, hide_index=True, use_container_width=True)
                
                st.write("---")
                st.write("**Tambah / Ubah Lokasi**")
                col_l1, col_l2 = st.columns([1, 3])
                with col_l1: 
                    # Cari ID baru otomatis (max + 1)
                    ids = [int(k) for k in LOKASI_SEKARANG.keys()]
                    next_id = str(max(ids) + 1) if ids else "1"
                    input_id = st.text_input("ID", value=next_id)
                with col_l2: input_nama_lok = st.text_input("Nama Gerobak")
                
                if st.button("💾 Simpan Lokasi"):
                    if input_id and input_nama_lok:
                        simpan_lokasi_baru(input_id, input_nama_lok)
                        st.success(f"Lokasi {input_nama_lok} tersimpan!")
                        st.rerun()
                
                st.write("---")
                pilih_hapus_lok = st.selectbox("Hapus Lokasi:", [f"{k} - {v}" for k,v in LOKASI_SEKARANG.items()])
                if st.button("🗑️ Hapus Lokasi"):
                    id_target = pilih_hapus_lok.split(" - ")[0]
                    hapus_lokasi(id_target)
                    st.warning("Lokasi dihapus.")
                    st.rerun()
            st.divider()

        # === OPERASIONAL STAFF ===
        st.subheader("📍 Pilih Lokasi Kerja")
        # Dropdown mengambil dari database Lokasi
        pilihan_gerobak = st.selectbox("Lokasi:", list(LOKASI_SEKARANG.values()))
        
        db_gerobak = load_json(FILE_DB_GEROBAK)
        shift = db_gerobak.get(pilihan_gerobak)

        if shift: st.info(f"⚡ Shift Aktif: {shift['pic']} ({shift['jam_masuk']})")
        else: st.success("✅ Siap Buka Shift")

        t_op, t_cl = st.tabs(["☀️ BUKA TOKO", "🌙 TUTUP TOKO"])

        with t_op:
            if shift and shift['pin_pic'] != pin: st.error("⛔ Shift orang lain!")
            else:
                with st.form("op"):
                    st.write("📦 Stok Awal:")
                    stok = {}
                    cols = st.columns(2)
                    for i, m in enumerate(MENU_SEKARANG):
                        val = shift['stok'].get(m, 0) if shift else 0
                        with cols[i%2]: stok[m] = st.number_input(f"{m}", value=int(val), min_value=0)
                    if st.form_submit_button("SIMPAN"):
                        d = {"tanggal": datetime.now().strftime("%Y-%m-%d"), "jam_masuk": shift['jam_masuk'] if shift else datetime.now().strftime("%H:%M"), "pic": user, "pin_pic": pin, "stok": stok}
                        db_gerobak[pilihan_gerobak] = d; save_json(FILE_DB_GEROBAK, db_gerobak)
                        kirim_telegram(f"☀️ OPENING {pilihan_gerobak}\n👤 {user}\n📦 Stok Terisi"); st.rerun()

        with t_cl:
            if not shift: st.info("Belum Opening.")
            elif shift['pin_pic'] != pin: st.error("⛔ Bukan Shift Anda.")
            else:
                with st.form("cl"):
                    st.write("📊 Sisa Stok:")
                    omzet=0; rows=[]
                    for m,pr in MENU_SEKARANG.items():
                        aw = int(shift['stok'].get(m,0))
                        sisa = st.number_input(f"Sisa {m} (Awal: {aw})", max_value=aw, min_value=0)
                        laku = aw-sisa; duit=laku*pr; omzet+=duit
                        rows.append({"TANGGAL":datetime.now().strftime("%Y-%m-%d"), "GEROBAK":pilihan_gerobak, "STAFF":user, "ITEM":m, "AWAL":aw, "SISA":sisa, "TERJUAL":laku, "OMZET_ITEM":duit, "TIPE":"JUAL"})
                    
                    st.write(f"💰 Total: {format_rupiah(omzet)}")
                    tn = st.number_input("Tunai", step=500); qr = st.number_input("QRIS", step=500); nt = st.text_area("Catatan")
                    if st.form_submit_button("KIRIM LAPORAN"):
                        rows.append({"TANGGAL":datetime.now().strftime("%Y-%m-%d"), "GEROBAK":pilihan_gerobak, "STAFF":user, "ITEM":"SETORAN", "AWAL":0,"SISA":0,"TERJUAL":0, "OMZET_ITEM":tn+qr, "TIPE":"SETORAN"})
                        simpan_ke_excel_database(rows); kirim_file_excel_telegram()
                        kirim_telegram(f"🌙 CLOSING {pilihan_gerobak}\n👤 {user}\n💰 Target: {format_rupiah(omzet)}\n💵 Setor: {format_rupiah(tn+qr)}\n📝 {nt}")
                        del db_gerobak[pilihan_gerobak]; save_json(FILE_DB_GEROBAK, db_gerobak); st.balloons(); st.rerun()

    else: st.info("👈 Login dulu ya.")

if __name__ == "__main__":
    main()
    
