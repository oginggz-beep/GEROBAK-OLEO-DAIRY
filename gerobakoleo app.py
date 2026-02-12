import streamlit as st
import json
import os
import requests
import pandas as pd
from datetime import datetime, timedelta

# --- LIBRARY GOOGLE SHEET (Opsional biar ga error kalau belum install) ---
try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
    HAS_GSHEET_LIB = True
except ImportError:
    HAS_GSHEET_LIB = False

# ================= 1. KONFIGURASI UTAMA =================
TOKEN_BOT = "8285539149:AAHQd-_W9aaBGSz3AUPg0oCuxabZUL6yJo4" 
ID_OWNER  = "8505488457"  
PIN_OWNER = "8888"
NAMA_GOOGLE_SHEET = "Laporan_Gerobak_Apps" # Ganti sesuai nama Sheet Anda

# ================= 2. DATABASE & FILE =================
FILE_DB_GEROBAK = "database_gerobak.json" 
FILE_DB_STAFF   = "database_staff.json"   
FILE_DB_MENU    = "database_menu.json"    
FILE_DB_LOKASI  = "database_lokasi.json"  
FILE_DB_RIWAYAT = "database_riwayat.json" # Pengganti Excel (Sementara)

# Data Default
MENU_DEFAULT = {
    "Strawberry Milk": 10000, "Coklat Milk": 12000,
    "Kopi Susu Aren": 15000, "Matcha Latte": 15000
}
LOKASI_DEFAULT = {
    "1": "Gerobak Alun-Alun", "2": "Gerobak Stasiun", "3": "Gerobak Pasar"
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
        requests.post(url, data={"chat_id": ID_OWNER, "text": pesan, "parse_mode": "Markdown"}, timeout=3)
    except: pass

def load_json(filename):
    if os.path.exists(filename):
        try:
            with open(filename, 'r') as f: return json.load(f)
        except json.JSONDecodeError: return {}
    return {}

def save_json(filename, data):
    with open(filename, 'w') as f: json.dump(data, f, indent=4)

# --- FUNGSI UPDATE DATA MASTER ---
def get_lokasi_aktif():
    data = load_json(FILE_DB_LOKASI)
    if not data: save_json(FILE_DB_LOKASI, LOKASI_DEFAULT); return LOKASI_DEFAULT
    return data

def simpan_lokasi_baru(id_lokasi, nama_lokasi):
    data = get_lokasi_aktif(); data[str(id_lokasi)] = nama_lokasi; save_json(FILE_DB_LOKASI, data)

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

# ================= 4. FUNGSI RIWAYAT & GOOGLE SHEET =================

def simpan_riwayat_lokal(data_list):
    """
    Menyimpan data transaksi ke JSON lokal (Pengganti sementara Excel).
    Ini sangat cepat dan tidak bikin lag.
    """
    riwayat_lama = load_json(FILE_DB_RIWAYAT)
    if not isinstance(riwayat_lama, list): riwayat_lama = []
    
    # Gabungkan data baru
    riwayat_baru = riwayat_lama + data_list
    save_json(FILE_DB_RIWAYAT, riwayat_baru)

def upload_ke_gsheet():
    """
    Fungsi Eksklusif Owner: Upload data dari JSON lokal ke Google Sheet
    """
    if not HAS_GSHEET_LIB:
        return False, "Library gspread belum terinstall. Cek terminal."
    
    if not os.path.exists("credentials.json"):
        return False, "File 'credentials.json' tidak ditemukan!"

    try:
        # 1. Koneksi ke Google Sheet
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
        client = gspread.authorize(creds)
        sheet = client.open(NAMA_GOOGLE_SHEET).sheet1
        
        # 2. Ambil Data Lokal
        data_lokal = load_json(FILE_DB_RIWAYAT)
        if not data_lokal:
            return False, "Tidak ada data baru untuk di-upload."

        # 3. Siapkan Data untuk Upload (Convert dict to list values)
        # Ambil header dari data pertama jika sheet kosong
        try:
            existing_data = sheet.get_all_values()
            is_empty = len(existing_data) == 0
        except: is_empty = True

        rows_to_upload = []
        if is_empty and len(data_lokal) > 0:
            header = list(data_lokal[0].keys())
            rows_to_upload.append(header) # Tambah header jika sheet baru

        for entry in data_lokal:
            rows_to_upload.append(list(entry.values()))

        # 4. Push ke Sheet
        sheet.append_rows(rows_to_upload)

        # 5. Bersihkan Data Lokal setelah sukses upload (Opsional, agar tidak duplikat)
        # Kita kosongkan file riwayat lokal karena sudah pindah ke cloud
        save_json(FILE_DB_RIWAYAT, [])
        
        return True, f"Berhasil upload {len(data_lokal)} data transaksi!"

    except Exception as e:
        return False, f"Gagal Upload: {str(e)}"

# ================= 5. TAMPILAN APLIKASI UTAMA =================
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
            riwayat_pending = load_json(FILE_DB_RIWAYAT)
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Gerobak Buka", f"{len(db_gerobak)}")
            c2.metric("Total Staff", f"{len(ds)}")
            c3.metric("Pending Upload", f"{len(riwayat_pending)} Data")
            
            t1, t2, t3, t4, t5 = st.tabs(["🛒 Cek Toko", "👥 Staff", "📋 Menu", "📍 Lokasi", "☁️ Google Sheet"])
            
            with t1: 
                st.write("**Status Gerobak:**")
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
                st.dataframe(pd.DataFrame(list(LOKASI_SEKARANG.items()), columns=['ID','Nama Cabang']), hide_index=True, use_container_width=True)
                c_l1, c_l2 = st.columns([1,3])
                ids = [int(k) for k in LOKASI_SEKARANG.keys()]
                next_id = str(max(ids) + 1) if ids else "1"
                new_id = c_l1.text_input("ID", value=next_id); new_nm = c_l2.text_input("Nama Cabang")
                if st.button("Tambah Cabang") and new_nm: simpan_lokasi_baru(new_id, new_nm); st.rerun()
                if LOKASI_SEKARANG:
                    del_lok = st.selectbox("Hapus Cabang:", [f"{k} - {v}" for k,v in LOKASI_SEKARANG.items()])
                    if st.button("Hapus Cabang"): hapus_lokasi(del_lok.split(' - ')[0]); st.rerun()

            with t5: 
                st.subheader("Simpan Data ke Google Sheet")
                st.write(f"Saat ini ada **{len(riwayat_pending)}** data transaksi yang belum disimpan ke Google Sheet.")
                
                if len(riwayat_pending) > 0:
                    st.warning("⚠️ Data ini masih di laptop/server. Klik tombol di bawah untuk mengamankannya ke Google Sheet.")
                    if st.button("☁️ UPLOAD SEKARANG KE GOOGLE SHEET"):
                        with st.spinner("Sedang menghubungkan ke Google..."):
                            sukses, pesan = upload_ke_gsheet()
                            if sukses:
                                st.success(pesan)
                                st.balloons()
                                st.rerun()
                            else:
                                st.error(pesan)
                else:
                    st.success("✅ Semua data aman! Belum ada transaksi baru.")
            st.divider()

        # ================= FITUR STAFF =================
        if not LOKASI_SEKARANG: st.error("Database Kosong"); st.stop()

        st.subheader("📍 Pilih Lokasi Kerja")
        pilihan_gerobak = st.selectbox("Lokasi Anda:", list(LOKASI_SEKARANG.values()))
        
        db_gerobak = load_json(FILE_DB_GEROBAK)
        shift_aktif_di_lokasi = db_gerobak.get(pilihan_gerobak)

        is_lokasi_terisi = shift_aktif_di_lokasi is not None
        is_saya_di_sini  = is_lokasi_terisi and shift_aktif_di_lokasi['pin_pic'] == pin
        
        lokasi_lain_user = None
        for nama_g, data_g in db_gerobak.items():
            if data_g['pin_pic'] == pin and nama_g != pilihan_gerobak: lokasi_lain_user = nama_g; break

        if is_lokasi_terisi:
            if is_saya_di_sini: st.success(f"✅ ANDA SEDANG AKTIF DI SINI ({pilihan_gerobak})")
            else: st.error(f"⛔ LOKASI INI DIPAKAI OLEH: {shift_aktif_di_lokasi['pic']}")
        else: st.info("🟢 Lokasi Kosong. Siap Buka Shift.")

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
                with st.form("form_buka_toko"):
                    stok_input = {}; cols = st.columns(2)
                    for i, m in enumerate(MENU_SEKARANG):
                        with cols[i%2]: stok_input[m] = st.number_input(f"Stok {m}", min_value=0, value=0)
                    
                    tombol_buka = st.form_submit_button("🚀 BUKA SHIFT SEKARANG")
                    
                    if tombol_buka:
                        jam_skrg = get_wib_now().strftime("%H:%M")
                        
                        # Generate Text Stok untuk Telegram
                        list_stok_text = ""
                        for item, jml in stok_input.items():
                            if jml > 0: list_stok_text += f"\n📦 {item}: {jml}"
                        if not list_stok_text: list_stok_text = "\n(Tidak ada stok diinput)"

                        d = {"tanggal": get_wib_now().strftime("%Y-%m-%d"), "jam_masuk": jam_skrg, "pic": user, "pin_pic": pin, "stok": stok_input}
                        db_gerobak[pilihan_gerobak] = d
                        save_json(FILE_DB_GEROBAK, db_gerobak)
                        
                        kirim_telegram(f"☀️ *OPENING {pilihan_gerobak}*\n👤 {user}\n⏰ {jam_skrg}\n\n*STOK AWAL:*{list_stok_text}")
                        st.success("✅ Berhasil Buka!"); st.rerun()

        with t_cl:
            if not is_saya_di_sini:
                if is_lokasi_terisi: st.error("⛔ Bukan shift Anda.")
                else: st.info("Toko belum dibuka.")
            else:
                st.write("📝 **Laporan Penjualan**")
                with st.form("form_tutup_toko"):
                    omzet_total = 0; list_transaksi = []
                    st.write("---")
                    for m, harga_satuan in MENU_SEKARANG.items():
                        stok_awal = int(shift_aktif_di_lokasi['stok'].get(m, 0))
                        sisa = st.number_input(f"Sisa {m} (Awal: {stok_awal})", max_value=stok_awal, min_value=0, key=f"sisa_{m}")
                        terjual = stok_awal - sisa; omzet_item = terjual * harga_satuan; omzet_total += omzet_item
                        list_transaksi.append({
                            "TANGGAL": get_wib_now().strftime("%Y-%m-%d"), "GEROBAK": pilihan_gerobak, "STAFF": user, 
                            "ITEM": m, "HARGA": harga_satuan, "AWAL": stok_awal, "SISA": sisa, 
                            "TERJUAL": terjual, "OMZET": omzet_item, "TIPE": "JUAL"
                        })
                    
                    st.write("---")
                    st.markdown(f"### 💰 Total: {format_rupiah(omzet_total)}")
                    c1, c2 = st.columns(2)
                    uang_tunai = c1.number_input("Tunai", step=500); uang_qris = c2.number_input("QRIS", step=500)
                    total_setor = uang_tunai + uang_qris; catatan = st.text_area("Catatan")
                    
                    if (total_setor - omzet_total) != 0: st.warning(f"⚠️ Selisih: {format_rupiah(total_setor - omzet_total)}")

                    tombol_tutup = st.form_submit_button("🔒 TUTUP SHIFT & KIRIM")
                    if tombol_tutup:
                        # Tambah baris setoran ke list
                        list_transaksi.append({
                            "TANGGAL": get_wib_now().strftime("%Y-%m-%d"), "GEROBAK": pilihan_gerobak, "STAFF": user, 
                            "ITEM": "SETORAN", "HARGA":0, "AWAL":0, "SISA":0, "TERJUAL":0, "OMZET": total_setor, "TIPE": "SETORAN", "CATATAN": catatan
                        })
                        
                        # 1. Simpan ke Riwayat Lokal (Sangat Cepat)
                        simpan_riwayat_lokal(list_transaksi)
                        
                        # 2. Kirim Rincian Telegram (Hanya Text)
                        rincian_text = ""
                        for item in list_transaksi:
                            if item['TIPE'] == 'JUAL' and item['TERJUAL'] > 0:
                                rincian_text += f"\n▫️ {item['ITEM']}: {item['TERJUAL']}"
                        if not rincian_text: rincian_text = "\n(Tidak ada item terjual)"

                        msg = (f"🌙 *CLOSING {pilihan_gerobak}*\n👤 {user}\n\n📊 *RINCIAN TERJUAL:*{rincian_text}\n\n"
                               f"💰 *Omzet:* {format_rupiah(omzet_total)}\n"
                               f"💵 *Setor:* {format_rupiah(total_setor)}\n"
                               f"📝 *Catatan:* {catatan}")
                        
                        kirim_telegram(msg)
                        
                        # 3. Hapus Sesi
                        if pilihan_gerobak in db_gerobak:
                            del db_gerobak[pilihan_gerobak]; save_json(FILE_DB_GEROBAK, db_gerobak)
                        
                        st.balloons(); st.success("Shift Berakhir. Data tersimpan di antrian upload."); st.rerun()

    else: st.info("👈 Login di Menu Kiri")

if __name__ == "__main__":
    main()
    
