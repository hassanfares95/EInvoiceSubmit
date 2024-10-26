from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import os
import pathlib
import xml.etree.ElementTree as ET  # Use Python's built-in XML library

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///einvoices.db'
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

db = SQLAlchemy(app)

# Define the Invoice model
class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(255))
    amount = db.Column(db.Float)
    date = db.Column(db.String(20))
    status = db.Column(db.String(50))  # Status of the invoice

# Function to generate UBL XML for the invoice
def generate_ubl_invoice(invoice):
    # Create the root element for the UBL Invoice
    root = ET.Element("Invoice", xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2")
    
    # Add basic UBL elements
    cbc_id = ET.SubElement(root, "cbc:ID", xmlns="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2")
    cbc_id.text = str(invoice.id)
    
    cbc_issue_date = ET.SubElement(root, "cbc:IssueDate")
    cbc_issue_date.text = invoice.date
    
    cbc_invoice_type_code = ET.SubElement(root, "cbc:InvoiceTypeCode")
    cbc_invoice_type_code.text = "380"
    
    cbc_currency_code = ET.SubElement(root, "cbc:DocumentCurrencyCode")
    cbc_currency_code.text = "MYR"  # Malaysian Ringgit

    # Supplier (Hardcoded for simplicity)
    supplier_party = ET.SubElement(root, "cac:AccountingSupplierParty", xmlns="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2")
    supplier_party_name = ET.SubElement(supplier_party, "cbc:PartyName")
    supplier_party_name.text = "My Company"

    # Customer (Hardcoded for simplicity)
    customer_party = ET.SubElement(root, "cac:AccountingCustomerParty")
    customer_party_name = ET.SubElement(customer_party, "cbc:PartyName")
    customer_party_name.text = "Customer Name"

    # Invoice Line (For simplicity, one line item)
    invoice_line = ET.SubElement(root, "cac:InvoiceLine")
    invoice_line_id = ET.SubElement(invoice_line, "cbc:ID")
    invoice_line_id.text = "1"

    quantity = ET.SubElement(invoice_line, "cbc:InvoicedQuantity", unitCode="EA")
    quantity.text = "1"

    line_amount = ET.SubElement(invoice_line, "cbc:LineExtensionAmount", currencyID="MYR")
    line_amount.text = str(invoice.amount)

    # Convert the XML tree to a string
    xml_string = ET.tostring(root, encoding="utf-8", method="xml")
    
    return xml_string

# Save UBL XML to Desktop
def save_to_desktop(filename, content):
    # Get the path to the user's Desktop
    desktop_path = pathlib.Path.home() / "Desktop"
    
    # Full path to the file
    file_path = desktop_path / filename
    
    # Write the content to the file
    with open(file_path, 'wb') as file:
        file.write(content)

# Create Invoice and Save UBL XML to Desktop
@app.route('/invoice', methods=['POST'])
def create_invoice():
    data = request.get_json()
    
    # Create the invoice in the database
    new_invoice = Invoice(description=data['description'], amount=data['amount'], date=data['date'], status='Pending')
    db.session.add(new_invoice)
    db.session.commit()

    # Generate UBL XML for the created invoice
    ubl_invoice_xml = generate_ubl_invoice(new_invoice)

    # Save the UBL XML to Desktop
    filename = f"invoice_{new_invoice.id}.xml"
    save_to_desktop(filename, ubl_invoice_xml)

    # Return a response with the UBL XML as a string (for verification)
    return jsonify({
        'message': 'Invoice created successfully',
        'ubl_invoice': ubl_invoice_xml.decode('utf-8')  # Return the XML as a string
    }), 201

# Retrieve a specific invoice by ID (GET method)
@app.route('/invoice/<int:id>', methods=['GET'])
def get_invoice(id):
    invoice = Invoice.query.get_or_404(id)
    return jsonify({
        'id': invoice.id,
        'description': invoice.description,
        'amount': invoice.amount,
        'date': invoice.date,
        'status': invoice.status
    })

# Update an Invoice (PUT method)
@app.route('/invoice/<int:id>', methods=['PUT'])
def update_invoice(id):
    invoice = Invoice.query.get_or_404(id)
    data = request.get_json()

    # Update the invoice with new data
    invoice.description = data.get('description', invoice.description)
    invoice.amount = data.get('amount', invoice.amount)
    invoice.date = data.get('date', invoice.date)
    invoice.status = data.get('status', invoice.status)

    db.session.commit()

    # Generate and save the updated UBL XML
    ubl_invoice_xml = generate_ubl_invoice(invoice)
    filename = f"invoice_{invoice.id}.xml"
    save_to_desktop(filename, ubl_invoice_xml)

    return jsonify({
        'message': 'Invoice updated successfully',
        'ubl_invoice': ubl_invoice_xml.decode('utf-8')  # Return the updated XML
    })

# Delete an Invoice (DELETE method)
@app.route('/invoice/<int:id>', methods=['DELETE'])
def delete_invoice(id):
    invoice = Invoice.query.get_or_404(id)
    
    db.session.delete(invoice)
    db.session.commit()

    return jsonify({'message': 'Invoice deleted successfully'})

if __name__ == '__main__':
    app.run(debug=True)
