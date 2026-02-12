import streamlit as st
import json
import os
import requests
import pandas as pd
from datetime import datetime, timedelta
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
import openpyxl

# ================= KONFIGURASI UTAMA =================
TOKEN_BOT = "8285539149:AAHQd-_W9aaBGSz3AUPg0oCuxabZUL6yJo4" 
ID_OWNER  = "8505488457"  
PIN_OWNER = "8888"        

# ================= DATABASE & FILE =================
FILE_DB_GEROBAK = "database_gerobak.json" 
FILE_DB_STAFF   = "database_staff.json"   
FILE_DB_MENU    = "database_menu.json"    
FILE_DB_LOKASI  = "database_lokasi.json"  
FILE_EXCEL_REP  = "LAPORAN_HARIAN_LENGKAP.xlsx"

# Data Default
MENU_DEFAULT = {
    "Strawberry Milk": 10000, "Coklat Milk": 12000,
    "Kopi Susu Aren": 15000, "Matcha Latte": 15000
}
LOKASI_DEFAULT = {
    "1": "Gerobak Alun-Alun", 
    "2": "Gerobak Stasiun", 
    "3": "Gerobak Pasar"
}

# ================= FUNGSI BANTUAN (DIPERBAIKI) =================
def get_wib_now():
    # Mengambil waktu server dan mengubah ke WIB (UTC+7)
    return datetime.utcnow() + timedelta(hours=7)

def format_rupiah(angka):
    return f"Rp {int(angka):,}".replace(",", ".")

def kirim_telegram(pesan):
    if "PASTE_TOKEN" in TOKEN_BOT: return
    try:
        url = f"https://api.telegram.org/bot{TOKEN_BOT}/sendMessage"
        # Timeout ditambahkan agar aplikasi tidak hang jika internet lambat
        requests.post(url, data={"chat_id": ID_OWNER, "text": pesan}, timeout=5)
    except: pass

def kirim_file_excel_telegram():
    if "PASTE_TOKEN" in TOKEN_BOT: return
    if os.path.exists(FILE_EXCEL_REP):
        try:
            url = f"https://api.telegram.org/bot{TOKEN_BOT}/sendDocument"
            with open(FILE_EXCEL_REP, 'rb') as f:
                requests.post(url, data={'chat_id': ID_OWNER, 'caption': '📊 Update Laporan Excel'}, files={'document': f}, timeout=10)
        except: pass

def load_json(filename):
    # Proteksi: Jika file tidak ada atau rusak (kosong), kembalikan dictionary kosong
    if os.path.exists(filename):
        try:
            with open(filename, 'r') as f: return json.load(f)
        except json.JSONDecodeError: return {} # Handle jika file corrupt
    return {}

def save_json(filename, data):
    with open(filename, 'w') as f: json.dump(data, f, indent=4)

# --- FUNGSI LOKASI ---
def get_lokasi_aktif():
    data = load_json(FILE_DB_LOKASI)
    if not data:
        save_json(FILE_DB_LOKASI, LOKASI_DEFAULT)
        return LOKASI_DEFAULT
    return data

def simpan_lokasi_baru(id_lokasi, nama_lokasi):
    data = get_lokasi_aktif()
    data[str(id_lokasi)] = nama_lokasi # Pastikan key string
    save_json(FILE_DB_LOKASI, data)

def hapus_lokasi(id_lokasi):
    data = get_lokasi_aktif()
    id_str = str(id_lokasi)
    if id_str in data:
        del data[id_str]
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
        # Styling Header
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
                    if cell.value and len(str(cell.value)) > max_len: 
                        max_len = len(str(cell.value))
                except: pass
                
                # Format Rupiah Otomatis
                header_text = ws[f"{col_letter}1"].value
                if header_text and any(x in str(header_text).upper() for x in ['OMZET', 'HARGA', 'TUNAI', 'QRIS', 'TOTAL']):
                    cell.number_format = '#,##0 "Rp"'
            
            ws.column_dimensions[col_letter].width = (max_len + 5)
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
    
    # Load Data Awal
    LOKASI_SEKARANG = get_lokasi_aktif()
    MENU_SEKARANG = get_menu_aktif()
    waktu_skrg = get_wib_now()
    
    st.title("🏪 Kasir & Absensi Gerobak")
    st.caption(f"📅 {waktu_skrg.strftime('%d-%m-%Y %H:%M')} WIB")

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
                    else: st.error("PIN Salah / Belum Terdaftar")
            elif mode == "Daftar Staff":
                nm = st.text_input("Nama"); pn = st.text_input("PIN Baru", max_chars=6)
                if st.button("Simpan"): 
                    if not nm or not pn: st.error("Isi nama dan PIN!")
                    elif simpan_staff_baru(nm, pn): 
                        st.success("OK!"); kirim_telegram(f"🆕 STAFF: {nm} ({pn})")
                    else: st.error("PIN Sudah Terpakai")
        else:
            st.success(f"👤 {st.session_state['user_nama']}")
            if st.button("Keluar"): st.session_state['user_nama']=None; st.rerun()

    # --- KONTEN UTAMA ---
    if st.session_state['user_nama']:
        user = st.session_state['user_nama']
        pin  = st.session_state['user_pin']

        # === FITUR OWNER ===
        if user == "OWNER":
            st.info("🔧 **DASHBOARD OWNER**")
            
            # -- Quick Stats (Baru) --
            db_gerobak = load_json(FILE_DB_GEROBAK)
            ds = load_json(FILE_DB_STAFF)
            col_m1, col_m2, col_m3 = st.columns(3)
            col_m1.metric("Gerobak Buka", f"{len(db_gerobak)} / {len(LOKASI_SEKARANG)}")
            col_m2.metric("Total Staff", f"{len(ds)}")
            col_m3.metric("Total Menu", f"{len(MENU_SEKARANG)}")
            
            t1, t2, t3, t4, t5 = st.tabs(["🛒 Status", "👥 Staff", "📋 Menu", "📍 Lokasi", "📥 Laporan"])
            
            with t1: # Status Shift
                st.write("Pantau Shift Aktif:")
                if not db_gerobak: st.caption("Belum ada gerobak yang buka.")
                
                for id_lok, nama_lok in LOKASI_SEKARANG.items():
                    info = db_gerobak.get(nama_lok)
                    with st.expander(f"{nama_lok}", expanded=bool(info)):
                        if info:
                            st.write(f"👤 **Staff:** {info['pic']}")
                            st.write(f"⏰ **Masuk:** {info['jam_masuk']}")
                            if st.button(f"Paksa Reset {nama_lok}", key=f"rst_{id_lok}"):
                                del db_gerobak[nama_lok]; save_json(FILE_DB_GEROBAK, db_gerobak); st.rerun()
                        else:
                            st.write("🔴 Tutup / Belum Buka")
            
            with t2: # Staff
                if ds:
                    st.dataframe(pd.DataFrame(list(ds.items()), columns=['PIN','NAMA']), hide_index=True, use_container_width=True)
                    pilih = st.selectbox("Hapus Staff:", [f"{v} ({k})" for k,v in ds.items()])
                    if st.button("Hapus Staff Terpilih"): hapus_staff(pilih.split('(')[1][:-1]); st.rerun()
                else: st.warning("Belum ada staff.")

            with t3: # Menu
                st.dataframe(pd.DataFrame(list(MENU_SEKARANG.items()), columns=['Menu','Harga']), hide_index=True, use_container_width=True)
                c1,c2 = st.columns(2)
                nm = c1.text_input("Nama Menu Baru"); hg = c2.number_input("Harga", step=500)
                if st.button("Simpan Menu"): 
                    if nm: simpan_menu_baru(nm, hg); st.rerun()
                
                if MENU_SEKARANG:
                    if st.button("Hapus Menu"): hapus_menu(st.selectbox("Hapus:", list(MENU_SEKARANG.keys()))); st.rerun()

            with t4: # Lokasi
                st.write("**Kelola Cabang / Gerobak**")
                if LOKASI_SEKARANG:
                    df_lok = pd.DataFrame(list(LOKASI_SEKARANG.items()), columns=['ID', 'Nama Lokasi'])
                    st.dataframe(df_lok, hide_index=True, use_container_width=True)
                
                c_l1, c_l2 = st.columns([1,3])
                ids = [int(k) for k in LOKASI_SEKARANG.keys()]
                next_id = str(max(ids) + 1) if ids else "1"
                
                new_id = c_l1.text_input("ID", value=next_id)
                new_nm = c_l2.text_input("Nama Lokasi")
                if st.button("Tambah Lokasi"):
                    if new_nm: simpan_lokasi_baru(new_id, new_nm); st.success("Tersimpan"); st.rerun()
                
                if LOKASI_SEKARANG:
                    del_lok = st.selectbox("Hapus Lokasi:", [f"{k} - {v}" for k,v in LOKASI_SEKARANG.items()])
                    if st.button("Hapus Lokasi Terpilih"):
                        hapus_lokasi(del_lok.split(' - ')[0]); st.rerun()

            with t5: # Laporan (Fitur Download)
                st.write("Download Data Laporan Excel:")
                if os.path.exists(FILE_EXCEL_REP):
                    with open(FILE_EXCEL_REP, "rb") as file:
                        st.download_button(
                            label="📥 Download Excel Laporan",
                            data=file,
                            file_name=FILE_EXCEL_REP,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                else:
                    st.warning("Belum ada data laporan yang tersimpan.")

            st.divider()

        # === OPERASIONAL STAFF ===
        # Proteksi jika belum ada lokasi
        if not LOKASI_SEKARANG:
            st.error("⚠️ Database Lokasi Kosong. Hubungi Owner untuk setup lokasi.")
            st.stop()

        st.subheader("📍 Pilih Lokasi Kerja")
        pilihan_gerobak = st.selectbox("Lokasi:", list(LOKASI_SEKARANG.values()))
        
        db_gerobak = load_json(FILE_DB_GEROBAK)
        shift = db_gerobak.get(pilihan_gerobak)

        if shift: 
            st.info(f"⚡ Shift Aktif: **{shift['pic']}** (Sejak: {shift['jam_masuk']})")
        else: 
            st.success("✅ Toko Tutup. Siap Buka Shift.")

        t_op, t_cl = st.tabs(["☀️ BUKA TOKO", "🌙 TUTUP TOKO"])

        with t_op:
            if shift and shift['pin_pic'] != pin: st.error(f"⛔ Shift sedang dijalankan oleh {shift['pic']}!")
            elif shift: st.warning("Anda sudah login di lokasi ini.")
            else:
                with st.form("op"):
                    st.write("📦 **Cek Stok Awal**")
                    stok = {}
                    cols = st.columns(2)
                    for i, m in enumerate(MENU_SEKARANG):
                        # Ambil sisa stok kemarin jika ada (opsional, saat ini default 0)
                        val = 0 
                        with cols[i%2]: stok[m] = st.number_input(f"{m}", value=int(val), min_value=0)
                    
                    if st.form_submit_button("🚀 BUKA SHIFT"):
                        jam_skrg = get_wib_now().strftime("%H:%M")
                        d = {
                            "tanggal": get_wib_now().strftime("%Y-%m-%d"), 
                            "jam_masuk": jam_skrg, 
                            "pic": user, 
                            "pin_pic": pin, 
                            "stok": stok
                        }
                        db_gerobak[pilihan_gerobak] = d
                        save_json(FILE_DB_GEROBAK, db_gerobak)
                        
                        with st.spinner("Mengirim notifikasi..."):
                            kirim_telegram(f"☀️ OPENING {pilihan_gerobak}\n👤 {user}\n⏰ {jam_skrg}\n📦 Stok Terisi")
                        st.success("Berhasil Buka Toko!"); st.rerun()

        with t_cl:
            if not shift: st.info("Belum Opening, tidak bisa Closing.")
            elif shift['pin_pic'] != pin: st.error("⛔ Anda tidak bisa menutup shift orang lain.")
            else:
                with st.form("cl"):
                    st.write("📊 **Hitung Penjualan**")
                    omzet=0; rows=[]
                    
                    # Logic perhitungan
                    for m,pr in MENU_SEKARANG.items():
                        aw = int(shift['stok'].get(m,0))
                        sisa = st.number_input(f"Sisa {m} (Awal: {aw})", max_value=aw, min_value=0)
                        laku = aw-sisa
                        duit = laku*pr
                        omzet += duit
                        rows.append({
                            "TANGGAL": get_wib_now().strftime("%Y-%m-%d"), 
                            "GEROBAK": pilihan_gerobak, 
                            "STAFF": user, 
                            "ITEM": m, 
                            "HARGA_SATUAN": pr,
                            "AWAL": aw, 
                            "SISA": sisa, 
                            "TERJUAL": laku, 
                            "OMZET_ITEM": duit, 
                            "TIPE": "JUAL"
                        })
                    
                    st.markdown(f"### 💰 Total Omzet: :green[{format_rupiah(omzet)}]")
                    
                    c1, c2 = st.columns(2)
                    tn = c1.number_input("Uang Tunai Diterima", step=500)
                    qr = c2.number_input("Transaksi QRIS", step=500)
                    nt = st.text_area("Catatan Harian (Pengeluaran/Insiden)")
                    
                    selisih = (tn + qr) - omzet
                    if selisih != 0:
                        st.warning(f"⚠️ Ada selisih uang: {format_rupiah(selisih)} (Cek ulang inputan)")

                    if st.form_submit_button("🔒 TUTUP SHIFT & KIRIM LAPORAN"):
                        # Tambah baris setoran
                        rows.append({
                            "TANGGAL": get_wib_now().strftime("%Y-%m-%d"), 
                            "GEROBAK": pilihan_gerobak, 
                            "STAFF": user, 
                            "ITEM": "SETORAN", 
                            "HARGA_SATUAN": 0, "AWAL":0,"SISA":0,"TERJUAL":0, 
                            "OMZET_ITEM": tn+qr, 
                            "TIPE": "SETORAN",
                            "CATATAN": nt
                        })
                        
                        with st.spinner("Menyimpan & Mengirim Laporan..."):
                            simpan_ke_excel_database(rows)
                            kirim_file_excel_telegram()
                            kirim_telegram(f"🌙 CLOSING {pilihan_gerobak}\n👤 {user}\n💰 Target: {format_rupiah(omzet)}\n💵 Setor: {format_rupiah(tn+qr)}\n📝 {nt}")
                            
                            # Hapus sesi shift
                            if pilihan_gerobak in db_gerobak:
                                del db_gerobak[pilihan_gerobak]
                                save_json(FILE_DB_GEROBAK, db_gerobak)
                        
                        st.balloons()
                        st.success("Laporan Terkirim! Shift Ditutup.")
                        st.rerun()

    else: 
        st.info("👈 Silakan Login di Menu Sebelah Kiri")

if __name__ == "__main__":
    main()
                                 
