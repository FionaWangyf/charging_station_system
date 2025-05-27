from flask import request, jsonify
from app import app

@app.route('/api/user/login', methods=['POST'])
def user_login():
    return jsonify({'message': '用户登录接口'})

@app.route('/api/user/register', methods=['POST'])
def user_register():
    return jsonify({'message': '用户注册接口'})