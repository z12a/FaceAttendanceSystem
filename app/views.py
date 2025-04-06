from app import app

from .student import student
from .teacher import teacher

# 注册蓝图
app.register_blueprint(student, url_prefix='/student')
app.register_blueprint(teacher, url_prefix='/teacher')
