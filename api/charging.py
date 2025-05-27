from flask import request, jsonify
from app import app

@app.route('/api/charging/request', methods=['POST'])
def charging_request():
    return jsonify({'message': '充电请求接口'})

@app.route('/api/charging/status', methods=['GET'])
def charging_status():
    return jsonify({'message': '充电状态接口'})