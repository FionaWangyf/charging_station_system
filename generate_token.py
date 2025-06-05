import jwt
from datetime import datetime, timedelta

SECRET_KEY = 'asdfg'

# 生成用户token
user_payload = {
    'user_id': 'user-001',
    'role': 'user',
    'exp': datetime.utcnow() + timedelta(hours=24)
}
user_token = jwt.encode(user_payload, SECRET_KEY, algorithm='HS256')
if isinstance(user_token, bytes):
    user_token = user_token.decode('utf-8')

# 生成管理员token
admin_payload = {
    'user_id': 'admin-001',
    'role': 'admin',
    'exp': datetime.utcnow() + timedelta(hours=24)
}
admin_token = jwt.encode(admin_payload, SECRET_KEY, algorithm='HS256')
if isinstance(admin_token, bytes):
    admin_token = admin_token.decode('utf-8')

print("用户Token:")
print(user_token)
print("\n管理员Token:")
print(admin_token)