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
    "1": "Gerobak Alun-Alun", 
    "2": "Gerobak Stasiun", 
    "3": "Gerobak Pasar"
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

# --- UPDATE: Kirim File Excel Spesifik ---
def kirim_file_excel_telegram(filename_target):
    if "PASTE_TOKEN" in TOKEN_BOT: return
    if os.path.exists(filename_target):
        try:
            url = f"https://api.telegram.org/bot{TOKEN_BOT}/sendDocument"
            with open(filename_target, 'rb') as f:
                requests.post(url, data={'chat_id': ID_OWNER, 'caption': f'📊 Laporan: {filename_target}'}, files={'document': f}, timeout=10)
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

# ================= 4. FUNGSI EXCEL PER STAFF (BARU) =================
def get_nama_file_excel(nama_staff):
    # Ubah nama staff jadi format file yang aman (Hilangkan spasi)
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
        
        for cell in ws[1]:
            cell.font = header_font; cell.fill = header_fill; cell.alignment = center; cell.border = thin_border

        for col in ws.columns:
            max_len = 0
            col_letter = col[0].column_letter
            for cell in col:
                cell.border = thin_border
                try:
                    if cell.value and len(str(cell.value)) > max_len: max_len = len(str(cell.value))
                except: pass
                
                header_text = ws[f"{col_letter}1"].value
                if header_text and any(x in str(header_text).upper() for x in ['OMZET', 'HARGA', 'TUNAI', 'QRIS', 'TOTAL']):
                    cell.number_format = '#,##0 "Rp"'
            ws.column_dimensions[col_letter].width = (max_len + 5)
        wb.save(filename)
    except: pass

def simpan_ke_excel_staff(data_rows, nama_staff):
    try:
        # Generate nama file berdasarkan nama staff
        nama_file = get_nama_file_excel(nama_staff)
        
        df_baru = pd.DataFrame(data_rows)
        if os.path.exists(nama_file):
            df_lama = pd.read_excel(nama_file)
            df_final = pd.concat([df_lama, df_baru], ignore_index=True)
        else:
            df_final = df_baru
            
        df_final.to_excel(nama_file, index=False)
        rapikan_excel(nama_file)
        return nama_file # Kembalikan nama file agar bisa dikirim bot
    except Exception as e:
        st.error(f"❌ Gagal Simpan Excel: {e}")
        return None

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
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Gerobak Buka", f"{len(db_gerobak)}")
            c2.metric("Total Staff", f"{len(ds)}")
            c3.metric("Total Menu", f"{len(MENU_SEKARANG)}")
            
            t1, t2, t3, t4, t5 = st.tabs(["🛒 Cek Toko", "👥 Staff", "📋 Menu", "📍 Lokasi", "📥 Laporan"])
            
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

            with t5: # UPDATE: DOWNLOAD PER STAFF
                st.write("Unduh Laporan Per Staff:")
                if ds:
                    # Ambil daftar nama staff
                    list_nama_staff = list(ds.values())
                    pilih_staff_dl = st.selectbox("Pilih Staff:", list_nama_staff)
                    
                    # Generate nama file target
                    file_target = get_nama_file_excel(pilih_staff_dl)
                    
                    if os.path.exists(file_target):
                        st.success(f"File ditemukan: {file_target}")
                        with open(file_target, "rb") as file:
                            st.download_button(
                                label=f"📥 Download Excel {pilih_staff_dl}",
                                data=file,
                                file_name=file_target,
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                    else:
                        st.warning(f"Belum ada laporan dari staff: {pilih_staff_dl}")
                else:
                    st.warning("Belum ada data staff.")
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
                        d = {"tanggal": get_wib_now().strftime("%Y-%m-%d"), "jam_masuk": jam_skrg, "pic": user, "pin_pic": pin, "stok": stok_input}
                        db_gerobak[pilihan_gerobak] = d; save_json(FILE_DB_GEROBAK, db_gerobak)
                        kirim_telegram(f"☀️ OPENING {pilihan_gerobak}\n👤 {user}\n⏰ {jam_skrg}"); st.success("✅ Berhasil Buka!"); st.rerun()

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
                        list_transaksi.append({
                            "TANGGAL": get_wib_now().strftime("%Y-%m-%d"), "GEROBAK": pilihan_gerobak, "STAFF": user, 
                            "ITEM": "SETORAN", "HARGA":0, "AWAL":0, "SISA":0, "TERJUAL":0, "OMZET": total_setor, "TIPE": "SETORAN", "CATATAN": catatan
                        })
                        
                        with st.spinner("Menyimpan Laporan Staff..."):
                            # Simpan ke Excel Khusus Staff
                            nama_file_excel = simpan_ke_excel_staff(list_transaksi, user)
                            
                            # Kirim file spesifik ke Telegram
                            if nama_file_excel:
                                kirim_file_excel_telegram(nama_file_excel)
                            
                            kirim_telegram(f"🌙 CLOSING {pilihan_gerobak}\n👤 {user}\n💰 Omzet: {format_rupiah(omzet_total)}\n💵 Setor: {format_rupiah(total_setor)}\n📝 {catatan}")
                            
                            if pilihan_gerobak in db_gerobak:
                                del db_gerobak[pilihan_gerobak]; save_json(FILE_DB_GEROBAK, db_gerobak)
                        
                        st.balloons(); st.success("Shift Berakhir."); st.rerun()

    else: st.info("👈 Login di Menu Kiri")

if __name__ == "__main__":
    main()
                    
