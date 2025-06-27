from app.model_controller.auth_model import User
from app.utils import generate_username, generate_password,response_with_code
from bson import ObjectId
from werkzeug.security import generate_password_hash
import random
from datetime import datetime,timedelta

class AuthService:
    def __init__(self, db): 
        self.auth_model = User(db)

    def signup(self, data):
        if self.auth_model.find_by_email(data.email):
            return None, "User with this email already exists"  
        if self.auth_model.find_by_mobile(data.mobile_number):
            return None, "User with this mobile number already exists"

        user_id = self.auth_model.create_user(data.user_name, data.mobile_number, data.email)
        user = self.auth_model.find_by_id(user_id)
        return user, None

    def signin(self, data):
        # Try finding user by username, email, mobile, or partnerName
        user = (
            self.auth_model.find_by_username(data.login_input)
            or self.auth_model.find_by_email(data.login_input)
            or self.auth_model.find_by_mobile(data.login_input)
            or self.auth_model.find_by_partnername(data.login_input)  
        )

        if not user:
            return None, "User not found"

        if user.get("userStatus") != "Accepted":
            return None, f"Access denied. Your registration status is '{user.get('userStatus', 'Unknown')}'. Please wait for approval."

        if not user.get('password'):
            return None, "Password not set. Please contact support"

        if not self.auth_model.check_password(user['password'], data.password):
            return None, "Incorrect password"

        return str(user['_id']), None

    def user_change_password(self, user_id, data):
        if data.new_password != data.confirm_password:
            return False, "Passwords do not match"

        user = self.auth_model.find_by_id(user_id)
        if not user:
            return False, "User not found"

        if user.get("status") != "Accepted":
            return False, f"Cannot change password. Status is '{user.get('status')}'."

        hashed_password = generate_password_hash(data.new_password)
        result = self.auth_model.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"userStatus": "Accepted"}}
)

        if result.modified_count == 0:
            return False, "Password not updated"

        return True, None

    def update_password(self, email, new_password):
        user = self.auth_model.find_by_email(email)

        if not user:
            return False, "User not found"

        if user.get("status") != "Accepted":
            return False, f"Cannot change password. Status is '{user.get('status')}'."

        hashed = hash_password(new_password)
        result = self.auth_model.update({'email': email}, {'password': hashed})

        if result.modified_count == 1:
            return True, None

        return False, "Update failed"


    def find_user_by_email(self, email):
        return self.auth_model.find_by_email(email)

    def generate_otp(self, length=6):
        return ''.join(str(random.randint(0, 9)) for _ in range(length))

    def store_otp(self, email, otp):
        return self.auth_model.store_otp(email, otp)

    def verify_otp(self, user, otp, expiry_minutes=15):
        if not user.get('otp') or not user.get('otp_created_at'):
            return False
        if user['otp'] != otp:
            return False
        otp_age = datetime.utcnow() - user['otp_created_at']
        if otp_age > timedelta(minutes=expiry_minutes):
            return False
        return True

    def update_password(self, email, new_password):
        return self.auth_model.update_password(email, new_password)

    def find_user_by_otp(self, otp):
        return self.auth_model.find_by_otp(otp)

    def get_all_pending_users(self):
        try:
            users = list(self.auth_model.find_many({"userStatus": "Accepted"}))
            for user in users:
                user["_id"] = str(user["_id"])
            return response_with_code(200, "Fetched all pending user requests", users)
        except Exception as e:
            return response_with_code(500, f"Error fetching users: {str(e)}")

    def get_customer_dashboard(self, user_id):
        try:
            user = self.auth_model.find_by_id(user_id)
            if not user:
                return response_with_code(404, "User not found")

            payment = self.auth_model.find_payment_by_user_id(user_id)

            user_data = {
                "_id": str(user.get('_id')),
                "user_name": user.get('user_name'),
                "email": user.get('email'),
                "mobile_number": user.get('mobile_number'),
                "username": user.get('username'),
                "userStatus": user.get('userStatus'),
                "credentialsSent": user.get('credentialsSent'),
                "createdAt": str(user.get('createdAt')),
                "updatedAt": str(user.get('updatedAt')),
            }

            payment_data = {}
            if payment:
                payment_data = {
                    "_id": str(payment.get('_id')),
                    "planAmount": payment.get('planAmount'),
                    "paymentStatus": payment.get('paymentStatus', 'Pending'),
                    "fullPaymentStatus": payment.get('fullPaymentStatus', 'Pending'),
                    "canParticipateLuckyDraw": payment.get('canParticipateLuckyDraw', False),
                    "luckyDrawMessage": payment.get('luckyDrawMessage', ''),
                    "nextDueDate": str(payment.get('nextDueDate')),
                    "planType": payment.get('planType'),
                    "registrationAmount": payment.get('registrationAmount'),
                    "createdAt": str(payment.get('createdAt')),
                    "updatedAt": str(payment.get('updatedAt')),
                }

            return response_with_code(200, "User and payment data fetched", {
                "data": [
                    {
                        "user": user_data,
                        "payment": payment_data,
                        "partner": {}  # Optional: you can add partner data here if needed
                    }
                ]
            })

        except Exception as e:
            return response_with_code(500, f"Server error: {str(e)}")


