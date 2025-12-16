import streamlit as st
from fpdf import FPDF
import pandas as pd
import datetime
from num2words import num2words
import tempfile
import numpy as np

import os

# --- HELPER: Save Uploaded File to Temp ---
def save_uploaded_file(uploaded_file):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}") as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            return tmp_file.name
    except Exception as e:
        st.error(f"Error handling file: {e}")
        return None

# --- PDF GENERATION CLASS ---
class InvoicePDF(FPDF):
    def header(self):
        pass

    def footer(self):
        # Position at 1.5 cm from bottom
        self.set_y(-15)
        self.set_font('Arial', 'I', 7) # Smaller font for footer
        self.set_text_color(128, 128, 128)
        #self.cell(0, 4, '*This is computer generated invoice no physical signature required.', 0, 1, 'C')
        #self.cell(0, 4, 'Digital signature is valid.', 0, 1, 'C')

def generate_pdf(invoice_data, items_df, bank_data, totals, logo_path, signature_path):
    # A4 Size = 210mm x 297mm
    pdf = InvoicePDF()
    pdf.set_auto_page_break(auto=False) # <--- CRITICAL: Force single page
    pdf.add_page()
    
    # --- BACKGROUND ---
    pdf.set_fill_color(245, 247, 250) 
    pdf.rect(0, 0, 210, 297, 'F') 

    # --- TOP HEADER ---
    y_curr = 10
    
    # Logo
    if logo_path:
        pdf.image(logo_path, x=10, y=y_curr, w=25)
    
    # "INVOICE" Title
    pdf.set_xy(150, y_curr + 5)
    pdf.set_font('Arial', 'B', 20)
    pdf.set_text_color(44, 62, 80)
    pdf.cell(50, 10, 'INVOICE', 0, 0, 'R')
    
    # Reset Y for next section (Moved up slightly to save space)
    if logo_path:
        y_curr = 35
    else:
        y_curr = 20
    
    pdf.set_xy(10, y_curr)
    
    # Studio Name
    pdf.set_font('Arial', 'B', 16)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 8, invoice_data['billed_by_name'], 0, 1, 'L')
    
    # --- COLUMNS: BILLED BY vs INVOICE DETAILS ---
    y_cols_start = pdf.get_y() + 2
    
    # LEFT: Billed By
    pdf.set_xy(10, y_cols_start)
    pdf.set_font('Arial', 'B', 9)
    pdf.set_text_color(50, 50, 50)
    pdf.cell(90, 4, "Billed By:", 0, 1)
    pdf.set_font('Arial', '', 9)
    pdf.cell(90, 4, invoice_data['sender_person'], 0, 1)
    pdf.multi_cell(90, 4, invoice_data['sender_address'])
    pdf.cell(90, 4, f"GSTIN: {invoice_data['sender_gst']}", 0, 1)
    pdf.cell(90, 4, f"PAN: {invoice_data['sender_pan']}", 0, 1)
    pdf.cell(90, 4, f"Email: {invoice_data['sender_email']}", 0, 1)
    pdf.cell(90, 4, f"Phone: {invoice_data['sender_phone']}", 0, 1)
    
    left_col_end = pdf.get_y()

    # RIGHT: Invoice Details
    pdf.set_xy(120, y_cols_start)
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(80, 5, f"Invoice No: {invoice_data['invoice_no']}", 0, 1, 'R')
    pdf.set_xy(120, pdf.get_y())
    pdf.cell(80, 5, f"Date: {invoice_data['date'].strftime('%d-%b-%Y')}", 0, 1, 'R')
    
    # Determine start of next section (whichever column is longer)
    y_next = max(left_col_end, pdf.get_y()) + 4
    
    # --- BILLED TO ---
    pdf.set_xy(10, y_next)
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(0, 4, "Billed To:", 0, 1)
    pdf.set_font('Arial', '', 9)
    pdf.cell(0, 4, invoice_data['client_name'], 0, 1)
    pdf.multi_cell(0, 4, invoice_data['client_address'])
    pdf.cell(0, 4, f"PAN: {invoice_data['client_phone']}", 0, 1)
    pdf.cell(0, 4, f"GSTIN: {invoice_data['client_gst']}", 0, 1)
    
    # Divider
    pdf.ln(3)
    pdf.set_draw_color(200, 200, 200)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(3)

    # --- PROJECT DETAILS (Compact Grid) ---
    pdf.set_text_color(50, 50, 50)
    pdf.set_font('Arial', 'B', 9); pdf.cell(25, 5, "Service:", 0, 0)
    pdf.set_font('Arial', '', 9); pdf.cell(70, 5, invoice_data['service_desc'], 0, 0)
    
    pdf.set_font('Arial', 'B', 9); pdf.cell(25, 5, "HSN/SAC:", 0, 0)
    pdf.set_font('Arial', '', 9); pdf.cell(0, 5, invoice_data['hsn_sac'], 0, 1)

    pdf.set_font('Arial', 'B', 9); pdf.cell(25, 5, "Project:", 0, 0)
    pdf.set_font('Arial', '', 9); pdf.cell(70, 5, invoice_data['project_name'], 0, 0)

    pdf.set_font('Arial', 'B', 9); pdf.cell(25, 5, "Designation:", 0, 0)
    pdf.set_font('Arial', '', 9); pdf.cell(0, 5, invoice_data['designation'], 0, 1)
    
    pdf.ln(5)

    # --- ITEMS TABLE ---
    # Header
    pdf.set_fill_color(225, 230, 235) 
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(140, 7, "Description / Period", 1, 0, 'L', 1)
    pdf.cell(50, 7, "Amount (INR)", 1, 1, 'R', 1)
    
    # Rows
    pdf.set_fill_color(255, 255, 255) 
    pdf.set_font('Arial', '', 9)
    

    for index, row in items_df.iterrows():
        pdf.cell(140, 7, str(row['Description']), 1, 0, 'L', 1)
        pdf.cell(50, 7, f"{row['Amount']:,.2f}", 1, 1, 'R', 1)
    
    pdf.ln(5)

    # --- BOTTOM SECTION (Bank & Totals) ---
    # We fix this section towards the bottom half to ensure it fits, 
    # but flows naturally after the table.
    
    y_bottom_start = pdf.get_y()
    
    # Bank Details (Left)
    pdf.set_xy(10, y_bottom_start)
    pdf.set_font('Arial', 'B', 9)
    pdf.set_text_color(50, 50, 50)
    pdf.cell(100, 5, "Bank Details:", 0, 1)
    pdf.set_font('Arial', '', 8) # Slightly smaller for bank info to fit tight
    pdf.cell(30, 4, "Account Name:", 0, 0); pdf.cell(0, 4, bank_data['acc_name'], 0, 1)
    pdf.cell(30, 4, "Account No:", 0, 0); pdf.cell(0, 4, bank_data['acc_no'], 0, 1)
    pdf.cell(30, 4, "IFSC Code:", 0, 0); pdf.cell(0, 4, bank_data['ifsc'], 0, 1)
    pdf.cell(30, 4, "Bank Name:", 0, 0); pdf.cell(0, 4, bank_data['bank_name'], 0, 1)
    pdf.cell(30, 4, "Account Type:", 0, 0); pdf.cell(0, 4, bank_data['acc_type'], 0, 1)

    # Totals (Right)
    pdf.set_xy(130, y_bottom_start)
    pdf.set_font('Arial', '', 9)
    pdf.cell(30, 5, "Sub Total:", 0, 0, 'R'); pdf.cell(30, 5, f"{totals['subtotal']:,.0f}", 0, 1, 'R')
    pdf.set_xy(130, pdf.get_y())
    pdf.cell(30, 5, "GST (18%):", 0, 0, 'R'); pdf.cell(30, 5, f"{totals['gst']:,.0f}", 0, 1, 'R')
    
    pdf.set_xy(130, pdf.get_y() + 2)
    pdf.set_fill_color(44, 62, 80)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(60, 8, f" Total: {totals['grand_total']:,.0f} ", 0, 1, 'R', 1)
    
    # Words
    pdf.set_text_color(0, 0, 0)
    pdf.set_xy(10, max(pdf.get_y(), y_bottom_start + 30) + 5) # Ensure we are below bank details
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(0, 5, "Total (in words):", 0, 1)
    pdf.set_font('Arial', 'I', 9)
    pdf.multi_cell(0, 5, f"{totals['words']} Only".upper())

    # --- SIGNATURE (Absolute positioning at bottom right) ---
    # We place this fixed at Y=250 (near bottom of A4)
    sig_y_fixed = 245
    
    if signature_path:
        pdf.image(signature_path, x=150, y=sig_y_fixed - 15, w=35) # Place image slightly above name

    pdf.set_xy(120, sig_y_fixed)
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(70, 5, f"From {invoice_data['billed_by_name']}", 0, 1, 'R')
    pdf.set_xy(120, pdf.get_y())
    pdf.cell(70, 5, invoice_data['sender_person'], 0, 1, 'R')
    pdf.set_font('Arial', '', 8)
    pdf.cell(180, 4, "(Proprietor)", 4, 4, 'R')
    #pdf.set_xy(120, pdf.get_y() - 1)

    return pdf.output(dest='S').encode('latin-1')

# --- STREAMLIT UI ---
st.set_page_config(page_title="One-Page Invoice", layout="wide")
st.title("🧾 Single Page Invoice Generator")

# --- SIDEBAR ---
with st.sidebar:
    st.header("🎨 Branding")
    uploaded_logo = st.file_uploader("Upload Logo", type=['png', 'jpg'])
    uploaded_signature = st.file_uploader("Upload Signature", type=['png', 'jpg'])

col1, col2 = st.columns(2)

# --- INPUTS ---
with col1:
    st.subheader("Billed By")
    billed_by_name = st.text_input("Studio Name", "GRAFFITI STUDIO")
    sender_person = st.text_input("Proprietor Name", "RISHI ANAND")
    sender_address = st.text_area("Your Address", "D-243, Goyla Dairy, Qutub Vihar Ph-1, Samta Enclave, New Delhi-110071")
    sender_gst = st.text_input("Your GSTIN", "07BAWPA1626B2Z1")
    sender_pan = st.text_input("Your PAN", "BAWPA1626B")
    sender_email = st.text_input("Email", "rishianand@graffitistudio.in")
    sender_phone = st.text_input("Your Phone", "+91 9871097871")

with col2:
    st.subheader("Billed To")
    client_name = st.text_input("Client Name", "SOL PRODUCTION LLP")
    client_address = st.text_area("Client Address", "74 Russell House, 2nd Floor, Hasnabad Road, Khar West, Mumbai, Maharashtra 400052")
    client_phone = st.text_input("Pan No.", "AFPFS6334H ")
    client_gst = st.text_input("Client GSTIN", "27AFPFS6334H1ZI")
    st.divider()
    invoice_no = st.text_input("Invoice No", "06")
    invoice_date = st.date_input("Invoice Date", datetime.date.today())

st.subheader("Project Details")
p_col1, p_col2 = st.columns(2)
with p_col1:
    project_name = st.text_input("Project Name", "The great Indian Kapil Show Season 4")
    designation = st.text_input("Designation", "Senior Post Producer")
    
with p_col2:
    service_desc = st.text_input("Service Type", "Audio-visual post-production services")
    hsn_sac = st.text_input("HSN/SAC Code", "999613")
    

st.subheader("Invoice Items")
default_items = pd.DataFrame([
    {"Description": "Monthly salary: 160000", "Amount": 0},
    {"Description": "5th Nov 2025 to 30th Nov 2025(26days)", "Amount": 138666},
])
items_df = st.data_editor(default_items, num_rows="dynamic", use_container_width=True)

st.subheader("Bank Details")
b_col1, b_col2 = st.columns(2)
with b_col1:
    acc_name = st.text_input("Account Name", "GRAFFITI STUDIO")
    acc_no = st.text_input("Account Number", "50200110989706")
    ifsc = st.text_input("IFSC Code", "HDFC0001357")
with b_col2:
    bank_name = st.text_input("Bank Name", "HDFC BANK")
    acc_type = st.text_input("Account Type", "Current Account")

if not items_df.empty:
    subtotal = items_df['Amount'].sum()
    gst_amount = subtotal * 0.18
    grand_total = subtotal + gst_amount
    total_words = num2words(np.ceil(grand_total), lang='en_IN')
    
    totals = {"subtotal": subtotal, "gst": gst_amount, "grand_total": grand_total, "words": total_words}
    
    invoice_data = {
        "billed_by_name": billed_by_name, "sender_person": sender_person,
        "sender_address": sender_address, "sender_gst": sender_gst,
        "sender_pan": sender_pan, "sender_email": sender_email,
        "sender_phone": sender_phone, "client_name": client_name,
        "client_address": client_address, "client_phone": client_phone,
        "client_gst": client_gst, "invoice_no": invoice_no,
        "date": invoice_date, "project_name": project_name,
        "designation": designation, "service_desc": service_desc,
        "hsn_sac": hsn_sac
    }
    
    bank_data = {
        "acc_name": acc_name, "acc_no": acc_no, "ifsc": ifsc, "bank_name": bank_name, "acc_type": acc_type
    }

    st.divider()
    st.metric("Grand Total", f"₹{grand_total:,.2f}")
    
    if st.button("Generate PDF Invoice"):
        logo_path = save_uploaded_file(uploaded_logo) if uploaded_logo else None
        signature_path = save_uploaded_file(uploaded_signature) if uploaded_signature else None
        
        try:
            pdf_bytes = generate_pdf(invoice_data, items_df, bank_data, totals, logo_path, signature_path)
            st.success("PDF Generated Successfully!")
            st.download_button(
                label="Download PDF",
                data=pdf_bytes,
                file_name=f"Invoice_{invoice_no}.pdf",
                mime="application/pdf"
            )
        finally:
            if logo_path and os.path.exists(logo_path): os.remove(logo_path)
            if signature_path and os.path.exists(signature_path): os.remove(signature_path)
