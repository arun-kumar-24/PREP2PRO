from flask import Blueprint, jsonify # type: ignore

user_bp = Blueprint('user', __name__)

@user_bp.route('/profile', methods=['GET'])
def get_user_profile():
    return jsonify({"user": "Profile data not yet implemented."})
