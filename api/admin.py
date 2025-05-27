from flask import request, jsonify
from app import app

@app.route('/api/admin/piles', methods=['GET'])
def get_piles():
    return jsonify({'message': '获取充电桩状态'})

@app.route('/api/admin/reports', methods=['GET'])
def get_reports():
    return jsonify({'message': '获取报表数据'})