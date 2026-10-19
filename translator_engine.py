"""
Translator Engine Module
Menerjemahkan teks komposisi dan label pangan dari Bahasa Indonesia ke Bahasa Inggris.
Mendukung:
1. MyMemoryTranslator & GoogleTranslator (Gratis)
2. Gemini AI (Jika ada API Key)
3. Food & Packaging Glossary Post-Processing
"""

import re
from deep_translator import MyMemoryTranslator, GoogleTranslator

# Kamus istilah pangan & kemasan standar regulasi (BPOM / FDA / Codex)
FOOD_GLOSSARY = {
    r"\bkomposisi\b": "Ingredients",
    r"\bbahan-bahan\b": "Ingredients",
    r"\binformasi nilai gizi\b": "Nutrition Facts",
    r"\btakaran saji\b": "Serving Size",
    r"\bjumlah sajian per kemasan\b": "Servings Per Container",
    r"\bjumlah per sajian\b": "Amount Per Serving",
    r"\benergi total\b": "Total Calories",
    r"\benergi dari lemak\b": "Calories from Fat",
    r"\blemak total\b": "Total Fat",
    r"\blemak jenuh\b": "Saturated Fat",
    r"\bkolesterol\b": "Cholesterol",
    r"\bprotein\b": "Protein",
    r"\bkarbohidrat total\b": "Total Carbohydrate",
    r"\bserat pangan\b": "Dietary Fiber",
    r"\bgula total\b": "Total Sugars",
    r"\bgaram\s*\(\s*natrium\s*\)": "Sodium",
    r"\bnatrium\b": "Sodium",
    r"\bperingatan alergen\b": "Allergen Warning",
    r"\bmengandung alergen\b": "Contains allergens",
    r"\bpetunjuk penyimpanan\b": "Storage Instructions",
    r"\bsimpan di tempat sejuk dan kering\b": "Store in a cool, dry place",
    r"\bhindari sinar matahari langsung\b": "Avoid direct sunlight",
    r"\bdiproduksi oleh\b": "Manufactured by",
    r"\bdidistribusikan oleh\b": "Distributed by",
    r"\bbaik digunakan sebelum\b": "Best Before",
    r"\bkode produksi\b": "Batch Code / Production Code",
    r"\bberat bersih\b": "Net Weight",
    r"\bisi bersih\b": "Net Content",
    r"\bminyak kelapa sawit\b": "palm oil",
    r"\bminyak nabati\b": "vegetable oil",
    r"\btepung terigu\b": "wheat flour",
    r"\bgula pasir\b": "sugar",
    r"\bcokelat bubuk\b": "cocoa powder",
    r"\bsusu bubuk skim\b": "skimmed milk powder",
    r"\bpengemulsi lesitin kedelai\b": "soy lecithin emulsifier",
    r"\bperisa sintetik\b": "synthetic flavoring",
    r"\bperisa alami\b": "natural flavoring",
    r"\bpewarna makanan\b": "food coloring",
    r"\bgaram beriodium\b": "iodized salt",
    r"\bantioksidan tokoferol\b": "tocopherol antioxidant",
    r"\bpengatur keasaman\b": "acidity regulator",
    r"\bpengembang\b": "raising agent"
}

def translate_indonesian_to_english(text: str, engine_choice: str = "auto", api_key: str = "", model_name: str = "gemini-3.8-flash") -> str:
    """
    Menerjemahkan teks dari Bahasa Indonesia ke Bahasa Inggris.
    """
    if not text or not text.strip():
        return ""

    text = text.strip()

    # Jika pengguna memilih Gemini dan ada API Key
    if engine_choice == "gemini" and api_key:
        try:
            return translate_with_gemini(text, api_key, model_name=model_name)
        except Exception as e:
            print(f"Gemini translation fallback due to: {e}")

    # Fallback / Default: Mesin Terjemahan Bebas (MyMemory / GoogleTranslator)
    lines = text.split("\n")
    translated_lines = []

    for line in lines:
        line_clean = line.strip()
        if not line_clean:
            translated_lines.append("")
            continue

        # Coba terjemahkan line per line
        trans_line = _translate_chunk(line_clean)
        translated_lines.append(trans_line)

    result = "\n".join(translated_lines)
    return result

def _translate_chunk(text_chunk: str) -> str:
    """
    Menerjemahkan potongan teks dengan failover yang kuat.
    """
    # 1. Coba MyMemoryTranslator
    try:
        translator = MyMemoryTranslator(source='id-ID', target='en-GB')
        translated = translator.translate(text_chunk)
        if translated and not translated.lower().startswith("my memory"):
            return translated
    except Exception:
        pass

    # 2. Coba GoogleTranslator
    try:
        translator = GoogleTranslator(source='id', target='en')
        translated = translator.translate(text_chunk)
        if translated:
            return translated
    except Exception:
        pass

    # 3. Fallback: terapkan kamus istilah langsung
    fallback_text = text_chunk
    for pattern, replacement in FOOD_GLOSSARY.items():
        fallback_text = re.sub(pattern, replacement, fallback_text, flags=re.IGNORECASE)
    return fallback_text

def translate_with_gemini(text: str, api_key: str, model_name: str = "gemini-3.8-flash") -> str:
    """
    Terjemahan mendalam menggunakan Gemini 3.8 yang memahami regulasi label pangan internasional.
    """
    from google import genai
    client = genai.Client(api_key=api_key)
    
    prompt = f"""
    Anda adalah ahli regulasi label kemasan pangan internasional (FDA / EFSA / Codex Alimentarius).
    Tolong terjemahkan teks label kemasan produk berikut dari Bahasa Indonesia ke Bahasa Inggris dengan standar baku internasional yang tepat.
    Pertahankan tata letak baris, persentase bahan, peringatan alergen, dan nama bahan kimia pangan sesuai konvensi bahasa Inggris.
    
    Teks Bahasa Indonesia:
    \"\"\"{text}\"\"\"
    
    Keluarkan HANYA teks hasil terjemahan dalam Bahasa Inggris:
    """
    active_models = ["gemini-3.8-flash", "gemini-3.7-flash", "gemini-flash-latest"]
    models_to_try = [model_name] + [m for m in active_models if m != model_name]
    response = None
    last_err = None
    
    for mod in models_to_try:
        try:
            response = client.models.generate_content(
                model=mod,
                contents=prompt
            )
            if response and response.text:
                return response.text.strip()
        except Exception as e:
            last_err = e
            continue
            
    raise RuntimeError(f"Gemini translation error: {last_err}")


def translate_serving_text(text: str) -> str:
    """
    Menerjemahkan teks takaran saji & jumlah sajian ke standar internasional (FDA / Codex).
    Mendukung format bebas penulisan biasa, misal:
    'TAKARAN SAJI: 12 g \n 20 Sajian' -> 'SERVING SIZE: 12 g \n 20 Servings per container'
    """
    if not text or not text.strip():
        return ""
    lines = text.strip().splitlines()
    res = []
    for line in lines:
        l = line.strip()
        if not l:
            res.append("")
            continue
        
        orig_l = l
        
        # 1. Takaran saji
        l = re.sub(r'^(TAKARAN\s+SAJI)(\s*[:\-])?', r'SERVING SIZE\2', l, flags=re.IGNORECASE)
        
        # 2. Jumlah sajian per kemasan / per wadah
        l = re.sub(r'^(JUMLAH\s+SAJIAN\s+PER\s+KEMASAN)(\s*[:\-])?', r'SERVINGS PER PACK\2', l, flags=re.IGNORECASE)
        l = re.sub(r'^(JUMLAH\s+SAJIAN\s+PER\s+WADAH)(\s*[:\-])?', r'SERVINGS PER CONTAINER\2', l, flags=re.IGNORECASE)
        l = re.sub(r'^(JUMLAH\s+SAJIAN)(\s*[:\-])?', r'SERVINGS PER PACK\2', l, flags=re.IGNORECASE)
        l = re.sub(r'^(SAJIAN\s+PER\s+KEMASAN)(\s*[:\-])?', r'SERVINGS PER PACK\2', l, flags=re.IGNORECASE)
        
        # 3. '20 Sajian' -> '20 Servings per container' or '20 Servings'
        l = re.sub(r'^(\d+)\s*sajian\s*(per\s*kemasan)?$', r'\1 Servings per container', l, flags=re.IGNORECASE)
        l = re.sub(r'^(\d+)\s*sajian\s*per\s*wadah$', r'\1 Servings per container', l, flags=re.IGNORECASE)
        l = re.sub(r'\b(\d+)\s*sajian\b', r'\1 Servings', l, flags=re.IGNORECASE)
        
        # 4. Units / packaging terms with plural support
        l = re.sub(r'(\d+)\s*botol\b', lambda m: f"{m.group(1)} " + ("bottle" if m.group(1) == "1" else "bottles"), l, flags=re.IGNORECASE)
        l = re.sub(r'\bbotol\b', 'bottle', l, flags=re.IGNORECASE)
        l = re.sub(r'(\d+)\s*kaleng\b', lambda m: f"{m.group(1)} " + ("can" if m.group(1) == "1" else "cans"), l, flags=re.IGNORECASE)
        l = re.sub(r'\bkaleng\b', 'can', l, flags=re.IGNORECASE)
        l = re.sub(r'(\d+)\s*bungkus\b', lambda m: f"{m.group(1)} " + ("pack" if m.group(1) == "1" else "packs"), l, flags=re.IGNORECASE)
        l = re.sub(r'\bbungkus\b', 'pack', l, flags=re.IGNORECASE)
        l = re.sub(r'(\d+)\s*(?:kantung|kantong)\b', lambda m: f"{m.group(1)} " + ("sachet" if m.group(1) == "1" else "sachets"), l, flags=re.IGNORECASE)
        l = re.sub(r'\b(?:kantung|kantong)\b', 'sachet', l, flags=re.IGNORECASE)
        l = re.sub(r'(\d+)\s*keping\b', lambda m: f"{m.group(1)} " + ("piece" if m.group(1) == "1" else "pieces"), l, flags=re.IGNORECASE)
        l = re.sub(r'\bkeping\b', 'pieces', l, flags=re.IGNORECASE)
        l = re.sub(r'(\d+)\s*porsi\b', lambda m: f"{m.group(1)} " + ("serving" if m.group(1) == "1" else "servings"), l, flags=re.IGNORECASE)
        l = re.sub(r'\bporsi\b', 'serving', l, flags=re.IGNORECASE)
        l = re.sub(r'(\d+)\s*sendok\s+makan\b', lambda m: f"{m.group(1)} " + ("tablespoon" if m.group(1) == "1" else "tablespoons"), l, flags=re.IGNORECASE)
        l = re.sub(r'\bsendok\s+makan\b', 'tablespoon', l, flags=re.IGNORECASE)
        l = re.sub(r'(\d+)\s*sendok\s+teh\b', lambda m: f"{m.group(1)} " + ("teaspoon" if m.group(1) == "1" else "teaspoons"), l, flags=re.IGNORECASE)
        l = re.sub(r'\bsendok\s+teh\b', 'teaspoon', l, flags=re.IGNORECASE)
        l = re.sub(r'\bsekitar\b', 'About', l, flags=re.IGNORECASE)
        l = re.sub(r'\bkurang\s+lebih\b', 'Approx.', l, flags=re.IGNORECASE)
        
        # If no regex altered the line, try _translate_chunk
        if l == orig_l:
            try:
                trans = _translate_chunk(orig_l)
                if trans:
                    l = trans
            except Exception:
                pass
        
        res.append(l)
    return "\n".join(res)

