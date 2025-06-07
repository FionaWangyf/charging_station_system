from flask_socketio import join_room, leave_room, emit
from flask import session, request
from datetime import datetime

def register_socketio_events(socketio):
    """注册WebSocket事件处理器"""
    
    @socketio.on('connect')
    def handle_connect():
        """处理客户端连接"""
        print(f"客户端连接: {request.sid}")
        emit('connected', {'message': '连接成功', 'sid': request.sid})
    
    @socketio.on('disconnect')
    def handle_disconnect():
        """处理客户端断开连接"""
        print(f"客户端断开连接: {request.sid}")
    
    @socketio.on('join_user_room')
    def handle_join_user_room(data):
        """用户加入个人房间以接收专属消息"""
        user_id = data.get('user_id')
        if user_id:
            room = f'user_{user_id}'
            join_room(room)
            emit('room_joined', {
                'message': f'已加入用户房间: {room}',
                'room': room,
                'user_id': user_id
            })
            print(f"用户 {user_id} 加入房间: {room}")
        else:
            emit('error', {'message': '用户ID不能为空'})
    
    @socketio.on('leave_user_room')
    def handle_leave_user_room(data):
        """用户离开个人房间"""
        user_id = data.get('user_id')
        if user_id:
            room = f'user_{user_id}'
            leave_room(room)
            emit('room_left', {
                'message': f'已离开用户房间: {room}',
                'room': room,
                'user_id': user_id
            })
            print(f"用户 {user_id} 离开房间: {room}")
    
    @socketio.on('join_admin_room')
    def handle_join_admin_room():
        """管理员加入管理房间"""
        admin_room = 'admin_room'
        join_room(admin_room)
        emit('admin_room_joined', {
            'message': '已加入管理员房间',
            'room': admin_room
        })
        print(f"管理员加入房间: {admin_room}")
    
    @socketio.on('request_system_status')
    def handle_request_system_status():
        """客户端请求系统状态更新"""
        try:
            from flask import current_app
            charging_service = current_app.extensions.get('charging_service')
            
            if charging_service:
                status_data = charging_service.get_system_status_for_ui()
                emit('status_update', status_data)
            else:
                emit('error', {'message': '充电服务不可用'})
        except Exception as e:
            print(f"处理系统状态请求错误: {e}")
            emit('error', {'message': '获取系统状态失败'})
    
    @socketio.on('ping')
    def handle_ping():
        """处理心跳检测"""
        emit('pong', {'timestamp': datetime.now().isoformat()})
    
    return socketio