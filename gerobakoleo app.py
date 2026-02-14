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
TOKEN_FONNTE    = "VP1u4odNqETyKTs8mXp4"  # Token Fonnte Kamu
TARGET_WA       = "120363405943853807@g.us" # Ganti dengan ID Grup WA
PIN_OWNER_LOGIN = "8888" # PIN untuk Login ke Menu Owner
PASSWORD_RESET  = "ciroclistopel" # Password khusus untuk Hapus Data

# ================= 2. DATABASE & FILE =================
FILE_DB_GEROBAK     = "database_gerobak.json" 
FILE_DB_STAFF       = "database_staff.json"   
FILE_DB_MENU        = "database_menu.json"    
FILE_DB_LOKASI      = "database_lokasi.json"  
FILE_DB_SURAT_JALAN = "database_surat_jalan.json"

# --- DATA DEFAULT (3 KATEGORI) ---
MENU_DEFAULT = {
    "Regular (Cup)": {
        "Fresh Milk": 8000, 
        "Coklat Milk": 10000,
        "Strawberry Milk": 10000,
        "Vanilla Milk": 10000,
        "Mango Milk": 10000,
        "Melon Milk": 10000
    },
    "Botol 250ml": {
        "Fresh Milk": 10000, 
        "Coklat Milk": 15000,
        "Strawberry Milk": 15000,
        "Vanilla Milk": 15000,
        "Mango Milk": 15000,
        "Melon Milk": 15000
    },
    "Botol 1 Liter": {
        "Plastic Edition": 20000, 
        "Coklat Milk": 45000,
        "Strawberry Milk": 45000,
        "Vanilla Milk": 45000,
        "Mango Milk": 45000,
        "Melon Milk": 45000
    }
}

LOKASI_DEFAULT = {
    "1": "Gerobak 01 - SD Kartika", 
    "2": "Gerobak 02 - belum ada", 
    "3": "Gerobak 03 - belum ada"
}

# ================= 3. FUNGSI BANTUAN =================
def get_wib_now():
    return datetime.utcnow() + timedelta(hours=7)

def format_rupiah(angka):
    return f"Rp {int(angka):,}".replace(",", ".")

# --- FUNGSI BARU: KIRIM KE WHATSAPP VIA FONNTE ---
def kirim_whatsapp(pesan):
    if "PASTE_ID" in TARGET_WA: return # Cegah error jika ID belum diisi
    try:
        url = "https://api.fonnte.com/send"
        headers = {
            'Authorization': TOKEN_FONNTE
        }
        data = {
            'target': TARGET_WA,
            'message': pesan
        }
        requests.post(url, headers=headers, data=data, timeout=5)
    except Exception as e:
        print(f"Gagal kirim WA: {e}")

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

# ================= 4. FUNGSI EXCEL =================
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
            "CASH": uang_tunai,
            "QRIS": uang_qris,
            "TOTAL OMZET": total_setor,
        }

        for item in list_transaksi:
            if item['TIPE'] == 'JUAL':
                col_name = f"{item['KATEGORI']} - {item['ITEM']} ({int(item['HARGA'])})"
                data_row[col_name] = item['TERJUAL']

        data_row["CATATAN"] = catatan

        df_baru = pd.DataFrame([data_row])

        if os.path.exists(nama_file):
            df_lama = pd.read_excel(nama_file)
            df_final = pd.concat([df_lama, df_baru], ignore_index=True)
            df_final = df_final.fillna(0)
        else:
            df_final = df_baru.fillna(0)
            
        kolom_utama = ["TANGGAL", "JAM", "NAMA", "GEROBAK", "CASH", "QRIS", "TOTAL OMZET"]
        kolom_menu = [col for col in df_final.columns if col not in kolom_utama and col != "CATATAN"]
        
        urutan_final = kolom_utama + kolom_menu
        if "CATATAN" in df_final.columns:
            urutan_final.append("CATATAN")
            
        df_final = df_final[urutan_final]
        df_final.to_excel(nama_file, index=False)
            
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
    
    st.title("OLEO DAIRY 🐮")
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
                    if pin == PIN_OWNER_LOGIN:
                        st.session_state['user_nama'] = "OWNER"; st.session_state['user_pin'] = PIN_OWNER_LOGIN; st.rerun()
                    elif pin in data_staff:
                        st.session_state['user_nama'] = data_staff[pin]; st.session_state['user_pin'] = pin; st.rerun()
                    else: st.error("PIN Tidak Dikenal")
            elif mode == "Daftar Staff Baru":
                nm = st.text_input("Nama Lengkap")
                pn = st.text_input("PIN (Angka)", max_chars=6)
                if st.button("Daftarkan Staff"): 
                    if not nm or not pn: st.error("Nama dan PIN wajib diisi!")
                    elif simpan_staff_baru(nm, pn): 
                        st.success(f"Staff {nm} Terdaftar!")
                        # PENGIRIMAN NOTIFIKASI WA UNTUK STAFF BARU DIHAPUS DI SINI
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
            
            total_menu = sum(len(items) for items in MENU_SEKARANG.values())
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Gerobak Buka", f"{len(db_gerobak)}")
            c2.metric("Total Staff", f"{len(ds)}")
            c3.metric("Total Menu", f"{total_menu}")
            
            t1, t2, t3, t4, t5, t6 = st.tabs(["🛒 Cek Toko", "👥 Staff", "📋 Menu", "📍 Lokasi", "📥 Laporan", "🚚 Surat Jalan"])
            
            with t1: 
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
            
            with t2: 
                st.dataframe(pd.DataFrame(list(ds.items()), columns=['PIN','NAMA']), hide_index=True, use_container_width=True)
                if ds:
                    pilih = st.selectbox("Hapus Staff:", [f"{v} ({k})" for k,v in ds.items()])
                    if st.button("Hapus"): hapus_staff(pilih.split('(')[1][:-1]); st.rerun()

            with t3: 
                st.write("**Kelola Menu Per Kategori**")
                c_kat, c_nama, c_harga = st.columns(3)
                kat_baru = c_kat.selectbox("Kategori:", ["Regular (Cup)", "Botol 250ml", "Botol 1 Liter"])
                nama_baru = c_nama.text_input("Nama Menu")
                harga_baru = c_harga.number_input("Harga", step=500)
                
                if st.button("💾 Simpan Menu"):
                    if nama_baru:
                        simpan_menu_baru(kat_baru, nama_baru, harga_baru)
                        st.success("Menu Disimpan!"); st.rerun()

                st.divider()
                for kat, items in MENU_SEKARANG.items():
                    with st.expander(f"📂 {kat} ({len(items)} menu)"):
                        if items:
                            df_menu = pd.DataFrame(list(items.items()), columns=['Nama Menu', 'Harga'])
                            st.dataframe(df_menu, hide_index=True, use_container_width=True)
                            to_del = st.selectbox(f"Hapus Menu di {kat}:", list(items.keys()), key=f"del_{kat}")
                            if st.button(f"Hapus {to_del}", key=f"btn_del_{kat}"):
                                hapus_menu(kat, to_del); st.rerun()

            with t4: 
                st.subheader("Daftar Gerobak")
                if LOKASI_SEKARANG:
                    df_lokasi = pd.DataFrame(list(LOKASI_SEKARANG.items()), columns=['ID', 'Nama Gerobak - Lokasi'])
                    st.dataframe(df_lokasi, hide_index=True, use_container_width=True)
                
                c_l1, c_l2 = st.columns([1,3])
                ids = [int(k) for k in LOKASI_SEKARANG.keys()]
                next_id = str(max(ids) + 1) if ids else "1"
                
                input_id = c_l1.text_input("ID", value=next_id)
                input_nama = c_l2.text_input("Nama Gerobak (Cth: Gerobak 01)")
                input_lokasi = st.text_input("📍 Lokasi (Cth: Unand)")
                
                if st.button("💾 Simpan Lokasi"):
                    if input_nama and input_lokasi:
                        nama_lengkap = f"{input_nama} - {input_lokasi}"
                        simpan_lokasi_baru(input_id, nama_lengkap)
                        st.rerun()

                if LOKASI_SEKARANG:
                    del_lok = st.selectbox("Hapus:", [f"{k} - {v}" for k,v in LOKASI_SEKARANG.items()])
                    if st.button("🗑️ Hapus"): hapus_lokasi(del_lok.split(' - ')[0]); st.rerun()

            with t5: 
                st.subheader("📥 Download Laporan")
                if ds:
                    list_nama_staff = list(ds.values())
                    pilih_staff_dl = st.selectbox("Pilih Staff:", list_nama_staff)
                    file_target = get_nama_file_excel(pilih_staff_dl)
                    
                    if os.path.exists(file_target):
                        with open(file_target, "rb") as file:
                            st.download_button(label=f"📥 Download {pilih_staff_dl}", data=file, file_name=file_target, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                    else: st.warning("Belum ada laporan.")

                st.divider()
                st.error("⚠️ RESET SEMUA DATA (DANGER)")
                st.write("Menghapus: Staff, Menu, Lokasi, Surat Jalan, dan Semua Laporan.")
                
                with st.expander("🔴 Buka Menu Reset"):
                    password_reset = st.text_input("Masukkan Password Reset:", type="password")
                    
                    if st.button("🔥 PIKIA-PIKIA BANA LUU"):
                        if password_reset == PASSWORD_RESET: 
                            try:
                                files_db = [FILE_DB_GEROBAK, FILE_DB_STAFF, FILE_DB_MENU, FILE_DB_LOKASI, FILE_DB_SURAT_JALAN]
                                for fdb in files_db:
                                    if os.path.exists(fdb): os.remove(fdb)
                                
                                file_excel = glob.glob("LAPORAN_*.xlsx")
                                for f in file_excel: os.remove(f)
                                
                                st.success("✅ SYSTEM RESET BERHASIL!")
                                kirim_whatsapp("⚠️ *SYSTEM ALERT:* OWNER MELAKUKAN FULL RESET DATA.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Gagal Reset: {e}")
                        else:
                            st.error("⛔ Password Salah!")
                            
            with t6:
                st.subheader("🚚 Buat Surat Jalan Baru")
                if not LOKASI_SEKARANG:
                    st.warning("Belum ada lokasi gerobak.")
                else:
                    sj_lokasi = st.selectbox("Tujuan Gerobak:", list(LOKASI_SEKARANG.values()), key="sj_lokasi")
                    
                    st.write("**Pilih Barang & Jumlah yang Dikirim:**")
                    sj_stok_input = {}
                    
                    for kategori, items in MENU_SEKARANG.items():
                        with st.expander(f"📦 Kirim {kategori}", expanded=False):
                            cols = st.columns(2)
                            for i, (m, hrg) in enumerate(items.items()):
                                key_input = f"{kategori}_{m}"
                                with cols[i%2]: 
                                    val = st.number_input(f"{m}", min_value=0, value=0, key=f"sj_kirim_{key_input}")
                                    if val > 0: sj_stok_input[key_input] = val 

                    if st.button("Kirim Surat Jalan"):
                        if not sj_stok_input:
                            st.error("Daftar barang tidak boleh kosong! Isi minimal 1 barang.")
                        else:
                            db_sj = load_json(FILE_DB_SURAT_JALAN)
                            id_sj = f"SJ-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                            
                            sj_catatan_text = ""
                            for k_item, jml in sj_stok_input.items():
                                kat_split, nama_split = k_item.split('_', 1)
                                sj_catatan_text += f"\n▫️ [{kat_split}] {nama_split}: {jml}"

                            db_sj[id_sj] = {
                                "tanggal": get_wib_now().strftime("%Y-%m-%d %H:%M"),
                                "tujuan": sj_lokasi,
                                "barang_dict": sj_stok_input, 
                                "barang_text": sj_catatan_text, 
                                "status": "Menunggu Konfirmasi",
                                "penerima": "-"
                            }
                            save_json(FILE_DB_SURAT_JALAN, db_sj)
                            
                            tgl_sj = get_wib_now().strftime("%d-%m-%Y")
                            jam_sj = get_wib_now().strftime("%H:%M WIB")
                            kirim_whatsapp(f"🚚 *INFO SURAT JALAN BARU*\n📅 Tanggal: {tgl_sj}\n⏰ Waktu: {jam_sj}\n👤 Pengirim: {user} (Owner)\n📍 Tujuan: {sj_lokasi}\n\n*Barang Dikirim:*{sj_catatan_text}\n\n_Menunggu konfirmasi staff._")
                            st.success("Surat Jalan berhasil dikirim ke staff!")
                            st.rerun()

                st.divider()
                st.write("**Riwayat Surat Jalan Terakhir**")
                db_sj = load_json(FILE_DB_SURAT_JALAN)
                if db_sj:
                    for id_sj, data_sj in reversed(list(db_sj.items())):
                        status_icon = "⏳" if data_sj['status'] == "Menunggu Konfirmasi" else "✅"
                        with st.expander(f"{status_icon} {data_sj['tanggal']} | Tujuan: {data_sj['tujuan']}"):
                            st.write(f"**Barang:**{data_sj.get('barang_text', data_sj.get('barang', ''))}")
                            st.write(f"**Status:** {data_sj['status']} (Penerima: {data_sj['penerima']})")
                            if st.button(f"Hapus Riwayat", key=f"del_sj_{id_sj}"):
                                del db_sj[id_sj]
                                save_json(FILE_DB_SURAT_JALAN, db_sj)
                                st.rerun()
                else:
                    st.caption("Belum ada riwayat surat jalan.")

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
            else: st.error(f"⛔ SEDANG DIPAKAI: {shift_aktif_di_lokasi['pic']}")
        else: st.info(f"🟢 {pilihan_gerobak} Kosong.")

        # --- CEK SURAT JALAN UNTUK STAFF ---
        db_sj = load_json(FILE_DB_SURAT_JALAN)
        ada_surat_jalan = False
        
        for id_sj, data_sj in db_sj.items():
            if data_sj['tujuan'] == pilihan_gerobak and data_sj['status'] == "Menunggu Konfirmasi":
                ada_surat_jalan = True
                st.warning("🚚 **ADA BARANG MASUK DARI GUDANG!**")
                st.info(f"**Daftar Tambahan Stok Jualan:**{data_sj.get('barang_text', data_sj.get('barang', ''))}")
                
                if st.button("✅ Konfirmasi Terima Barang", key=f"terima_{id_sj}"):
                    data_sj['status'] = "Diterima"
                    data_sj['penerima'] = user
                    save_json(FILE_DB_SURAT_JALAN, db_sj)

                    pesan_tambahan_bot = ""
                    if is_saya_di_sini:
                        stok_aktif = db_gerobak[pilihan_gerobak].get('stok', {})
                        barang_masuk = data_sj.get('barang_dict', {})
                        
                        for k, v in barang_masuk.items():
                            if k in stok_aktif:
                                stok_aktif[k] += v  
                            else:
                                stok_aktif[k] = v   
                        
                        db_gerobak[pilihan_gerobak]['stok'] = stok_aktif
                        save_json(FILE_DB_GEROBAK, db_gerobak)
                        pesan_tambahan_bot = "\n\n_(Stok berhasil ditambahkan otomatis ke menu closing)_"

                    tgl_terima = get_wib_now().strftime("%d-%m-%Y")
                    jam_terima = get_wib_now().strftime("%H:%M WIB")
                    kirim_whatsapp(f"✅ *LAPORAN TERIMA BARANG*\n📅 Tanggal: {tgl_terima}\n⏰ Waktu: {jam_terima}\n👤 Penerima: {user}\n📍 Lokasi: {pilihan_gerobak}{pesan_tambahan_bot}")
                    st.success("Barang berhasil dikonfirmasi masuk!")
                    st.rerun()

        if ada_surat_jalan:
            st.error("⚠️ Anda wajib mengonfirmasi penerimaan Surat Jalan di atas sebelum bisa mengakses menu Gerobak.")
            st.stop() 

        # --- TABS BUKA/TUTUP TOKO STAFF ---
        t_op, t_cl = st.tabs(["☀️ BUKA TOKO", "🌙 TUTUP TOKO"])

        with t_op:
            if lokasi_lain_user: st.error("❌ Anda masih aktif di tempat lain.")
            elif is_lokasi_terisi and not is_saya_di_sini: st.error("🔒 Terkunci.")
            elif is_saya_di_sini: st.info("Toko sudah buka.")
            else:
                st.write("📝 **Persiapan Buka Toko (Input Stok)**")
                stok_input = {}
                
                for kategori, items in MENU_SEKARANG.items():
                    with st.expander(f"📦 Stok {kategori}", expanded=True):
                        cols = st.columns(2)
                        for i, (m, hrg) in enumerate(items.items()):
                            key_input = f"{kategori}_{m}"
                            with cols[i%2]: 
                                val = st.number_input(f"{m}", min_value=0, value=0, key=f"stok_{key_input}")
                                if val > 0: stok_input[key_input] = val 
                
                st.write("---")
                if st.button("🚀 BUKA SHIFT SEKARANG", key="btn_open"):
                    if not stok_input:
                        st.error("⚠️ Stok awal tidak boleh kosong! Wajib isi minimal 1 barang untuk buka toko.")
                    else:
                        tgl_skrg = get_wib_now().strftime("%d-%m-%Y")
                        jam_skrg_wib = get_wib_now().strftime("%H:%M WIB")
                        jam_masuk_db = get_wib_now().strftime("%H:%M")
                        
                        list_stok_text = ""
                        for k_item, jml in stok_input.items():
                            kat_split, nama_split = k_item.split('_', 1)
                            list_stok_text += f"\n📦 [{kat_split}] {nama_split}: {jml}"

                        d = {"tanggal": get_wib_now().strftime("%Y-%m-%d"), "jam_masuk": jam_masuk_db, "pic": user, "pin_pic": pin, "stok": stok_input}
                        db_gerobak[pilihan_gerobak] = d; save_json(FILE_DB_GEROBAK, db_gerobak)
                        
                        kirim_whatsapp(f"☀️ *LAPORAN OPENING SHIFT*\n📅 Tanggal: {tgl_skrg}\n⏰ Waktu: {jam_skrg_wib}\n👤 Nama: {user}\n📍 Lokasi: {pilihan_gerobak}\n\n*STOK AWAL:*{list_stok_text}")
                        st.success("Buka!"); st.rerun()

        with t_cl:
            if not is_saya_di_sini:
                if is_lokasi_terisi: st.error("⛔ Bukan shift Anda.")
                else: st.info("Toko belum dibuka.")
            else:
                st.write("📝 **Laporan Penjualan**")
                omzet_total = 0; list_penjualan_temporary = [] 
                
                for kategori, items in MENU_SEKARANG.items():
                    with st.expander(f"💰 Penjualan {kategori}", expanded=True):
                        for m, harga_satuan in items.items():
                            key_unik = f"{kategori}_{m}"
                            stok_awal = int(shift_aktif_di_lokasi['stok'].get(key_unik, 0))
                            
                            if stok_awal > 0:
                                sisa = st.number_input(f"Sisa {m} (Awal + Tambahan: {stok_awal})", max_value=stok_awal, min_value=0, key=f"sisa_{key_unik}")
                                terjual = stok_awal - sisa
                                omzet_item = terjual * harga_satuan
                                omzet_total += omzet_item
                                
                                list_penjualan_temporary.append({
                                    "KATEGORI": kategori, "ITEM": m, "HARGA": harga_satuan,
                                    "TERJUAL": terjual, "TIPE": "JUAL", "GEROBAK": pilihan_gerobak
                                })
                
                st.write("---")
                st.markdown(f"### 💰 Total Penjualan: {format_rupiah(omzet_total)}")
                
                c1, c2 = st.columns(2)
                uang_tunai = c1.number_input("Tunai", step=500, key="uang_tunai")
                uang_qris = c2.number_input("QRIS", step=500, key="uang_qris")
                catatan = st.text_area("Catatan", key="catatan_closing")
                
                total_setor = uang_tunai + uang_qris
                selisih = total_setor - omzet_total
                
                if selisih == 0:
                    st.success("✅ Uang Pas! Mantaaaaaaaaaaaaaap.")
                    if st.button("🔒 TUTUP SHIFT & KIRIM", key="btn_close"):
                        
                        with st.spinner("Memproses..."):
                            nama_file_excel = simpan_ke_excel_staff(
                                list_penjualan_temporary, user, uang_tunai, uang_qris, total_setor, catatan
                            )
                            
                            rincian_text = ""
                            for item in list_penjualan_temporary:
                                if item['TERJUAL'] > 0:
                                    rincian_text += f"\n▫️ [{item['KATEGORI']}] {item['ITEM']}: {item['TERJUAL']}"
                            if not rincian_text: rincian_text = "\n(Nihil)"

                            tgl_tutup = get_wib_now().strftime("%d-%m-%Y")
                            jam_tutup = get_wib_now().strftime("%H:%M WIB")

                            msg = (f"🌙 *LAPORAN CLOSING SHIFT*\n"
                                   f"📅 Tanggal: {tgl_tutup}\n"
                                   f"⏰ Waktu: {jam_tutup}\n"
                                   f"👤 Nama: {user}\n"
                                   f"📍 Lokasi: {pilihan_gerobak}\n\n"
                                   f"📊 *RINCIAN TERJUAL:*{rincian_text}\n\n"
                                   f"💵 *Tunai:* {format_rupiah(uang_tunai)}\n"
                                   f"💳 *QRIS:* {format_rupiah(uang_qris)}\n"
                                   f"💰 *Total Setor:* {format_rupiah(total_setor)}\n"
                                   f"📝 *Catatan:* {catatan}")

                            kirim_whatsapp(msg)
                            
                            if pilihan_gerobak in db_gerobak:
                                del db_gerobak[pilihan_gerobak]; save_json(FILE_DB_GEROBAK, db_gerobak)
                        
                        st.balloons(); st.success("Selesai!"); st.rerun()
                else:
                    st.error(f"⚠️ **ADA SELISIH: {format_rupiah(selisih)}**")
                    st.warning("Tombol kirim terkunci. Pastikan jumlah uang (Tunai + QRIS) SAMA PERSIS dengan Total Penjualan.")

    else: st.info("☝️☝️ Login ada di Kiri atas 👈👈")

if __name__ == "__main__":
    main()
