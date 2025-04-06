# 创建数据库表，初始化的时候用（执行SQL文件不需要）
# 不需要运行
from flask import Flask

from app import db

app = Flask(__name__)
app.config.from_pyfile('../config.py')
db.init_app(app)

with app.app_context():
    db.create_all()
