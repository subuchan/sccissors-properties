from flask import Blueprint
from app.auth_controller.auth import (
    Signup, Login, Forgot_password,customer_dashboard,Change_password,Reset_password,Complete_payment,get_lucky_charm_status,validate_user_id
)

auth_bp = Blueprint('auth_bp', __name__)

auth_bp.route('/register', methods=['POST'])(Signup)
auth_bp.route('/login', methods=['POST'])(Login)
auth_bp.route('/forgot-password', methods=['POST'])(Forgot_password)
auth_bp.route('/reset-password', methods=['POST'])(Reset_password)
auth_bp.route('/change-password', methods=['POST'])(Change_password)

auth_bp.route('/complete-payment', methods=['POST'])(Complete_payment)
auth_bp.route('/user/lucky-charm-status', methods=['GET'])(get_lucky_charm_status)
auth_bp.route('/current-user', methods=['GET'])(customer_dashboard)
auth_bp.route('/validate-id', methods=['GET'])(validate_user_id)
