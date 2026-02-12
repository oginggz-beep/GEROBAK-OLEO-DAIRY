import streamlit as st
import json
import os
import requests
import pandas as pd
from datetime import datetime, timedelta
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
import openpyxl
import glob 

# ================= 1. KONFIGURASI UTAMA =================
TOKEN_BOT = "8285539149:AAHQd-_W9aaBGSz3AUPg0oCuxabZUL6yJo4" 
ID_OWNER  = "8505488457"  
PIN_OWNER = "8888"        

# ================= 2. DATABASE & FILE =================
FILE_DB_GEROBAK = "database_gerobak.json" 
FILE_DB_STAFF   = "database_staff.json"   
FILE_DB_MENU    = "database_menu.json"    
FILE_DB_LOKASI  = "database_lokasi.json"  

# --- DATA DEFAULT BARU (3 KATEGORI) ---
MENU_DEFAULT = {
    "Regular (Cup)": {
        "Strawberry Milk": 10000, 
        "Coklat Milk": 12000,
        "Kopi Susu Aren": 15000
    },
    "Botol 250ml": {
        "Strawberry Milk": 15000,
        "Coklat Milk": 17000
    },
    "Botol 1 Liter": {
        "Strawberry Milk": 50000,
        "Kopi Literan": 65000
    }
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

# --- FUNGSI MENU BARU (BERTINGKAT) ---
def get_menu_aktif():
    data = load_json(FILE_DB_MENU)
    # Validasi struktur: Jika data lama (flat), paksa reset ke default baru
    if not data or not isinstance(list(data.values())[0], dict): 
        save_json(FILE_DB_MENU, MENU_DEFAULT)
        return MENU_DEFAULT
    return data

def simpan_menu_baru(kategori, nama, harga):
    data = get_menu_aktif()
    if kategori not in data: data[kategori] = {}
    data[kategori][nama] = int(harga)
    save_json(FILE_DB_MENU, data)

def hapus_menu(kategori, nama):
    data = get_menu_aktif()
    if kategori in data and nama in data[kategori]:
        del data[kategori][nama]
        save_json(FILE_DB_MENU, data)

def simpan_staff_baru(nama, pin):
    data = load_json(FILE_DB_STAFF); 
    if pin in data: return False
    data[pin] = nama; save_json(FILE_DB_STAFF, data); return True

def hapus_staff(pin):
    data = load_json(FILE_DB_STAFF)
    if pin in data: del data[pin]; save_json(FILE_DB_STAFF, data); return True
    return False

# ================= 4. FUNGSI EXCEL (WIDE FORMAT + KATEGORI) =================
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
        
        for cell in ws[1]:
            cell.font = header_font; cell.fill = header_fill; cell.alignment = center; cell.border = thin_border

        for col in ws.columns:
            max_len = 0
            col_letter = col[0].column_letter
            header_cell = ws[f"{col_letter}1"]
            header_text = str(header_cell.value).upper() if header_cell.value else ""
            
            is_currency = any(x in header_text for x in ['CASH', 'QRIS', 'TOTAL'])
            # Kolom menu sekarang punya format "Kategori - Nama (Harga)"
            is_menu_col = "(" in header_text and ")" in header_text and "-" in header_text

            for cell in col:
                cell.border = thin_border
                if is_currency and cell.row > 1:
                    try: 
                        if isinstance(cell.value, (int, float)): cell.number_format = '"Rp" #,##0'
                    except: pass
                
                if is_menu_col and cell.row > 1: cell.alignment = center

                try:
                    if cell.value and len(str(cell.value)) > max_len: max_len = len(str(cell.value))
                except: pass
            
            ws.column_dimensions[col_letter].width = max((max_len + 2), 12)
        wb.save(filename)
    except Exception as e:
        print(f"Error styling Excel: {e}")

def simpan_ke_excel_staff(list_transaksi, nama_staff, uang_tunai, uang_qris, total_setor, catatan):
    try:
        nama_file = get_nama_file_excel(nama_staff)
        
        data_row = {
            "TANGGAL": get_wib_now().strftime("%Y-%m-%d"),
            "JAM": get_wib_now().strftime("%H:%M"),
            "NAMA": nama_staff,
            "GEROBAK": list_transaksi[0]['GEROBAK'] if list_transaksi else "-",
        }

        # Masukkan Data Menu (Dengan Nama Kategori agar unik)
        for item in list_transaksi:
            if item['TIPE'] == 'JUAL':
                # Format Kolom: "Kategori - Menu (Harga)"
                # Contoh: "Botol 250ml - Strawberry Milk (15000)"
                col_name = f"{item['KATEGORI']} - {item['ITEM']} ({int(item['HARGA'])})"
                data_row[col_name] = item['TERJUAL']

        data_row["CASH"] = uang_tunai
        data_row["QRIS"] = uang_qris
        data_row["TOTAL OMZET"] = total_setor
        data_row["CATATAN"] = catatan

        df_baru = pd.DataFrame([data_row])

        if os.path.exists(nama_file):
            df_lama = pd.read_excel(nama_file)
            df_final = pd.concat([df_lama, df_baru], ignore_index=True)
            df_final = df_final.fillna(0)
            df_final.to_excel(nama_file, index=False)
        else:
            df_baru = df_baru.fillna(0)
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
            
            # Hitung total menu
            total_menu = sum(len(items) for items in MENU_SEKARANG.values())
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Gerobak Buka", f"{len(db_gerobak)}")
            c2.metric("Total Staff", f"{len(ds)}")
            c3.metric("Total Menu", f"{total_menu}")
            
            t1, t2, t3, t4, t5 = st.tabs(["🛒 Cek Toko", "👥 Staff", "📋 Menu (3 Kategori)", "📍 Kelola Gerobak", "📥 Laporan & Reset"])
            
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
                st.write("**Kelola Menu Per Kategori**")
                
                # Input Tambah Menu
                c_kat, c_nama, c_harga = st.columns(3)
                kat_baru = c_kat.selectbox("Kategori:", ["Regular (Cup)", "Botol 250ml", "Botol 1 Liter"])
                nama_baru = c_nama.text_input("Nama Menu")
                harga_baru = c_harga.number_input("Harga", step=500)
                
                if st.button("💾 Simpan Menu"):
                    if nama_baru:
                        simpan_menu_baru(kat_baru, nama_baru, harga_baru)
                        st.success("Menu Disimpan!"); st.rerun()

                st.divider()
                # Tampilkan Menu per Kategori
                for kat, items in MENU_SEKARANG.items():
                    with st.expander(f"📂 {kat} ({len(items)} menu)"):
                        if items:
                            df_menu = pd.DataFrame(list(items.items()), columns=['Nama Menu', 'Harga'])
                            st.dataframe(df_menu, hide_index=True, use_container_width=True)
                            
                            # Hapus Menu
                            to_del = st.selectbox(f"Hapus Menu di {kat}:", list(items.keys()), key=f"del_{kat}")
                            if st.button(f"Hapus {to_del}", key=f"btn_del_{kat}"):
                                hapus_menu(kat, to_del); st.rerun()
                        else:
                            st.caption("Belum ada menu di kategori ini.")

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
                st.subheader("📥 Download Laporan")
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

                # --- FITUR RESET SYSTEM TOTAL (KIAMAT) ---
                st.divider()
                st.error("⚠️ ZONA BERBAHAYA (RESET TOTAL PABRIK)")
                st.write("Tombol ini akan menghapus **SEMUA**: Staff, Menu, Lokasi, dan Laporan. Kembali seperti baru install.")
                
                with st.expander("🔴 Buka Menu Reset"):
                    password_reset = st.text_input("Masukkan Password Owner:", type="password")
                    
                    if st.button("🔥 HAPUS SEMUA DATA & RESET SYSTEM"):
                        if password_reset == PIN_OWNER:
                            try:
                                # 1. Hapus File JSON Database
                                files_db = [FILE_DB_GEROBAK, FILE_DB_STAFF, FILE_DB_MENU, FILE_DB_LOKASI]
                                for fdb in files_db:
                                    if os.path.exists(fdb): os.remove(fdb)
                                
                                # 2. Hapus Semua File Excel Laporan
                                file_excel = glob.glob("LAPORAN_*.xlsx")
                                for f in file_excel: os.remove(f)
                                
                                st.success("✅ SYSTEM BERHASIL DI-RESET KE PENGATURAN PABRIK!")
                                kirim_telegram("⚠️ SYSTEM ALERT: OWNER MELAKUKAN FULL RESET DATA.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Gagal Reset: {e}")
                        else:
                            st.error("⛔ Password Salah!")

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
                st.write("📝 **Persiapan Buka Toko (Input Stok)**")
                stok_input = {}
                
                # --- UPDATE: LOOPING PER KATEGORI (ACCORDION) ---
                for kategori, items in MENU_SEKARANG.items():
                    with st.expander(f"📦 Stok {kategori}", expanded=True):
                        cols = st.columns(2)
                        for i, (m, hrg) in enumerate(items.items()):
                            # Key unik: kategori_nama
                            key_input = f"{kategori}_{m}"
                            with cols[i%2]: 
                                val = st.number_input(f"{m}", min_value=0, value=0, key=f"stok_{key_input}")
                                if val > 0:
                                    stok_input[key_input] = val # Simpan dengan key unik
                
                st.write("---")
                if st.button("🚀 BUKA SHIFT SEKARANG", key="btn_open"):
                    jam_skrg = get_wib_now().strftime("%H:%M")
                    list_stok_text = ""
                    
                    # Generate text telegram
                    for k_item, jml in stok_input.items():
                        # k_item format: Kategori_NamaMenu
                        kat_split, nama_split = k_item.split('_', 1)
                        list_stok_text += f"\n📦 [{kat_split}] {nama_split}: {jml}"
                        
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
                omzet_total = 0; list_penjualan_temporary = [] 
                
                # --- UPDATE: LOOPING PER KATEGORI (ACCORDION) UNTUK CLOSING ---
                for kategori, items in MENU_SEKARANG.items():
                    # Cek apakah ada stok di kategori ini agar expander tidak kosong
                    # Tapi tetap tampilkan agar konsisten
                    with st.expander(f"💰 Penjualan {kategori}", expanded=True):
                        for m, harga_satuan in items.items():
                            key_unik = f"{kategori}_{m}"
                            stok_awal = int(shift_aktif_di_lokasi['stok'].get(key_unik, 0))
                            
                            if stok_awal > 0:
                                sisa = st.number_input(f"Sisa {m} (Awal: {stok_awal})", max_value=stok_awal, min_value=0, key=f"sisa_{key_unik}")
                                terjual = stok_awal - sisa
                                omzet_item = terjual * harga_satuan
                                omzet_total += omzet_item
                                
                                list_penjualan_temporary.append({
                                    "KATEGORI": kategori,
                                    "ITEM": m,
                                    "HARGA": harga_satuan,
                                    "TERJUAL": terjual,
                                    "TIPE": "JUAL",
                                    "GEROBAK": pilihan_gerobak
                                })
                            # Jika stok 0, tidak ditampilkan inputnya (Clean)
                
                st.write("---")
                st.markdown(f"### 💰 Total: {format_rupiah(omzet_total)}")
                
                c1, c2 = st.columns(2)
                uang_tunai = c1.number_input("Tunai", step=500, key="uang_tunai")
                uang_qris = c2.number_input("QRIS", step=500, key="uang_qris")
                catatan = st.text_area("Catatan", key="catatan_closing")
                
                total_setor = uang_tunai + uang_qris
                if (total_setor - omzet_total) != 0: 
                    st.warning(f"⚠️ Selisih: {format_rupiah(total_setor - omzet_total)}")

                st.write("---")
                
                if st.button("🔒 TUTUP SHIFT & KIRIM", key="btn_close"):
                    
                    with st.spinner("Menyimpan Laporan..."):
                        nama_file_excel = simpan_ke_excel_staff(
                            list_penjualan_temporary, 
                            user, 
                            uang_tunai, 
                            uang_qris, 
                            total_setor, 
                            catatan
                        )
                        
                        rincian_text = ""
                        # Urutkan text per kategori biar rapi
                        for item in list_penjualan_temporary:
                            if item['TERJUAL'] > 0:
                                rincian_text += f"\n▫️ [{item['KATEGORI']}] {item['ITEM']}: {item['TERJUAL']}"
                        if not rincian_text: rincian_text = "\n(Tidak ada item terjual)"

                        msg = (f"🌙 CLOSING {pilihan_gerobak}\n👤 {user}\n\n"
                               f"📊 **RINCIAN TERJUAL:**{rincian_text}\n\n"
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
