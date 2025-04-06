from app import app
from app import db


# 学生信息
class Student(db.Model):
    __tablename__ = 'students'  # 学生信息表
    s_id = db.Column(db.String(13), primary_key=True)  # id
    s_name = db.Column(db.String(80), nullable=False)  # 姓名
    s_password = db.Column(db.String(32), nullable=False)  # 密码
    flag = db.Column(db.Integer, default=0)  # 标签 是否人脸录入
    before = db.Column(db.DateTime)  # 时间

    def __repr__(self):
        return '<Student %r,%r>' % (self.s_id, self.s_name)


# 教师信息表
class Teacher(db.Model):
    __tablename__ = 'teachers'  # 教师信息表
    t_id = db.Column(db.String(8), primary_key=True)  # id
    t_name = db.Column(db.String(80), nullable=False)  # 姓名
    t_password = db.Column(db.String(32), nullable=False)  # 密码
    before = db.Column(db.DateTime)  # 上次登录时间

    def __repr__(self):
        return '<Teacher %r,%r>' % (self.t_id, self.t_name)


# 人脸信息
class Faces(db.Model):
    __tablename__ = 'student_faces'
    s_id = db.Column(db.String(13), primary_key=True)  # id
    feature = db.Column(db.Text, nullable=False)  # 特征值

    def __repr__(self):
        return '<Faces %r>' % self.s_id


# 课程信息
class Course(db.Model):
    __tablename__ = 'courses'
    c_id = db.Column(db.String(6), primary_key=True)  # 课程id
    t_id = db.Column(db.String(8), db.ForeignKey('teachers.t_id'), nullable=False)  # 教师id
    c_name = db.Column(db.String(100), nullable=False)  # 课程名称
    times = db.Column(db.Text, default="0000-00-00 00:00")  # 时间
    flag = db.Column(db.String(50), default="不可选课")  # 课程状态

    def __repr__(self):
        return '<Course %r,%r,%r>' % (self.c_id, self.t_id, self.c_name)


# 学生选课
class SC(db.Model):
    __tablename__ = 'student_course'
    s_id = db.Column(db.String(13), db.ForeignKey('students.s_id'), primary_key=True)  # 学生id
    c_id = db.Column(db.String(100), db.ForeignKey('courses.c_id'), primary_key=True)  # 课程id

    def __repr__(self):
        return '<SC %r,%r> ' % (self.s_id, self.c_id)


# 签到信息
class Attendance(db.Model):
    __tablename__ = 'attendance'
    id = db.Column(db.Integer, primary_key=True)  # id
    s_id = db.Column(db.String(13), db.ForeignKey('students.s_id'))  # 学生id
    c_id = db.Column(db.String(100), db.ForeignKey('courses.c_id'))  # 课程id
    time = db.Column(db.DateTime)  # 时间
    result = db.Column(db.String(10), nullable=False)  # 签到结果

    def __repr__(self):
        return '<Attendance %r,%r,%r,%r>' % (self.s_id, self.c_id, self.time, self.result)


# 创建一个时间类
class Time_id():
    id = ''
    time = ''

    def __init__(self, id, time):
        self.id = id
        self.time = time


# 选课信息
class choose_course():
    __tablename___ = 'choose_course'  # 选课信息
    c_id = db.Column(db.String(6), primary_key=True)  # 课程id
    t_id = db.Column(db.String(8), nullable=False)  # 教师id
    c_name = db.Column(db.String(100), nullable=False)  # 课程名称

    def __repr__(self):
        return '<Course %r,%r,%r>' % (self.c_id, self.t_id, self.c_name)


with app.app_context():
    db.create_all()
