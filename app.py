from flask import Flask, jsonify, request, render_template
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import xml.etree.ElementTree as ET
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
import os
import pathlib

# Load the env
load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///einvoices.db'
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

db = SQLAlchemy(app)

# Define the Invoice model data
class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(50))
    date = db.Column(db.String(20))
    due_date = db.Column(db.String(20))
    from_name = db.Column(db.String(255))
    from_address = db.Column(db.String(255))
    from_city = db.Column(db.String(255))
    from_phone = db.Column(db.String(50))
    from_email = db.Column(db.String(255))
    to_name = db.Column(db.String(255))
    to_address = db.Column(db.String(255))
    to_city = db.Column(db.String(255))
    to_phone = db.Column(db.String(50))
    to_email = db.Column(db.String(255))
    description = db.Column(db.String(255))
    amount = db.Column(db.Float)

# Function to generate UBL XML
def generate_ubl_invoice(invoice):
    root = ET.Element("Invoice", xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2")
    cbc_id = ET.SubElement(root, "cbc:ID")
    cbc_id.text = invoice.invoice_number
    cbc_issue_date = ET.SubElement(root, "cbc:IssueDate")
    cbc_issue_date.text = invoice.date
    cbc_due_date = ET.SubElement(root, "cbc:DueDate")
    cbc_due_date.text = invoice.due_date
    cbc_currency_code = ET.SubElement(root, "cbc:DocumentCurrencyCode")
    cbc_currency_code.text = "MYR"  # Malaysian Ringgit currency 
    supplier_party = ET.SubElement(root, "cac:AccountingSupplierParty")
    supplier_party_name = ET.SubElement(supplier_party, "cbc:PartyName")
    supplier_party_name.text = invoice.from_name
    customer_party = ET.SubElement(root, "cac:AccountingCustomerParty")
    customer_party_name = ET.SubElement(customer_party, "cbc:PartyName")
    customer_party_name.text = invoice.to_name
    invoice_line = ET.SubElement(root, "cac:InvoiceLine")
    invoice_line_id = ET.SubElement(invoice_line, "cbc:ID")
    invoice_line_id.text = "1"
    quantity = ET.SubElement(invoice_line, "cbc:InvoicedQuantity", unitCode="EA")
    quantity.text = "1"
    line_amount = ET.SubElement(invoice_line, "cbc:LineExtensionAmount", currencyID="MYR")
    line_amount.text = str(invoice.amount)
    xml_string = ET.tostring(root, encoding="utf-8", method="xml")
    return xml_string

#saving to desktop
def save_to_desktop(filename, content, binary_mode=True):
    desktop_path = pathlib.Path.home() / "Desktop"
    file_path = desktop_path / filename
    mode = 'wb' if binary_mode else 'w'
    with open(file_path, mode) as file:
        file.write(content)
    return file_path

# Function to generate PDF invoice
def generate_pdf_invoice(invoice):
    desktop_path = pathlib.Path.home() / "Desktop"
    filename = f"invoice_{invoice.invoice_number}.pdf"  # Using the invoice number input as same as the file name
    filepath = desktop_path / filename
    
    # Create PDF 
    c = canvas.Canvas(str(filepath), pagesize=A4)
    width, height = A4
    c.setFont("Helvetica-Bold", 24)
    c.drawString(1 * inch, height - 1 * inch, "INVOICE")

    # Invoice design
    c.setFont("Helvetica", 12)
    c.drawString(1 * inch, height - 1.5 * inch, f"Invoice Number: {invoice.invoice_number}")
    c.drawString(1 * inch, height - 1.75 * inch, f"Date: {invoice.date}")
    c.drawString(4 * inch, height - 1.75 * inch, f"Due Date: {invoice.due_date}")

    c.setFont("Helvetica-Bold", 14)
    c.drawString(1 * inch, height - 2.25 * inch, "Bill From")
    c.setFont("Helvetica", 12)
    c.drawString(1 * inch, height - 2.5 * inch, invoice.from_name)
    c.drawString(1 * inch, height - 2.65 * inch, invoice.from_address)
    c.drawString(1 * inch, height - 2.8 * inch, invoice.from_city)
    c.drawString(1 * inch, height - 2.95 * inch, f"Phone: {invoice.from_phone}")
    c.drawString(1 * inch, height - 3.1 * inch, f"Email: {invoice.from_email}")

    c.setFont("Helvetica-Bold", 14)
    c.drawString(4 * inch, height - 2.25 * inch, "Bill To")
    c.setFont("Helvetica", 12)
    c.drawString(4 * inch, height - 2.5 * inch, invoice.to_name)
    c.drawString(4 * inch, height - 2.65 * inch, invoice.to_address)
    c.drawString(4 * inch, height - 2.8 * inch, invoice.to_city)
    c.drawString(4 * inch, height - 2.95 * inch, f"Phone: {invoice.to_phone}")
    c.drawString(4 * inch, height - 3.1 * inch, f"Email: {invoice.to_email}")

    c.drawString(1 * inch, height - 3.5 * inch, "DESCRIPTION")
    c.drawString(5.5 * inch, height - 3.5 * inch, "AMOUNT")
    y = height - 3.75 * inch
    c.drawString(1 * inch, y, invoice.description)
    c.drawString(5.5 * inch, y, f"MYR {invoice.amount:.2f}")


    c.setFont("Helvetica-Bold", 12)
    c.drawString(4.5 * inch, y - 0.5 * inch, "TOTAL")
    c.drawString(5.5 * inch, y - 0.5 * inch, f"MYR {invoice.amount:.2f}")
    c.showPage()
    c.save()
    return filepath

# endpoint HTML invoice creation page
@app.route('/create-invoice')
def create_invoice_page():
    return render_template('invoice.html')

# Create the Invoice and Save XML and PDF with Invoice Number in the filename
@app.route('/invoice', methods=['POST'])
def create_invoice():
    data = request.get_json()
    
    # Create the invoice in the database
    new_invoice = Invoice(
        invoice_number=data['invoiceNumber'],
        date=data['date'],
        due_date=data['dueDate'],
        from_name=data['fromName'],
        from_address=data['fromAddress'],
        from_city=data['fromCity'],
        from_phone=data['fromPhone'],
        from_email=data['fromEmail'],
        to_name=data['toName'],
        to_address=data['toAddress'],
        to_city=data['toCity'],
        to_phone=data['toPhone'],
        to_email=data['toEmail'],
        description=data['description'],
        amount=data['amount']
    )
    db.session.add(new_invoice)
    db.session.commit()

    # Generate UBL XML the save it
    ubl_invoice_xml = generate_ubl_invoice(new_invoice)
    xml_filename = f"invoice_{new_invoice.invoice_number}.xml"  # Use invoice number in filename
    save_to_desktop(xml_filename, ubl_invoice_xml)

    # Generate PDF invoice then save it
    pdf_filename = generate_pdf_invoice(new_invoice)

    return jsonify({
        'message': 'Invoice created successfully',
        'xml_invoice_path': str(pathlib.Path.home() / "Desktop" / xml_filename),
        'pdf_invoice_path': str(pdf_filename)
    }), 201

if __name__ == '__main__':
    db.create_all()
    app.run(debug=True)
