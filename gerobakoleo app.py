import streamlit as st
import json
import os
import requests
import pandas as pd
from datetime import datetime
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
import openpyxl

# ================= KONFIGURASI (ISI TOKEN DISINI) =================
TOKEN_BOT = "PASTE_TOKEN_BOT_ANDA_DISINI"  # 👈 GANTI INI DENGAN TOKEN ANDA
ID_OWNER  = "8505488457"
PIN_OWNER = "8888"

# ================= DATABASE & FILE =================
FILE_DB_GEROBAK = "database_gerobak.json"
FILE_DB_STAFF   = "database_staff.json"
FILE_DB_MENU    = "database_menu.json"
FILE_DB_LOKASI  = "database_lokasi.json"
FILE_EXCEL_REP  = "LAPORAN_LENGKAP_V2.xlsx" # Nama file baru biar fresh

# Default Data
MENU_DEFAULT = {"Strawberry Milk": 10000, "Coklat Milk": 12000, "Kopi Aren": 15000}
LOKASI_DEFAULT = {"1": "Gerobak Alun-Alun", "2": "Gerobak Stasiun"}

# ================= FUNGSI BANTUAN =================
def kirim_telegram(pesan):
    if TOKEN_BOT == "PASTE_TOKEN_BOT_ANDA_DISINI": return
    try:
        requests.post(f"https://api.telegram.org/bot{TOKEN_BOT}/sendMessage", data={"chat_id": ID_OWNER, "text": pesan})
    except: pass

def kirim_file_excel_telegram():
    if TOKEN_BOT == "PASTE_TOKEN_BOT_ANDA_DISINI": return
    if os.path.exists(FILE_EXCEL_REP):
        try:
            with open(FILE_EXCEL_REP, 'rb') as f:
                requests.post(f"https://api.telegram.org/bot{TOKEN_BOT}/sendDocument", 
                              data={'chat_id': ID_OWNER, 'caption': '📊 Laporan Detail Lengkap'}, files={'document': f})
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

# --- FUNGSI MANAJEMEN DATA ---
def get_data(filename, default):
    data = load_json(filename)
    if not data:
        save_json(filename, default)
        return default
    return data

def simpan_staff(nama, pin):
    d = load_json(FILE_DB_STAFF)
    if pin in d: return False
    d[pin] = nama; save_json(FILE_DB_STAFF, d); return True

def hapus_staff(pin):
    d = load_json(FILE_DB_STAFF)
    if pin in d: del d[pin]; save_json(FILE_DB_STAFF, d); return True
    return False

# ================= EXCEL SUPER LENGKAP =================
def rapikan_excel(filename):
    try:
        wb = openpyxl.load_workbook(filename)
        ws = wb.active
        
        # Style Header
        header_style = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid") # Biru Profesional
        font_style = Font(bold=True, color="FFFFFF")
        border_style = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
        
        for cell in ws[1]:
            cell.fill = header_style
            cell.font = font_style
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = border_style

        # Auto Width & Format
        for col in ws.columns:
            max_len = 0
            col_letter = col[0].column_letter
            for cell in col:
                cell.border = border_style
                try:
                    if len(str(cell.value)) > max_len: max_len = len(str(cell.value))
                except: pass
                
                # Format Rupiah
                header = ws[f"{col_letter}1"].value
                if header and any(x in str(header).upper() for x in ['HARGA', 'OMZET', 'TUNAI', 'QRIS', 'TOTAL']):
                    cell.number_format = '#,##0 "Rp"'
            
            ws.column_dimensions[col_letter].width = (max_len + 4)
        wb.save(filename)
    except: pass

def simpan_laporan_lengkap(list_data):
    """
    Menyimpan data dengan kolom yang SANGAT LENGKAP:
    Tanggal | Jam Lapor | Lokasi | Staff | Shift Masuk | Shift Pulang | 
    Nama Item | Harga Satuan | Stok Awal | Sisa | Terjual | Total Omzet | 
    Setor Tunai | Setor QRIS | Catatan
    """
    try:
        df_new = pd.DataFrame(list_data)
        
        # Urutan Kolom Biar Rapi
        kolom_urut = [
            "TANGGAL", "JAM_LAPORAN", "LOKASI", "STAFF", 
            "SHIFT_MASUK", "SHIFT_PULANG", "ITEM", "HARGA_SATUAN",
            "STOK_AWAL", "SISA_STOK", "TERJUAL", "TOTAL_OMZET",
            "SETOR_TUNAI", "SETOR_QRIS", "CATATAN", "TIPE_BARIS"
        ]
        
        # Reorder kolom jika ada, isi N/A jika kosong
        for col in kolom_urut:
            if col not in df_new.columns:
                df_new[col] = "-"
        
        df_new = df_new[kolom_urut]

        if os.path.exists(FILE_EXCEL_REP):
            df_old = pd.read_excel(FILE_EXCEL_REP)
            df_final = pd.concat([df_old, df_new], ignore_index=True)
        else:
            df_final = df_new
            
        df_final.to_excel(FILE_EXCEL_REP, index=False)
        rapikan_excel(FILE_EXCEL_REP)
        return True
    except Exception as e:
        st.error(f"Gagal Simpan Excel: {e}"); return False

# ================= MAIN APP =================
def main():
    st.set_page_config(page_title="POS Lengkap", page_icon="📊")
    
    if TOKEN_BOT == "PASTE_TOKEN_BOT_ANDA_DISINI":
        st.error("⚠️ TOKEN KOSONG! Edit file app.py baris ke-11."); st.stop()

    # Load Data
    MENU = get_data(FILE_DB_MENU, MENU_DEFAULT)
    LOKASI = get_data(FILE_DB_LOKASI, LOKASI_DEFAULT)
    STAFF = load_json(FILE_DB_STAFF)
    GEROBAK = load_json(FILE_DB_GEROBAK)

    st.title("📊 Sistem Kasir & Laporan Lengkap")
    tgl_ini = datetime.now().strftime('%d-%m-%Y')
    st.caption(f"Hari ini: {tgl_ini}")

    if 'user' not in st.session_state: st.session_state['user'] = None
    if 'pin' not in st.session_state: st.session_state['pin'] = None

    # --- SIDEBAR ---
    with st.sidebar:
        st.header("🔐 Login")
        if not st.session_state['user']:
            menu = st.radio("Opsi:", ["Login", "Daftar Staff"])
            if menu == "Login":
                p = st.text_input("PIN", type="password", max_chars=6)
                if st.button("Masuk"):
                    if p == PIN_OWNER:
                        st.session_state['user']="OWNER"; st.session_state['pin']=p; st.rerun()
                    elif p in STAFF:
                        st.session_state['user']=STAFF[p]; st.session_state['pin']=p; st.rerun()
                    else: st.error("PIN Salah")
            else:
                n = st.text_input("Nama"); p = st.text_input("PIN Baru", max_chars=6)
                if st.button("Daftar"):
                    if simpan_staff(n, p): st.success("OK"); kirim_telegram(f"🆕 STAFF: {n}"); st.rerun()
                    else: st.error("Gagal")
        else:
            st.info(f"👤 {st.session_state['user']}")
            if st.button("Keluar"): st.session_state['user']=None; st.rerun()

    # --- KONTEN ---
    if st.session_state['user']:
        user = st.session_state['user']
        pin = st.session_state['pin']

        # OWNER AREA
        if user == "OWNER":
            st.warning("🔧 **ADMIN PANEL**")
            t1, t2, t3 = st.tabs(["Lokasi & Status", "Menu Harga", "Staff"])
            
            with t1:
                st.write("**Status Gerobak:**")
                for id_lok, nm_lok in LOKASI.items():
                    info = GEROBAK.get(nm_lok)
                    status = f"🔴 AKTIF ({info['pic']})" if info else "🟢 KOSONG"
                    c1, c2 = st.columns([3,1])
                    c1.write(f"{nm_lok}: {status}")
                    if info and c2.button("Reset", key=id_lok):
                        del GEROBAK[nm_lok]; save_json(FILE_DB_GEROBAK, GEROBAK); st.rerun()
                
                st.write("---")
                st.write("**Tambah Lokasi:**")
                c_id, c_nm = st.columns([1,3])
                new_id = c_id.text_input("ID Lokasi")
                new_nm = c_nm.text_input("Nama Gerobak")
                if st.button("Simpan Lokasi"):
                    d_lok = get_data(FILE_DB_LOKASI, LOKASI_DEFAULT)
                    d_lok[new_id] = new_nm; save_json(FILE_DB_LOKASI, d_lok); st.rerun()

            with t2:
                st.dataframe(pd.DataFrame(list(MENU.items()), columns=['Item','Harga']), hide_index=True)
                c1, c2 = st.columns(2)
                nm_m = c1.text_input("Menu Baru/Edit")
                hr_m = c2.number_input("Harga", step=500)
                if st.button("Simpan Menu"):
                    MENU[nm_m] = int(hr_m); save_json(FILE_DB_MENU, MENU); st.rerun()
                if st.button("Hapus Menu"):
                    hps = st.selectbox("Pilih", list(MENU.keys()))
                    if st.button("Hapus"): del MENU[hps]; save_json(FILE_DB_MENU, MENU); st.rerun()
            
            with t3:
                st.dataframe(pd.DataFrame(list(STAFF.items()), columns=['PIN','NAMA']))

        # OPERASIONAL AREA
        st.subheader("📍 Operasional Harian")
        lokasi_pilih = st.selectbox("Pilih Lokasi Kerja:", list(LOKASI.values()))
        shift_data = GEROBAK.get(lokasi_pilih)

        if shift_data: st.info(f"⚡ Shift Berjalan: {shift_data['pic']} (Masuk: {shift_data['jam_masuk']})")
        else: st.success("✅ Siap Buka Toko")

        tab_buka, tab_tutup = st.tabs(["☀️ BUKA SHIFT", "🌙 TUTUP SHIFT & LAPORAN"])

        with tab_buka:
            if shift_data and shift_data['pin_pic'] != pin:
                st.error("⛔ Shift ini milik orang lain.")
            else:
                with st.form("buka"):
                    st.write("📦 **Stok Awal Barang:**")
                    stok_input = {}
                    cols = st.columns(2)
                    for i, m in enumerate(MENU):
                        val = shift_data['stok'].get(m, 0) if shift_data else 0
                        with cols[i%2]: stok_input[m] = st.number_input(f"{m}", value=int(val), min_value=0)
                    
                    if st.form_submit_button("SIMPAN STOK AWAL"):
                        jam_skrg = datetime.now().strftime("%H:%M")
                        # Pertahankan jam masuk jika edit, buat baru jika belum ada
                        jam_masuk = shift_data['jam_masuk'] if shift_data else jam_skrg
                        
                        data_baru = {
                            "tanggal": datetime.now().strftime("%d-%m-%Y"),
                            "jam_masuk": jam_masuk,
                            "pic": user, "pin_pic": pin, "stok": stok_input
                        }
                        GEROBAK[lokasi_pilih] = data_baru
                        save_json(FILE_DB_GEROBAK, GEROBAK)
                        kirim_telegram(f"☀️ OPENING {lokasi_pilih}\n👤 {user}\n🕒 {jam_masuk}")
                        st.success("Data Tersimpan!"); st.rerun()

        with tab_tutup:
            if not shift_data: st.info("Harap isi Stok Awal dulu.")
            elif shift_data['pin_pic'] != pin: st.error("Bukan shift Anda.")
            else:
                with st.form("tutup"):
                    st.write("📊 **Hitung Penjualan:**")
                    
                    laporan_list = []
                    total_omzet = 0
                    tgl_skrg = datetime.now().strftime("%d-%m-%Y")
                    jam_plg = datetime.now().strftime("%H:%M")
                    
                    # 1. LOOP BARANG (Row Detail)
                    st.write("---")
                    for item, harga in MENU.items():
                        stok_awal = int(shift_data['stok'].get(item, 0))
                        
                        col_a, col_b = st.columns([2,1])
                        sisa = col_a.number_input(f"Sisa {item} (Awal: {stok_awal})", min_value=0, max_value=stok_awal)
                        
                        terjual = stok_awal - sisa
                        omzet_item = terjual * harga
                        total_omzet += omzet_item
                        
                        col_b.write(f"Jual: {terjual} x {format_rupiah(harga)}")

                        # Simpan Data Detail ke List
                        laporan_list.append({
                            "TANGGAL": tgl_skrg,
                            "JAM_LAPORAN": jam_plg,
                            "LOKASI": lokasi_pilih,
                            "STAFF": user,
                            "SHIFT_MASUK": shift_data['jam_masuk'],
                            "SHIFT_PULANG": jam_plg,
                            "ITEM": item,
                            "HARGA_SATUAN": harga,
                            "STOK_AWAL": stok_awal,
                            "SISA_STOK": sisa,
                            "TERJUAL": terjual,
                            "TOTAL_OMZET": omzet_item,
                            "SETOR_TUNAI": "-", "SETOR_QRIS": "-", "CATATAN": "-", # Kosongkan di baris item
                            "TIPE_BARIS": "ITEM"
                        })
                    
                    st.write("---")
                    st.markdown(f"### 💰 Total Penjualan: {format_rupiah(total_omzet)}")
                    
                    # 2. INPUT KEUANGAN (Row Summary)
                    c1, c2 = st.columns(2)
                    tunai = c1.number_input("Fisik Uang Tunai", step=500)
                    qris  = c2.number_input("Total Transfer/QRIS", step=500)
                    catatan = st.text_area("Catatan Shift")
                    
                    if st.form_submit_button("KIRIM LAPORAN LENGKAP"):
                        selisih = (tunai + qris) - total_omzet
                        status_duit = "PAS ✅" if selisih == 0 else (f"MINUS {selisih} ⚠️" if selisih < 0 else f"LEBIH {selisih} ℹ️")
                        
                        # Tambah Baris Total ke Excel
                        laporan_list.append({
                            "TANGGAL": tgl_skrg, "JAM_LAPORAN": jam_plg,
                            "LOKASI": lokasi_pilih, "STAFF": user,
                            "SHIFT_MASUK": shift_data['jam_masuk'], "SHIFT_PULANG": jam_plg,
                            "ITEM": "TOTAL SETORAN", "HARGA_SATUAN": "-", 
                            "STOK_AWAL": "-", "SISA_STOK": "-", "TERJUAL": "-",
                            "TOTAL_OMZET": total_omzet,
                            "SETOR_TUNAI": tunai,
                            "SETOR_QRIS": qris,
                            "CATATAN": f"{status_duit} | {catatan}",
                            "TIPE_BARIS": "SUMMARY"
                        })
                        
                        # Simpan ke Excel & Kirim
                        if simpan_laporan_lengkap(laporan_list):
                            kirim_file_excel_telegram()
                            
                            # Kirim Chat Singkat
                            msg = (f"🌙 *CLOSING LENGKAP*\n📍 {lokasi_pilih}\n👤 {user}\n"
                                   f"🕒 {shift_data['jam_masuk']} - {jam_plg}\n"
                                   f"💰 Omzet: {format_rupiah(total_omzet)}\n"
                                   f"💵 Tunai: {format_rupiah(tunai)}\n"
                                   f"💳 QRIS: {format_rupiah(qris)}\n"
                                   f"📝 Status: {status_duit}")
                            kirim_telegram(msg)
                            
                            # Bersihkan Shift
                            del GEROBAK[lokasi_pilih]; save_json(FILE_DB_GEROBAK, GEROBAK)
                            st.success("Laporan Lengkap Terkirim!"); st.balloons(); st.rerun()

    else:
        st.info("👈 Silakan Login dulu di menu samping.")

if __name__ == "__main__":
    main()
                        
