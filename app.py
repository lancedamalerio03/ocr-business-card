import os
import io
import streamlit as st
import pandas as pd

from utils.ocr_utils import process_uploaded_image

import gspread
from google.oauth2.service_account import Credentials

# — Streamlit page setup —
st.set_page_config(page_title="Business Card OCR → Google Sheets", layout="wide")

# Custom styling
st.markdown(
    """
    <style>
        .main {
            padding: 2rem;
        }
        .stButton>button { 
            background-color: #00B388 !important; 
            color: white !important; 
        }
        .css-1lcbmhc { 
            padding-top: 1rem !important; 
        }
        .centered-header {
            display: flex;
            align-items: center;
            justify-content: center;
            margin-bottom: 3rem;
            margin-top: 2rem;
        }
        .header-logo {
            margin-right: 1.5rem;
        }
        .header-title {
            font-size: 2.5rem;
            font-weight: 600;
            color: white;
            margin: 0;
        }
        .section-spacing {
            margin-top: 3rem;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# Initialize session state
if 'openai_api_key' not in st.session_state:
    st.session_state.openai_api_key = ''
if 'processed_cards' not in st.session_state:
    st.session_state.processed_cards = None
if 'upload_key' not in st.session_state:
    st.session_state.upload_key = 0
if 'selected_model' not in st.session_state:
    st.session_state.selected_model = 'gpt-4o-mini'

# Function to validate OpenAI API key
def validate_openai_key(api_key: str) -> bool:
    """Simple validation - you can enhance this with actual API call"""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        # Make a simple API call to test the key
        response = client.models.list()
        return True
    except Exception as e:
        return False

# API Key Validation Page
if not st.session_state.openai_api_key:
    # Logo in left corner, title centered
    col1, col2, col3 = st.columns([1, 6, 1])
    
    with col1:
        st.image("images/keepital.png", width=120)
    
    with col2:
        st.markdown('<h1 style="text-align: center; margin-top: 1rem;">Keepital Business Card Reader</h1>', unsafe_allow_html=True)
    
    # API Key section with better spacing
    st.markdown('<div style="margin-top: 3rem;">', unsafe_allow_html=True)
    st.markdown("## OpenAI API Key Required")
    st.markdown("Please enter your OpenAI API key to start using the business card reader")
    
    api_key = st.text_input(
        "OpenAI API Key",
        type="password",
        placeholder="Enter your OpenAI API key here...",
        help="Your API key will not be stored and is only used for this session. You can find this in your OpenAI dashboard.",
        label_visibility="collapsed"
    )
    
    if api_key:
        if st.button("Validate API Key", type="primary"):
            with st.spinner("Validating API key..."):
                if validate_openai_key(api_key):
                    st.session_state.openai_api_key = api_key
                    st.success("API key validated successfully! You can now use the business card reader.")
                    st.rerun()
                else:
                    st.error("Invalid API key. Please check your API key and try again.")
    
    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# Main Application (after API key validation)
# Header with logo in left corner and centered title
col1, col2, col3 = st.columns([1, 6, 1])

with col1:
    st.image("images/keepital.png", width=120)

with col2:
    st.markdown('<h1 style="text-align: center; margin-top: 1rem;">Keepital Business Card Reader</h1>', unsafe_allow_html=True)
   

st.markdown("---")

# Model Selection Section
st.markdown("### 🤖 AI Model Selection")
col1, col2 = st.columns(2)

with col1:
    model_options = {
        'gpt-4o-mini': 'GPT-4o Mini (Recommended) - Fast & Cost-effective',
        'gpt-3.5-turbo': 'GPT-3.5 Turbo - Most Affordable',
        'gpt-4': 'GPT-4 - Most Capable (Expensive)',
        'gpt-4o': 'GPT-4o - Latest & Advanced'
    }
    
    selected_model = st.selectbox(
        "Choose AI Model",
        options=list(model_options.keys()),
        format_func=lambda x: model_options[x],
        index=0,  # Default to gpt-4o-mini
        help="Select the AI model for processing business cards. GPT-4o Mini offers the best balance of speed, accuracy, and cost for this task."
    )
    
    st.session_state.selected_model = selected_model

with col2:
    # Model info display
    model_info = {
        'gpt-4o-mini': {'cost': 'Low', 'speed': 'Fast', 'accuracy': 'High'},
        'gpt-3.5-turbo': {'cost': 'Lowest', 'speed': 'Fastest', 'accuracy': 'Good'},
        'gpt-4': {'cost': 'High', 'speed': 'Slower', 'accuracy': 'Highest'},
        'gpt-4o': {'cost': 'High', 'speed': 'Fast', 'accuracy': 'Highest'}
    }
    
    info = model_info[selected_model]
    st.markdown("**Model Details:**")
    st.markdown(f"💰 **Cost**: {info['cost']}")
    st.markdown(f"⚡ **Speed**: {info['speed']}")
    st.markdown(f"🎯 **Accuracy**: {info['accuracy']}")

st.markdown("---")

# Show API key status
with st.expander("🔑 API Key Status", expanded=False):
    st.success("✅ OpenAI API key is configured and validated")
    if st.button("Reset API Key"):
        st.session_state.openai_api_key = ''
        st.rerun()

# — Google Sheets auth - FIXED to read SHEET_ID from google section —
st.markdown("### Google Sheets Configuration")
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

try:
    # Check if running on Streamlit Cloud (has secrets) or locally
    if "google" in st.secrets:
        # Running on Streamlit Cloud - use secrets
        creds = Credentials.from_service_account_info(st.secrets["google"], scopes=SCOPES)
        
        # FIXED: Look for SHEET_ID in the google section, not at root level
        if "SHEET_ID" in st.secrets["google"]:
            sheet_id = st.secrets["google"]["SHEET_ID"]
        else:
            st.error("❌ SHEET_ID not found in google section of secrets")
            st.stop()
            
        st.success("✅ Google Sheets authentication successful (using Streamlit secrets)")
    else:
        # Running locally - use environment variables
        sa_file = os.getenv("SERVICE_ACCOUNT_FILE")
        if not sa_file or not os.path.isfile(sa_file):
            st.error("🔑 SERVICE_ACCOUNT_FILE not set or file not found in .env")
            st.stop()
        
        creds = Credentials.from_service_account_file(sa_file, scopes=SCOPES)
        sheet_id = os.getenv("SHEET_ID")
        if not sheet_id:
            st.error("🆔 SHEET_ID not set in .env")
            st.stop()
        st.success("✅ Google Sheets authentication successful (using local .env)")
    
    gc = gspread.authorize(creds)
    
except Exception as e:
    st.error(f"❌ Google Sheets authentication failed: {e}")
    st.stop()

try:
    worksheet = gc.open_by_key(sheet_id).sheet1
    sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}"
    st.info(f"📋 Connected to Google Sheet: [Open Sheet]({sheet_url})")
except Exception as e:
    st.error(f"❌ Failed to connect to Google Sheet: {e}")
    st.stop()

st.markdown("---")

# — File Upload Section —
st.markdown("### Upload Business Cards")

# — File uploader (key changes to reset) —
uploader_key = f"uploader_{st.session_state.upload_key}"
uploaded_files = st.file_uploader(
    "Upload business card images (PNG/JPG)",
    type=["png", "jpg", "jpeg"],
    accept_multiple_files=True,
    key=uploader_key,
    help="You can upload multiple business card images at once"
)

# — Images ready info —
if uploaded_files:
    st.info(f"📁 {len(uploaded_files)} image{'s' if len(uploaded_files)>1 else ''} ready for processing.")
    
    # Show preview of uploaded images
    with st.expander("🖼️ Preview Uploaded Images", expanded=False):
        cols = st.columns(min(len(uploaded_files), 3))
        for idx, img in enumerate(uploaded_files[:3]):  # Show first 3 images
            with cols[idx % 3]:
                st.image(img, caption=img.name, use_container_width=True)
        if len(uploaded_files) > 3:
            st.info(f"... and {len(uploaded_files) - 3} more images")

# — Process Images —
if uploaded_files and st.button("🔄 Process Images", type="primary"):
    all_cards = []
    progress_text = st.empty()
    progress_bar = st.progress(0)
    
    with st.spinner("Processing images with AI..."):
        total = len(uploaded_files)
        for idx, img in enumerate(uploaded_files, start=1):
            try:
                progress_text.text(f"Processing {img.name}... ({idx}/{total})")
                cards = process_uploaded_image(img, st.session_state.openai_api_key, st.session_state.selected_model)
                all_cards.extend(cards)
                st.success(f"✅ Processed {img.name}")
            except Exception as e:
                st.error(f"❌ Failed to process {img.name}: {e}")
            
            progress_bar.progress(int(idx/total*100))
        
        progress_text.text(f"✅ Processing complete! Extracted {len(all_cards)} contact(s)")
    
    st.session_state.processed_cards = all_cards

# — Preview and Append —
if st.session_state.processed_cards:
    st.markdown("---")
    st.markdown("### 📋 Extracted Contact Information")
    
    df = pd.DataFrame(st.session_state.processed_cards)
    
    # Show summary statistics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Contacts", len(df))
    with col2:
        st.metric("With Email", len(df[df['email'].notna()]))
    with col3:
        st.metric("With Mobile", len(df[df['mobile_number'].notna()]))
    
    # Show preview
    st.subheader("Preview (first 10 rows)")
    st.dataframe(df.head(10), use_container_width=True)
    
    if len(df) > 10:
        with st.expander("📄 View All Extracted Data", expanded=False):
            st.dataframe(df, use_container_width=True)
    
    # Export options
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📊 Append to Google Sheet", type="primary"):
            with st.spinner("Appending to Google Sheet..."):
                rows = df.fillna("").values.tolist()
                try:
                    worksheet.append_rows(rows, value_input_option="RAW")
                    st.success(f"✅ Successfully appended {len(rows)} rows to Google Sheet!")
                    st.markdown(f"🔗 [Open Google Sheet]({sheet_url})")
                    
                    # Set flag for successful upload
                    st.session_state.upload_successful = True
                    st.balloons()  # Celebration effect
                except Exception as e:
                    st.error(f"❌ Error appending rows: {e}")
    
    with col2:
        # Download as CSV option
        csv = df.to_csv(index=False)
        st.download_button(
            label="💾 Download as CSV",
            data=csv,
            file_name="business_cards_contacts.csv",
            mime="text/csv"
        )
    
    # Reset section after successful upload
    if st.session_state.get('upload_successful', False):
        st.markdown("---")
        st.markdown("### 🎉 Upload Complete!")
        col1, col2, col3 = st.columns([2, 1, 2])
        with col2:
            if st.button("🔄 Process More Cards", type="secondary", use_container_width=True):
                # Clear all processing data and refresh
                st.session_state.processed_cards = None
                st.session_state.upload_key += 1
                st.session_state.upload_successful = False
                st.rerun()

# Footer
st.markdown("---")
st.markdown("### Usage Guide")
st.markdown("""
- Use clear, high-resolution images
- Ensure business cards are well-lit and not blurry
- Cards should be oriented correctly (not upside down)
- Do not used Scanned Images
- Cards with handwritten text may not be extracted accurately 
- Cards with with texts that use complex fonts may not be extracted correctly 
- Multiple cards can be processed in one batch
- Skim through the extracted data before appending to Google Sheets
""")