from flask import Flask

app = Flask(__name__)

# 导入所有API接口
from api import user, charging, admin

@app.route('/')
def home():
    return {'message': '充电站管理系统API', 'status': 'running'}

if __name__ == '__main__':
    app.run(debug=True, port=5000)