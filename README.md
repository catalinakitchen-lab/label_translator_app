# 🏷️ Aplikasi Pemindai & Penerjemah Label Kemasan ke PDF (Bilingual ID -> EN)

Aplikasi berbasis web untuk membaca teks komposisi, bahan baku, informasi gizi, dan peringatan alergen pada kemasan produk makanan/barang, menerjemahkannya secara otomatis dari **Bahasa Indonesia ke Bahasa Inggris**, serta mengekspornya ke dalam dokumen **PDF Spesifikasi Ekspor Bilingual** yang profesional.

---

## ✨ Fitur Utama

1. **Fleksibilitas Input & Pemotongan Gambar**:
   - 📁 **Unggah File**: Mendukung format JPG, JPEG, PNG, WEBP, BMP.
   - 📸 **Kamera Langsung**: Ambil foto label kemasan langsung dari webcam laptop atau smartphone.
   - ✂️ **Fitur Pemotong Area Label (Interactive Cropper)**: Kotak potong interaktif yang dapat digeser dan diubah ukurannya untuk memilih hanya area tabel komposisi/informasi gizi saja, membuang latar belakang foto yang tidak perlu agar OCR jauh lebih cepat dan akurat.
   - 🔄 **Fitur Rotasi Gambar**: Memutar foto 90°, 180°, 270° jika hasil jepretan kamera miring atau terbalik.
   - 🧪 **Preset Contoh Label**: Uji coba 1-klik dengan contoh label kemasan (Meses Cokelat & Biskuit Gandum).

2. **Pilihan Mesin OCR & AI Vision**:
   - ✨ **Mode Cloud AI (Google Gemini 3.8 Flash Vision)**:
     - Menggunakan model multimodal generasi terbaru **Google Gemini 3.8 Flash**.
     - Sangat akurat dalam membaca teks kemasan yang melengkung, font tulisan tangan/dekoratif, kemasan miring, dan foto dengan pencahayaan rendah.
     - Menganalisis sekaligus mengekstrak secara otomatis: nama produk, berat bersih (netto), komposisi (ID & EN), informasi importir/distributor, dan peringatan alergen.
     - Pilihan versi model fleksibel: `gemini-3.8-flash`, `gemini-2.5-flash`, `gemini-2.0-flash`.
   - 🚀 **Mode Lokal (RapidOCR - Gratis & Cepat)**:
     - 100% Offline, gratis tanpa batas, dan tanpa memerlukan API Key.
     - Menggunakan model ONNX yang berjalan langsung di komputer lokal.

3. **Editor Interaktif Dua Kolom (Bilingual Editor)**:
   - Kolom kiri: Teks Asli Bahasa Indonesia (dapat dikoreksi langsung jika ada karakter kemasan yang buram).
   - Kolom kanan: Terjemahan Bahasa Inggris (dapat diedit sesuai terminologi ekspor yang diinginkan).
   - Tombol **"🔄 Terjemahkan Ulang"** yang otomatis mengupdate bahasa Inggris jika teks Indonesia disunting.
   - Input khusus untuk **Peringatan Alergen** (*Allergen Information*).

4. **Ekspor Dokumen PDF Format Stiker Kemasan & Lembar Spesifikasi**:
   - 🏷️ **Format Stiker Cetak Kemasan (Sesuai Standar Stiker Milo Cube)**:
     - Menggunakan font resmi **GothamOffice-Bold** (tebal, modern, dan geometris persis seperti contoh kemasan internasional).
     - Teks tebal hitam di atas putih (bold sans-serif), rapi dan jelas.
     - Pilihan ukuran stiker:
       - **`3x5 cm`** (Stiker Produk Kecil - 30x50 mm)
       - **`4x6 cm`** (Stiker Standar Kemasan - 40x60 mm)
       - **`5x7 cm`** (Stiker Sedang - 50x70 mm)
       - **`3x5 inch`** & **`4x6 inch`** (Label Thermal / Pengiriman Ekspor)
       - **`Kustom (mm)`** (Atur panjang & lebar sendiri)
     - **Sistem Auto-Fit 1 Halaman**: Memastikan teks komposisi pas tercetak dalam 1 halaman stiker tanpa meluber.
     - Pratinjau visual real-time langsung di layar sebelum mengunduh.
     - Mendukung format huruf kapital semua (**UPPERCASE**) dan garis potong stiker (**Border**).
     - Field khusus untuk kontak distributor/importir (`IMPORTED BY :`, `DISTRIBUTED BY :`, `MANUFACTURED BY :`).
   - 📋 **Format Lembar Dokumen Spesifikasi A4 (Bilingual)**:
     - Dokumen arsip komparatif bilingual lengkap dengan foto kemasan, tabel perbandingan bahan, peringatan alergen, dan nomor halaman dinamis.
     - Tombol unduh instan berkas **PDF** dan berkas teks **TXT**.

---

## 🚀 Cara Menjalankan Aplikasi

### Cara 1: Menggunakan File Shortcut (Paling Mudah)
Cukup **klik ganda (double-click)** pada file:
👉 `JALANKAN_LABEL_TRANSLATOR.bat` (di folder utama `e:\DATA LOUIS\LINTAS`)  
atau  
👉 `label_translator_app\Jalankan_Aplikasi.bat`

Browser akan otomatis terbuka menampilkan aplikasi di:
`http://localhost:8501`

### Cara 2: Melalui Terminal / PowerShell
```powershell
cd "e:\DATA LOUIS\LINTAS\label_translator_app"
python -m streamlit run app.py
```

---

## 📋 Struktur File

```
E:\DATA LOUIS\LINTAS\
│
├── JALANKAN_LABEL_TRANSLATOR.bat   <-- File launcher 1-klik untuk pengguna
│
└── label_translator_app\
    ├── app.py                      <-- Antarmuka Streamlit Web UI
    ├── ocr_engine.py               <-- Mesin ekstraksi teks (RapidOCR & Gemini Vision)
    ├── translator_engine.py        <-- Mesin terjemahan & kamus istilah pangan
    ├── pdf_generator.py            <-- Pembuat dokumen PDF bilingual ReportLab
    ├── Jalankan_Aplikasi.bat       <-- Launcher di dalam folder
    ├── requirements.txt            <-- Daftar dependensi pustaka Python
    ├── .env                        <-- Penyimpanan Gemini API Key (opsional)
    └── README.md                   <-- Dokumentasi petunjuk penggunaan
```

---

## 🛠️ Persyaratan Sistem & Pustaka
Aplikasi ini menggunakan Python 3.11 dan library berikut:
- `streamlit`
- `rapidocr_onnxruntime`
- `deep-translator`
- `reportlab`
- `pillow`
- `google-genai`
- `python-dotenv`
