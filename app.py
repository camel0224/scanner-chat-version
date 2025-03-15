import streamlit as st
import cv2
import pytesseract
import numpy as np
import requests
from pyzbar.pyzbar import decode
from bs4 import BeautifulSoup
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Google Sheets Setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
client = gspread.authorize(creds)
sheet = client.open("Toilet Inventory").sheet1

# Streamlit UI
st.title("Toilet Inventory Scanner 📦🚽")

# 1️⃣ Upload Image from Camera or File
image_file = st.camera_input("Take a picture of the barcode") or st.file_uploader("Or upload an image", type=["jpg", "png", "jpeg"])

if image_file:
    file_bytes = np.asarray(bytearray(image_file.read()), dtype=np.uint8)
    image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

    # 2️⃣ Scan Barcode
    def scan_barcode(image):
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        barcodes = decode(gray)
        for barcode in barcodes:
            return barcode.data.decode("utf-8")
        return None

    barcode_result = scan_barcode(image)
    st.write(f"**Barcode:** {barcode_result}" if barcode_result else "**No barcode found.**")

    # 3️⃣ Extract Product Number
    def extract_product_number(image):
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        text = pytesseract.image_to_string(gray)
        for line in text.split("\n"):
            if "-" in line and any(char.isdigit() for char in line):  # Detect product number
                return line.strip()
        return None

    product_number = extract_product_number(image)
    st.write(f"**Product Number:** {product_number}" if product_number else "**No product number found.**")

    # 4️⃣ Search Ferguson, Home Depot, Lowe's
    def search_product(product_number):
        search_urls = {
            "Ferguson": f"https://www.google.com/search?q=site:ferguson.com+{product_number}",
            "Home Depot": f"https://www.google.com/search?q=site:homedepot.com+{product_number}",
            "Lowe's": f"https://www.google.com/search?q=site:lowes.com+{product_number}",
        }
        results = {}

        for store, url in search_urls.items():
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(url, headers=headers)
            soup = BeautifulSoup(response.text, "html.parser")

            for link in soup.find_all("a"):
                href = link.get("href")
                if store.lower() in href:
                    results[store] = href.split("&")[0].replace("/url?q=", "")
                    break
        return results

    if product_number:
        search_results = search_product(product_number)
        for store, link in search_results.items():
            st.write(f"**{store}:** [{link}]({link})")

    # 5️⃣ Save to Google Sheets
    if st.button("Save to Google Sheets"):
        sheet.append_row([product_number, barcode_result or "N/A", search_results.get("Ferguson", "Not Found"),
                          search_results.get("Home Depot", "Not Found"), search_results.get("Lowe's", "Not Found")])
        st.success("Saved to Google Sheets! ✅")
