"""
Aplikasi Web: Pengubah & Penerjemah Label Kemasan (Image to PDF & Translate EN)
Framework: Streamlit
Fitur:
- OCR Gambar Label Kemasan (RapidOCR Lokal / Gemini Vision AI)
- Terjemahan Otomatis Bahasa Indonesia -> Bahasa Inggris
- Editor Interaktif Bilingual (ID & EN)
- Ekspor Dokumen PDF Profesional (ReportLab)
"""

import io
import os
import hashlib
import base64
import html
from pathlib import Path
import streamlit as st
from PIL import Image
from dotenv import load_dotenv
from streamlit_cropper import st_cropper

# Kredensial Akun Internal Kantor (CV Lintas Tujuh Benua)
INTERNAL_USERS = {
    "admin": {
        "password_hash": hashlib.sha256(b"lintas2026").hexdigest(),
        "name": "Administrator Kantor",
        "role": "Admin",
    },
    "staff": {
        "password_hash": hashlib.sha256(b"kantor123").hexdigest(),
        "name": "Staff Operasional",
        "role": "Staff",
    },
}

def verify_credentials(username: str, password: str):
    """Verifikasi ID Pengguna dan Kata Sandi akun internal kantor."""
    u = username.strip().lower()
    p_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
    if u in INTERNAL_USERS and INTERNAL_USERS[u]["password_hash"] == p_hash:
        return True, INTERNAL_USERS[u]["name"], INTERNAL_USERS[u]["role"]
    # Fallback cek st.secrets jika pengguna menambah akun via secrets.toml
    try:
        if "internal_users" in st.secrets and u in st.secrets["internal_users"]:
            if str(st.secrets["internal_users"][u]) == password:
                return True, u.title(), "User"
    except Exception:
        pass
    return False, None, None

# Muat environment variable dari .env jika ada
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

# Sinkronkan GEMINI_API_KEY dari st.secrets jika berjalan di Streamlit Cloud
try:
    if "GEMINI_API_KEY" in st.secrets and st.secrets["GEMINI_API_KEY"]:
        os.environ["GEMINI_API_KEY"] = str(st.secrets["GEMINI_API_KEY"]).strip()
except Exception:
    pass


import pandas as pd
from ocr_engine import extract_text_rapid_ocr, extract_with_gemini_vision, extract_nutrition_facts_vision, parse_nutrition_facts_text
from translator_engine import translate_indonesian_to_english, translate_serving_text
from pdf_generator import (
    build_bilingual_label_pdf,
    build_sticker_label_pdf,
    build_nutrition_facts_sticker_pdf,
    build_nutrition_spec_sheet_pdf,
    pdf_to_preview_image
)

# Set konfigurasi halaman Streamlit
LOGO_PATH = Path(__file__).parent / "assets" / "company_logo.jpg"
st.set_page_config(
    page_title="Penerjemah Label Kemasan ke PDF - CV Lintas Tujuh Benua",
    page_icon=str(LOGO_PATH) if LOGO_PATH.exists() else None,
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS styling terinspirasi dari tema desain modern SaaS (Plus Jakarta Sans, Royal Blue gradient, Pill buttons, Frosted Cards)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');

    /* Global Typography & Font Family */
    html, body, [class*="css"], .stApp, .stMarkdown, p, div, span, button, input, textarea, select {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
    }

    /* Preserve Streamlit Material Icons */
    [data-testid="stIconMaterial"], .material-symbols-rounded, .material-symbols-outlined, [class*="material-icons"], i.material-icons {
        font-family: "Material Symbols Rounded", "Material Symbols Outlined", "Material Icons" !important;
    }

    /* Background Luminous Aura - Putih Bersih di Atas, Gradasi Ungu/Biru Elegan di Bawah */
    .stApp {
        background: 
            radial-gradient(ellipse 90% 55% at 50% 100%, rgba(99, 102, 241, 0.18) 0%, rgba(139, 92, 246, 0.13) 32%, rgba(224, 231, 255, 0.2) 65%, rgba(255, 255, 255, 0) 100%),
            linear-gradient(180deg, #FFFFFF 0%, #FAFBFC 40%, #F5F7FB 100%) !important;
        background-attachment: fixed !important;
    }

    /* Container Spacing */
    .main .block-container {
        padding-top: 1.8rem !important;
        padding-bottom: 5rem !important;
        max-width: 1200px !important;
    }

    /* Top Navbar */
    .top-navbar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.85rem 1.4rem;
        background: rgba(255, 255, 255, 0.92);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(226, 232, 240, 0.85);
        border-radius: 9999px;
        box-shadow: 0 4px 20px -2px rgba(15, 23, 42, 0.04);
        margin-bottom: 2.2rem;
    }
    .top-nav-brand {
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .top-nav-brand-icon {
        font-size: 1.35rem;
    }
    .top-nav-brand-title {
        font-size: 1.05rem;
        font-weight: 800;
        color: #0F172A;
        letter-spacing: -0.02em;
    }
    .top-nav-brand-tag {
        font-size: 0.72rem;
        font-weight: 700;
        background: #EEF2FF;
        color: #4F46E5;
        padding: 3px 9px;
        border-radius: 9999px;
        letter-spacing: 0.04em;
        text-transform: uppercase;
    }
    .top-nav-links {
        display: flex;
        align-items: center;
        gap: 32px;
    }
    .top-nav-link, a.top-nav-link {
        font-size: 0.93rem !important;
        font-weight: 600 !important;
        color: #64748B !important;
        text-decoration: none !important;
        border-bottom: none !important;
        outline: none !important;
        padding: 8px 22px !important;
        border-radius: 9999px !important;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
        cursor: pointer !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        border: 1px solid transparent !important;
        background: transparent !important;
        letter-spacing: -0.01em !important;
    }
    .top-nav-link:hover, a.top-nav-link:hover {
        color: #1E293B !important;
        background: #F1F5F9 !important;
        border-color: #E2E8F0 !important;
        text-decoration: none !important;
        border-bottom: none !important;
    }
    .top-nav-link.active, a.top-nav-link.active {
        color: #2563EB !important;
        background: #EEF2FF !important;
        border-color: #C7D2FE !important;
        font-weight: 700 !important;
        box-shadow: 0 2px 10px rgba(37, 99, 235, 0.12) !important;
        text-decoration: none !important;
        border-bottom: none !important;
    }
    .top-nav-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: #F0FDF4;
        border: 1px solid #BBF7D0;
        color: #15803D;
        font-size: 0.8rem;
        font-weight: 700;
        padding: 5px 14px;
        border-radius: 9999px;
    }
    .status-dot-pulse {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background-color: #22C55E;
        box-shadow: 0 0 10px #22C55E;
    }

    /* Hero Section */
    .hero-container {
        text-align: center !important;
        padding: 0.5rem 1rem 2.8rem 1rem !important;
        max-width: 880px !important;
        margin: 0 auto !important;
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        justify-content: center !important;
        width: 100% !important;
    }
    .hero-pill-badge {
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        gap: 8px !important;
        background: #FFFFFF !important;
        border: 1px solid #E2E8F0 !important;
        padding: 7px 18px !important;
        border-radius: 9999px !important;
        font-size: 0.85rem !important;
        font-weight: 600 !important;
        color: #334155 !important;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.04) !important;
        margin: 0 auto 1.5rem auto !important;
    }
    .hero-title-dark {
        font-size: 3.1rem !important;
        font-weight: 800 !important;
        color: #0F172A !important;
        line-height: 1.15 !important;
        letter-spacing: -0.035em !important;
        margin: 0 0 0.3rem 0 !important;
        text-align: center !important;
        width: 100% !important;
    }
    .hero-title-gradient {
        font-size: 3.1rem !important;
        font-weight: 800 !important;
        line-height: 1.15 !important;
        letter-spacing: -0.035em !important;
        background: linear-gradient(135deg, #1E40AF 0%, #2563EB 45%, #6366F1 80%, #8B5CF6 100%) !important;
        -webkit-background-clip: text !important;
        -webkit-text-fill-color: transparent !important;
        margin: 0 0 1.25rem 0 !important;
        text-align: center !important;
        width: 100% !important;
    }
    .hero-subtitle-text {
        font-size: 1.08rem !important;
        color: #64748B !important;
        line-height: 1.65 !important;
        max-width: 760px !important;
        margin: 0 auto !important;
        font-weight: 400 !important;
        text-align: center !important;
        width: 100% !important;
    }

    /* Step Section Badges */
    .step-header-box {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-top: 2rem;
        margin-bottom: 1.1rem;
    }
    .step-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: linear-gradient(135deg, #EEF2FF 0%, #E0E7FF 100%);
        color: #4F46E5;
        font-size: 0.76rem;
        font-weight: 800;
        letter-spacing: 0.06em;
        padding: 5px 13px;
        border-radius: 9999px;
        border: 1px solid #C7D2FE;
        text-transform: uppercase;
    }
    .step-title-text {
        font-size: 1.35rem;
        font-weight: 800;
        color: #0F172A;
        letter-spacing: -0.02em;
        margin: 0;
    }

    /* Modern SaaS Primary Button (Persis Tombol 'Start your campaign ->') */
    button[kind="primary"], 
    .stButton>button[kind="primary"],
    button[kind="primaryFormSubmit"],
    .stFormSubmitButton>button,
    .stFormSubmitButton>button[kind="primaryFormSubmit"],
    div[data-testid="stFormSubmitButton"] button,
    button[data-testid="stBaseButton-primaryFormSubmit"],
    button[data-testid="stBaseButton-primary"] {
        background: linear-gradient(135deg, #2563EB 0%, #4F46E5 100%) !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 9999px !important;
        padding: 0.68rem 1.8rem !important;
        font-weight: 700 !important;
        font-size: 0.95rem !important;
        letter-spacing: 0.01em !important;
        box-shadow: 0 10px 25px -4px rgba(37, 99, 235, 0.45) !important;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        gap: 8px !important;
    }
    button[kind="primary"]:hover, 
    .stButton>button[kind="primary"]:hover,
    button[kind="primaryFormSubmit"]:hover,
    .stFormSubmitButton>button:hover,
    .stFormSubmitButton>button[kind="primaryFormSubmit"]:hover,
    div[data-testid="stFormSubmitButton"] button:hover,
    button[data-testid="stBaseButton-primaryFormSubmit"]:hover,
    button[data-testid="stBaseButton-primary"]:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 16px 34px -4px rgba(37, 99, 235, 0.6) !important;
        background: linear-gradient(135deg, #1D4ED8 0%, #4338CA 100%) !important;
        color: #FFFFFF !important;
    }
    button[kind="primary"] *, 
    .stButton>button[kind="primary"] *,
    button[kind="primaryFormSubmit"] *,
    .stFormSubmitButton>button *,
    div[data-testid="stFormSubmitButton"] button * {
        color: #FFFFFF !important;
        fill: #FFFFFF !important;
    }

    /* Secondary Button (Sleek Outline Pill) */
    button[kind="secondary"], .stButton>button:not([kind="primary"]) {
        background: #FFFFFF !important;
        color: #1E293B !important;
        border: 1.5px solid #E2E8F0 !important;
        border-radius: 9999px !important;
        padding: 0.55rem 0.95rem !important;
        font-weight: 600 !important;
        font-size: 0.88rem !important;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.03) !important;
        transition: all 0.2s ease !important;
        white-space: nowrap !important;
    }
    button[kind="secondary"]:hover, .stButton>button:not([kind="primary"]):hover {
        border-color: #3B82F6 !important;
        color: #2563EB !important;
        background: #F8FAFC !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 14px rgba(37, 99, 235, 0.12) !important;
    }

    /* Tombol Upload pada File Uploader & Kamera bergaya Primary Button Elegan */
    div[data-testid="stFileUploader"] button,
    [data-testid="stFileUploaderDropzone"] button,
    div[data-testid="stFileUploaderDropzoneInstructions"] button,
    div[data-testid="stFileUploader"] [data-testid*="Button"],
    section[data-testid="stFileUploadDropzone"] button,
    div[data-testid="stCameraInput"] button[kind="primary"] {
        background: linear-gradient(135deg, #2563EB 0%, #4F46E5 100%) !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 9999px !important;
        padding: 0.65rem 1.8rem !important;
        font-weight: 700 !important;
        font-size: 0.95rem !important;
        letter-spacing: 0.01em !important;
        box-shadow: 0 10px 25px -4px rgba(37, 99, 235, 0.45) !important;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        gap: 8px !important;
        cursor: pointer !important;
    }

    div[data-testid="stFileUploader"] button:hover,
    [data-testid="stFileUploaderDropzone"] button:hover,
    div[data-testid="stFileUploaderDropzoneInstructions"] button:hover,
    div[data-testid="stFileUploader"] [data-testid*="Button"]:hover,
    section[data-testid="stFileUploadDropzone"] button:hover,
    div[data-testid="stCameraInput"] button[kind="primary"]:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 16px 34px -4px rgba(37, 99, 235, 0.6) !important;
        background: linear-gradient(135deg, #1D4ED8 0%, #4338CA 100%) !important;
        color: #FFFFFF !important;
    }

    div[data-testid="stFileUploader"] button *,
    [data-testid="stFileUploaderDropzone"] button *,
    div[data-testid="stFileUploader"] [data-testid*="Button"] * {
        color: #FFFFFF !important;
        fill: #FFFFFF !important;
        stroke: #FFFFFF !important;
    }

    /* Dropzone Box Area */
    div[data-testid="stFileUploaderDropzone"] {
        border: 2px dashed #CBD5E1 !important;
        border-radius: 20px !important;
        background-color: #F8FAFC !important;
        transition: all 0.25s ease !important;
    }
    div[data-testid="stFileUploaderDropzone"]:hover {
        border-color: #3B82F6 !important;
        background-color: #F0F7FF !important;
    }

    /* Streamlit Tabs - Pill Capsule Navigation Persis Header */
    div[data-testid="stTabs"] .react-aria-SelectionIndicator,
    [data-testid="stTabs"] .react-aria-SelectionIndicator,
    div[data-testid="stTabs"] [data-baseweb="tab-highlight"],
    .stTabs [data-baseweb="tab-highlight"] {
        display: none !important;
        opacity: 0 !important;
        visibility: hidden !important;
        height: 0 !important;
        width: 0 !important;
        border: none !important;
    }

    div[data-testid="stTabs"] [role="tablist"],
    [data-testid="stTabs"] [role="tablist"],
    .stTabs [data-baseweb="tab-list"] {
        display: inline-flex !important;
        align-items: center !important;
        gap: 12px !important;
        background: rgba(255, 255, 255, 0.95) !important;
        backdrop-filter: blur(12px) !important;
        -webkit-backdrop-filter: blur(12px) !important;
        border: 1px solid rgba(226, 232, 240, 0.9) !important;
        border-radius: 9999px !important;
        padding: 5px 8px !important;
        box-shadow: 0 4px 20px -2px rgba(15, 23, 42, 0.04) !important;
        margin-bottom: 1.5rem !important;
        width: fit-content !important;
        border-bottom: 1px solid rgba(226, 232, 240, 0.9) !important;
    }

    /* Masing-masing Tab (Mencakup div, button, atau role="tab") */
    div[data-testid="stTabs"] [role="tab"],
    [data-testid="stTabs"] [role="tab"],
    div[data-testid="stTabs"] [data-testid="stTab"],
    [data-testid="stTab"],
    .stTabs [data-baseweb="tab"] {
        font-size: 0.92rem !important;
        font-weight: 600 !important;
        color: #64748B !important;
        text-decoration: none !important;
        border: 1.5px solid transparent !important;
        border-bottom: 1.5px solid transparent !important;
        outline: none !important;
        padding: 8px 22px !important;
        height: auto !important;
        min-height: unset !important;
        border-radius: 9999px !important;
        background: transparent !important;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
        cursor: pointer !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        letter-spacing: -0.01em !important;
        box-sizing: border-box !important;
    }

    div[data-testid="stTabs"] [role="tab"] *,
    [data-testid="stTab"] *,
    .stTabs [data-baseweb="tab"] * {
        margin: 0 !important;
        padding: 0 !important;
        font-size: inherit !important;
        font-weight: inherit !important;
        color: inherit !important;
        line-height: 1.3 !important;
    }

    div[data-testid="stTabs"] [role="tab"]:hover,
    [data-testid="stTab"]:hover,
    .stTabs [data-baseweb="tab"]:hover {
        color: #1E293B !important;
        background: #F1F5F9 !important;
        border-color: #E2E8F0 !important;
        border-radius: 9999px !important;
        text-decoration: none !important;
    }

    /* Tab Aktif - Pill Lembut Berwarna Biru dengan Rounded Penuh */
    div[data-testid="stTabs"] [role="tab"][aria-selected="true"],
    div[data-testid="stTabs"] [role="tab"][data-selected="true"],
    [data-testid="stTabs"] [role="tab"][aria-selected="true"],
    [data-testid="stTabs"] [role="tab"][data-selected="true"],
    [data-testid="stTab"][aria-selected="true"],
    [data-testid="stTab"][data-selected="true"],
    .stTabs [aria-selected="true"] {
        color: #2563EB !important;
        background: #EEF2FF !important;
        border: 1.5px solid #C7D2FE !important;
        border-radius: 9999px !important;
        font-weight: 700 !important;
        box-shadow: 0 2px 10px rgba(37, 99, 235, 0.12) !important;
        text-decoration: none !important;
    }

    /* Segmented Control Pill Styling (Modern SaaS Capsule Tabs) */
    div[data-testid="stSegmentedControl"] {
        display: flex !important;
        width: 100% !important;
    }
    div[data-testid="stSegmentedControl"] > div,
    div[data-testid="stSegmentedControl"] [data-baseweb="button-group"],
    div[data-testid="stSegmentedControl"] [role="radiogroup"] {
        display: flex !important;
        width: 100% !important;
        background: #F1F5F9 !important;
        border: 1.5px solid #E2E8F0 !important;
        border-radius: 9999px !important;
        padding: 5px !important;
        gap: 6px !important;
        box-shadow: inset 0 2px 4px rgba(15, 23, 42, 0.04) !important;
    }
    div[data-testid="stSegmentedControl"] button,
    div[data-testid="stSegmentedControl"] [role="radio"] {
        flex: 1 1 0 !important;
        border-radius: 9999px !important;
        border: none !important;
        background: transparent !important;
        color: #475569 !important;
        font-weight: 600 !important;
        font-size: 0.88rem !important;
        padding: 9px 14px !important;
        transition: all 0.22s cubic-bezier(0.4, 0, 0.2, 1) !important;
        cursor: pointer !important;
        text-align: center !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        white-space: nowrap !important;
        box-shadow: none !important;
    }
    div[data-testid="stSegmentedControl"] button:hover,
    div[data-testid="stSegmentedControl"] [role="radio"]:hover {
        color: #0F172A !important;
        background: rgba(255, 255, 255, 0.75) !important;
        transform: translateY(-1px) !important;
    }
    div[data-testid="stSegmentedControl"] button[aria-checked="true"],
    div[data-testid="stSegmentedControl"] [role="radio"][aria-checked="true"],
    div[data-testid="stSegmentedControl"] button[data-checked="true"] {
        color: #FFFFFF !important;
        background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%) !important;
        border: none !important;
        border-radius: 9999px !important;
        font-weight: 700 !important;
        box-shadow: 0 4px 14px rgba(37, 99, 235, 0.35) !important;
        transform: translateY(-1px) !important;
    }
    div[data-testid="stSegmentedControl"] button[aria-checked="true"] *,
    div[data-testid="stSegmentedControl"] [role="radio"][aria-checked="true"] *,
    div[data-testid="stSegmentedControl"] button[data-checked="true"] * {
        color: #FFFFFF !important;
        fill: #FFFFFF !important;
        stroke: #FFFFFF !important;
        font-weight: 700 !important;
    }

    /* Form Inputs, Text Areas, Number Inputs */
    .stTextInput input, .stTextArea textarea, .stNumberInput input {
        border-radius: 14px !important;
        border: 1.5px solid #E2E8F0 !important;
        background-color: #FFFFFF !important;
        color: #0F172A !important;
        font-size: 0.93rem !important;
        transition: all 0.2s ease !important;
    }
    .stTextInput input:focus, .stTextArea textarea:focus, .stNumberInput input:focus {
        border-color: #3B82F6 !important;
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.16) !important;
    }

    /* Modern SaaS Capsule Dropdown Button (Selectbox) */
    div[data-baseweb="select"] > div {
        border-radius: 9999px !important;
        border: 1.5px solid #E2E8F0 !important;
        background-color: #FFFFFF !important;
        color: #1E293B !important;
        font-weight: 600 !important;
        font-size: 0.88rem !important;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.03) !important;
        transition: all 0.2s ease !important;
        cursor: pointer !important;
    }
    div[data-baseweb="select"] > div:hover {
        border-color: #3B82F6 !important;
        color: #2563EB !important;
        background-color: #F8FAFC !important;
        box-shadow: 0 4px 14px rgba(37, 99, 235, 0.12) !important;
    }
    div[data-baseweb="select"] > div:focus-within {
        border-color: #3B82F6 !important;
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.16) !important;
    }
    ul[data-baseweb="menu"] {
        border-radius: 16px !important;
        border: 1px solid #E2E8F0 !important;
        box-shadow: 0 12px 30px rgba(15, 23, 42, 0.12) !important;
        padding: 6px !important;
    }
    li[data-baseweb="menu-item"] {
        border-radius: 10px !important;
        font-size: 0.88rem !important;
        font-weight: 500 !important;
        padding: 8px 14px !important;
        transition: all 0.15s ease !important;
    }
    li[data-baseweb="menu-item"]:hover {
        background: #EEF2FF !important;
        color: #2563EB !important;
    }

    /* Sidebar Royal Blue Theme (Mengikuti Tema Aplikasi) */
    section[data-testid="stSidebar"],
    section[data-testid="stSidebar"] div[data-testid="stSidebarContent"],
    section[data-testid="stSidebar"] div[data-testid="stSidebarUserContent"],
    section[data-testid="stSidebar"] div[data-testid="stSidebarHeader"] {
        background: transparent !important;
    }
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1E3A8A 0%, #1E40AF 45%, #2563EB 100%) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.15) !important;
    }
    section[data-testid="stSidebar"] > div {
        background: transparent !important;
    }
    section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
        background: transparent !important;
        padding-top: 1.6rem !important;
    }
    section[data-testid="stSidebar"] h1, 
    section[data-testid="stSidebar"] h2, 
    section[data-testid="stSidebar"] h3 {
        color: #FFFFFF !important;
        font-weight: 800 !important;
        letter-spacing: -0.02em !important;
    }

    /* Center Gambar Logo di Sidebar Secara Presisi */
    section[data-testid="stSidebar"] div[data-testid="stElementContainer"]:has([data-testid="stImage"]),
    section[data-testid="stSidebar"] .stElementContainer:has(.stImage),
    section[data-testid="stSidebar"] div[data-testid="stColumn"]:has([data-testid="stImage"]),
    section[data-testid="stSidebar"] [data-testid="stImage"] {
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
        text-align: center !important;
        margin-left: auto !important;
        margin-right: auto !important;
        width: 100% !important;
    }
    section[data-testid="stSidebar"] [data-testid="stImage"] > div,
    section[data-testid="stSidebar"] [data-testid="stImageContainer"] {
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
        margin-left: auto !important;
        margin-right: auto !important;
        width: 100% !important;
    }
    section[data-testid="stSidebar"] [data-testid="stImage"] > img,
    section[data-testid="stSidebar"] [data-testid="stImage"] img {
        margin: 0 auto !important;
        border-radius: 20px !important;
        border: 2px solid rgba(255, 255, 255, 0.35) !important;
        box-shadow: 0 10px 25px -4px rgba(0, 0, 0, 0.35) !important;
        display: block !important;
        object-fit: cover !important;
    }

    /* Tombol Collapse (<<) pada Sidebar */
    section[data-testid="stSidebar"] [data-testid="stSidebarCollapseButton"] button {
        color: #FFFFFF !important;
        background: rgba(255, 255, 255, 0.15) !important;
        border: 1px solid rgba(255, 255, 255, 0.25) !important;
        border-radius: 50% !important;
        width: 34px !important;
        height: 34px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        transition: all 0.2s ease !important;
    }
    section[data-testid="stSidebar"] [data-testid="stSidebarCollapseButton"] button:hover {
        background: rgba(255, 255, 255, 0.3) !important;
        transform: scale(1.08) !important;
    }
    section[data-testid="stSidebar"] [data-testid="stSidebarCollapseButton"] svg {
        fill: #FFFFFF !important;
        stroke: #FFFFFF !important;
    }

    /* Tombol Logout di Sidebar */
    section[data-testid="stSidebar"] .stButton > button {
        background: #FFFFFF !important;
        color: #1E3A8A !important;
        border: none !important;
        border-radius: 9999px !important;
        padding: 0.6rem 1.4rem !important;
        font-weight: 700 !important;
        font-size: 0.92rem !important;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.15) !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }
    section[data-testid="stSidebar"] .stButton > button:hover {
        background: #F8FAFC !important;
        color: #2563EB !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.25) !important;
    }
    section[data-testid="stSidebar"] .stButton > button * {
        color: #1E3A8A !important;
        fill: #1E3A8A !important;
    }
    section[data-testid="stSidebar"] .stButton > button:hover * {
        color: #2563EB !important;
        fill: #2563EB !important;
    }

    /* Garis Divider & Teks Caption di Sidebar */
    section[data-testid="stSidebar"] hr {
        border-color: rgba(255, 255, 255, 0.2) !important;
        margin: 1.2rem 0 !important;
    }
    section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {
        color: rgba(255, 255, 255, 0.75) !important;
        text-align: center !important;
        font-size: 0.76rem !important;
    }

    /* Checkbox & Radio Controls */
    input[type="checkbox"], input[type="radio"] {
        accent-color: #2563EB !important;
    }

    /* Container Checkbox Bersih & Rapi */
    div[data-testid="stCheckbox"] {
        background: transparent !important;
        padding: 2px 0 !important;
    }

    /* Label & Teks Checkbox SELALU Transparan (Mencegah blok biru pada teks) */
    div[data-testid="stCheckbox"] label,
    div[data-testid="stCheckbox"] label[data-selected="true"],
    div[data-testid="stCheckbox"] label *,
    div[data-testid="stCheckbox"] [data-testid="stWidgetLabel"],
    div[data-testid="stCheckbox"] [data-testid="stWidgetLabel"] * {
        background: transparent !important;
        background-color: transparent !important;
    }

    /* Tipografi Teks Checkbox */
    div[data-testid="stCheckbox"] label,
    div[data-testid="stCheckbox"] label p,
    div[data-testid="stCheckbox"] label span {
        color: #0F172A !important;
        font-size: 0.92rem !important;
        font-weight: 500 !important;
        line-height: 1.4 !important;
    }

    div[data-testid="stCheckbox"] label {
        display: inline-flex !important;
        align-items: center !important;
        gap: 10px !important;
        cursor: pointer !important;
        padding: 5px 8px !important;
        border-radius: 10px !important;
        transition: background-color 0.2s ease !important;
    }
    div[data-testid="stCheckbox"] label:hover {
        background-color: #F1F5F9 !important;
    }

    /* HANYA KOTAK KECIL CENTANG (Elemen Indikator Pertama) */
    div[data-testid="stCheckbox"] label > div:first-of-type,
    div[data-testid="stCheckbox"] label > div:first-child {
        width: 19px !important;
        height: 19px !important;
        min-width: 19px !important;
        min-height: 19px !important;
        max-width: 19px !important;
        max-height: 19px !important;
        border-radius: 6px !important;
        border: 1.5px solid #CBD5E1 !important;
        background-color: #FFFFFF !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        flex-shrink: 0 !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05) !important;
    }

    /* Kotak Centang Saat Terpilih (Checked) - Hanya Elemen Kotak Kecil */
    div[data-testid="stCheckbox"] label[data-selected="true"] > div:first-of-type,
    div[data-testid="stCheckbox"] label[data-selected="true"] > div:first-child,
    div[data-testid="stCheckbox"] label:has(input:checked) > div:first-of-type,
    div[data-testid="stCheckbox"] input:checked + div {
        background-color: #2563EB !important;
        border-color: #2563EB !important;
        box-shadow: 0 2px 8px rgba(37, 99, 235, 0.35) !important;
    }

    div[data-testid="stCheckbox"] label:hover > div:first-of-type {
        border-color: #3B82F6 !important;
    }

    /* Icon Centang Putih di dalam Kotak */
    div[data-testid="stCheckbox"] svg {
        stroke: #FFFFFF !important;
        fill: none !important;
        width: 13px !important;
        height: 13px !important;
        background: transparent !important;
    }
    div[data-testid="stCheckbox"] svg path {
        stroke: #FFFFFF !important;
        fill: none !important;
        background: transparent !important;
    }

    /* Slider Styling (Semua Slider Diubah Menjadi Royal Blue) */
    div[data-testid="stSlider"] div[role="slider"],
    div[data-baseweb="slider"] div[role="slider"],
    div[data-testid="stSlider"] [role="slider"] {
        background-color: #2563EB !important;
        border: 2.5px solid #FFFFFF !important;
        box-shadow: 0 2px 10px rgba(37, 99, 235, 0.45) !important;
        transition: transform 0.15s ease, box-shadow 0.15s ease !important;
    }
    div[data-testid="stSlider"] div[role="slider"]:hover,
    div[data-baseweb="slider"] div[role="slider"]:hover {
        background-color: #1D4ED8 !important;
        transform: scale(1.15) !important;
        box-shadow: 0 4px 14px rgba(37, 99, 235, 0.6) !important;
    }

    /* Angka / Nilai Slider yang melayang di atas thumb */
    div[data-testid="stSliderThumbValue"],
    .stSliderThumbValue,
    div[data-testid="stSlider"] [data-testid="stSliderThumbValue"],
    div[data-testid="stSlider"] div[style*="color: rgb(255, 75, 75)"] {
        color: #2563EB !important;
        font-weight: 700 !important;
    }

    /* Filter untuk Linear-Gradient Track Slider jika menggunakan inline gradient */
    div[data-testid="stSlider"] div[data-baseweb="slider"] div[style*="linear-gradient"],
    div[data-testid="stSlider"] div[style*="linear-gradient"] {
        filter: hue-rotate(215deg) saturate(1.8) !important;
    }

    /* Toggle Switch jika ada */
    div[data-testid="stToggle"] [aria-checked="true"],
    div[data-testid="stToggle"] input:checked ~ div {
        background-color: #2563EB !important;
        border-color: #2563EB !important;
    }

    /* Radio button jika ada */
    div[data-testid="stRadio"] div[role="radiogroup"] [aria-checked="true"] > div:first-child {
        border-color: #2563EB !important;
    }
    div[data-testid="stRadio"] div[role="radiogroup"] [aria-checked="true"] > div:first-child > div {
        background-color: #2563EB !important;
    }

    /* Card Box Utility */
    .card-box {
        background-color: rgba(255, 255, 255, 0.92);
        border-radius: 18px;
        padding: 1.4rem;
        border: 1px solid #E2E8F0;
        box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.05);
        margin-bottom: 1.2rem;
    }

    /* Kotak Pengaturan Stiker Scrollable yang Elegan */
    .st-key-sticker_settings_scroll,
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.st-key-sticker_settings_scroll) {
        border-radius: 20px !important;
        border: 1.5px solid #E2E8F0 !important;
        background: #FFFFFF !important;
        box-shadow: 0 4px 18px rgba(15, 23, 42, 0.04) !important;
    }
    .st-key-sticker_settings_scroll::-webkit-scrollbar,
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.st-key-sticker_settings_scroll)::-webkit-scrollbar {
        width: 6px !important;
    }
    .st-key-sticker_settings_scroll::-webkit-scrollbar-track,
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.st-key-sticker_settings_scroll)::-webkit-scrollbar-track {
        background: #F8FAFC !important;
        border-radius: 9999px !important;
    }
    .st-key-sticker_settings_scroll::-webkit-scrollbar-thumb,
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.st-key-sticker_settings_scroll)::-webkit-scrollbar-thumb {
        background: #CBD5E1 !important;
        border-radius: 9999px !important;
    }
    .st-key-sticker_settings_scroll::-webkit-scrollbar-thumb:hover,
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.st-key-sticker_settings_scroll)::-webkit-scrollbar-thumb:hover {
        background: #2563EB !important;
    }

    /* Floating Icon-Only Delete Button (Di Sisi Kanan Bawah Gambar) */
    .st-key-img_preview_box,
    .st-key-crop_preview_box {
        position: relative !important;
        width: 100% !important;
        display: block !important;
    }
    .st-key-img_preview_box [data-testid="stImage"] img {
        border-radius: 14px !important;
        border: 1px solid #E2E8F0 !important;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05) !important;
    }
    .st-key-btn_del_full,
    .st-key-btn_del_crop {
        position: absolute !important;
        bottom: 16px !important;
        right: 16px !important;
        z-index: 99 !important;
        width: auto !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    .st-key-btn_del_full > div,
    .st-key-btn_del_crop > div {
        width: auto !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    .st-key-btn_del_full button,
    .st-key-btn_del_crop button {
        width: 44px !important;
        height: 44px !important;
        min-width: 44px !important;
        min-height: 44px !important;
        max-width: 44px !important;
        max-height: 44px !important;
        border-radius: 50% !important;
        padding: 0 !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        background: linear-gradient(135deg, #2563EB 0%, #4F46E5 100%) !important;
        color: #FFFFFF !important;
        border: 2.5px solid #FFFFFF !important;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3), 0 2px 6px rgba(37, 99, 235, 0.4) !important;
        cursor: pointer !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }
    .st-key-btn_del_full button:hover,
    .st-key-btn_del_crop button:hover {
        transform: scale(1.12) !important;
        background: linear-gradient(135deg, #1D4ED8 0%, #4338CA 100%) !important;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35), 0 4px 12px rgba(37, 99, 235, 0.55) !important;
    }
    .st-key-btn_del_full button:active,
    .st-key-btn_del_crop button:active {
        transform: scale(0.94) !important;
    }
    .st-key-btn_del_full button p,
    .st-key-btn_del_crop button p {
        display: none !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    .st-key-btn_del_full button span,
    .st-key-btn_del_crop button span {
        font-size: 22px !important;
        line-height: 1 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        margin: 0 !important;
    }
</style>
""", unsafe_allow_html=True)

# Inisialisasi Session State Login
if "is_authenticated" not in st.session_state:
    st.session_state.is_authenticated = False
if "logged_in_user" not in st.session_state:
    st.session_state.logged_in_user = None
if "user_role" not in st.session_state:
    st.session_state.user_role = None
if "user_fullname" not in st.session_state:
    st.session_state.user_fullname = None

# Inisialisasi Session State Aplikasi
if "raw_text_id" not in st.session_state:
    st.session_state.raw_text_id = ""
if "translated_text_en" not in st.session_state:
    st.session_state.translated_text_en = ""
if "allergen_id" not in st.session_state:
    st.session_state.allergen_id = ""
if "allergen_en" not in st.session_state:
    st.session_state.allergen_en = ""
if "product_name" not in st.session_state:
    st.session_state.product_name = "Label Kemasan Produk"
if "variant_name" not in st.session_state:
    st.session_state.variant_name = "Original"
if "net_weight" not in st.session_state:
    st.session_state.net_weight = "100 g"
if "image_rotation" not in st.session_state:
    st.session_state.image_rotation = 0
if "processed_image_bytes" not in st.session_state:
    st.session_state.processed_image_bytes = None
if "enable_crop" not in st.session_state:
    st.session_state.enable_crop = True
if "uploader_nonce" not in st.session_state:
    st.session_state.uploader_nonce = 0
LOGO_PATH = Path(__file__).parent / "assets" / "company_logo.jpg"
if "company_logo_bytes" not in st.session_state:
    if LOGO_PATH.exists():
        with open(LOGO_PATH, "rb") as f:
            st.session_state.company_logo_bytes = f.read()
    else:
        st.session_state.company_logo_bytes = None

if "company_name" not in st.session_state:
    st.session_state.company_name = "CV LINTAS TUJUH BENUA"
if "company_subtitle" not in st.session_state:
    st.session_state.company_subtitle = "EXPORT | IMPORT"

if "distributor_header" not in st.session_state:
    st.session_state.distributor_header = "IMPORTED BY :"
if "distributor_info" not in st.session_state:
    st.session_state.distributor_info = "LOLLO WHOLESALE\n7505071 / 3395050\nSALES@LOLLO.MV"
if "sticker_size" not in st.session_state:
    st.session_state.sticker_size = "4x6 cm"
if "pdf_format_mode" not in st.session_state:
    st.session_state.pdf_format_mode = "Label Stiker Cetak Kemasan (Format Milo Cube)"
if "engine_choice" not in st.session_state:
    st.session_state.engine_choice = "Google Gemini 3.8 Flash (AI Vision)"

if "app_mode" not in st.session_state:
    st.session_state.app_mode = "Stiker Biasa"
if "input_source" not in st.session_state:
    st.session_state.input_source = "Unggah Berkas Gambar"

if "nutrition_product_name" not in st.session_state:
    st.session_state.nutrition_product_name = ""
if "nutrition_serving_size_id" not in st.session_state:
    st.session_state.nutrition_serving_size_id = ""
if "nutrition_serving_size_en" not in st.session_state:
    st.session_state.nutrition_serving_size_en = ""
if "nutrition_servings_per_pack" not in st.session_state:
    st.session_state.nutrition_servings_per_pack = ""
if "nutrition_serving_text_id" not in st.session_state:
    st.session_state.nutrition_serving_text_id = ""
if "nutrition_serving_text_en" not in st.session_state:
    st.session_state.nutrition_serving_text_en = ""

# Pastikan nilai awal takaran saji kosong (menunggu pemindaian AI atau ketikan pengguna)
if "1 BOTOL (140ML)" in str(st.session_state.get("nutrition_serving_text_id", "")):
    st.session_state.nutrition_serving_text_id = ""
if "1 BOTTLE (140ML)" in str(st.session_state.get("nutrition_serving_text_en", "")):
    st.session_state.nutrition_serving_text_en = ""
if "nutrition_ingredients_en" not in st.session_state:
    st.session_state.nutrition_ingredients_en = "SUGAR, FRUCTOSE, FRUIT JUICE LESS THAN 10% DERIVED FROM FRESH MANGO JUICE, BETA CAROTENE, MANGO FLAVOR, ACESULFAME, SUCRALOSE, AND WATER."
if "nutrition_calories_total" not in st.session_state:
    st.session_state.nutrition_calories_total = "60 KCAL"
if "nutrition_calories_fat" not in st.session_state:
    st.session_state.nutrition_calories_fat = ""
if "nutrition_amount_per_serving_title_id" not in st.session_state:
    st.session_state.nutrition_amount_per_serving_title_id = "JUMLAH PER SAJIAN"
if "nutrition_amount_per_serving_title_en" not in st.session_state:
    st.session_state.nutrition_amount_per_serving_title_en = "AMOUNT PER SERVING"
if "nutrition_energy_items" not in st.session_state:
    st.session_state.nutrition_energy_items = []
if "nutrition_items" not in st.session_state:
    st.session_state.nutrition_items = []

# Bersihkan data dummy YOU C1000 lama jika belum ada pemindaian gambar baru
if "nutrition_items" in st.session_state and isinstance(st.session_state.nutrition_items, list):
    if len(st.session_state.nutrition_items) == 7 and any("Vitamin C (Asam Askorbat)" in str(x.get("Nutrisi (ID)", "")) for x in st.session_state.nutrition_items):
        st.session_state.nutrition_items = []
        st.session_state.nutrition_energy_items = []
if "nutrition_footnote_id" not in st.session_state:
    st.session_state.nutrition_footnote_id = "*Persen AKG berdasarkan kebutuhan energi 2150 kkal."
if "nutrition_footnote_en" not in st.session_state:
    st.session_state.nutrition_footnote_en = "*Percent Daily Values (% DV) are based on a 2,000 calorie diet."
if "nutrition_raw_id" not in st.session_state:
    st.session_state.nutrition_raw_id = ""
if "nutrition_raw_en" not in st.session_state:
    st.session_state.nutrition_raw_en = ""
if "nutrition_sticker_size" not in st.session_state:
    st.session_state.nutrition_sticker_size = "3x5 cm"
if "nutrition_header_text" not in st.session_state:
    st.session_state.nutrition_header_text = "INGREDIENTS & NUTRITIONAL INFORMATION"
if "nutrition_dv_header" not in st.session_state:
    st.session_state.nutrition_dv_header = "%DV*"
if "active_nutrition_sesi" not in st.session_state:
    st.session_state.active_nutrition_sesi = "Sesi 1: Judul"
if "Sesi 1" in str(st.session_state.get("active_nutrition_sesi", "")):
    st.session_state.active_nutrition_sesi = "Sesi 1: Judul"
elif "Sesi 2" in str(st.session_state.get("active_nutrition_sesi", "")):
    st.session_state.active_nutrition_sesi = "Sesi 2: Takaran Saji"
elif "Sesi 3" in str(st.session_state.get("active_nutrition_sesi", "")):
    st.session_state.active_nutrition_sesi = "Sesi 3: Jumlah per Sajian"
elif "Sesi 4" in str(st.session_state.get("active_nutrition_sesi", "")):
    st.session_state.active_nutrition_sesi = "Sesi 4: Informasi Gizi & AKG"
elif "Sesi 5" in str(st.session_state.get("active_nutrition_sesi", "")):
    st.session_state.active_nutrition_sesi = "Sesi 5: Catatan Kaki AKG"
if "nutrition_scan_completed" not in st.session_state:
    st.session_state.nutrition_scan_completed = False
if "nutrition_table_height_scale" not in st.session_state:
    st.session_state.nutrition_table_height_scale = 1.0
if "nutrition_font_scale_s1" not in st.session_state:
    st.session_state.nutrition_font_scale_s1 = 1.0
if "nutrition_font_scale_s2" not in st.session_state:
    st.session_state.nutrition_font_scale_s2 = 1.0
if "nutrition_font_scale_s3" not in st.session_state:
    st.session_state.nutrition_font_scale_s3 = 1.0
if "nutrition_font_scale_s4" not in st.session_state:
    st.session_state.nutrition_font_scale_s4 = 1.0
if "nutrition_font_scale_s5" not in st.session_state:
    st.session_state.nutrition_font_scale_s5 = 1.0
if "nutrition_font_scale_dist" not in st.session_state:
    st.session_state.nutrition_font_scale_dist = 1.0

LOGIN_BG_PATH_WEBP = Path(__file__).parent / "assets" / "login_bg.webp"
LOGIN_BG_PATH_PNG = Path(__file__).parent / "assets" / "login_bg.png"
if "login_bg_b64" not in st.session_state:
    if LOGIN_BG_PATH_WEBP.exists():
        with open(LOGIN_BG_PATH_WEBP, "rb") as f:
            st.session_state.login_bg_b64 = f"data:image/webp;base64,{base64.b64encode(f.read()).decode('utf-8')}"
    elif LOGIN_BG_PATH_PNG.exists():
        with open(LOGIN_BG_PATH_PNG, "rb") as f:
            st.session_state.login_bg_b64 = f"data:image/png;base64,{base64.b64encode(f.read()).decode('utf-8')}"
    else:
        st.session_state.login_bg_b64 = ""

LOGIN_LOGO_PATH_WEBP = Path(__file__).parent / "assets" / "login_logo.webp"
LOGIN_LOGO_PATH_PNG = Path(__file__).parent / "assets" / "login_logo.png"
if "login_logo_b64" not in st.session_state:
    if LOGIN_LOGO_PATH_WEBP.exists():
        with open(LOGIN_LOGO_PATH_WEBP, "rb") as f:
            st.session_state.login_logo_b64 = f"data:image/webp;base64,{base64.b64encode(f.read()).decode('utf-8')}"
    elif LOGIN_LOGO_PATH_PNG.exists():
        with open(LOGIN_LOGO_PATH_PNG, "rb") as f:
            st.session_state.login_logo_b64 = f"data:image/png;base64,{base64.b64encode(f.read()).decode('utf-8')}"
    else:
        st.session_state.login_logo_b64 = ""

# ==================== SISTEM LOGIN AKSES INTERNAL ====================
if not st.session_state.is_authenticated:
    bg_css = ""
    if st.session_state.get("login_bg_b64"):
        bg_css = f"""
        .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {{
            background-image: url("{st.session_state.login_bg_b64}") !important;
            background-size: cover !important;
            background-position: center center !important;
            background-repeat: no-repeat !important;
            background-attachment: fixed !important;
        }}
        header[data-testid="stHeader"] {{
            background: transparent !important;
        }}
        """

    # Sembunyikan sidebar dan kontrol navigasi saat di halaman login
    st.markdown(f"""
    <style>
        {bg_css}
        section[data-testid="stSidebar"], [data-testid="collapsedControl"] {{
            display: none !important;
        }}
        .main .block-container {{
            max-width: 480px !important;
            padding-top: 3.5rem !important;
        }}
        .st-key-login_card {{
            background: rgba(255, 255, 255, 0.92) !important;
            backdrop-filter: blur(24px) !important;
            -webkit-backdrop-filter: blur(24px) !important;
            border: 1px solid rgba(255, 255, 255, 0.85) !important;
            border-radius: 24px !important;
            padding: 2.2rem 2rem !important;
            box-shadow: 0 20px 45px -10px rgba(30, 58, 138, 0.12), 0 2px 6px rgba(0, 0, 0, 0.04) !important;
            margin-bottom: 1.2rem !important;
        }}
        .st-key-login_card [data-testid="stForm"] {{
            border: none !important;
            padding: 0 !important;
            background: transparent !important;
        }}
        .st-key-login_card div[data-testid="stFormSubmitButton"] button,
        .st-key-login_card button[kind="primaryFormSubmit"],
        .st-key-login_card button[kind="primary"] {{
            background: linear-gradient(135deg, #2563EB 0%, #4F46E5 100%) !important;
            color: #FFFFFF !important;
            border: none !important;
            border-radius: 9999px !important;
            padding: 0.68rem 1.8rem !important;
            font-weight: 700 !important;
            font-size: 0.95rem !important;
            letter-spacing: 0.01em !important;
            box-shadow: 0 10px 25px -4px rgba(37, 99, 235, 0.45) !important;
            transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            gap: 8px !important;
            width: 100% !important;
        }}
        .st-key-login_card div[data-testid="stFormSubmitButton"] button:hover,
        .st-key-login_card button[kind="primaryFormSubmit"]:hover,
        .st-key-login_card button[kind="primary"]:hover {{
            transform: translateY(-2px) !important;
            box-shadow: 0 16px 34px -4px rgba(37, 99, 235, 0.6) !important;
            background: linear-gradient(135deg, #1D4ED8 0%, #4338CA 100%) !important;
            color: #FFFFFF !important;
        }}
        .st-key-login_card div[data-testid="stFormSubmitButton"] button *,
        .st-key-login_card button[kind="primaryFormSubmit"] * {{
            color: #FFFFFF !important;
            fill: #FFFFFF !important;
        }}
    </style>
    """, unsafe_allow_html=True)

    # Card Box Utama untuk Form Login
    with st.container(key="login_card"):
        # Logo Perusahaan Baru di Dalam Kartu (Centered Presisi)
        logo_html = ""
        if st.session_state.get("login_logo_b64"):
            logo_html = f'''<div style="text-align: center; display: flex; justify-content: center; align-items: center; width: 100%; margin: 0 auto 0.6rem auto;">
<img src="{st.session_state.login_logo_b64}" style="width: 155px; height: auto; max-width: 100%; object-fit: contain; margin: 0 auto; display: block;" alt="CV Lintas Tujuh Benua" />
</div>'''
        elif st.session_state.get("company_logo_bytes"):
            c_l1, c_l2, c_l3 = st.columns([1.2, 1, 1.2])
            with c_l2:
                st.image(st.session_state.company_logo_bytes, width=100)

        st.markdown(f"""{logo_html}
<div style="text-align: center; margin-top: 0.2rem; margin-bottom: 1.2rem;">
<div style="font-size: 1.65rem; font-weight: 800; color: #0F172A; margin: 0 0 0.35rem 0; letter-spacing: -0.025em; line-height: 1.25;">
Silahkan Masukan Akun
</div>
<p style="color: #64748B; font-size: 0.88rem; margin: 0;">
CV Lintas Tujuh Benua
</p>
</div>""", unsafe_allow_html=True)

        with st.form("login_form", clear_on_submit=False, border=False):
            user_input = st.text_input("ID Pengguna / Username", placeholder="Masukkan ID pengguna (misal: admin)...")
            pass_input = st.text_input("Kata Sandi / Password", type="password", placeholder="Masukkan kata sandi Anda...")
            
            st.markdown("<div style='height: 6px;'></div>", unsafe_allow_html=True)
            login_btn = st.form_submit_button("Masuk ke Sistem", type="primary", use_container_width=True)

            if login_btn:
                is_valid, fullname, role = verify_credentials(user_input, pass_input)
                if is_valid:
                    st.session_state.is_authenticated = True
                    st.session_state.logged_in_user = user_input.strip().lower()
                    st.session_state.user_role = role
                    st.session_state.user_fullname = fullname
                    st.rerun()
                else:
                    st.error("ID Pengguna atau Kata Sandi salah! Periksa kembali huruf besar/kecil.")

    # Kotak Informasi Akun Percobaan (Sleek SaaS Card)
    st.markdown("""
    <div class="card-box" style="background: rgba(255, 255, 255, 0.88); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px); border: 1.5px dashed #93C5FD; border-radius: 20px; padding: 1.3rem 1.5rem; margin-top: 0.5rem; box-shadow: 0 10px 25px -5px rgba(30, 58, 138, 0.08);">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.85rem;">
            <div style="font-size: 0.8rem; font-weight: 800; color: #334155; text-transform: uppercase; letter-spacing: 0.05em; display: flex; align-items: center; gap: 6px;">
                Akun Percobaan Internal:
            </div>
            <span style="font-size: 0.72rem; color: #4F46E5; font-weight: 700; background: #EEF2FF; padding: 3px 9px; border-radius: 9999px;">Siap Digunakan</span>
        </div>
        <div style="display: flex; flex-direction: column; gap: 8px;">
            <div style="display: flex; align-items: center; justify-content: space-between; background: #F8FAFC; border: 1px solid #E2E8F0; padding: 9px 14px; border-radius: 12px;">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="font-size: 0.72rem; font-weight: 800; background: #EEF2FF; color: #4F46E5; padding: 3px 9px; border-radius: 9999px;">ADMIN</span>
                    <span style="font-size: 0.86rem; color: #1E293B; font-weight: 600;">ID: <code style="color: #2563EB;">admin</code></span>
                </div>
                <span style="font-size: 0.86rem; color: #1E293B;">Pass: <code style="color: #2563EB;">lintas2026</code></span>
            </div>
            <div style="display: flex; align-items: center; justify-content: space-between; background: #F8FAFC; border: 1px solid #E2E8F0; padding: 9px 14px; border-radius: 12px;">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="font-size: 0.72rem; font-weight: 800; background: #F0FDF4; color: #16A34A; padding: 3px 9px; border-radius: 9999px;">STAFF</span>
                    <span style="font-size: 0.86rem; color: #1E293B; font-weight: 600;">ID: <code style="color: #2563EB;">staff</code></span>
                </div>
                <span style="font-size: 0.86rem; color: #1E293B;">Pass: <code style="color: #2563EB;">kantor123</code></span>
            </div>
        </div>
        <div style="font-size: 0.75rem; color: #94A3B8; margin-top: 10px; text-align: center;">
            *Tekan tombol 'Masuk ke Sistem' atau Enter setelah mengisi kolom di atas.
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.stop()

# ==================== SIDEBAR ====================
with st.sidebar:
    if st.session_state.get("company_logo_bytes"):
        c_sb1, c_sb2, c_sb3 = st.columns([1, 1.35, 1])
        with c_sb2:
            st.image(st.session_state.company_logo_bytes, use_container_width=True)

    company_name = st.session_state.company_name
    company_sub = st.session_state.company_subtitle
    user_fullname = st.session_state.get('user_fullname', 'Staff')
    user_role = st.session_state.get('user_role', 'Internal')

    st.markdown(f"""<div style="text-align: center; margin-bottom: 1.3rem;">
<div style="font-size: 1.05rem; font-weight: 800; color: #FFFFFF; letter-spacing: -0.015em; margin-bottom: 3px; line-height: 1.25;">{company_name}</div>
<div style="font-size: 0.8rem; font-weight: 600; color: rgba(255, 255, 255, 0.82); font-style: italic; letter-spacing: 0.05em;">{company_sub}</div>
</div>
<div style="background: rgba(255, 255, 255, 0.12); backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px); border: 1px solid rgba(255, 255, 255, 0.22); border-radius: 16px; padding: 13px 16px; margin-bottom: 0.9rem; box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);">
<div style="font-size: 0.72rem; font-weight: 700; color: rgba(255, 255, 255, 0.75); text-transform: uppercase; letter-spacing: 0.05em;">Pengguna Masuk</div>
<div style="font-size: 0.98rem; font-weight: 800; color: #FFFFFF; margin: 3px 0 6px 0;">{user_fullname}</div>
<div style="display: inline-block; background: rgba(255, 255, 255, 0.22); color: #FFFFFF; font-size: 0.72rem; font-weight: 700; padding: 2px 10px; border-radius: 9999px; border: 1px solid rgba(255, 255, 255, 0.32);">{user_role}</div>
</div>""", unsafe_allow_html=True)

    if st.button("Keluar (Logout)", icon=":material/logout:", use_container_width=True, help="Keluar dari akun dan kunci sistem"):
        st.session_state.is_authenticated = False
        st.session_state.logged_in_user = None
        st.session_state.user_role = None
        st.session_state.user_fullname = None
        st.rerun()

    # Pengaturan backend otomatis tanpa mengotori sidebar: ambil API Key dari st.secrets, os.environ, atau session_state
    gemini_api_key = ""
    try:
        if "GEMINI_API_KEY" in st.secrets and st.secrets["GEMINI_API_KEY"]:
            gemini_api_key = str(st.secrets["GEMINI_API_KEY"]).strip()
    except Exception:
        pass
    if not gemini_api_key:
        gemini_api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not gemini_api_key:
        gemini_api_key = st.session_state.get("custom_gemini_api_key", "").strip()
    page_size = "A4"
    include_logo_in_a4 = True
    include_image_in_pdf = True

    st.markdown("---")
    st.caption("Aplikasi Pemindai & Penerjemah Komposisi Kemasan v1.0 • CV Lintas Tujuh Benua")


# ==================== MAIN CONTENT ====================
active_page = st.query_params.get("page", "maker")
if active_page not in ["maker", "tutorial"]:
    active_page = "maker"

nav_maker_active = "active" if active_page == "maker" else ""
nav_tut_active = "active" if active_page == "tutorial" else ""

# Modern Top Navbar (Sticker Generator & Tutorial)
st.markdown(f"""
<div class="top-navbar">
    <div class="top-nav-brand">
        <span class="top-nav-brand-title">CV Lintas Tujuh Benua</span>
        <span class="top-nav-brand-tag">Export &bull; Import</span>
    </div>
    <div class="top-nav-links">
        <a class="top-nav-link {nav_maker_active}" href="?page=maker" target="_self">Sticker Generator</a>
        <a class="top-nav-link {nav_tut_active}" href="?page=tutorial" target="_self">Tutorial</a>
    </div>
    <div class="top-nav-badge">
        <span class="status-dot-pulse"></span>
        <span>{st.session_state.get('user_fullname', 'Staff')} &bull; Online</span>
    </div>
</div>
""", unsafe_allow_html=True)

# Jika Pengguna Memilih Halaman Tutorial
if active_page == "tutorial":
    st.markdown("""
    <div class="hero-container">
        <div class="hero-pill-badge">
            <span class="status-dot-pulse"></span>
            <span>Panduan Penggunaan Lengkap</span>
        </div>
        <h1 class="hero-title-dark">Panduan &amp; Tutorial</h1>
        <h1 class="hero-title-gradient">Pembuat Stiker Label Kemasan</h1>
        <p class="hero-subtitle-text">
            Pelajari langkah-langkah praktis mengubah gambar komposisi kemasan menjadi stiker cetak berkualitas ekspor dengan font resmi GothamOffice-Bold.
        </p>
    </div>

    <div class="card-box">
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 0.8rem;">
            <span class="step-pill">LANGKAH 01</span>
            <h3 style="margin: 0; color: #0F172A; font-weight: 700;">Masukkan Gambar Label Kemasan</h3>
        </div>
        <p style="color: #475569; line-height: 1.6; margin: 0 0 0.8rem 0;">
            • <b>Unggah Berkas Gambar</b>: Pilih file foto label kemasan dalam format JPG, PNG, atau WEBP dari komputer atau perangkat Anda.<br/>
            • <b>Jepret Kamera</b>: Ambil foto label secara langsung menggunakan webcam laptop atau kamera ponsel.<br/>
            • <b>Fitur Crop &amp; Rotasi</b>: Jika posisi foto miring atau terbalik, gunakan tombol <b>Putar 90°</b>. Aktifkan kotak pemotong (crop) dan seret sudut kotak biru agar pembacaan teks fokus hanya pada tabel komposisi/bahan baku.
        </p>
    </div>

    <div class="card-box">
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 0.8rem;">
            <span class="step-pill">LANGKAH 02</span>
            <h3 style="margin: 0; color: #0F172A; font-weight: 700;">Pemindaian OCR &amp; Penerjemahan Komposisi (Bilingual)</h3>
        </div>
        <p style="color: #475569; line-height: 1.6; margin: 0 0 0.8rem 0;">
            • <b>AI Vision Gemini 3.8 Flash</b>: Membaca teks kemasan bahkan yang berkerut atau melengkung dengan akurasi sangat tinggi dan langsung menerjemahkan bahan baku ke Bahasa Inggris standar ekspor pangan.<br/>
            • <b>Mesin Lokal (RapidOCR)</b>: Alternatif pemindaian offline tanpa internet dan tanpa kuota API.<br/>
            • <b>Penyunting Teks</b>: Periksa hasil bacaan pada kolom Bahasa Indonesia dan Bahasa Inggris. Anda dapat menyunting langsung atau menekan tombol <b>Terjemahkan Ulang</b> jika terdapat penyesuaian.
        </p>
    </div>

    <div class="card-box">
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 0.8rem;">
            <span class="step-pill">LANGKAH 03</span>
            <h3 style="margin: 0; color: #0F172A; font-weight: 700;">Pengaturan &amp; Ekspor PDF Stiker Siap Cetak</h3>
        </div>
        <p style="color: #475569; line-height: 1.6; margin: 0 0 0.8rem 0;">
            • <b>Pilihan Ukuran Stiker</b>: Pilih ukuran label stiker yang diinginkan (3x5 cm, 4x6 cm, 5x7 cm, atau kustom mm).<br/>
            • <b>Font GothamOffice-Bold</b>: Font otomatis terkunci menggunakan GothamOffice-Bold persis stiker referensi Milo Cube.<br/>
            • <b>Auto-Fit 1 Halaman</b>: Sistem otomatis menghitung dan menyesuaikan ukuran teks agar seluruh informasi pasti pas dalam 1 halaman stiker tanpa terpotong.<br/>
            • <b>Profil Distributor</b>: Masukkan atau edit identitas importir/distributor langsung pada kolom teks.<br/>
            • <b>Unduh &amp; Cetak</b>: Klik tombol <b>Unduh PDF Stiker</b> untuk mendapatkan berkas PDF siap cetak ke printer label.
        </p>
    </div>

    <div style="text-align: center; margin-top: 2rem; margin-bottom: 3rem;">
        <a href="?page=maker" target="_self" style="
            display: inline-block;
            background: linear-gradient(135deg, #2563EB 0%, #4F46E5 100%);
            color: #FFFFFF !important;
            text-decoration: none;
            border-radius: 9999px;
            padding: 0.75rem 2.2rem;
            font-weight: 700;
            font-size: 0.98rem;
            box-shadow: 0 10px 25px -4px rgba(37, 99, 235, 0.45);
        ">Mulai Buat Stiker Sekarang &rarr;</a>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

st.markdown("""
<div class="hero-container" style="text-align: center; display: flex; flex-direction: column; align-items: center;">
    <div class="hero-pill-badge" style="margin: 0 auto 1.5rem auto;">
        <span class="status-dot-pulse"></span>
        <span>Food Packaging Vision &amp; Multilingual Export Compliance</span>
    </div>
    <h1 class="hero-title-dark" style="text-align: center; width: 100%;">Packaging Label Translation</h1>
    <h1 class="hero-title-gradient" style="text-align: center; width: 100%;">Made Easy For Businesses</h1>
    <p class="hero-subtitle-text" style="text-align: center; margin: 0 auto; max-width: 760px;">
        Pindai teks komposisi dan bahan baku kemasan makanan, terjemahkan otomatis ke standar regulasi internasional, dan hasilkan label stiker presisi siap cetak
    </p>
</div>

<div class="step-header-box">
    <span class="step-pill">LANGKAH 01</span>
    <h3 class="step-title-text">Masukkan Gambar Label Kemasan</h3>
</div>
""", unsafe_allow_html=True)

col_src_sel, col_mode_sel = st.columns([1.08, 1.25], vertical_alignment="center")

with col_src_sel:
    input_source = st.segmented_control(
        "Metode Input:",
        options=["Unggah Berkas Gambar", "Jepret Kamera"],
        default=st.session_state.get("input_source", "Unggah Berkas Gambar"),
        selection_mode="single",
        required=True,
        label_visibility="collapsed",
        key="input_source_segmented"
    )
    st.session_state.input_source = input_source

with col_mode_sel:
    app_mode = st.segmented_control(
        "Mode Pengerjaan:",
        options=["Stiker Biasa", "Tabel Nilai Gizi"],
        default=st.session_state.get("app_mode", "Stiker Biasa"),
        selection_mode="single",
        required=True,
        label_visibility="collapsed",
        key="app_mode_segmented"
    )
    st.session_state.app_mode = app_mode

current_image = None

if input_source == "Jepret Kamera":
    camera_file = st.camera_input(
        "Ambil foto label kemasan langsung menggunakan kamera",
        key=f"camera_{st.session_state.uploader_nonce}"
    )
    if camera_file is not None:
        try:
            current_image = Image.open(camera_file)
        except Exception as e:
            st.error(f"Gagal mengambil gambar kamera: {e}")
else:
    uploaded_file = st.file_uploader(
        "Pilih file gambar label kemasan (JPG, PNG, JPEG, WEBP)",
        type=["jpg", "jpeg", "png", "webp", "bmp"],
        key=f"uploader_{st.session_state.uploader_nonce}"
    )
    if uploaded_file is not None:
        try:
            current_image = Image.open(uploaded_file)
        except Exception as e:
            st.error(f"Gagal membuka file gambar: {e}")

# Preview & Penyesuaian Gambar (Rotasi & Crop)
if current_image is not None:
    # Terapkan rotasi jika pengguna memutar gambar
    if st.session_state.image_rotation != 0:
        current_image = current_image.rotate(-st.session_state.image_rotation, expand=True)

    # Baris Alat: Orientasi, Mesin Pembaca, dan Opsi Pemotong (Crop)
    c_tools1, c_tools2, c_tools3 = st.columns([1.1, 1.45, 1.15])
    with c_tools1:
        st.markdown("**Orientasi & Rotasi:**")
        r_col1, r_col2 = st.columns([1, 1])
        with r_col1:
            if st.button("Putar 90°", use_container_width=True):
                st.session_state.image_rotation = (st.session_state.image_rotation + 90) % 360
                st.rerun()
        with r_col2:
            if st.button("Reset Putar", use_container_width=True):
                st.session_state.image_rotation = 0
                st.rerun()
    with c_tools2:
        st.markdown("**Pilihan Mesin Pembaca:**")
        ai_engine_options = [
            "Google Gemini 3.8 Flash (AI Vision)",
            "Google Gemini 3.7 Flash (AI Vision)",
            "Google Gemini Flash Latest (AI Vision)",
            "Lokal (RapidOCR - Offline)"
        ]
        curr_idx = 0
        if st.session_state.get("engine_choice") in ai_engine_options:
            curr_idx = ai_engine_options.index(st.session_state.engine_choice)
        elif "3.7" in str(st.session_state.get("engine_choice", "")):
            curr_idx = 1
        elif "Latest" in str(st.session_state.get("engine_choice", "")) or "latest" in str(st.session_state.get("engine_choice", "")):
            curr_idx = 2
        elif "Lokal" in str(st.session_state.get("engine_choice", "")):
            curr_idx = 3

        selected_engine = st.selectbox(
            "Pilih Mesin AI:",
            options=ai_engine_options,
            index=curr_idx,
            key="main_engine_selector",
            label_visibility="collapsed",
            help="Klik tombol ini untuk memilih opsi mesin AI pembaca kemasan (Gemini 3.8, Gemini 3.7, Flash Latest, atau RapidOCR Lokal)."
        )
        st.session_state.engine_choice = selected_engine
    with c_tools3:
        st.markdown("**Fitur Pemotong Area (Crop):**")
        st.session_state.enable_crop = st.checkbox(
            "Aktifkan Pemotong Area Label (Crop Area)",
            value=st.session_state.enable_crop,
            help="Tandai area tabel komposisi/gizi saja dengan kotak pemotong agar pembacaan OCR lebih terfokus dan akurat."
        )

    if "Gemini" in st.session_state.engine_choice and not gemini_api_key:
        st.warning("Kunci API Gemini belum terhubung di server online ini. Masukkan kunci API Anda di bawah agar Gemini Vision AI aktif:", icon=":material/key:")
        col_k1, col_k2 = st.columns([3, 1])
        with col_k1:
            input_k = st.text_input("Kunci API Gemini:", type="password", key="custom_gemini_key_input", placeholder="Tempelkan API Key Gemini (AQ.Ab8...)", label_visibility="collapsed")
        with col_k2:
            if st.button("Aktifkan Gemini", type="primary", use_container_width=True):
                if input_k.strip():
                    st.session_state.custom_gemini_api_key = input_k.strip()
                    os.environ["GEMINI_API_KEY"] = input_k.strip()
                    gemini_api_key = input_k.strip()
                    st.success("API Key Gemini berhasil disimpan!")
                    st.rerun()

    cropped_img = None
    target_image = current_image

    if st.session_state.enable_crop:
        col_crop_view, col_crop_preview = st.columns([1.6, 1.4])
        with col_crop_view:
            st.markdown("**Pilih area teks menggunakan kotak pemotong:**")
            with st.container(key="crop_preview_box"):
                cropped_img = st_cropper(
                    current_image,
                    realtime_update=True,
                    box_color='#2563EB',
                    aspect_ratio=None,
                    key=f"cropper_{st.session_state.image_rotation}_{st.session_state.uploader_nonce}"
                )
                if st.button("", icon=":material/delete_outline:", type="primary", key="btn_del_crop", help="Hapus gambar yang diunggah dan bersihkan"):
                    st.session_state.uploader_nonce += 1
                    st.session_state.image_rotation = 0
                    st.session_state.enable_crop = False
                    st.session_state.processed_image_bytes = None
                    st.session_state.raw_text_id = ""
                    st.session_state.translated_text_en = ""
                    st.session_state.nutrition_raw_id = ""
                    st.session_state.nutrition_raw_en = ""
                    st.session_state.nutrition_items = []
                    st.session_state.nutrition_energy_items = []
                    st.session_state.nutrition_serving_text_id = ""
                    st.session_state.nutrition_serving_text_en = ""
                    st.session_state.nutrition_product_name = ""
                    st.session_state.nutrition_scan_completed = False
                    st.rerun()
        with col_crop_preview:
            st.markdown("**Pratinjau Area Terpilih:**")
            if cropped_img is not None:
                st.image(cropped_img, caption="Area yang akan dipindai", use_container_width=True)
                target_image = cropped_img
            else:
                st.info("Pilih area pada gambar sebelah kiri.")

            st.markdown("---")
            st.caption(f"Mesin pembaca yang digunakan: **{st.session_state.engine_choice}**")
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                btn_crop_scan = st.button("Pindai Area Pilihan", type="primary", use_container_width=True)
            with col_b2:
                btn_full_scan = st.button("Pindai Seluruh Gambar", use_container_width=True)

            process_btn = btn_crop_scan or btn_full_scan
            if btn_full_scan:
                target_image = current_image
    else:
        col_img, col_ctrl = st.columns([2, 1])
        with col_img:
            st.markdown("**Pratinjau Gambar Penuh:**")
            with st.container(key="img_preview_box"):
                st.image(current_image, use_container_width=True)
                if st.button("", icon=":material/delete_outline:", type="primary", key="btn_del_full", help="Hapus gambar yang diunggah dan bersihkan"):
                    st.session_state.uploader_nonce += 1
                    st.session_state.image_rotation = 0
                    st.session_state.enable_crop = False
                    st.session_state.processed_image_bytes = None
                    st.session_state.raw_text_id = ""
                    st.session_state.translated_text_en = ""
                    st.session_state.nutrition_raw_id = ""
                    st.session_state.nutrition_raw_en = ""
                    st.session_state.nutrition_items = []
                    st.session_state.nutrition_energy_items = []
                    st.session_state.nutrition_serving_text_id = ""
                    st.session_state.nutrition_serving_text_en = ""
                    st.session_state.nutrition_product_name = ""
                    st.session_state.nutrition_scan_completed = False
                    st.rerun()
        with col_ctrl:
            st.info(f"Mode Gambar Penuh aktif.\n\nMesin pembaca terpilih:\n**{st.session_state.engine_choice}**")
            target_image = current_image
            process_btn = st.button("Mulai Pindai & Terjemahkan", type="primary", use_container_width=True)

    # Simpan target image yang dipilih untuk PDF
    buf = io.BytesIO()
    target_image.save(buf, format="JPEG")
    st.session_state.processed_image_bytes = buf.getvalue()

    if process_btn:
        active_engine = st.session_state.engine_choice
        if "3.7" in active_engine:
            active_model = "gemini-3.7-flash"
        elif "Latest" in active_engine or "latest" in active_engine:
            active_model = "gemini-flash-latest"
        else:
            active_model = "gemini-3.8-flash"

        if "Tabel Nilai Gizi" in st.session_state.app_mode:
            spinner_msg = f"Sedang menganalisis tabel Informasi Nilai Gizi menggunakan Google {active_model} Vision AI..." if ("Gemini" in active_engine and gemini_api_key) else "Sedang membaca tabel nilai gizi pada kemasan..."
            with st.spinner(spinner_msg):
                if "Gemini" in active_engine and gemini_api_key:
                    try:
                        g_nutr = extract_nutrition_facts_vision(target_image, gemini_api_key, model_name=active_model)
                        if g_nutr.get("product_name"):
                            st.session_state.nutrition_product_name = g_nutr.get("product_name")
                        if g_nutr.get("serving_size_id"):
                            st.session_state.nutrition_serving_size_id = g_nutr.get("serving_size_id")
                        if g_nutr.get("serving_size_en"):
                            st.session_state.nutrition_serving_size_en = g_nutr.get("serving_size_en")
                        if g_nutr.get("servings_per_pack"):
                            st.session_state.nutrition_servings_per_pack = g_nutr.get("servings_per_pack")
                        ss_id_val = (g_nutr.get("serving_size_id") or "").strip()
                        ss_en_val = (g_nutr.get("serving_size_en") or "").strip()
                        sp_val = (g_nutr.get("servings_per_pack") or "").strip()
                        st_id_val = (g_nutr.get("serving_text_id") or "").strip()
                        st_en_val = (g_nutr.get("serving_text_en") or "").strip()

                        if ss_id_val:
                            st.session_state.nutrition_serving_size_id = ss_id_val
                        if ss_en_val:
                            st.session_state.nutrition_serving_size_en = ss_en_val
                        if sp_val:
                            st.session_state.nutrition_servings_per_pack = sp_val

                        # Tulis teks takaran saji hasil bacaan AI
                        if st_id_val:
                            st.session_state.nutrition_serving_text_id = st_id_val
                        else:
                            st_id_lines = []
                            if ss_id_val:
                                st_id_lines.append(f"TAKARAN SAJI: {ss_id_val}")
                            if sp_val:
                                if "sajian" in sp_val.lower() or "kemasan" in sp_val.lower():
                                    st_id_lines.append(sp_val)
                                else:
                                    st_id_lines.append(f"JUMLAH SAJIAN PER KEMASAN: {sp_val}")
                            st.session_state.nutrition_serving_text_id = "\n".join(st_id_lines).strip()

                        # Biarkan AI penerjemah yang menulis terjemahan takaran saji ke bahasa Inggris
                        if st_en_val:
                            st.session_state.nutrition_serving_text_en = st_en_val
                        elif st.session_state.nutrition_serving_text_id:
                            st.session_state.nutrition_serving_text_en = translate_serving_text(st.session_state.nutrition_serving_text_id)
                        else:
                            st.session_state.nutrition_serving_text_en = ""

                        parsed_energy = []
                        if g_nutr.get("energy_items") and isinstance(g_nutr["energy_items"], list):
                            for eit in g_nutr["energy_items"]:
                                if isinstance(eit, dict):
                                    eid = str(eit.get("name_id") or eit.get("Nama Energi (ID)") or "").strip()
                                    een = str(eit.get("name_en") or eit.get("Energy Name (EN)") or "").strip()
                                    eamt = str(eit.get("amount") or eit.get("Nilai (Amount)") or "").strip()
                                    if eid or een or eamt:
                                        parsed_energy.append({
                                            "Nama Energi (ID)": eid,
                                            "Energy Name (EN)": een,
                                            "Nilai (Amount)": eamt
                                        })
                        if not parsed_energy:
                            if g_nutr.get("calories_total"):
                                st.session_state.nutrition_calories_total = g_nutr.get("calories_total")
                            if g_nutr.get("calories_fat"):
                                st.session_state.nutrition_calories_fat = g_nutr.get("calories_fat")
                            c_tot_val = (g_nutr.get("calories_total") or st.session_state.nutrition_calories_total or "").strip()
                            c_fat_val = (g_nutr.get("calories_fat") or st.session_state.nutrition_calories_fat or "").strip()
                            if c_tot_val:
                                parsed_energy.append({"Nama Energi (ID)": "Energi total", "Energy Name (EN)": "Total Energy", "Nilai (Amount)": c_tot_val})
                            if c_fat_val:
                                parsed_energy.append({"Nama Energi (ID)": "  Energi dari lemak", "Energy Name (EN)": "  Calories from Fat", "Nilai (Amount)": c_fat_val})
                        st.session_state.nutrition_energy_items = parsed_energy

                        if g_nutr.get("footnote_id"):
                            st.session_state.nutrition_footnote_id = g_nutr.get("footnote_id")
                        if g_nutr.get("footnote_en"):
                            st.session_state.nutrition_footnote_en = g_nutr.get("footnote_en")
                        if g_nutr.get("ingredients_en"):
                            st.session_state.nutrition_ingredients_en = g_nutr.get("ingredients_en")
                        if g_nutr.get("distributor_header"):
                            st.session_state.distributor_header = g_nutr.get("distributor_header")
                        if g_nutr.get("distributor_info"):
                            st.session_state.distributor_info = g_nutr.get("distributor_info")
                        st.session_state.nutrition_raw_id = g_nutr.get("raw_nutrition_id", "")
                        st.session_state.nutrition_raw_en = g_nutr.get("raw_nutrition_en", "")

                        raw_nutr_list = g_nutr.get("nutrients", [])
                        parsed_rows = []
                        if raw_nutr_list and isinstance(raw_nutr_list, list):
                            for it in raw_nutr_list:
                                if isinstance(it, dict):
                                    n_id_str = str(it.get("name_id", "")).strip()
                                    n_en_str = str(it.get("name_en", "")).strip()
                                    if any(k in n_id_str.lower() or k in n_en_str.lower() for k in ["energi", "energy", "kalori", "calorie"]):
                                        continue
                                    amt_str = str(it.get("amount", "")).strip()
                                    dv_str = str(it.get("daily_value", "-")).strip()
                                    if n_id_str or n_en_str or amt_str:
                                        parsed_rows.append({
                                            "Nutrisi (ID)": n_id_str,
                                            "Nutrient (EN)": n_en_str,
                                            "Jumlah (Amount)": amt_str,
                                            "% AKG / DV": dv_str
                                        })
                        st.session_state.nutrition_items = parsed_rows
                        st.session_state.nutrition_scan_completed = True
                        st.success(f"Berhasil membaca dan menstrukturkan {len(st.session_state.nutrition_items)} baris tabel nilai gizi dengan Google {active_model} Vision AI.")
                    except Exception as e:
                        st.error(f"Respon Google Gemini: {e}")
                        st.info("Mengalihkan pemindaian ke Mesin Lokal (RapidOCR)...")
                        raw_id = extract_text_rapid_ocr(target_image)
                        st.session_state.nutrition_raw_id = raw_id
                        trans_en = translate_indonesian_to_english(raw_id)
                        st.session_state.nutrition_raw_en = trans_en
                        parsed_local = parse_nutrition_facts_text(raw_id)
                        if parsed_local.get("serving_lines"):
                            st.session_state.nutrition_serving_text_id = "\n".join(parsed_local["serving_lines"])
                            st.session_state.nutrition_serving_text_en = translate_serving_text(st.session_state.nutrition_serving_text_id)
                        if parsed_local.get("energy_items"):
                            st.session_state.nutrition_energy_items = parsed_local["energy_items"]
                        else:
                            st.session_state.nutrition_energy_items = []
                        if parsed_local.get("nutrients"):
                            st.session_state.nutrition_items = parsed_local["nutrients"]
                        else:
                            st.session_state.nutrition_items = []
                        if parsed_local.get("footnote"):
                            st.session_state.nutrition_footnote_id = parsed_local["footnote"]
                            st.session_state.nutrition_footnote_en = translate_indonesian_to_english(parsed_local["footnote"])
                        st.session_state.nutrition_scan_completed = True
                        st.success(f"Teks nilai gizi ({len(st.session_state.nutrition_items)} baris) berhasil dibaca secara lokal dan diterjemahkan.")
                else:
                    if "Gemini" in active_engine and not gemini_api_key:
                        st.warning("Kunci API Gemini (GEMINI_API_KEY) belum terhubung di server. Pemindaian dialihkan ke Mesin OCR Lokal (RapidOCR).", icon=":material/key_off:")
                    raw_id = extract_text_rapid_ocr(target_image)
                    st.session_state.nutrition_raw_id = raw_id
                    trans_en = translate_indonesian_to_english(raw_id)
                    st.session_state.nutrition_raw_en = trans_en
                    parsed_local = parse_nutrition_facts_text(raw_id)
                    if parsed_local.get("serving_lines"):
                        st.session_state.nutrition_serving_text_id = "\n".join(parsed_local["serving_lines"])
                        st.session_state.nutrition_serving_text_en = translate_serving_text(st.session_state.nutrition_serving_text_id)
                    if parsed_local.get("energy_items"):
                        st.session_state.nutrition_energy_items = parsed_local["energy_items"]
                    else:
                        st.session_state.nutrition_energy_items = []
                    if parsed_local.get("nutrients"):
                        st.session_state.nutrition_items = parsed_local["nutrients"]
                    else:
                        st.session_state.nutrition_items = []
                    if parsed_local.get("footnote"):
                        st.session_state.nutrition_footnote_id = parsed_local["footnote"]
                        st.session_state.nutrition_footnote_en = translate_indonesian_to_english(parsed_local["footnote"])
                    st.session_state.nutrition_scan_completed = True
                    st.success(f"Teks nilai gizi ({len(st.session_state.nutrition_items)} baris) berhasil dibaca secara lokal dan diterjemahkan.")
        else:
            # Mode Stiker Biasa (Komposisi)
            spinner_msg = f"Sedang menganalisis kemasan menggunakan Google {active_model} Vision AI..." if ("Gemini" in active_engine and gemini_api_key) else "Sedang membaca teks pada label kemasan dan menerjemahkan..."
            with st.spinner(spinner_msg):
                if "Gemini" in active_engine and gemini_api_key:
                    try:
                        gemini_res = extract_with_gemini_vision(target_image, gemini_api_key, model_name=active_model)
                        st.session_state.raw_text_id = gemini_res.get("indonesian_text", "")
                        st.session_state.translated_text_en = gemini_res.get("english_text", "")
                        if gemini_res.get("product_name"):
                            st.session_state.product_name = gemini_res.get("product_name")
                        if gemini_res.get("net_weight"):
                            st.session_state.net_weight = gemini_res.get("net_weight")
                        if gemini_res.get("distributor_header"):
                            st.session_state.distributor_header = gemini_res.get("distributor_header")
                        if gemini_res.get("distributor_info"):
                            st.session_state.distributor_info = gemini_res.get("distributor_info")
                        st.session_state.allergen_id = gemini_res.get("allergen_id", "")
                        st.session_state.allergen_en = gemini_res.get("allergen_en", "")
                        st.success(f"Berhasil membaca dan menerjemahkan kemasan dengan Google {active_model} Vision AI.")
                    except Exception as e:
                        st.error(f"Respon Google Gemini: {e}")
                        st.info("Mengalihkan pemindaian otomatis ke Mesin Lokal (RapidOCR)...")
                        raw_id = extract_text_rapid_ocr(target_image)
                        st.session_state.raw_text_id = raw_id
                        trans_en = translate_indonesian_to_english(raw_id)
                        st.session_state.translated_text_en = trans_en
                        st.success("Berhasil dipindai menggunakan Mesin OCR Lokal dan diterjemahkan.")
                else:
                    # Mode Lokal RapidOCR + Translator
                    if "Gemini" in active_engine and not gemini_api_key:
                        st.warning("Kunci API Gemini (GEMINI_API_KEY) belum terhubung di server. Pemindaian dialihkan ke Mesin OCR Lokal (RapidOCR).", icon=":material/key_off:")
                    raw_id = extract_text_rapid_ocr(target_image)
                    st.session_state.raw_text_id = raw_id
                    trans_en = translate_indonesian_to_english(raw_id)
                    st.session_state.translated_text_en = trans_en
                    st.success("Berhasil dipindai menggunakan Mesin OCR Lokal dan diterjemahkan.")

st.markdown("---")

# =========================================================================
# JIKA MODE: TABEL NILAI GIZI (NUTRITION FACTS)
# =========================================================================
if "Tabel Nilai Gizi" in st.session_state.app_mode:
    # Langkah 02: Editor Gizi 5 Sesi
    st.markdown("""
    <div class="step-header-box">
        <span class="step-pill">LANGKAH 02</span>
        <h3 class="step-title-text">Verifikasi &amp; Edit Tabel Nilai Gizi (5 Sesi Terstruktur)</h3>
    </div>
    """, unsafe_allow_html=True)
    st.caption("Pengeditan tabel Informasi Nilai Gizi dibagi menjadi 5 sesi terarah untuk menjamin presisi tata letak dan kepatuhan ekspor standar internasional.")

    def nav_to_nutrition_sesi(sesi_name):
        st.session_state.active_nutrition_sesi = sesi_name

    # 5 Sesi Navigation Pills (Elegan & Konsisten dengan Mode Stiker Biasa)
    sesi_options = [
        "Sesi 1: Judul",
        "Sesi 2: Takaran Saji",
        "Sesi 3: Jumlah per Sajian",
        "Sesi 4: Informasi Gizi & AKG",
        "Sesi 5: Catatan Kaki AKG"
    ]
    if "active_nutrition_sesi" not in st.session_state or st.session_state.active_nutrition_sesi not in sesi_options:
        st.session_state.active_nutrition_sesi = "Sesi 1: Judul"

    st.pills(
        "Pilih Sesi Pengeditan:",
        options=sesi_options,
        key="active_nutrition_sesi",
        label_visibility="collapsed"
    )

    curr_sesi = st.session_state.active_nutrition_sesi

    st.markdown("""
    <style>
    /* Clean Pill Tabs for Sesi Navigation */
    div[data-testid="stPills"] {
        display: flex !important;
        flex-wrap: wrap !important;
        gap: 8px !important;
        margin-top: 0.3rem !important;
        margin-bottom: 1.3rem !important;
    }
    div[data-testid="stPills"] button {
        border-radius: 9999px !important;
        font-weight: 600 !important;
        font-size: 0.90rem !important;
        padding: 7px 18px !important;
        border: 1.5px solid #E2E8F0 !important;
        background: #FFFFFF !important;
        color: #475569 !important;
        transition: all 0.2s ease !important;
    }
    div[data-testid="stPills"] button:hover {
        border-color: #3B82F6 !important;
        color: #2563EB !important;
        background: #F8FAFC !important;
    }
    div[data-testid="stPills"] button[aria-selected="true"],
    div[data-testid="stPills"] button[aria-checked="true"] {
        background: linear-gradient(135deg, #2563EB 0%, #4F46E5 100%) !important;
        color: #FFFFFF !important;
        border: 1.5px solid transparent !important;
        font-weight: 700 !important;
        box-shadow: 0 4px 14px rgba(37, 99, 235, 0.3) !important;
    }
    div[data-testid="stPills"] button[aria-selected="true"] *,
    div[data-testid="stPills"] button[aria-checked="true"] * {
        color: #FFFFFF !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # ==================== SESI 1: PENGEDITAN JUDUL ====================
    if curr_sesi == "Sesi 1: Judul":
        st.markdown("#### Sesi 1: Judul & Varian Produk")
        st.caption("Sunting nama produk atau varian yang dicetak di posisi luar kotak bagian atas stiker.")

        st.session_state.nutrition_product_name = st.text_input(
            "Nama Produk / Varian (Dicetak Luar Kotak Bagian Atas):",
            value=st.session_state.nutrition_product_name,
            placeholder="Misal: YOU C1000 140ML MANGO",
            key="s1_product_name"
        )

        st.markdown("<br/>", unsafe_allow_html=True)
        col_nav_l, col_nav_r = st.columns([1.5, 1])
        with col_nav_r:
            st.button(
                "Lanjut ke Sesi 2: Takaran Saji",
                key="btn_to_s2",
                type="primary",
                icon=":material/arrow_forward:",
                use_container_width=True,
                on_click=nav_to_nutrition_sesi,
                args=("Sesi 2: Takaran Saji",)
            )

    # ==================== SESI 2: PENGEDITAN KOLOM TAKARAN SAJI ====================
    elif curr_sesi == "Sesi 2: Takaran Saji":
        st.markdown("#### Sesi 2: Header Kotak & Takaran Saji (Serving Size)")
        st.caption("Sunting judul header tabel dalam kotak stiker serta teks takaran saji dan jumlah sajian per kemasan.")

        st.session_state.nutrition_header_text = st.text_input(
            "Header Kotak Stiker (Header Seksi 1):",
            value=st.session_state.nutrition_header_text,
            placeholder="Misal: INGREDIENTS & NUTRITIONAL INFORMATION",
            key="s2_header_text"
        )

        def on_serving_text_id_changed():
            val = st.session_state.nutrition_serving_text_id.strip()
            if val:
                st.session_state.nutrition_serving_text_en = translate_serving_text(val)
            else:
                st.session_state.nutrition_serving_text_en = ""

        c_s2_1, c_s2_2 = st.columns(2)
        with c_s2_1:
            st.markdown("##### Takaran Saji (Bahasa Indonesia)")
            st.text_area(
                "Teks Takaran Saji (Bahasa Indonesia):",
                height=130,
                placeholder="Kosong (Menunggu hasil pemindaian AI atau ketik langsung di sini...)\nMisal:\nTAKARAN SAJI: 12 g\n20 Sajian per kemasan",
                key="nutrition_serving_text_id",
                on_change=on_serving_text_id_changed,
                label_visibility="collapsed"
            )
            c_s2_b1, c_s2_b2 = st.columns([1.6, 1])
            with c_s2_b1:
                if st.button("Terjemahkan ke English", key="btn_trans_serving", type="primary", icon=":material/translate:", use_container_width=True):
                    val = st.session_state.nutrition_serving_text_id.strip()
                    if val:
                        with st.spinner("Menerjemahkan takaran saji..."):
                            st.session_state.nutrition_serving_text_en = translate_serving_text(val)
                            st.success("Takaran saji berhasil diterjemahkan.")
                            st.rerun()
            with c_s2_b2:
                if st.button("Kosongkan", key="btn_clear_serving", icon=":material/delete_outline:", use_container_width=True):
                    st.session_state.nutrition_serving_text_id = ""
                    st.session_state.nutrition_serving_text_en = ""
                    st.rerun()

        with c_s2_2:
            st.markdown("##### Takaran Saji (English Translation)")
            st.text_area(
                "Teks Takaran Saji (English Translation):",
                height=130,
                placeholder="Kosong (AI penerjemah akan otomatis mengisi teks ini saat Anda mengetik / memindai...)\nMisal:\nSERVING SIZE: 12 g\n20 Servings per container",
                key="nutrition_serving_text_en",
                label_visibility="collapsed"
            )

        st.markdown("<br/>", unsafe_allow_html=True)
        col_nav_l, col_nav_r = st.columns(2)
        with col_nav_l:
            st.button(
                "Kembali ke Sesi 1: Judul",
                key="btn_back_to_s1",
                icon=":material/arrow_back:",
                use_container_width=True,
                on_click=nav_to_nutrition_sesi,
                args=("Sesi 1: Judul",)
            )
        with col_nav_r:
            st.button(
                "Lanjut ke Sesi 3: Jumlah per Sajian",
                key="btn_to_s3",
                type="primary",
                icon=":material/arrow_forward:",
                use_container_width=True,
                on_click=nav_to_nutrition_sesi,
                args=("Sesi 3: Jumlah per Sajian",)
            )

    # ==================== SESI 3: PENGEDITAN KOLOM JUMLAH PER SAJIAN ====================
    elif curr_sesi == "Sesi 3: Jumlah per Sajian":
        st.markdown("#### Sesi 3: Jumlah per Sajian (Amount Per Serving)")
        st.caption("Sunting judul seksi energi dan rincian energi total maupun energi dari lemak.")

        c_s3_t1, c_s3_t2 = st.columns(2)
        with c_s3_t1:
            st.session_state.nutrition_amount_per_serving_title_id = st.text_input(
                "Judul Seksi (Bahasa Indonesia):",
                value=st.session_state.nutrition_amount_per_serving_title_id,
                placeholder="JUMLAH PER SAJIAN",
                key="s3_title_id"
            )
        with c_s3_t2:
            st.session_state.nutrition_amount_per_serving_title_en = st.text_input(
                "Judul Seksi (English):",
                value=st.session_state.nutrition_amount_per_serving_title_en,
                placeholder="AMOUNT PER SERVING",
                key="s3_title_en"
            )

        st.markdown("##### Tabel Rincian Energi")
        st.caption("Klik langsung pada sel untuk mengedit. Tambah baris (+) untuk sub-item energi (misal: Energi dari lemak), atau centang untuk menghapus baris.")

        if st.session_state.nutrition_energy_items:
            df_energy = pd.DataFrame(st.session_state.nutrition_energy_items)
        else:
            df_energy = pd.DataFrame(columns=["Nama Energi (ID)", "Energy Name (EN)", "Nilai (Amount)"])
        edited_energy_df = st.data_editor(
            df_energy,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "Nama Energi (ID)": st.column_config.TextColumn("Nama Energi (ID)", required=True),
                "Energy Name (EN)": st.column_config.TextColumn("Energy Name (EN)", required=True),
                "Nilai (Amount)": st.column_config.TextColumn("Nilai / Jumlah", required=True),
            },
            key="data_editor_energy_items"
        )
        st.session_state.nutrition_energy_items = edited_energy_df.to_dict('records')

        st.markdown("<br/>", unsafe_allow_html=True)
        col_nav_l, col_nav_r = st.columns(2)
        with col_nav_l:
            st.button(
                "Kembali ke Sesi 2: Takaran Saji",
                key="btn_back_to_s2",
                icon=":material/arrow_back:",
                use_container_width=True,
                on_click=nav_to_nutrition_sesi,
                args=("Sesi 2: Takaran Saji",)
            )
        with col_nav_r:
            st.button(
                "Lanjut ke Sesi 4: Informasi Gizi & AKG",
                key="btn_to_s4",
                type="primary",
                icon=":material/arrow_forward:",
                use_container_width=True,
                on_click=nav_to_nutrition_sesi,
                args=("Sesi 4: Informasi Gizi & AKG",)
            )

    # ==================== SESI 4: PENGEDITAN INFORMASI GIZI & PERSEN AKG ====================
    elif curr_sesi == "Sesi 4: Informasi Gizi & AKG":
        st.markdown("#### Sesi 4: Rincian Informasi Zat Gizi & Persen AKG")
        st.caption("Sunting daftar zat gizi lengkap (nama, takaran per sajian, dan % AKG/DV) serta simbol header kolom AKG.")

        c_akg_hdr1, c_akg_hdr2 = st.columns([1, 1.5])
        with c_akg_hdr1:
            st.session_state.nutrition_dv_header = st.text_input(
                "Simbol Header Kolom AKG pada Stiker:",
                value=st.session_state.nutrition_dv_header,
                placeholder="Misal: %DV* atau % AKG",
                key="s4_dv_header"
            )
        with c_akg_hdr2:
            st.info("Standar acuan: % DV mengacu pada kebutuhan energi 2.000 kkal (FDA / Ekspor) atau 2.150 kkal (BPOM RI).", icon=":material/info:")

        st.markdown("##### Tabel Rincian Zat Gizi & Persen AKG (% AKG / % DV)")
        st.caption("Klik langsung pada sel untuk menyunting nama nutrisi, kandungan, atau % AKG. Anda juga dapat menambahkan baris baru (+) atau menghapus baris.")

        if st.session_state.nutrition_items:
            df_nutr = pd.DataFrame(st.session_state.nutrition_items)
        else:
            df_nutr = pd.DataFrame(columns=["Nutrisi (ID)", "Nutrient (EN)", "Jumlah (Amount)", "% AKG / DV"])
        edited_df = st.data_editor(
            df_nutr,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "Nutrisi (ID)": st.column_config.TextColumn("Nutrisi (Bahasa Indonesia)", required=True),
                "Nutrient (EN)": st.column_config.TextColumn("Nutrient (English)", required=True),
                "Jumlah (Amount)": st.column_config.TextColumn("Jumlah per Sajian (Amount)", required=True),
                "% AKG / DV": st.column_config.TextColumn("Persen AKG / % Daily Value (% AKG / DV)", required=False),
            },
            key="data_editor_nutrition_master"
        )
        st.session_state.nutrition_items = edited_df.to_dict('records')

        st.markdown("<br/>", unsafe_allow_html=True)
        col_nav_l, col_nav_r = st.columns(2)
        with col_nav_l:
            st.button(
                "Kembali ke Sesi 3: Jumlah per Sajian",
                key="btn_back_to_s3",
                icon=":material/arrow_back:",
                use_container_width=True,
                on_click=nav_to_nutrition_sesi,
                args=("Sesi 3: Jumlah per Sajian",)
            )
        with col_nav_r:
            st.button(
                "Lanjut ke Sesi 5: Catatan Kaki AKG",
                key="btn_to_s5",
                type="primary",
                icon=":material/arrow_forward:",
                use_container_width=True,
                on_click=nav_to_nutrition_sesi,
                args=("Sesi 5: Catatan Kaki AKG",)
            )

    # ==================== SESI 5: PENGEDITAN CATATAN KAKI AKG (BARIS TABEL 4) ====================
    elif curr_sesi == "Sesi 5: Catatan Kaki AKG":
        st.markdown("#### Sesi 5: Catatan Kaki AKG (Footnote)")
        st.caption("Sunting dan terjemahkan tulisan catatan kaki persentase AKG (Percent Daily Values footnote) untuk kompartemen paling bawah pada stiker nilai gizi.")

        c_fn1, c_fn2 = st.columns(2)
        with c_fn1:
            st.markdown("##### Catatan Kaki (Bahasa Indonesia)")
            st.session_state.nutrition_footnote_id = st.text_area(
                "Teks Catatan Kaki (Bahasa Indonesia):",
                value=st.session_state.nutrition_footnote_id,
                height=120,
                placeholder="* Persen AKG berdasarkan kebutuhan energi 2150 Kkal. Kebutuhan energi anda mungkin lebih tinggi atau lebih rendah.",
                key="s5_footnote_id",
                label_visibility="collapsed"
            )
            if st.button("Terjemahkan ke English", key="btn_trans_fn", type="primary", icon=":material/translate:", use_container_width=True):
                raw_fn = st.session_state.nutrition_footnote_id.strip()
                if raw_fn:
                    with st.spinner("Menerjemahkan catatan kaki..."):
                        try:
                            trans = translate_indonesian_to_english(raw_fn)
                            st.session_state.nutrition_footnote_en = trans
                            st.success("Catatan kaki berhasil diterjemahkan.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Gagal menerjemahkan: {e}")

        with c_fn2:
            st.markdown("##### Catatan Kaki (English Translation)")
            st.session_state.nutrition_footnote_en = st.text_area(
                "Teks Catatan Kaki (English Translation):",
                value=st.session_state.nutrition_footnote_en,
                height=120,
                placeholder="* Percent Daily Values (% DV) are based on a 2,000 calorie diet. Your daily values may be higher or lower depending on your calorie needs.",
                key="s5_footnote_en",
                label_visibility="collapsed"
            )

        with st.expander("Lihat / Edit Teks Mentah Tabel Nilai Gizi (Bilingual Raw Text)"):
            c_r1, c_r2 = st.columns(2)
            with c_r1:
                st.session_state.nutrition_raw_id = st.text_area("Teks Asli (ID):", value=st.session_state.nutrition_raw_id, height=130, key="s5_raw_id")
            with c_r2:
                st.session_state.nutrition_raw_en = st.text_area("Terjemahan (EN):", value=st.session_state.nutrition_raw_en, height=130, key="s5_raw_en")

        st.markdown("<br/>", unsafe_allow_html=True)
        col_nav_l, col_nav_m, col_nav_r = st.columns([1.2, 1, 1.4])
        with col_nav_l:
            st.button(
                "Kembali ke Sesi 4: Informasi Gizi",
                key="btn_back_to_s4",
                icon=":material/arrow_back:",
                use_container_width=True,
                on_click=nav_to_nutrition_sesi,
                args=("Sesi 4: Informasi Gizi & AKG",)
            )
        with col_nav_m:
            st.button(
                "Kembali ke Sesi 1",
                key="btn_back_to_s1_from_s5",
                icon=":material/first_page:",
                use_container_width=True,
                on_click=nav_to_nutrition_sesi,
                args=("Sesi 1: Judul",)
            )
        with col_nav_r:
            if st.button("Selesai & Lanjut ke Pratinjau Stiker", key="btn_to_preview", type="primary", icon=":material/done_all:", use_container_width=True):
                st.toast("Semua 5 Sesi Pengeditan Telah Siap! Silakan periksa pratinjau stiker di Langkah 03 di bawah.", icon=":material/check_circle:")

    st.markdown("---")

    # Langkah 03: Format & Pratinjau Stiker Nilai Gizi
    st.markdown("""
    <div class="step-header-box">
        <span class="step-pill">LANGKAH 03</span>
        <h3 class="step-title-text">Format &amp; Pratinjau Stiker Tabel Nilai Gizi (Nutrition Facts Preview)</h3>
    </div>
    """, unsafe_allow_html=True)
    has_nutrition_data = (
        st.session_state.get("nutrition_scan_completed", False)
        or bool(st.session_state.get("nutrition_raw_id", "").strip())
        or bool(st.session_state.get("nutrition_raw_en", "").strip())
        or bool(st.session_state.get("nutrition_items"))
        or bool(st.session_state.get("nutrition_energy_items"))
        or bool(st.session_state.get("nutrition_serving_text_id", "").strip())
    )

    if not has_nutrition_data:
        st.info("Unggah gambar label kemasan pada Langkah 1 terlebih dahulu untuk menghasilkan dokumen PDF.")
    else:
        st.caption("Sesuaikan ukuran label stiker nilai gizi, orientasi, dan bahasa tampilan sebelum mencetak atau mengunduh PDF.")

        col_n_cfg, col_n_prev = st.columns([1.3, 1.2])

        with col_n_cfg:
            st.markdown("#### Pengaturan Stiker Cetak Nilai Gizi")
            with st.container(height=660, border=True, key="sticker_settings_scroll"):
                c_sz1, c_sz2 = st.columns(2)
                with c_sz1:
                    size_options = ["3x5 cm", "4x6 cm", "5x7 cm", "3x5 inch", "4x6 inch", "Kustom (mm)"]
                    curr_sz_idx = 0
                    if st.session_state.nutrition_sticker_size in size_options:
                        curr_sz_idx = size_options.index(st.session_state.nutrition_sticker_size)
                    nutr_sticker_sz = st.selectbox(
                        "Pilihan Ukuran Stiker:",
                        options=size_options,
                        index=curr_sz_idx,
                        key="nutr_size_sel",
                        help="Ukuran 3x5 cm (30x50 mm) adalah ukuran standar persis sesuai referensi export YOU C1000."
                    )
                    st.session_state.nutrition_sticker_size = nutr_sticker_sz
                with c_sz2:
                    nutr_orient = st.selectbox(
                        "Orientasi Stiker:",
                        options=["Portrait (Tegak)", "Landscape (Mendatar)"],
                        index=0,
                        key="nutr_orient_sel"
                    )

                custom_w_mm, custom_h_mm = 30.0, 50.0
                if nutr_sticker_sz == "Kustom (mm)":
                    ck1, ck2 = st.columns(2)
                    with ck1:
                        custom_w_mm = st.number_input("Lebar (mm):", min_value=20.0, max_value=300.0, value=30.0, step=1.0)
                    with ck2:
                        custom_h_mm = st.number_input("Tinggi (mm):", min_value=20.0, max_value=300.0, value=50.0, step=1.0)

                st.markdown("---")
                st.markdown("##### Bahasa &amp; Tampilan:")
                c_l1, c_l2 = st.columns(2)
                with c_l1:
                    lang_options = [
                        "English Only (Standar Ekspor)",
                        "Bilingual (Indonesia & English)",
                        "Bahasa Indonesia (Standar BPOM)"
                    ]
                    nutr_lang = st.selectbox("Bahasa Tabel:", options=lang_options, index=0, key="nutr_lang_sel")
                with c_l2:
                    show_border_nutr = st.checkbox("Border Kotak Tebal (Box Border)", value=True, help="Format standar Nutrition Facts selalu menggunakan border kotak hitam tebal.")

                c_dim1, c_dim2 = st.columns(2)
                with c_dim1:
                    nutr_table_height_scale = st.slider(
                        "Tinggi Kotak Tabel:",
                        min_value=0.60,
                        max_value=1.40,
                        value=float(st.session_state.get("nutrition_table_height_scale", 1.0)),
                        step=0.05,
                        format="%.2fx",
                        key="nutr_table_h_scale_slider",
                        help="Sesuaikan tinggi vertikal kotak tabel nilai gizi pada stiker (0.60x s/d 1.40x)."
                    )
                    st.session_state.nutrition_table_height_scale = nutr_table_height_scale
                with c_dim2:
                    nutr_font_scale = st.slider(
                        "Skala Huruf (Global):",
                        min_value=0.70,
                        max_value=1.40,
                        value=1.0,
                        step=0.05,
                        format="%.2fx",
                        key="nutr_font_scale_slider",
                        help="Skala pengali ukuran seluruh teks secara bersamaan."
                    )

                c_m1, c_m2 = st.columns(2)
                with c_m1:
                    nutr_margin_mm = st.slider("Margin Tepi (mm):", min_value=1.0, max_value=6.0, value=2.0, step=0.5, key="nutr_margin_slider")
                with c_m2:
                    st.caption("Atur tinggi kotak dan skala font per sesi di bawah untuk penataan letak yang presisi.")

                with st.expander("Penyesuaian Ukuran Font per Sesi (Sesi 1 - 5)", expanded=True):
                    st.caption("Atur besar-kecil font untuk tiap seksi tabel nilai gizi secara mandiri:")
                    c_fs1, c_fs2 = st.columns(2)
                    with c_fs1:
                        font_s1 = st.slider(
                            "Sesi 1: Judul & Nama",
                            min_value=0.60,
                            max_value=1.50,
                            value=float(st.session_state.get("nutrition_font_scale_s1", 1.0)),
                            step=0.05,
                            format="%.2fx",
                            key="slider_font_s1",
                            help="Ukuran font 'INGREDIENTS & NUTRITIONAL INFORMATION' & Nama Produk."
                        )
                        st.session_state.nutrition_font_scale_s1 = font_s1

                        font_s3 = st.slider(
                            "Sesi 3: Jumlah/Sajian",
                            min_value=0.60,
                            max_value=1.50,
                            value=float(st.session_state.get("nutrition_font_scale_s3", 1.0)),
                            step=0.05,
                            format="%.2fx",
                            key="slider_font_s3",
                            help="Ukuran font 'AMOUNT PER SERVING' dan baris energi/kalori."
                        )
                        st.session_state.nutrition_font_scale_s3 = font_s3

                        font_s5 = st.slider(
                            "Sesi 5: Catatan Kaki AKG",
                            min_value=0.60,
                            max_value=1.50,
                            value=float(st.session_state.get("nutrition_font_scale_s5", 1.0)),
                            step=0.05,
                            format="%.2fx",
                            key="slider_font_s5",
                            help="Ukuran font teks catatan kaki AKG / Footnote."
                        )
                        st.session_state.nutrition_font_scale_s5 = font_s5

                    with c_fs2:
                        font_s2 = st.slider(
                            "Sesi 2: Takaran Saji",
                            min_value=0.60,
                            max_value=1.50,
                            value=float(st.session_state.get("nutrition_font_scale_s2", 1.0)),
                            step=0.05,
                            format="%.2fx",
                            key="slider_font_s2",
                            help="Ukuran font takaran saji & sajian per kemasan."
                        )
                        st.session_state.nutrition_font_scale_s2 = font_s2

                        font_s4 = st.slider(
                            "Sesi 4: Informasi Zat Gizi",
                            min_value=0.60,
                            max_value=1.50,
                            value=float(st.session_state.get("nutrition_font_scale_s4", 1.0)),
                            step=0.05,
                            format="%.2fx",
                            key="slider_font_s4",
                            help="Ukuran font baris rincian nutrisi (Lemak, Protein, Karbo, dsb) & %DV*."
                        )
                        st.session_state.nutrition_font_scale_s4 = font_s4

                        if st.button("Reset Font Sesi ke 1.0x", key="btn_reset_session_fonts", icon=":material/restart_alt:", use_container_width=True):
                            st.session_state.nutrition_font_scale_s1 = 1.0
                            st.session_state.nutrition_font_scale_s2 = 1.0
                            st.session_state.nutrition_font_scale_s3 = 1.0
                            st.session_state.nutrition_font_scale_s4 = 1.0
                            st.session_state.nutrition_font_scale_s5 = 1.0
                            st.session_state.nutrition_font_scale_dist = 1.0
                            st.rerun()

                st.markdown("---")
                include_company_nutr = st.checkbox(
                    "Sertakan Informasi Distributor / Importir di Bagian Bawah",
                    value=True,
                    key="include_company_nutr"
                )

                if include_company_nutr:
                    st.markdown("##### Informasi Distributor / Importir (Footer Stiker)")
                    c_dist1, c_dist2 = st.columns([1, 1.8])
                    with c_dist1:
                        st.session_state.distributor_header = st.text_input(
                            "Header Distributor / Importir:",
                            value=st.session_state.distributor_header,
                            placeholder="Misal: IMPORTED BY :",
                            key="cfg_dist_header"
                        )
                    with c_dist2:
                        st.session_state.distributor_info = st.text_area(
                            "Data Kontak Distributor / Importir:",
                            value=st.session_state.distributor_info,
                            height=85,
                            placeholder="LOLLO WHOLESALE\n7505071 / 3395050\nSALES@LOLLO.MV",
                            key="cfg_dist_info"
                        )

                    font_dist = st.slider(
                        "Besar Font Distributor / Importir:",
                        min_value=0.50,
                        max_value=1.60,
                        value=float(st.session_state.get("nutrition_font_scale_dist", 1.0)),
                        step=0.05,
                        format="%.2fx",
                        key="slider_font_dist",
                        help="Sesuaikan besar-kecil font teks informasi distributor / importir di bagian bawah stiker."
                    )
                    st.session_state.nutrition_font_scale_dist = font_dist

        with col_n_prev:
            st.markdown("#### Pratinjau Stiker Nilai Gizi")

            try:
                if "English" in nutr_lang:
                    serving_text_choice = st.session_state.nutrition_serving_text_en
                elif "Indonesia" in nutr_lang:
                    serving_text_choice = st.session_state.nutrition_serving_text_id
                else:
                    serving_text_choice = f"{st.session_state.nutrition_serving_text_id}\n{st.session_state.nutrition_serving_text_en}"

                if "English" in nutr_lang:
                    energy_title_choice = st.session_state.nutrition_amount_per_serving_title_en
                elif "Indonesia" in nutr_lang:
                    energy_title_choice = st.session_state.nutrition_amount_per_serving_title_id
                else:
                    energy_title_choice = f"{st.session_state.nutrition_amount_per_serving_title_id} / {st.session_state.nutrition_amount_per_serving_title_en}"

                nutr_pdf_bytes = build_nutrition_facts_sticker_pdf(
                    product_name=st.session_state.nutrition_product_name,
                    serving_size=serving_text_choice,
                    servings_per_pack="",
                    calories_total=st.session_state.nutrition_calories_total,
                    calories_fat=st.session_state.nutrition_calories_fat,
                    energy_title=energy_title_choice,
                    energy_items=st.session_state.nutrition_energy_items,
                    header_text=st.session_state.nutrition_header_text,
                    dv_header=st.session_state.nutrition_dv_header,
                    ingredients_text="",
                    nutrients_list=st.session_state.nutrition_items,
                    distributor_header=st.session_state.distributor_header if include_company_nutr else "",
                    distributor_info=st.session_state.distributor_info if include_company_nutr else "",
                    footnote_text=st.session_state.nutrition_footnote_en if "English" in nutr_lang else (
                        st.session_state.nutrition_footnote_id if "Indonesia" in nutr_lang else f"{st.session_state.nutrition_footnote_id}\n{st.session_state.nutrition_footnote_en}"
                    ),
                    company_name=st.session_state.company_name if include_company_nutr else "",
                    size_choice=nutr_sticker_sz,
                    custom_width_mm=custom_w_mm,
                    custom_height_mm=custom_h_mm,
                    orientation="landscape" if "Landscape" in nutr_orient else "portrait",
                    language_choice="english" if "English" in nutr_lang else ("indonesian" if "Indonesia" in nutr_lang else "bilingual"),
                    font_scale=nutr_font_scale,
                    table_height_scale=st.session_state.nutrition_table_height_scale,
                    font_scale_s1=st.session_state.nutrition_font_scale_s1,
                    font_scale_s2=st.session_state.nutrition_font_scale_s2,
                    font_scale_s3=st.session_state.nutrition_font_scale_s3,
                    font_scale_s4=st.session_state.nutrition_font_scale_s4,
                    font_scale_s5=st.session_state.nutrition_font_scale_s5,
                    font_scale_dist=st.session_state.nutrition_font_scale_dist,
                    margin_mm=nutr_margin_mm,
                    show_border=show_border_nutr
                )

                preview_img_bytes = pdf_to_preview_image(nutr_pdf_bytes, dpi=180)
                if preview_img_bytes:
                    st.image(preview_img_bytes, caption=f"Pratinjau Stiker Nilai Gizi ({nutr_sticker_sz})", use_container_width=True)
                else:
                    st.info("Membuat pratinjau...")

                c_dl1, c_dl2 = st.columns(2)
                with c_dl1:
                    st.download_button(
                        label="Unduh Stiker Gizi (PDF)",
                        data=nutr_pdf_bytes,
                        file_name=f"Stiker_Gizi_{st.session_state.nutrition_product_name.replace(' ', '_')}_{nutr_sticker_sz.replace(' ', '_')}.pdf",
                        mime="application/pdf",
                        type="primary",
                        icon=":material/download:",
                        use_container_width=True
                    )
                with c_dl2:
                    spec_pdf_bytes = build_nutrition_spec_sheet_pdf(
                        product_name=st.session_state.nutrition_product_name,
                        serving_size=serving_text_choice.replace("\n", " | "),
                        servings_per_pack="",
                        calories_total=st.session_state.nutrition_calories_total,
                        calories_fat=st.session_state.nutrition_calories_fat,
                        nutrients_list=st.session_state.nutrition_items,
                        footnote_text=f"{st.session_state.nutrition_footnote_id} {st.session_state.nutrition_footnote_en}",
                        raw_text_id=st.session_state.nutrition_raw_id,
                        raw_text_en=st.session_state.nutrition_raw_en,
                        company_name=st.session_state.company_name,
                        company_subtitle=st.session_state.company_subtitle,
                        company_logo_bytes=st.session_state.company_logo_bytes
                    )
                    st.download_button(
                        label="Unduh Lembar Spek Gizi (A4)",
                        data=spec_pdf_bytes,
                        file_name=f"Spesifikasi_Gizi_{st.session_state.nutrition_product_name.replace(' ', '_')}.pdf",
                        mime="application/pdf",
                        icon=":material/description:",
                        use_container_width=True
                    )
            except Exception as e:
                st.error(f"Gagal membuat pratinjau stiker gizi: {e}")

    # Hentikan eksekusi di sini agar tidak merender Langkah 02 & 03 Stiker Biasa
    st.stop()

# Step 2: Editor Teks Bilingual
st.markdown("""
<div class="step-header-box">
    <span class="step-pill">LANGKAH 02</span>
    <h3 class="step-title-text">Verifikasi &amp; Edit Teks Komposisi (Bilingual Editor)</h3>
</div>
""", unsafe_allow_html=True)
st.caption("Anda dapat menyunting teks di bawah ini untuk memperbaiki kata yang buram atau menyesuaikan terjemahan.")

# Metadata Produk
col_m1, col_m2, col_m3 = st.columns(3)
with col_m1:
    st.session_state.product_name = st.text_input("Nama Produk:", value=st.session_state.product_name)
with col_m2:
    st.session_state.variant_name = st.text_input("Varian / Jenis:", value=st.session_state.variant_name)
with col_m3:
    st.session_state.net_weight = st.text_input("Berat Bersih / Netto:", value=st.session_state.net_weight)

# Dua Kolom: Bahasa Indonesia vs Bahasa Inggris
col_id, col_en = st.columns(2)

with col_id:
    st.markdown("#### Teks Asli (Bahasa Indonesia)")
    text_id_input = st.text_area(
        "Teks yang terdeteksi dari kemasan:",
        value=st.session_state.raw_text_id,
        height=260,
        help="Edit teks jika ada huruf yang kurang tepat akibat pencahayaan foto kemasan."
    )
    st.session_state.raw_text_id = text_id_input

with col_en:
    st.markdown("#### Terjemahan (English)")
    text_en_input = st.text_area(
        "Terjemahan bahasa Inggris untuk label ekspor:",
        value=st.session_state.translated_text_en,
        height=260,
        help="Edit terjemahan jika ingin disesuaikan dengan istilah regulasi tertentu."
    )
    st.session_state.translated_text_en = text_en_input

# Tombol Terjemahkan Ulang
retranslate_col1, retranslate_col2 = st.columns([1.3, 2.7])
with retranslate_col1:
    if st.button("Terjemahkan Ulang", type="primary", icon=":material/sync:", help="Klik untuk memperbarui teks Bahasa Inggris berdasarkan editan Bahasa Indonesia"):
        if st.session_state.raw_text_id.strip():
            with st.spinner("Menerjemahkan ulang..."):
                active_engine = st.session_state.engine_choice
                if "3.7" in active_engine:
                    active_model = "gemini-3.7-flash"
                elif "Latest" in active_engine or "latest" in active_engine:
                    active_model = "gemini-flash-latest"
                else:
                    active_model = "gemini-3.8-flash"

                engine_type = "gemini" if ("Gemini" in active_engine and gemini_api_key) else "auto"
                new_en = translate_indonesian_to_english(
                    st.session_state.raw_text_id,
                    engine_choice=engine_type,
                    api_key=gemini_api_key,
                    model_name=active_model
                )
                st.session_state.translated_text_en = new_en
                st.rerun()

st.markdown("---")

# Step 3: Buat & Unduh Dokumen PDF
st.markdown("""
<div class="step-header-box">
    <span class="step-pill">LANGKAH 03</span>
    <h3 class="step-title-text">Ekspor Dokumen PDF Label Kemasan &amp; Stiker</h3>
</div>
""", unsafe_allow_html=True)

if not st.session_state.raw_text_id.strip() and not st.session_state.translated_text_en.strip():
    st.info("Unggah gambar label kemasan pada Langkah 1 terlebih dahulu untuk menghasilkan dokumen PDF.")
else:
    doc_format_choice = st.radio(
        "Pilih Format Desain PDF:",
        options=[
            "Label Stiker Cetak Kemasan (Format Milo Cube - Ukuran 3x5, 4x6, dll)",
            "Lembar Dokumen Spesifikasi Ekspor (Bilingual A4)"
        ],
        index=0 if "Milo Cube" in st.session_state.pdf_format_mode else 1,
        help="Pilih 'Label Stiker' untuk mencetak stiker kemasan langsung (ukuran 3x5 cm, 4x6 cm, dll). Pilih 'Lembar Dokumen' untuk arsip teknis A4."
    )
    st.session_state.pdf_format_mode = doc_format_choice

    safe_filename = "".join([c if c.isalnum() or c in " _-" else "_" for c in st.session_state.product_name]).strip()
    if not safe_filename:
        safe_filename = "Label_Kemasan"

    # ==================== OPSI 1: FORMAT LABEL STIKER (MILO CUBE) ====================
    if "Label Stiker" in doc_format_choice:
        col_cfg, col_prev = st.columns([1.3, 1.2])

        with col_cfg:
            st.markdown("#### Pengaturan Stiker Cetak Kemasan")
            
            with st.container(height=520, border=True, key="sticker_settings_scroll"):
                c_sz1, c_sz2 = st.columns(2)
                with c_sz1:
                    size_options = ["3x5 cm", "4x6 cm", "5x7 cm", "3x5 inch", "4x6 inch", "Kustom (mm)"]
                    current_sz_idx = 1
                    if st.session_state.sticker_size in size_options:
                        current_sz_idx = size_options.index(st.session_state.sticker_size)
                    sticker_size = st.selectbox(
                        "Pilihan Ukuran Stiker:",
                        options=size_options,
                        index=current_sz_idx,
                        help="Pilih ukuran stiker. Ukuran 4x6 cm dan 3x5 cm adalah standar umum untuk kemasan kecil/sedang."
                    )
                    st.session_state.sticker_size = sticker_size
                with c_sz2:
                    sticker_orient = st.selectbox(
                        "Orientasi Stiker:",
                        options=["Portrait (Tegak)", "Landscape (Mendatar)"],
                        index=0
                    )

                custom_w, custom_h = 40.0, 60.0
                if sticker_size == "Kustom (mm)":
                    ck1, ck2 = st.columns(2)
                    with ck1:
                        custom_w = st.number_input("Lebar (mm):", min_value=15.0, max_value=300.0, value=40.0, step=1.0)
                    with ck2:
                        custom_h = st.number_input("Tinggi (mm):", min_value=15.0, max_value=300.0, value=60.0, step=1.0)

                # Bagian Distributor / Importir / Produsen
                c_dh1, c_dh2 = st.columns([1, 1.4])
                with c_dh1:
                    hdr_options = ["", "IMPORTED BY :", "DISTRIBUTED BY :", "MANUFACTURED BY :", "DIPRODUKSI OLEH :", "KUSTOM :"]
                    cur_hdr_idx = 0
                    if st.session_state.distributor_header in hdr_options:
                        cur_hdr_idx = hdr_options.index(st.session_state.distributor_header)
                    elif st.session_state.distributor_header:
                        cur_hdr_idx = hdr_options.index("KUSTOM :")
                    
                    dist_hdr_select = st.selectbox(
                        "Header Pihak Produsen / Importir:",
                        options=hdr_options,
                        index=cur_hdr_idx,
                        format_func=lambda x: "(Kosong / Tanpa Header)" if x == "" else x,
                        help="Pilih teks judul importir/produsen atau biarkan kosong jika tidak diperlukan."
                    )
                    if dist_hdr_select == "KUSTOM :":
                        final_dist_hdr = st.text_input("Teks Header Kustom:", value=st.session_state.distributor_header if st.session_state.distributor_header not in hdr_options else "")
                    else:
                        final_dist_hdr = dist_hdr_select
                    st.session_state.distributor_header = final_dist_hdr

                with c_dh2:
                    dist_info_input = st.text_area(
                        "Detail Produsen / Distributor:",
                        value=st.session_state.distributor_info,
                        height=75,
                        help="Nama perusahaan, telepon, email, dll (persis format Milo Cube)"
                    )
                    st.session_state.distributor_info = dist_info_input

                # Pengaturan Ukuran Font Sendiri-Sendiri (Judul, Isi, Detail Produsen)
                st.markdown("**Pengaturan Ukuran Font:**")
                scale_title = st.slider(
                    "Besar Font Judul (Nama Produk & Netto):",
                    min_value=0.6,
                    max_value=1.6,
                    value=1.0,
                    step=0.05,
                    help="Ukuran font nama produk dan berat bersih/netto."
                )
                scale_body = st.slider(
                    "Besar Font Isi (Komposisi / Ingredients):",
                    min_value=0.6,
                    max_value=1.6,
                    value=1.0,
                    step=0.05,
                    help="Ukuran font daftar bahan / teks komposisi (ingredients)."
                )
                scale_dist = st.slider(
                    "Besar Font Detail Produsen / Distributor:",
                    min_value=0.6,
                    max_value=1.6,
                    value=1.0,
                    step=0.05,
                    help="Ukuran font keterangan importir / distributor / produsen."
                )

                # Pengaturan Format Teks & Margin Kertas Stiker
                st.markdown("**Pengaturan Format Teks:**")
                opt_upper = st.checkbox(
                    "Huruf Kapital Semua (UPPERCASE)",
                    value=True,
                    help="Standar label stiker kemasan internasional biasanya menggunakan huruf kapital bold tebal."
                )

                st.markdown("**Pengaturan Margin Stiker (Jarak Tepi Kertas):**")
                separate_margin = st.checkbox(
                    "Atur margin tiap sisi secara terpisah (Atas, Bawah, Kiri, Kanan)",
                    value=False,
                    help="Centang jika ingin mengatur jarak margin atas, bawah, kiri, dan kanan secara berbeda."
                )

                if separate_margin:
                    margin_left_val = st.slider(
                        "Margin Kiri (mm):",
                        min_value=0.5,
                        max_value=8.0,
                        value=2.5,
                        step=0.5,
                        help="Jarak teks dari tepi kiri kertas stiker."
                    )
                    margin_right_val = st.slider(
                        "Margin Kanan (mm):",
                        min_value=0.5,
                        max_value=8.0,
                        value=2.5,
                        step=0.5,
                        help="Jarak teks dari tepi kanan kertas stiker."
                    )
                    margin_top_val = st.slider(
                        "Margin Atas (mm):",
                        min_value=0.5,
                        max_value=8.0,
                        value=3.0,
                        step=0.5,
                        help="Jarak teks dari tepi atas kertas stiker."
                    )
                    margin_bottom_val = st.slider(
                        "Margin Bawah (mm):",
                        min_value=0.5,
                        max_value=8.0,
                        value=2.5,
                        step=0.5,
                        help="Jarak teks dari tepi bawah kertas stiker."
                    )
                else:
                    margin_h_val = st.slider(
                        "Margin Kiri & Kanan (Horizontal mm):",
                        min_value=0.5,
                        max_value=8.0,
                        value=2.5,
                        step=0.5,
                        help="Jarak teks dari tepi kiri dan kanan kertas stiker."
                    )
                    margin_v_val = st.slider(
                        "Margin Atas & Bawah (Vertikal mm):",
                        min_value=0.5,
                        max_value=8.0,
                        value=3.0,
                        step=0.5,
                        help="Jarak teks dari tepi atas dan bawah kertas stiker."
                    )
                    margin_left_val = margin_h_val
                    margin_right_val = margin_h_val
                    margin_top_val = margin_v_val
                    margin_bottom_val = margin_v_val

                selected_font = "GothamOffice-Bold"

        with col_prev:
            st.markdown("#### Pratinjau Hasil PDF Stiker")
            
            orient_val = "portrait" if "Portrait" in sticker_orient else "landscape"
            used_ing = st.session_state.translated_text_en if st.session_state.translated_text_en.strip() else st.session_state.raw_text_id

            try:
                sticker_pdf_bytes = build_sticker_label_pdf(
                    product_name=st.session_state.product_name,
                    net_weight=st.session_state.net_weight,
                    ingredients_text=used_ing,
                    distributor_header=st.session_state.distributor_header,
                    distributor_info=st.session_state.distributor_info,
                    size_choice=sticker_size.replace(" (mm)", "").strip(),
                    custom_width_mm=custom_w,
                    custom_height_mm=custom_h,
                    orientation=orient_val,
                    uppercase=opt_upper,
                    manual_font_scale=1.0,
                    font_scale_title=scale_title,
                    font_scale_body=scale_body,
                    font_scale_dist=scale_dist,
                    margin_left_mm=margin_left_val,
                    margin_right_mm=margin_right_val,
                    margin_top_mm=margin_top_val,
                    margin_bottom_mm=margin_bottom_val,
                    show_border=False,
                    font_family="GothamOffice-Bold",
                    include_company_logo=False,
                    company_logo_bytes=None
                )

                # Render preview gambar langsung dari PDF
                preview_png = pdf_to_preview_image(sticker_pdf_bytes, dpi=200)
                if preview_png:
                    st.image(
                        preview_png,
                        caption=f"Pratinjau Hasil Stiker ({sticker_size} - 1 Halaman Pas)",
                        width=270
                    )
                else:
                    st.info("Pratinjau tidak dapat dimuat, namun file PDF siap diunduh.")

                clean_sz = sticker_size.replace(" ", "_")
                sticker_file_name = f"{safe_filename}_Sticker_{clean_sz}.pdf"

                st.download_button(
                    label=f"Unduh PDF Stiker ({sticker_size})",
                    data=sticker_pdf_bytes,
                    file_name=sticker_file_name,
                    mime="application/pdf",
                    type="primary",
                    use_container_width=True
                )
                st.caption(f"Ukuran file PDF: {len(sticker_pdf_bytes):,} bytes | Siap dicetak langsung ke printer label.")

            except Exception as e:
                st.error(f"Gagal memproses PDF Stiker: {e}")

    # ==================== OPSI 2: FORMAT LEMBAR DOKUMEN SPESIFIKASI (A4) ====================
    else:
        image_for_pdf = st.session_state.processed_image_bytes if include_image_in_pdf else None
        try:
            pdf_bytes = build_bilingual_label_pdf(
                product_name=st.session_state.product_name,
                indonesian_text=st.session_state.raw_text_id,
                english_text=st.session_state.translated_text_en,
                image_bytes=image_for_pdf,
                company_name=st.session_state.company_name,
                company_subtitle=st.session_state.company_subtitle,
                company_logo_bytes=st.session_state.company_logo_bytes if include_logo_in_a4 else None,
                variant=st.session_state.variant_name,
                net_weight=st.session_state.net_weight,
                allergen_note_id="",
                allergen_note_en="",
                page_size_choice=page_size
            )
            
            pdf_file_name = f"{safe_filename}_Bilingual_Specification.pdf"

            col_d1, col_d2 = st.columns([1.5, 1.5])
            with col_d1:
                st.download_button(
                    label="Unduh Dokumen PDF Spesifikasi (A4)",
                    data=pdf_bytes,
                    file_name=pdf_file_name,
                    mime="application/pdf",
                    type="primary",
                    use_container_width=True
                )
            with col_d2:
                bilingual_txt = (
                    f"=== SPESIFIKASI LABEL: {st.session_state.product_name} ===\n"
                    f"Varian: {st.session_state.variant_name} | Netto: {st.session_state.net_weight}\n\n"
                    f"--- BAHASA INDONESIA ---\n{st.session_state.raw_text_id}\n\n"
                    f"--- ENGLISH TRANSLATION ---\n{st.session_state.translated_text_en}\n"
                )
                st.download_button(
                    label="Unduh Format Teks (.txt)",
                    data=bilingual_txt.encode("utf-8"),
                    file_name=f"{safe_filename}_Label.txt",
                    mime="text/plain",
                    use_container_width=True
                )
            st.success(f"Dokumen PDF A4 siap diunduh ({len(pdf_bytes):,} bytes)")

        except Exception as e:
            st.error(f"Gagal membuat file PDF A4: {e}")
