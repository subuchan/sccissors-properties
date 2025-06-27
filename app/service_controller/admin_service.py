from app.model_controller.admin_model import Admin
from app.model_controller.payment_model import Payment
from app.utils import validate_password,generate_otp,send_otp_email,send_emi_confirmation_email,send_credentials_email,send_pending_payment_email,response_with_code,send_email,convert_objectid_to_str
import random
from datetime import datetime,timedelta
from bson import ObjectId
from app.model_controller.auth_model import User
import string
from flask import render_template
from werkzeug.security import generate_password_hash, check_password_hash

class AdminService:
    def __init__(self, db):
        self.admin_model = Admin(db)
        self.auth_model=User(db)
        self.payment_model=Payment(db)


    def register_user(self,data):
        try:
            if not validate_password(data.password):
                return True, "Provided password does not meet requirements"

            if self.admin_model.find_by_email(data.email):
                return None, "User already exists"

            admin_id = self.admin_model.create_admin_user(data)
            return admin_id, None

        except Exception as e:
            return None, str(e)
        
    def Admin(self,email, password):
        admin = self.admin_model.find_by_email(email)
        if admin and self.admin_model.check_password(admin['password'], password):
            return admin, None
        if not admin: 
            return False,"user not found"
        if not self.admin_model.check_password(admin['password'], password):
            return False,"password is Incorrect"

    def update_admin_status(self, admin_id, status):
        self.admin_model.update_status(admin_id, status)
        
    def handle_request(self, user_id, action):
        if action not in ['Accepted', 'Ignored']:
            return None, "Invalid action"

        result = self.admin_model.update_request_status(ObjectId(user_id), action)
        if result.modified_count == 0:
            return None, "No document updated"
        return True, None

    def change_password(self, admin_id, data):
        admin = self.admin_model.find_by_admin_id(admin_id)
        if not admin:
            return None, "Admin not found"

        if not self.admin_model.check_password(admin['password'], data.old_password):
            return None, "Old password is incorrect"

        if data.new_password != data.confirm_password:
            return None, "New passwords do not match"

        if not validate_password(data.new_password):
            return None, "Password does not meet requirements"

        updated = self.admin_model.update_password(admin_id, data.new_password)
        return updated, None

    def forgot_password(self, admin_id, email):
        admin = self.admin_model.find_by_admin_id(admin_id)
        if not admin or admin.get('email') != email:
            return None, "Admin not found or email mismatch"

        otp = generate_otp()
        self.admin_model.store_otp(admin_id, otp)
        send_otp_email(email, otp)
        return otp, None

    def find_admin_by_email(self, email):
        return self.admin_model.find_by_email(email)

    def generate_otp(self, length=6):
        return ''.join(str(random.randint(0, 9)) for _ in range(length))

    def update_password(self, email, new_password):
        return self.admin_model.update_password(email, new_password)

    def find_user_by_otp(self, otp):
        return self.admin_model.find_by_otp(otp)

    def verify_otp(self, admin, otp, expiry_minutes=15):
        if not admin.get('otp') or not admin.get('otp_created_at'):
            return False
        if admin['otp'] != otp:
            return False
        otp_age = datetime.utcnow() - admin['otp_created_at']
        if otp_age > timedelta(minutes=expiry_minutes):
            return False
        return True

    def update_password(self, user_id, new_password):
        return self.admin_model.update_password(user_id, new_password)

    def store_otp(self, user_id, otp):
        return self.admin_model.store_otp(user_id, otp)
                
    def get_all_pending_users(self):
        users = self.auth_model.find_pending_users()
        return response_with_code(200, "All pending users fetched", users)


    def get_pending_plan_a_b_users(self):
        users = self.auth_model.find_pending_users()
        final_users = []

        for user in users:
            try:
                payment = self.payment_model.get_payment_by_user(user['_id'])

                if (
                    payment
                    and payment.get("planType") in ["A", "B"]
                    and payment.get("fullPaymentStatus") == "Pending"
                ):
                    user['planType'] = payment.get('planType')
                    user['fullPaymentStatus'] = payment.get('fullPaymentStatus')
                    final_users.append(user)

            except Exception as e:
                print(f"❌ Error processing user {user['_id']}: {e}")

        return response_with_code(200, "Pending A/B users fetched", final_users)


    def approve_user(self, user_id, plan_type):
        user = self.auth_model.find_user_by_id(user_id)
        if not user:
            return response_with_code(404, "User not found")

        payment = self.payment_model.get_payment_by_user(user_id)
        payment_status = payment.get('fullPaymentStatus') if payment else None

        # Always set status to Accepted
        self.auth_model.update_one(
            {"_id": ObjectId(user_id)},
            {"userStatus": "Accepted"}
        )

        if plan_type in ['A', 'B']:
            send_pending_payment_email(user['email'], user.get('user_name', 'User'), plan_type)
            return response_with_code(200, "User approved, pending payment email sent.")

        elif plan_type == 'C':
            if not payment:
                return response_with_code(400, "Payment not found for Plan C user")
            
            if self.auth_model.has_sent_credentials(user_id):
                return response_with_code(200, "User approved for Plan C. Credentials already sent.")

            # ✅ Call internal method to send credentials
            return self._final_approval_and_send_credentials(user_id, user['email'])

        else:
            # ✅ Fallback response for unknown plan
            return response_with_code(400, f"Invalid plan type: {plan_type}")

    def decline_user(self, user_id):
        user = self.auth_model.find_user_by_id(user_id)
        if not user:
            return response_with_code(404, "User not found")

        self.auth_model.update_user_status_declined(user_id)

        html_body = render_template('decline_email.html', user_name=user.get("user_name", "User"), admin_email="admin@example.com")
        send_email(subject="Registration Declined", recipients=[user['email']], html_body=html_body)

        return response_with_code(400, "Invalid approval request or already completed")

    def generate_password(self, length=8):
        chars = string.ascii_letters + string.digits + "!@#$%^&*"
        return ''.join(random.choices(chars, k=length))

    def get_user_and_payment(self):
        data = self.admin_model.get_user_and_payment()
        return convert_objectid_to_str(data)   
    
    def disable_user_and_partner(self, user_id, disabled_status):
        user = self.auth_model.find_user_by_id(user_id)
        if not user:
            return False, "User not found"

        self.auth_model.update_user_disabled_status(user_id, disabled_status)
        self.partner_model.update_partner_disabled_status(user_id, disabled_status)
        return True, f"User and Partner disabled status set to {disabled_status}"

    def _final_approval_and_send_credentials(self, user_id, email):
        prefix = "50055"
        suffix = "5"
        last_user = self.auth_model.get_last_approved_user()

        if last_user and last_user.get("username", "").startswith(prefix):
            try:
                middle = int(last_user["username"][6:8])
            except:
                middle = 0
        else:
            middle = 0

        new_middle = str(middle + 1).zfill(2)
        username = f"{prefix}{new_middle}{suffix}"
        plain_password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
        hashed_password = generate_password_hash(plain_password)

        # ✅ Generate plots number
        last_plot = self.auth_model.get_last_plot_number()
        if last_plot:
            plot_num = int(last_plot[1:]) + 1
        else:
            plot_num = 1
        plots_value = f"P{plot_num:04d}"

        update_data = {
            "userStatus": "Accepted",
            "username": username,
            "password": hashed_password,
            "credentialsSent": True,
            "plots": plots_value
        }

        result = self.auth_model.update_one({"_id": ObjectId(user_id)}, update_data)

        if result.modified_count > 0:
            send_credentials_email(username, plain_password, email)
            return response_with_code(200, "User fully approved, credentials and plots generated.")

        return response_with_code(500, "Failed to approve user and set credentials.")


