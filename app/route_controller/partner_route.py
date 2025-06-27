from flask import Blueprint
from app.auth_controller.partner_controller import (
    make_partner, refer_user,handle_partner_request,partner_dashboard,approve_partner_request,decline_partner_request    
)

partner_db = Blueprint("partner_db", __name__)

partner_db.route("/approve", methods=["POST"])(approve_partner_request)
partner_db.route("/decline", methods=["POST"])(decline_partner_request)
partner_db.route("/confirm", methods=["POST"])(handle_partner_request)

partner_db.route("/make", methods=["POST"])(make_partner)
partner_db.route("/refer", methods=["POST"])(refer_user)
partner_db.route("/dashboard", methods=["GET"])(partner_dashboard)
# partner_db.route("/commission", methods=["POST"])(give_monthly_commission)