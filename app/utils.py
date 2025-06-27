from flask import request, current_app, jsonify,render_template
from flask_mail import Message
from flask_jwt_extended import verify_jwt_in_request
from functools import wraps
from app import mail
from bson import ObjectId
from datetime import datetime 
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import re
import random
import string

def token_required(fn):
    @wraps(fn)
    def decorator(*args, **kwargs):
        token = request.headers.get('Authorization', None)
        if not token:
            return jsonify({"message": "Token is missing", "status_code": 401}), 401
        
        try:
            token = token.split(' ')[1]
            verify_jwt_in_request()

            if not is_token_valid_in_mongodb(token):
                return jsonify({"message": "Token is invalid or expired", "status_code": 401}), 401
            
            return fn(*args, **kwargs)
        
        except Exception as e:
            print(str(e))
            return jsonify({"message": "Error validating token", "status_code": 401}), 401
    
    return decorator

def is_token_valid_in_mongodb(token):
    token_doc = current_app.db.userSessions.find_one({ "token" : token, "loggedIn" : True })
    return token_doc is not None



def response_with_code(status_code, message,data=None):
    response = {
        "message": message,
        "status_code":status_code
    }
    if data:
        response["data"] = data
    return jsonify(response), status_code

def generate_password(length=8):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=8))

def generate_username(user_name, mobile_number):
    return f"{user_name[:4].lower()}{str(mobile_number)[-4:]}"


def send_email(subject, recipients, html_body):
    try:
        msg = Message(subject, recipients=recipients)
        msg.html = html_body
        mail.send(msg)
    except Exception as e:
        print(e)


def convert_objectid_to_str(document):
    if isinstance(document, list):
        return [convert_objectid_to_str(item) for item in document]
    if isinstance(document, dict):
        return {key: convert_objectid_to_str(value) for key, value in document.items()}
    if isinstance(document, ObjectId):
        return str(document)
    if isinstance(document, datetime):
        return document.isoformat()
    return document

def generate_otp(length=6):
    return ''.join(random.choices(string.digits, k=length))


def send_otp_email(receiver_email, otp):
    try:
        subject = "OTP for Password Reset"
        html_body = render_template('otp_email.html', otp=otp)

        msg = Message(subject, recipients=[receiver_email])
        msg.html = html_body
        mail.send(msg)
        print(f"OTP email sent to {receiver_email}")
        return True, None
    except Exception as e:
        print(f"Failed to send OTP email: {e}")
        return False, str(e)

def send_welcome_email(user_name, to_email):
    html = render_template('welcome_email.html', user_name=user_name)
    send_email('Welcome to Platform', to_email, html)

def send_credentials_email(username, password, to_email):
    # Ensure string (unwrap from list if necessary)
    if isinstance(to_email, list):
        to_email = to_email[0]

    print(f"📧 Final email: {to_email}, type: {type(to_email)}")  # DEBUG
    html = render_template('send_credentials.html', username=username, password=password)
    msg = Message('Your Login Credentials', recipients=[to_email])
    msg.html = html
    mail.send(msg)


def validate_password(password): 
    if len(password) < 8:
        return False
    if not re.search(r"[A-Z]", password):
        return False
    if not re.search(r"[a-z]", password):
        return False
    if not re.search(r"\d", password):
        return False
    if not re.search(r"[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]", password):
        return False
    return True

def send_admin_notification_email(user):

    subject = "New Payment Confirmation"
    plan_type_map = {
        'A': 'Plan A (₹6,00,000)',
        'B': 'Plan B (₹3,00,000)',
        'C': 'Plan C (₹5,000 - 60 months EMI)'
    }

    plan_type = plan_type_map.get(user.get('plan'), 'N/A')
    amount = user.get('amount', 'N/A')
    formatted_amount = f"₹{amount:,}" if isinstance(amount, (int, float)) else amount

    msg = Message(subject, recipients=["santhana7999@gmail.com"])
    msg.body = f"""New user completed payment:

Name     : {user.get('user_name', 'N/A')}
Email    : {user.get('email', 'N/A')}
Mobile   : {user.get('mobile_number', 'N/A')}
PlanType : {plan_type}
Amount   : {formatted_amount}

Approve here: https://scissorsproperties.com/admin-login
"""
    mail.send(msg)

def send_pending_payment_email(email, user_name, plan_type):
    subject = "Complete Your Full Payment to Get Access"

    plan_type_map = {
        'A': 'Plan A (₹6,00,000)',
        'B': 'Plan B (₹3,00,000)'
    }
    plan_name = plan_type_map.get(plan_type, plan_type)

    html_body = render_template(
        'pending_payment_email.html',
        user_name=user_name,
        plan_name=plan_name
    )

    msg = Message(subject, recipients=[email])
    msg.html = html_body
    mail.send(msg)

def send_emi_confirmation_email(user):
    subject = "EMI Payment Received"
    msg_body = f"""
Hi {user.get('user_name', 'User')},

We have received your EMI payment of ₹5,000 under Plan C.

Thank you for your continued support.

Regards,  
Scissors Admin Team
"""
    msg = Message(subject, recipients=[user.get("email")])
    msg.body = msg_body
    mail.send(msg) 

def send_partner_credentials_email(partner_name, to_email):
    # Ensure to_email is a string
    if isinstance(to_email, list):
        to_email = to_email[0]

    print(f"📧 Sending partner approval email to: {to_email}, partnerName: {partner_name}")

    # Render template with just the partner_name
    html = render_template('partner_credentials.html', partner_name=partner_name)
    
    msg = Message('Your Partner ID is Ready', recipients=[to_email])
    msg.html = html
    mail.send(msg)
    
def send_partner_credentials_email(partner_name, to_email):
    # Ensure to_email is a string
    if isinstance(to_email, list):
        to_email = to_email[0]

    print(f"📧 Sending partner approval email to: {to_email}, partnerName: {partner_name}")

    # Render template with just the partner_name
    html = render_template('partner_credentials.html', partner_name=partner_name)
    
    msg = Message('Your Partner ID is Ready', recipients=[to_email])
    msg.html = html
    mail.send(msg)

def send_partner_request_email_to_admin(partner_name, email, user_id):
    admin_email = "santhana7999@gmail.com"
    subject = "🔔 New Partner Request"
    html = render_template("partner_request_admin.html", partner_name=partner_name, email=email, user_id=user_id)
    msg = Message(subject=subject, recipients=[admin_email])
    msg.html = html
    mail.send(msg)
    
def send_partner_decline_email(user_name, to_email):
    if isinstance(to_email, list):
        to_email = to_email[0]

    html = render_template('partner_decline.html', user_name=user_name)
    msg = Message('Partner Request Declined', recipients=[to_email])
    msg.html = html
    mail = current_app.extensions['mail']
    mail.send(msg)
