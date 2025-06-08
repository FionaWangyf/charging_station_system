# 充电站管理系统

## 快速开始
```bash
1. 安装依赖
pip install -r requirements.txt

2. 运行项目
python app.py

3. 打开两个新的命令行

命令行1-运行客户端
cd frontend/user
npm run build
npm run dev

命令行2-运行管理员端
cd frontend/admin
npm run build
npm run dev

3. 访问测试
用户端
# http://localhost:5001/user
管理员端
# http://localhost:5173/
```

在.env中配置自己的数据库用户名、密码等敏感信息 \
提前创建好数据库


frontend
├─ 📁admin
│  ├─ 📁public
│  │  └─ 📄vite.svg
│  ├─ 📁src
│  │  ├─ 📁assets
│  │  │  └─ 📄vue.svg
│  │  ├─ 📁components
│  │  │  ├─ 📄ChargingPileTable.vue
│  │  │  ├─ 📄ReportTable.vue
│  │  │  ├─ 📄SidebarMenu.vue
│  │  │  ├─ 📄TopBar.vue
│  │  │  └─ 📄WaitingPileCard.vue
│  │  ├─ 📁router
│  │  │  └─ 📄index.js
│  │  ├─ 📁styles
│  │  │  └─ 📄global.css
│  │  ├─ 📁views
│  │  │  ├─ 📄ChargingPileView.vue
│  │  │  ├─ 📄ReportView.vue
│  │  │  └─ 📄WaitingVehiclesView.vue
│  │  ├─ 📄.DS_Store
│  │  ├─ 📄App.vue
│  │  ├─ 📄main.js
│  │  └─ 📄style.css
│  ├─ 📄.DS_Store
│  ├─ 📄index.html
│  ├─ 📄package-lock.json
│  ├─ 📄package.json
│  └─ 📄vite.config.js
├─ 📁user
│  ├─ 📁public
│  │  ├─ 📄LoginBackground.jpg
│  │  └─ 📄desktop.ini
│  ├─ 📁src
│  │  ├─ 📁assets
│  │  │  └─ 📄style.css
│  │  ├─ 📁components
│  │  │  ├─ 📄ChargingDetailsPage.vue
│  │  │  ├─ 📄LoginPage.vue
│  │  │  ├─ 📄MainPage.vue
│  │  │  ├─ 📄NotificationPopup.vue
│  │  │  └─ 📄RegisterPage.vue
│  │  ├─ 📄App.vue
│  │  ├─ 📄env.d.ts
│  │  ├─ 📄main.ts
│  ├─ 📄index.html
│  ├─ 📄package-lock.json
│  ├─ 📄package.json
│  ├─ 📄tsconfig.json
│  ├─ 📄tsconfig.node.json
│  └─ 📄vite.config.ts
