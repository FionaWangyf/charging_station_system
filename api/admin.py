from flask import request, jsonify
from app import app

@app.route('/api/admin/piles', methods=['GET'])
def get_piles():
    '''获取充电桩状态'''
    return jsonify({
        'success': True,
        'message': '获取充电桩状态',
        'data': {
            'piles': []
        }
    })

@app.route('/api/admin/piles/<pile_id>/control', methods=['POST'])
def control_pile(pile_id):
    '''控制充电桩（启动/关闭）'''
    data = request.json
    action = data.get('action')  # 'start' or 'stop'
    
    return jsonify({
        'success': True,
        'message': f'充电桩{pile_id}已{action}',
        'data': {
            'pile_id': pile_id,
            'status': 'online' if action == 'start' else 'offline'
        }
    })

@app.route('/api/admin/reports', methods=['GET'])
def get_reports():
    '''获取报表数据'''
    return jsonify({
        'success': True,
        'message': '获取报表数据',
        'data': {
            'reports': []
        }
    })

@app.route('/api/admin/system/config', methods=['GET', 'POST'])
def system_config():
    '''系统配置管理'''
    if request.method == 'GET':
        return jsonify({
            'success': True,
            'data': {
                'fast_charging_pile_num': 2,
                'trickle_charging_pile_num': 3,
                'waiting_area_size': 6,
                'charging_queue_len': 2
            }
        })
    else:
        # 更新配置
        return jsonify({
            'success': True,
            'message': '配置更新成功'
        })