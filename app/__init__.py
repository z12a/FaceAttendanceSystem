from datetime import datetime
from datetime import timedelta

from flask import Flask, url_for, request, redirect, render_template, session, flash
from flask_sqlalchemy import SQLAlchemy

# 创建一个Flask应用实例
app = Flask(__name__)
# 从config.py文件加载应用配置
app.config.from_object('config')
# 设置Flask的秘钥，用于保护会话
app.secret_key = '123456'
# 自动重新加载模板
app.jinja_env.auto_reload = True
# 设置发送文件的最大延迟为1秒
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = timedelta(seconds=1)
# 初始化SQLAlchemy数据库对象
db = SQLAlchemy(app)

from app import models, views
from .models import Student, Teacher


# 用户登录
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if len(username) == 12:  # 学号12位 代表学生登录
            students = Student.query.filter(Student.s_id == username).first()
            if students:
                if students.s_password == password:
                    flash("登陆成功")
                    session['username'] = username
                    session['id'] = students.s_id
                    session['num'] = 0  # students.num
                    session['name'] = students.s_name
                    session['role'] = "student"
                    session['flag'] = students.flag
                    if students.before:  # 上次登录时间
                        session['time'] = students.before
                    else:
                        session['time'] = time
                    students.before = time
                    db.session.commit()
                    return redirect(url_for('student.home'))
                else:
                    flash("密码错误，请重试")
            else:
                flash("学号错误，请重试")
        elif len(username) == 8:  # 8位账号 代表教师或管理员登录
            teachers = Teacher.query.filter(Teacher.t_id == username).first()
            if teachers:
                if teachers.t_password == password:
                    flash("登陆成功")
                    session['username'] = username
                    session['id'] = teachers.t_id
                    session['name'] = teachers.t_name
                    session['role'] = "teacher"
                    session['attend'] = []
                    if teachers.before:
                        session['time'] = teachers.before
                    else:
                        session['time'] = time
                    teachers.before = time
                    db.session.commit()
                    return redirect(url_for('teacher.home'))
                else:
                    flash("密码错误，请重试")
            else:
                flash("工号错误，请重试")
        else:
            flash("账号不合法，请用学号/工号登录")
    return render_template('login.html')


# 退出登录
@app.route('/logout')
def logout():
    session.clear()
    return render_template('login.html')


# 请求拦截器
@app.before_request
def before():
    # 检查请求的URL扩展名是否为某些特定文件类型（如图片、CSS、JS等），
    # 如果是，则不进行任何操作
    list = ['png', 'css', 'js', 'ico', 'xlsx', 'xls', 'jpg']
    url_after = request.url.split('.')[-1]
    #  如果是上述文件类型，直接返回空值
    if url_after in list:
        return None
    # 如果不是上述文件类型，拦截器会进一步检查请求的终点URL
    url = str(request.endpoint)
    if url == 'logout':  # 退出登录放行
        return None
    if url == "login":  # 登录操作，检查session
        if 'username' in session:
            return redirect("logout")
        else:
            return None
    # 根据URL，拦截器会检查用户是否已登录，以及用户是否有权限访问该URL
    else:
        if 'username' in session:
            role = url.split('.')[0]
            if role == session['role']:
                return None
            else:
                new_endpoint = session['role'] + '.' + 'home'
                flash('权限不足')
                return redirect(url_for(new_endpoint))
        else:
            flash("未登录")
            return redirect('/')
