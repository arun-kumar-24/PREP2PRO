from flask import Blueprint, request, jsonify # type: ignore
from app.supabase_client import supabase_client

test_bp = Blueprint('testing', __name__)

@test_bp.route('/test', methods=['GET'])
def test_supabase():
    response = supabase_client.table("domains").select("id").eq("name", "SDE").execute()
    
    # Extract the id from the response
    id_value = response.data[0]['id']
    
    # You can now use the id_value variable as needed
    return jsonify({"stored_id": id_value})