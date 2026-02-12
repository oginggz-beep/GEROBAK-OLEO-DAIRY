import streamlit as st
import json
import os
import requests
import pandas as pd
from datetime import datetime, timedelta
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
import openpyxl

# ================= 1. KONFIGURASI UTAMA =================
TOKEN_BOT = "8285539149:AAHQd-_W9aaBGSz3AUPg0oCuxabZUL6yJo4" 
ID_OWNER  = "8505488457"  
PIN_OWNER = "8888"        

# ================= 2. DATABASE & FILE =================
FILE_DB_GEROBAK = "database_gerobak.json" 
FILE_DB_STAFF   = "database_staff.json"   
FILE_DB_MENU    = "database_menu.json"    
FILE_DB_LOKASI  = "database_lokasi.json"  

# Data Default
MENU_DEFAULT = {
    "Strawberry Milk": 10000, "Coklat Milk": 12000,
    "Kopi Susu Aren": 15000, "Matcha Latte": 15000
}
LOKASI_DEFAULT = {
    "1": "Gerobak 01 - Alun-Alun", 
    "2": "Gerobak 02 - Stasiun Kota", 
    "3": "Gerobak 03 - Kampus Unand"
}

# ================= 3. FUNGSI BANTUAN =================
def get_wib_now():
    return datetime.utcnow() + timedelta(hours=7)

def format_rupiah(angka):
    return f"Rp {int(angka):,}".replace(",", ".")

def kirim_telegram(pesan):
    if "PASTE_TOKEN" in TOKEN_BOT: return
    try:
        url = f"https://api.telegram.org/bot{TOKEN_BOT}/sendMessage"
        requests.post(url, data={"chat_id": ID_OWNER, "text": pesan}, timeout=3)
    except: pass

def load_json(filename):
    if os.path.exists(filename):
        try:
            with open(filename, 'r') as f: return json.load(f)
        except json.JSONDecodeError: return {}
    return {}

def save_json(filename, data):
    with open(filename, 'w') as f: json.dump(data, f, indent=4)

# --- FUNGSI UPDATE DATA ---
def get_lokasi_aktif():
    data = load_json(FILE_DB_LOKASI)
    if not data: save_json(FILE_DB_LOKASI, LOKASI_DEFAULT); return LOKASI_DEFAULT
    return data

def simpan_lokasi_baru(id_lokasi, nama_lengkap_lokasi):
    data = get_lokasi_aktif(); data[str(id_lokasi)] = nama_lengkap_lokasi; save_json(FILE_DB_LOKASI, data)

def hapus_lokasi(id_lokasi):
    data = get_lokasi_aktif()
    if str(id_lokasi) in data: del data[str(id_lokasi)]; save_json(FILE_DB_LOKASI, data)

def get_menu_aktif():
    data = load_json(FILE_DB_MENU)
    if not data: save_json(FILE_DB_MENU, MENU_DEFAULT); return MENU_DEFAULT
    return data

def simpan_menu_baru(nama, harga):
    data = get_menu_aktif(); data[nama] = int(harga); save_json(FILE_DB_MENU, data)

def hapus_menu(nama):
    data = get_menu_aktif()
    if nama in data: del data[nama]; save_json(FILE_DB_MENU, data)

def simpan_staff_baru(nama, pin):
    data = load_json(FILE_DB_STAFF); 
    if pin in data: return False
    data[pin] = nama; save_json(FILE_DB_STAFF, data); return True

def hapus_staff(pin):
    data = load_json(FILE_DB_STAFF)
    if pin in data: del data[pin]; save_json(FILE_DB_STAFF, data); return True
    return False

# ================= 4. FUNGSI EXCEL (FORMAT HORIZONTAL) =================
def get_nama_file_excel(nama_staff):
    nama_clean = nama_staff.replace(" ", "_").upper()
    return f"LAPORAN_{nama_clean}.xlsx"

def rapikan_excel(filename):
    try:
        wb = openpyxl.load_workbook(filename)
        ws = wb.active
        
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="203764", end_color="203764", fill_type="solid")
        center = Alignment(horizontal="center", vertical="center")
        thin_border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
        
        # 1. Format Header
        for cell in ws[1]:
            cell.font = header_font; cell.fill = header_fill; cell.alignment = center; cell.border = thin_border

        # 2. Format Kolom
        for col in ws.columns:
            max_len = 0
            col_letter = col[0].column_letter
            header_cell = ws[f"{col_letter}1"]
            header_text = str(header_cell.value).upper() if header_cell.value else ""
            
            # Kolom Uang (CASH, QRIS, TOTAL)
            is_currency = any(x in header_text for x in ['CASH', 'QRIS', 'TOTAL', 'OMZET'])

            for cell in col:
                cell.border = thin_border
                # Format Rupiah
                if is_currency and cell.row > 1: 
                    try:
                        if isinstance(cell.value, (int, float)):
                            cell.number_format = '"Rp" #,##0' 
                    except: pass
                
                # Auto Width
                try:
                    if cell.value and len(str(cell.value)) > max_len: max_len = len(str(cell.value))
                except: pass
            
            # Batasi lebar maksimal agar tidak kepanjangan
            final_width = max_len + 5
            if final_width > 30: final_width = 30
            ws.column_dimensions[col_letter].width = final_width

        wb.save(filename)
    except Exception as e:
        print(f"Error styling Excel: {e}")

def simpan_ke_excel_staff(data_dict, nama_staff):
    """
    Menerima data_dict (Satu baris data lengkap)
    """
    try:
        nama_file = get_nama_file_excel(nama_staff)
        # Bikin DataFrame dari 1 baris data (dict harus di-list-kan)
        df_baru = pd.DataFrame([data_dict])
        
        # Pastikan urutan kolom rapi (Info Utama -> Menu -> Keuangan)
        # Kita cari kolom menu secara dinamis
        cols = list(df_baru.columns)
        
        # Pisahkan kolom berdasarkan kategori
        cols_utama = ["TANGGAL", "NAMA", "GEROBAK"]
        cols_duit = ["TOTAL PCS", "CASH", "QRIS", "TOTAL OMZET", "CATATAN"]
        cols_menu = [c for c in cols if c not in cols_utama and c not in cols_duit]
        cols_menu.sort() # Urutkan menu sesuai abjad
        
        # Susun Ulang
        final_cols = cols_utama + cols_menu + cols_duit
        # Filter hanya kolom yg benar2 ada
        final_cols = [c for c in final_cols if c in df_baru.columns]
        
        df_baru = df_baru[final_cols]

        if os.path.exists(nama_file):
            # Gabung dengan data lama
            df_lama = pd.read_excel(nama_file)
            df_final = pd.concat([df_lama, df_baru], ignore_index=True)
            df_final.to_excel(nama_file, index=False)
        else:
            df_baru.to_excel(nama_file, index=False)
            
        rapikan_excel(nama_file)
        return nama_file
    except Exception as e:
        st.error(f"❌ Gagal Simpan Excel: {e}")
        return None

# ================= 5. TAMPILAN APLIKASI =================
def main():
    st.set_page_config(page_title="Sistem Gerobak Pro", page_icon="🏪", layout="centered")
    
    LOKASI_SEKARANG = get_lokasi_aktif()
    MENU_SEKARANG = get_menu_aktif()
    waktu_skrg = get_wib_now()
    
    st.title("🏪 Kasir & Absensi Gerobak")
    st.caption(f"📅 {waktu_skrg.strftime('%d-%m-%Y %H:%M')} WIB")

    if 'user_nama' not in st.session_state: st.session_state['user_nama'] = None
    if 'user_pin' not in st.session_state: st.session_state['user_pin'] = None

    # --- SIDEBAR LOGIN ---
    with st.sidebar:
        st.header("🔐 Akses Sistem")
        if st.session_state['user_nama'] is None:
            mode = st.radio("Pilih Menu:", ["Login Masuk", "Daftar Staff Baru"])
            if mode == "Login Masuk":
                pin = st.text_input("Masukkan PIN", type="password", max_chars=6)
                if st.button("Masuk Sistem"):
                    data_staff = load_json(FILE_DB_STAFF)
                    if pin == PIN_OWNER:
                        st.session_state['user_nama'] = "OWNER"; st.session_state['user_pin'] = PIN_OWNER; st.rerun()
                    elif pin in data_staff:
                        st.session_state['user_nama'] = data_staff[pin]; st.session_state['user_pin'] = pin; st.rerun()
                    else: st.error("PIN Tidak Dikenal")
            elif mode == "Daftar Staff Baru":
                nm = st.text_input("Nama Lengkap")
                pn = st.text_input("PIN (Angka)", max_chars=6)
                if st.button("Daftarkan Staff"): 
                    if not nm or not pn: st.error("Nama dan PIN wajib diisi!")
                    elif simpan_staff_baru(nm, pn): 
                        st.success(f"Staff {nm} Terdaftar!"); kirim_telegram(f"🆕 STAFF BARU: {nm} ({pn})")
                    else: st.error("PIN Sudah Dipakai")
        else:
            st.success(f"Halo, {st.session_state['user_nama']}")
            if st.button("Keluar (Logout)"): st.session_state['user_nama']=None; st.rerun()

    # --- KONTEN UTAMA ---
    if st.session_state['user_nama']:
        user = st.session_state['user_nama']
        pin  = st.session_state['user_pin']

        # ================= FITUR OWNER =================
        if user == "OWNER":
            st.info("🔧 **MODE ADMIN / PEMILIK**")
            
            db_gerobak = load_json(FILE_DB_GEROBAK)
            ds = load_json(FILE_DB_STAFF)
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Gerobak Buka", f"{len(db_gerobak)}")
            c2.metric("Total Staff", f"{len(ds)}")
            c3.metric("Total Menu", f"{len(MENU_SEKARANG)}")
            
            t1, t2, t3, t4, t5 = st.tabs(["🛒 Cek Toko", "👥 Staff", "📋 Menu", "📍 Kelola Gerobak", "📥 Laporan"])
            
            with t1: 
                st.write("**Status Operasional:**")
                if not db_gerobak: st.caption("Semua gerobak tutup.")
                for id_lok, nama_lok in LOKASI_SEKARANG.items():
                    info = db_gerobak.get(nama_lok)
                    status_icon = "🟢 TUTUP" if not info else "🔴 BUKA"
                    with st.expander(f"{status_icon} - {nama_lok}", expanded=bool(info)):
                        if info:
                            st.write(f"👤 **Penjaga:** {info['pic']}")
                            st.write(f"⏰ **Buka:** {info['jam_masuk']}")
                            if st.button(f"⛔ PAKSA TUTUP / RESET {nama_lok}", key=f"kick_{id_lok}"):
                                del db_gerobak[nama_lok]; save_json(FILE_DB_GEROBAK, db_gerobak); st.rerun()
                        else: st.write("Kosong.")
            
            with t2: 
                st.dataframe(pd.DataFrame(list(ds.items()), columns=['PIN','NAMA']), hide_index=True, use_container_width=True)
                if ds:
                    pilih = st.selectbox("Pilih Staff Hapus:", [f"{v} ({k})" for k,v in ds.items()])
                    if st.button("Hapus Staff"): hapus_staff(pilih.split('(')[1][:-1]); st.rerun()

            with t3: 
                st.dataframe(pd.DataFrame(list(MENU_SEKARANG.items()), columns=['Menu','Harga']), hide_index=True, use_container_width=True)
                c_m1,c_m2 = st.columns(2)
                nm_menu = c_m1.text_input("Nama Menu")
                hg_menu = c_m2.number_input("Harga", step=500)
                if st.button("Simpan Menu") and nm_menu: simpan_menu_baru(nm_menu, hg_menu); st.rerun()
                if MENU_SEKARANG:
                    del_m = st.selectbox("Hapus Menu:", list(MENU_SEKARANG.keys()))
                    if st.button("Hapus Menu Terpilih"): hapus_menu(del_m); st.rerun()

            with t4: 
                st.subheader("Daftar Gerobak & Lokasi")
                if LOKASI_SEKARANG:
                    df_lokasi = pd.DataFrame(list(LOKASI_SEKARANG.items()), columns=['ID', 'Nama Gerobak - Lokasi'])
                    st.dataframe(df_lokasi, hide_index=True, use_container_width=True)
                
                st.write("---")
                st.write("**Tambah Gerobak Baru**")
                c_l1, c_l2 = st.columns([1,3])
                ids = [int(k) for k in LOKASI_SEKARANG.keys()]
                next_id = str(max(ids) + 1) if ids else "1"
                
                input_id = c_l1.text_input("ID", value=next_id)
                input_nama = c_l2.text_input("Nama Gerobak (Cth: Gerobak 01)")
                input_lokasi = st.text_input("📍 Lokasi Fisik (Cth: Kampus Unand / Depan Masjid)")
                
                if st.button("💾 Simpan Gerobak"):
                    if input_nama and input_lokasi:
                        nama_lengkap = f"{input_nama} - {input_lokasi}"
                        simpan_lokasi_baru(input_id, nama_lengkap)
                        st.success(f"Berhasil: {nama_lengkap}"); st.rerun()
                    else: st.error("Nama Gerobak dan Lokasi wajib diisi!")

                if LOKASI_SEKARANG:
                    st.write("---")
                    del_lok = st.selectbox("Hapus Gerobak:", [f"{k} - {v}" for k,v in LOKASI_SEKARANG.items()])
                    if st.button("🗑️ Hapus Gerobak"): hapus_lokasi(del_lok.split(' - ')[0]); st.rerun()

            with t5: 
                st.write("Unduh Laporan Per Staff:")
                if ds:
                    list_nama_staff = list(ds.values())
                    pilih_staff_dl = st.selectbox("Pilih Staff:", list_nama_staff)
                    file_target = get_nama_file_excel(pilih_staff_dl)
                    
                    if os.path.exists(file_target):
                        st.success(f"File ditemukan: {file_target}")
                        with open(file_target, "rb") as file:
                            st.download_button(label=f"📥 Download Excel {pilih_staff_dl}", data=file, file_name=file_target, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                    else: st.warning(f"Belum ada laporan dari staff: {pilih_staff_dl}")
                else: st.warning("Belum ada data staff.")
            st.divider()

        # ================= FITUR STAFF =================
        if not LOKASI_SEKARANG: st.error("Database Kosong"); st.stop()

        st.subheader("📍 Pilih Posisi Gerobak")
        pilihan_gerobak = st.selectbox("Pilih Gerobak & Lokasi:", list(LOKASI_SEKARANG.values()))
        
        db_gerobak = load_json(FILE_DB_GEROBAK)
        shift_aktif_di_lokasi = db_gerobak.get(pilihan_gerobak)

        is_lokasi_terisi = shift_aktif_di_lokasi is not None
        is_saya_di_sini  = is_lokasi_terisi and shift_aktif_di_lokasi['pin_pic'] == pin
        
        lokasi_lain_user = None
        for nama_g, data_g in db_gerobak.items():
            if data_g['pin_pic'] == pin and nama_g != pilihan_gerobak: lokasi_lain_user = nama_g; break

        if is_lokasi_terisi:
            if is_saya_di_sini: st.success(f"✅ ANDA SEDANG AKTIF DI: {pilihan_gerobak}")
            else: st.error(f"⛔ {pilihan_gerobak} SEDANG DIPAKAI: {shift_aktif_di_lokasi['pic']}")
        else: st.info(f"🟢 {pilihan_gerobak} Kosong. Siap Buka Shift.")

        t_op, t_cl = st.tabs(["☀️ BUKA TOKO", "🌙 TUTUP TOKO"])

        with t_op:
            if lokasi_lain_user:
                st.error("❌ AKSES DITOLAK"); st.warning(f"Anda masih aktif di **{lokasi_lain_user}**. Tutup dulu disana.")
            elif is_lokasi_terisi and not is_saya_di_sini:
                st.error(f"🔒 Gerobak dipakai {shift_aktif_di_lokasi['pic']}.")
            elif is_saya_di_sini:
                st.info("Toko sudah buka. Klik tab 'TUTUP TOKO' jika ingin pulang.")
            else:
                st.write("📝 **Persiapan Buka Toko**")
                stok_input = {}; cols = st.columns(2)
                for i, m in enumerate(MENU_SEKARANG):
                    with cols[i%2]: stok_input[m] = st.number_input(f"Stok {m}", min_value=0, value=0)
                
                st.write("---")
                if st.button("🚀 BUKA SHIFT SEKARANG", key="btn_open"):
                    jam_skrg = get_wib_now().strftime("%H:%M")
                    list_stok_text = ""
                    for item, jml in stok_input.items():
                        if jml > 0: list_stok_text += f"\n📦 {item}: {jml}"
                    if not list_stok_text: list_stok_text = "\n(Tidak ada stok diinput)"

                    d = {"tanggal": get_wib_now().strftime("%Y-%m-%d"), "jam_masuk": jam_skrg, "pic": user, "pin_pic": pin, "stok": stok_input}
                    db_gerobak[pilihan_gerobak] = d; save_json(FILE_DB_GEROBAK, db_gerobak)
                    
                    kirim_telegram(f"☀️ OPENING {pilihan_gerobak}\n👤 {user}\n⏰ {jam_skrg}\n\n**STOK AWAL:**{list_stok_text}")
                    st.success("✅ Berhasil Buka!"); st.rerun()

        with t_cl:
            if not is_saya_di_sini:
                if is_lokasi_terisi: st.error("⛔ Bukan shift Anda.")
                else: st.info("Toko belum dibuka.")
            else:
                st.write("📝 **Laporan Penjualan**")
                
                # --- STRUKTUR DATA UTAMA LAPORAN ---
                # Kita akan menyusun satu baris dictionary yang berisi semua kolom
                data_laporan_shift = {
                    "TANGGAL": get_wib_now().strftime("%Y-%m-%d"),
                    "NAMA": user,
                    "GEROBAK": pilihan_gerobak,
                }

                omzet_total = 0
                total_pcs_terjual = 0
                rincian_telegram_text = ""
                
                st.write("---")
                
                # Loop setiap menu untuk input sisa & hitung terjual
                # Menu yang stok awal 0 tetap dihitung tapi hidden (input 0)
                
                for m, harga_satuan in MENU_SEKARANG.items():
                    stok_awal = int(shift_aktif_di_lokasi['stok'].get(m, 0))
                    
                    # Logika tampilan input
                    if stok_awal > 0:
                        sisa = st.number_input(f"Sisa {m} (Awal: {stok_awal})", max_value=stok_awal, min_value=0, key=f"sisa_{m}")
                    else:
                        sisa = 0 # Otomatis 0 kalau stok awal 0
                    
                    terjual = stok_awal - sisa
                    omzet_item = terjual * harga_satuan
                    omzet_total += omzet_item
                    total_pcs_terjual += terjual
                    
                    # --- KUNCI: Masukkan ke Data Laporan sebagai KOLOM ---
                    # Nama Kolom = "Nama Menu (Harga)"
                    nama_kolom_menu = f"{m} ({int(harga_satuan)})"
                    data_laporan_shift[nama_kolom_menu] = terjual

                    # Siapkan Text Telegram
                    if terjual > 0:
                        rincian_telegram_text += f"\n▫️ {m}: {terjual}"

                st.write("---")
                st.markdown(f"### 💰 Total: {format_rupiah(omzet_total)}")
                
                c1, c2 = st.columns(2)
                uang_tunai = c1.number_input("Tunai", step=500, key="uang_tunai")
                uang_qris = c2.number_input("QRIS", step=500, key="uang_qris")
                catatan = st.text_area("Catatan", key="catatan_closing")
                
                total_setor = uang_tunai + uang_qris
                if (total_setor - omzet_total) != 0: 
                    st.warning(f"⚠️ Selisih: {format_rupiah(total_setor - omzet_total)}")

                # Lengkapi Data Laporan
                data_laporan_shift["TOTAL PCS"] = total_pcs_terjual
                data_laporan_shift["CASH"] = uang_tunai
                data_laporan_shift["QRIS"] = uang_qris
                data_laporan_shift["TOTAL OMZET"] = total_setor
                data_laporan_shift["CATATAN"] = catatan

                st.write("---")
                
                if st.button("🔒 TUTUP SHIFT & KIRIM", key="btn_close"):
                    
                    with st.spinner("Menyimpan Laporan..."):
                        # Simpan ke Excel (Format Horizontal)
                        simpan_ke_excel_staff(data_laporan_shift, user)
                        
                        if not rincian_telegram_text: rincian_telegram_text = "\n(Tidak ada item terjual)"

                        msg = (f"🌙 CLOSING {pilihan_gerobak}\n👤 {user}\n\n"
                               f"📊 **RINCIAN TERJUAL:**{rincian_telegram_text}\n\n"
                               f"💵 **Tunai:** {format_rupiah(uang_tunai)}\n"
                               f"💳 **QRIS:** {format_rupiah(uang_qris)}\n"
                               f"💰 **Total Setor:** {format_rupiah(total_setor)}\n"
                               f"📝 **Catatan:** {catatan}")

                        kirim_telegram(msg)
                        
                        if pilihan_gerobak in db_gerobak:
                            del db_gerobak[pilihan_gerobak]; save_json(FILE_DB_GEROBAK, db_gerobak)
                    
                    st.balloons(); st.success("Shift Berakhir."); st.rerun()

    else: st.info("👈 Login di Menu Kiri")

if __name__ == "__main__":
    main()
