from datetime import datetime, timedelta
from bson import ObjectId

class Payment:
    def __init__(self, db):
        self.payment = db.payment

    def create_payment(self, user_id, plan_type, plan_amount, upi, upi_mobile_number):
        now = datetime.utcnow()

        next_due_date = now + timedelta(days=30) if plan_type == "C" else None

        if plan_type == "C":
            paid_months = 1
            pending_months = 59
        else:
            paid_months = 60
            pending_months = 0

        return self.payment.insert_one({
            "userId": ObjectId(user_id),
            "planType": plan_type,
            "planAmount": plan_amount,
            "registrationAmount": 5000,
            "fullPaymentStatus": "Pending",
            "nextDueDate": next_due_date,
            "createdAt": now,
            "updatedAt": now,
            "canParticipateLuckyDraw": True,
            "luckyDrawMessage": "Eligible for Lucky Charm participation.",
            "totalMonths": 60,
            "paidMonths": paid_months,
            "pendingMonths": pending_months,
            "upi": upi,
            "upiMobileNumber": upi_mobile_number,
            'walletBalance':0,
            "coupenCode":"",
            "coupenValidityStatus":False
        })
        
    def get_all_payment(self,user_id):
        return self.payment.find({'userId': ObjectId(user_id)})

    def update_payment_status(self, user_id, status):
        update_fields = {
            "fullPaymentStatus": status,
            "updatedAt": datetime.utcnow()
        }

        # If payment completed, re-enable Lucky Charm participation
        if status == "Completed":
            update_fields["canParticipateLuckyDraw"] = True
            update_fields["luckyDrawMessage"] = "Eligible for Lucky Charm participation."

        return self.payment.update_one(
            {"userId": ObjectId(user_id)},
            {"$set": update_fields}
        )

    def get_payment_by_user(self, user_id):
        return self.payment.find_one({"userId": ObjectId(user_id)})

    def get_plan_type(self, user_id):
        record = self.payment.find_one({"userId": ObjectId(user_id)})
        return record.get("planType") if record else None

    def mark_payment_complete(self, user_id):
        update_fields = {
            "fullPaymentStatus": "Completed",
            "updatedAt": datetime.utcnow(),
            "nextDueDate": None,
            "canParticipateLuckyDraw": True,
            "luckyDrawMessage": "Eligible for Lucky Charm participation.",
            "paidMonths": 60,
            "pendingMonths": 0
        }
        return self.payment.update_one(
            {"userId": ObjectId(user_id)},
            {"$set": update_fields}
        )
    def check_emi_status(self, auth_model):
        overdue_users = []
        today = datetime.utcnow()
        alert_time = today.replace(day=10, hour=12, minute=0, second=0, microsecond=0)

        # Only check for Plan C users whose EMI is pending
        users = self.payment.find({"planType": "C", "fullPaymentStatus": "Pending"})

        for u in users:
            due_date = u.get("nextDueDate")
            if due_date and today > due_date:
                update_fields = {
                    "updatedAt": today,
                    # Add next due date again for the next EMI cycle
                    "nextDueDate": due_date + timedelta(days=30),
                    "canParticipateLuckyDraw": False,
                    "luckyDrawMessage": "You missed the amount. You cannot participate in the Lucky Charm."
                }

                self.payment.update_one(
                    {"_id": u["_id"]},
                    {"$set": update_fields}
                )

                # Update user to block Lucky Charm participation
                auth_model.update(
                    {"_id": u["userId"]},
                    {"$set": {"canParticipateLuckyDraw": False}}
                )

                overdue_users.append(str(u["userId"]))

            # EMI alert logic on every 10th at 12:00 PM UTC
            elif due_date and today.date() == alert_time.date() and today.hour == 12:
                # Here you would send a notification or email alert (to be implemented)
                pass  # e.g., send_emi_alert_email(user_email)

        return overdue_users

    
    def find_all(self):
        return list(self.payment.find())

    # def update_one(self, filter_dict, update_dict):
    #     update_dict["updatedAt"] = datetime.utcnow()
    #     return self.payment.update_one(filter_dict, {"$set": update_dict})

    def update_one(self, filter_dict, update_dict):
        """
        Proper implementation of update_one
        """
        update_dict['updatedAt'] = datetime.utcnow()
        return self.users.update_one(
            filter_dict,
            {'$set': update_dict}  # Note the $set operator here
        )

    def get_payment_by_user(self, user_id):
        return self.payment.find_one({'userId': ObjectId(user_id)})

    def find_payment_by_user_id(self, user_id):
        print(f"🔎 Looking for payment by userId: {user_id}")
        try:
            if isinstance(user_id, str):
                user_id = ObjectId(user_id)
            payment = self.payment.find_one({'userId': user_id})
            print(f"📄 Found payment: {payment}")
            return payment
        except Exception as e:
            print(f"❌ Payment fetch failed for user {user_id}: {e}")
            return None

    def update_emi_month_progress(self, user_id):
        payment = self.get_payment_by_user(user_id)
        if not payment or payment.get("planType") != "C":
            return None

        paid = payment.get("paidMonths", 1)
        if paid < 60:
            new_paid = paid + 1
            new_pending = 60 - new_paid

            update_fields = {
                "paidMonths": new_paid,
                "pendingMonths": new_pending,
                "updatedAt": datetime.utcnow()
            }

            if new_pending == 0:
                update_fields["fullPaymentStatus"] = "Completed"
                update_fields["nextDueDate"] = None
                update_fields["canParticipateLuckyDraw"] = True
                update_fields["luckyDrawMessage"] = "Eligible for Lucky Charm participation."

            self.payment.update_one(
                {"userId": ObjectId(user_id)},
                {"$set": update_fields}
            )
            return update_fields

        return {"message": "EMI payment already completed."}