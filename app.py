from flask import Flask, jsonify, request, render_template, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
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

# Define the User model for registration and login
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)

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

# Saving to desktop
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

# User registration endpoint
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password, method='sha256')

        # Check if user already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            return "User already exists"

        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

# User login endpoint
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            return redirect(url_for('create_invoice_page'))
        return "Invalid username or password"
    return render_template('login.html')

# User logout endpoint
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

# Decorator to ensure user is logged in
def login_required(f):
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

# Endpoint HTML invoice creation page (requires login)
@app.route('/create-invoice')
@login_required
def create_invoice_page():
    return render_template('invoice.html')

@app.route('/invoice', methods=['POST'])
@login_required
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

    # Generate UBL XML and save it
    ubl_invoice_xml = generate_ubl_invoice(new_invoice)
    xml_filename = f"invoice_{new_invoice.invoice_number}.xml"
    xml_path = save_to_desktop(xml_filename, ubl_invoice_xml)

    # Generate PDF invoice and save it
    pdf_path = generate_pdf_invoice(new_invoice)

    # Return a success message, converting paths to strings
    return jsonify({
        'message': 'Invoice created successfully',
        'invoice_id': new_invoice.id,
        'xml_filename': str(xml_path),  # Convert to string
        'pdf_filename': str(pdf_path)   # Convert to string
    }), 201

# Retrieve all invoices (GET method)
@app.route('/invoices', methods=['GET'])
@login_required
def get_all_invoices():
    invoices = Invoice.query.all()
    invoice_list = []
    for invoice in invoices:
        invoice_list.append({
            'id': invoice.id,
            'invoice_number': invoice.invoice_number,
            'date': invoice.date,
            'due_date': invoice.due_date,
            'from_name': invoice.from_name,
            'from_address': invoice.from_address,
            'from_city': invoice.from_city,
            'from_phone': invoice.from_phone,
            'from_email': invoice.from_email,
            'to_name': invoice.to_name,
            'to_address': invoice.to_address,
            'to_city': invoice.to_city,
            'to_phone': invoice.to_phone,
            'to_email': invoice.to_email,
            'description': invoice.description,
            'amount': invoice.amount
        })
    return jsonify(invoice_list)

# Retrieve a specific invoice by ID (GET method)
@app.route('/invoice/<int:id>', methods=['GET'])
@login_required
def get_invoice(id):
    invoice = Invoice.query.get_or_404(id)
    return jsonify({
        'id': invoice.id,
        'invoice_number': invoice.invoice_number,
        'date': invoice.date,
        'due_date': invoice.due_date,
        'from_name': invoice.from_name,
        'from_address': invoice.from_address,
        'from_city': invoice.from_city,
        'from_phone': invoice.from_phone,
        'from_email': invoice.from_email,
        'to_name': invoice.to_name,
        'to_address': invoice.to_address,
        'to_city': invoice.to_city,
        'to_phone': invoice.to_phone,
        'to_email': invoice.to_email,
        'description': invoice.description,
        'amount': invoice.amount
    })

if __name__ == '__main__':
    db.create_all()
    app.run(debug=True)
