## 🛠️ 快速开始
### ⛳运行环境
- Python 3.7+
- Node.js 18+

### 🎯安装依赖
```
pip install -r requirements.txt
npm install
```

### 🎨配置文件
配置文件在项目根目录.env文件中，将下图自己的登录cookie放入其中，cookie获取➡️在浏览器f12打开控制台，点击网络，点击fetch，找一个接口点开
![image](https://github.com/user-attachments/assets/6a7e4ecb-0432-4581-890a-577e0eae463d)

复制cookie到.env文件中（注意！登录小红书后的cookie才是有效的，不登陆没有用）
![image](https://github.com/user-attachments/assets/5e62bc35-d758-463e-817c-7dcaacbee13c)

### 🚀运行项目
```
python main.py
```

### 🗝️注意事项
- main.py中的代码是爬虫的入口，可以根据自己的需求进行修改
- apis/xhs_pc_apis.py 中的代码包含了所有的api接口，可以根据自己的需求进行修改
- apis/xhs_creator_apis.py 中的代码包含了小红书创作者平台的api接口，可以根据自己的需求进行修改
