"""
OCR Engine Module
Mendukung:
1. RapidOCR (Lokal, OnnxRuntime, Cepat, Offline, Gratis)
2. Google Gemini Vision (Cloud AI, Sangat Akurat untuk label melengkung/bervariasi)
"""

import io
import os
import numpy as np
from PIL import Image

# Global cache for RapidOCR engine to avoid reloading model on every request
_RAPID_OCR_INSTANCE = None

def get_rapid_ocr():
    global _RAPID_OCR_INSTANCE
    if _RAPID_OCR_INSTANCE is None:
        from rapidocr_onnxruntime import RapidOCR
        _RAPID_OCR_INSTANCE = RapidOCR()
    return _RAPID_OCR_INSTANCE

def extract_text_rapid_ocr(image: Image.Image) -> str:
    """
    Ekstrak teks dari PIL Image menggunakan RapidOCR.
    Mengurutkan kotak teks secara vertikal & horizontal agar pembacaan paragraf rapi.
    """
    engine = get_rapid_ocr()
    
    # Convert PIL Image to RGB numpy array
    if image.mode != "RGB":
        image = image.convert("RGB")
    img_np = np.array(image)
    
    result, elapse = engine(img_np)
    
    if not result:
        return ""
    
    # result structure: [ [box_coords, text, score], ... ]
    # Sort boxes top-to-bottom, left-to-right
    # box_coords: [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
    def get_sort_key(item):
        box = item[0]
        y_min = min(pt[1] for pt in box)
        x_min = min(pt[0] for pt in box)
        return (y_min, x_min)
    
    sorted_items = sorted(result, key=get_sort_key)
    
    # Group items into lines based on vertical proximity
    lines = []
    current_line = []
    current_y = None
    line_threshold = 14  # pixel difference to consider as new line
    
    for item in sorted_items:
        box, text, score = item
        y_center = sum(pt[1] for pt in box) / 4.0
        x_center = sum(pt[0] for pt in box) / 4.0
        
        if current_y is None:
            current_y = y_center
            current_line.append((x_center, text))
        elif abs(y_center - current_y) <= line_threshold:
            current_line.append((x_center, text))
        else:
            # Sort current line left to right
            current_line.sort(key=lambda x: x[0])
            lines.append(" ".join([w[1] for w in current_line]))
            current_line = [(x_center, text)]
            current_y = y_center
            
    if current_line:
        current_line.sort(key=lambda x: x[0])
        lines.append(" ".join([w[1] for w in current_line]))
        
    extracted_text = "\n".join(lines)
    return extracted_text.strip()

def extract_with_gemini_vision(image: Image.Image, api_key: str, model_name: str = "gemini-3.8-flash") -> dict:
    """
    Ekstrak teks dan terjemahan menggunakan Google Gemini 3.8 Flash Vision AI.
    Menghasilkan struktur lengkap label kemasan:
    {
        "product_name": str,
        "net_weight": str,
        "indonesian_text": str,
        "english_text": str,
        "ingredients_id": str,
        "ingredients_en": str,
        "distributor_header": str,
        "distributor_info": str,
        "nutrition_id": str,
        "nutrition_en": str,
        "allergen_id": str,
        "allergen_en": str
    }
    """
    from google import genai
    from google.genai import types
    
    client = genai.Client(api_key=api_key)
    
    # Simpan gambar ke buffer bytes JPEG
    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='JPEG', quality=95)
    img_bytes = img_byte_arr.getvalue()
    
    prompt = """
    Anda adalah asisten AI ahli dalam membaca dan menerjemahkan label kemasan pangan (Food Packaging Vision & Compliance Specialist).
    Analisis gambar label kemasan ini secara sangat teliti.
    
    Tugas Anda:
    1. Baca nama produk dan berat bersih (netto) jika tertera.
    2. Ekstrak seluruh daftar komposisi (ingredients) dalam Bahasa Indonesia asli.
    3. Terjemahkan daftar komposisi ke dalam Bahasa Inggris baku (FDA/Codex Alimentarius).
    4. Baca informasi produsen / importir / distributor jika ada (nama PT/perusahaan, alamat, telepon, email).
    5. Baca peringatan alergen jika ada.
    
    Format respon HANYA dalam format JSON valid (tanpa teks pengantar) dengan struktur:
    {
        "product_name": "Nama produk jika tertera (misal: MILO CUBE)",
        "net_weight": "Berat bersih/netto jika ada (misal: 67.5GR atau 200g)",
        "indonesian_text": "Teks lengkap komposisi dalam Bahasa Indonesia asli",
        "english_text": "Full translation of ingredients list in English",
        "ingredients_id": "Daftar bahan dalam Bahasa Indonesia",
        "ingredients_en": "List of ingredients in professional English",
        "distributor_header": "IMPORTED BY : atau DISTRIBUTED BY : atau MANUFACTURED BY : (sesuai yang tertera)",
        "distributor_info": "Nama perusahaan, telepon, kontak distributor/importir per baris",
        "allergen_id": "Peringatan alergen dalam Bahasa Indonesia jika ada",
        "allergen_en": "Allergen warning in English if present",
        "nutrition_id": "Informasi nilai gizi jika ada",
        "nutrition_en": "Nutrition facts in English if present"
    }
    """
    
    # Hanya gunakan model aktif yang valid (hindari gemini-2.0 dan gemini-2.5 yang sudah 404/deprecated)
    active_models = ["gemini-3.8-flash", "gemini-3.7-flash", "gemini-flash-latest"]
    models_to_try = [model_name] + [m for m in active_models if m != model_name]
    
    response = None
    last_err = None
    
    for mod in models_to_try:
        try:
            response = client.models.generate_content(
                model=mod,
                contents=[
                    types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"),
                    prompt
                ],
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    response_mime_type="application/json"
                )
            )
            if response and response.text:
                break
        except Exception as e:
            last_err = e
            continue
            
    if response is None:
        err_msg = str(last_err)
        if "503" in err_msg or "UNAVAILABLE" in err_msg or "high demand" in err_msg.lower():
            raise RuntimeError("Server Google Gemini saat ini sedang mengalami lonjakan trafik tinggi (High Demand Spikes). Silakan coba lagi beberapa saat atau gunakan Mesin Lokal.")
        raise RuntimeError(f"Gagal memanggil Gemini 3.8 API: {err_msg}")
    
    import json
    raw_text = response.text.strip()
    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`")
        if raw_text.startswith("json"):
            raw_text = raw_text[4:].strip()
            
    try:
        data = json.loads(raw_text)
        return data
    except Exception:
        return {
            "product_name": "Produk",
            "net_weight": "",
            "indonesian_text": raw_text,
            "english_text": raw_text,
            "ingredients_id": raw_text,
            "ingredients_en": raw_text,
            "distributor_header": "",
            "distributor_info": "",
            "allergen_id": "",
            "allergen_en": "",
            "nutrition_id": "",
            "nutrition_en": ""
        }


def extract_nutrition_facts_vision(image: Image.Image, api_key: str, model_name: str = "gemini-3.8-flash") -> dict:
    """
    Ekstrak tabel informasi nilai gizi (Nutrition Facts) menggunakan Google Gemini Vision AI.
    Menghasilkan data terstruktur untuk tabel nilai gizi bilingual standar BPOM & FDA.
    """
    from google import genai
    from google.genai import types
    import json
    
    client = genai.Client(api_key=api_key)
    
    # Simpan gambar ke buffer bytes JPEG
    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='JPEG', quality=95)
    img_bytes = img_byte_arr.getvalue()
    
    prompt = """
    Anda adalah asisten AI spesialis pembacaan dan kepatuhan tabel Informasi Nilai Gizi kemasan pangan (Food Nutrition Facts Specialist).
    Analisis gambar tabel Informasi Nilai Gizi (Nutrition Facts) ini dengan sangat teliti dan akurat.
    
    Tugas Anda:
    1. Baca nama produk atau varian jika tertera di sekitar tabel gizi.
    2. Ekstrak Takaran Saji (Serving Size) dalam Bahasa Indonesia dan Bahasa Inggris (misal: "30 g (3 butir)").
    3. Ekstrak Jumlah Sajian per Kemasan (Servings Per Container/Pack).
    4. Ekstrak semua baris Energi / Kalori (misal: Energi Total, Energi dari Lemak, Energi dari Lemak Jenuh jika ada) ke dalam array "energy_items".
    5. PENTING - BANYAKNYA BARIS & URUTAN: Ekstrak HANYA baris-baris zat gizi yang BENAR-BENAR TERCANTUM pada gambar tabel nilai gizi ini ke dalam array "nutrients". JANGAN PERNAH mengarang atau menambahkan zat gizi yang tidak tertulis pada gambar. Banyaknya baris harus persis sama dengan jumlah baris yang ada di gambar label kemasan. Urutan baris dalam array "nutrients" harus persis urut dari atas ke bawah mengikuti gambar label kemasan aslinya.
    6. Ekstrak daftar komposisi bahan baku (Ingredients) dalam Bahasa Inggris HURUF KAPITAL jika terlihat pada kemasan.
    7. Ekstrak informasi distributor / importir jika terlihat pada kemasan (misal: "IMPORTED BY :", nama perusahaan distributor, telepon, email).
    8. Ekstrak catatan kaki persentase AKG (Percent Daily Values footnote) dalam Bahasa Indonesia dan Inggris jika ada.
    9. Berikan teks mentah asli Bahasa Indonesia (raw_nutrition_id) dan terjemahan Bahasa Inggris (raw_nutrition_en).
    
    Format respon HANYA dalam JSON valid:
    {
        "product_name": "Nama produk jika tertera",
        "serving_size_id": "Takaran saji (misal: 30 g / 3 butir)",
        "serving_size_en": "Serving size in English (e.g. 30 g / 3 pieces)",
        "servings_per_pack": "Jumlah sajian per kemasan (misal: 2 sajian / 2 servings)",
        "serving_text_id": "Teks lengkap takaran saji dan sajian per kemasan persis seperti tertulis di kemasan (misal: TAKARAN SAJI: 12 g\\n20 Sajian per kemasan)",
        "serving_text_en": "Terjemahan bahasa Inggris dari teks takaran saji (misal: SERVING SIZE: 12 g\\n20 Servings per container)",
        "calories_total": "Energi total jika ada (misal: 60 kkal)",
        "calories_fat": "Energi dari lemak jika ada",
        "energy_items": [
            {
                "name_id": "Energi total",
                "name_en": "Total Energy",
                "amount": "60 kkal"
            }
        ],
        "ingredients_en": "Daftar komposisi bahan baku dalam HURUF KAPITAL bahasa Inggris jika ada",
        "distributor_header": "Header importir/distributor jika ada (misal: IMPORTED BY :)",
        "distributor_info": "Nama dan kontak importir/distributor jika ada",
        "nutrients": [
            {
                "name_id": "Nama Zat Gizi persis di gambar",
                "name_en": "Nutrient Name in English",
                "amount": "Jumlah beserta satuan (misal: 1000 mg)",
                "daily_value": "Persentase AKG / DV jika ada (misal: 1110%), jika tidak ada beri '-'"
            }
        ],
        "footnote_id": "Catatan kaki AKG jika ada di kemasan",
        "footnote_en": "AKG / Percent Daily Values footnote in English if any",
        "raw_nutrition_id": "Teks mentah tabel nilai gizi baris per baris",
        "raw_nutrition_en": "Full English translation of nutrition facts lines"
    }
    """
    
    active_models = ["gemini-3.8-flash", "gemini-3.7-flash", "gemini-flash-latest"]
    models_to_try = [model_name] + [m for m in active_models if m != model_name]
    
    response = None
    last_err = None
    
    for mod in models_to_try:
        try:
            response = client.models.generate_content(
                model=mod,
                contents=[
                    types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"),
                    prompt
                ],
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    response_mime_type="application/json"
                )
            )
            if response and response.text:
                break
        except Exception as e:
            last_err = e
            continue
            
    if response is None:
        err_msg = str(last_err)
        if "503" in err_msg or "UNAVAILABLE" in err_msg or "high demand" in err_msg.lower():
            raise RuntimeError("Server Google Gemini sedang sibuk. Silakan coba beberapa saat lagi atau gunakan Mesin Lokal.")
        raise RuntimeError(f"Gagal memanggil Gemini Vision API: {err_msg}")
        
    raw_text = response.text.strip()
    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`")
        if raw_text.startswith("json"):
            raw_text = raw_text[4:].strip()
            
    try:
        data = json.loads(raw_text)
        return data
    except Exception:
        return {
            "product_name": "",
            "serving_size_id": "",
            "serving_size_en": "",
            "servings_per_pack": "",
            "calories_total": "",
            "calories_fat": "",
            "energy_items": [],
            "ingredients_en": "",
            "distributor_header": "",
            "distributor_info": "",
            "nutrients": [],
            "footnote_id": "",
            "footnote_en": "",
            "raw_nutrition_id": raw_text,
            "raw_nutrition_en": raw_text
        }


NUTRITION_TRANSLATIONS = {
    "energi total": "Total Energy",
    "energi dari lemak": "Calories from Fat",
    "energi dari lemak jenuh": "Calories from Saturated Fat",
    "lemak total": "Total Fat",
    "lemak jenuh": "Saturated Fat",
    "lemak trans": "Trans Fat",
    "kolesterol": "Cholesterol",
    "protein": "Protein",
    "karbohidrat total": "Total Carbohydrate",
    "serat pangan": "Dietary Fiber",
    "serat": "Dietary Fiber",
    "gula total": "Total Sugars",
    "gula": "Total Sugars",
    "garam": "Sodium",
    "natrium": "Sodium",
    "garam (natrium)": "Sodium",
    "kalium": "Potassium",
    "kalsium": "Calcium",
    "vitamin c": "Vitamin C",
    "vitamin a": "Vitamin A",
    "vitamin d": "Vitamin D",
    "vitamin b1": "Vitamin B1 (Thiamin)",
    "vitamin b2": "Vitamin B2 (Riboflavin)",
    "vitamin b3": "Vitamin B3 (Niacin)",
    "vitamin b6": "Vitamin B6",
    "vitamin b12": "Vitamin B12",
    "niasin": "Niacin",
    "zat besi": "Iron",
    "seng": "Zinc",
    "magnesium": "Magnesium",
    "fosfor": "Phosphorus",
    "asam folat": "Folate"
}


def parse_nutrition_facts_text(raw_text: str) -> dict:
    """
    Ekstrak baris takaran saji, energi, dan zat gizi dari teks hasil OCR lokal (RapidOCR).
    Membaca banyaknya baris sesuai dengan teks yang terbaca.
    """
    import re
    lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
    
    energy_items = []
    nutrients = []
    serving_lines = []
    footnote_lines = []
    
    energy_kw = ["energi", "energy", "kalori", "calorie", "calories"]
    skip_kw = ["informasi nilai gizi", "nutrition facts", "jumlah per sajian", "amount per serving", "% akg", "% dv"]
    
    for l in lines:
        lower = l.lower()
        if any(lower.startswith(sk) or lower == sk for sk in skip_kw):
            continue
        if any(sk in lower for sk in ["takaran saji", "serving size", "sajian per kemasan", "servings per"]):
            serving_lines.append(l)
            continue
        if lower.startswith("*") or "persen akg" in lower or "daily values" in lower or "kebutuhan energi" in lower:
            footnote_lines.append(l)
            continue
            
        if any(ek in lower for ek in energy_kw):
            amt_match = re.search(r'(\d+[\d.,]*\s*(?:kkal|kcal|kj|cal|g)?)$', l, re.IGNORECASE)
            if amt_match:
                amt = amt_match.group(1).strip()
                name_id = l[:amt_match.start()].strip(" :-").strip()
            else:
                parts = l.rsplit(None, 1)
                if len(parts) == 2:
                    name_id, amt = parts[0], parts[1]
                else:
                    name_id, amt = l, ""
            
            n_lower = name_id.lower()
            if "total" in n_lower:
                name_en = "Total Energy"
            elif "lemak jenuh" in n_lower or "saturated" in n_lower:
                name_en = "Calories from Saturated Fat"
            elif "lemak" in n_lower or "fat" in n_lower:
                name_en = "Calories from Fat"
            else:
                name_en = name_id
            
            energy_items.append({
                "Nama Energi (ID)": name_id,
                "Energy Name (EN)": name_en,
                "Nilai (Amount)": amt
            })
            continue
            
        # Baris Nutrisi
        dv = "-"
        dv_match = re.search(r'(\d+[\d.,]*\s*%|-)$', l)
        rem = l
        if dv_match:
            dv = dv_match.group(1).strip()
            rem = l[:dv_match.start()].strip()
            
        amt_match = re.search(r'(\d+[\d.,]*\s*(?:mg|mcg|µg|g|iu|ml|l))$', rem, re.IGNORECASE)
        if amt_match:
            amt = amt_match.group(1).strip()
            name_id = rem[:amt_match.start()].strip(" :-").strip()
        else:
            parts = rem.rsplit(None, 1)
            if len(parts) == 2 and re.match(r'^\d', parts[1]):
                name_id, amt = parts[0], parts[1]
            else:
                name_id = rem
                amt = ""
                
        if name_id and len(name_id) > 1:
            n_lower = name_id.strip().lower()
            name_en = name_id
            for k, v_en in NUTRITION_TRANSLATIONS.items():
                if k in n_lower:
                    name_en = v_en
                    break
            
            nutrients.append({
                "Nutrisi (ID)": name_id,
                "Nutrient (EN)": name_en,
                "Jumlah (Amount)": amt,
                "% AKG / DV": dv
            })
            
    return {
        "energy_items": energy_items,
        "nutrients": nutrients,
        "serving_lines": serving_lines,
        "footnote": "\n".join(footnote_lines)
    }

