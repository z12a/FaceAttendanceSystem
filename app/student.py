"""
@author:赵鸣宇
@project_name:考勤系统
@time:2025/3/04
@remarks:学生功能业务逻辑
"""

import base64
import os
from datetime import datetime

from flask import Blueprint, render_template, request, session, flash, redirect, url_for
from sqlalchemy import extract

from app import db
from app import features_extraction_to_csv as fc
from app import get_faces_from_camera as gf
from .models import Faces, Student, SC, Course, Attendance, Teacher

# 注册蓝图
student = Blueprint('student', __name__, static_folder='static')


# 首页
@student.route('/home')
def home():
    records = {}
    # 当前学生信息
    student = Student.query.filter(Student.s_id == session['id']).first()
    # 学生flag
    session['flag'] = student.flag
    # 该学生的签到信息
    attendances = db.session.query(Attendance).filter(Attendance.s_id == session['id']).order_by(
        Attendance.time.desc()).limit(5).all()
    # 签到信息里的课程信息
    for i in attendances:
        course = db.session.query(Course).filter(Course.c_id == i.c_id).all()
        records[i] = course
    # 当前年
    year = datetime.now().year
    # 当前月
    month = datetime.now().month
    # 统计签到信息
    # 请假次数
    qj = db.session.query(Attendance).filter(Attendance.s_id == session['id'],
                                             extract('month', Attendance.time) == month,
                                             extract('year', Attendance.time) == year,
                                             Attendance.result == '请假').count()
    # 迟到次数
    cd = db.session.query(Attendance).filter(Attendance.s_id == session['id'],
                                             extract('month', Attendance.time) == month,
                                             extract('year', Attendance.time) == year,
                                             Attendance.result == '迟到').count()
    # 缺勤次数
    qq = db.session.query(Attendance).filter(Attendance.s_id == session['id'],
                                             extract('month', Attendance.time) == month,
                                             extract('year', Attendance.time) == year,
                                             Attendance.result == '缺勤').count()
    # 已签到次数
    yqd = db.session.query(Attendance).filter(Attendance.s_id == session['id'],
                                              extract('month', Attendance.time) == month,
                                              extract('year', Attendance.time) == year,
                                              Attendance.result == '已签到').count()
    # 用字典存储数据
    num = {'qj': qj, 'cd': cd, 'qq': qq, 'yqd': yqd}
    return render_template('student/student_home.html', flag=session['flag'], before=session['time'], records=records,
                           name=session['name'], num=num)


# 创建文件夹方法
def pre_work_mkdir(path_photos_from_camera):
    if os.path.isdir(path_photos_from_camera):
        pass
    else:
        os.mkdir(path_photos_from_camera)


# 接收前端上传的人脸图片,处理后存入数据库
@student.route("/get_faces", methods=["GET", "POST"])
def get_faces():
    '''
        1、取上传来的数据的参数 request.form.get("my_img")
        2、上传的数据是base64格式,调用后端的base64进行解码
        3、存到后台变成图片
        4、调用face_reconginition的load_image-file读取文件
        5、调用 face-recognition的face_encodings对脸部进行编码
        6、利用bson和pickle模块组合把脸部编码数据变成128位bitdata数据
        上面是逻辑,但逻辑发生在post方式上,不发生在get,
        限定一下上面逻辑的发生条件,不是POST方式,就是GET,GET请求页面
        :return:
    '''
    if request.method == "POST":
        # 获取图片数据
        imgdata = request.form.get("face")
        # 调用后端的base64进行解码
        imgdata = base64.b64decode(imgdata)
        # 存储路径
        path = "app/static/data/data_faces_from_camera/" + session['id']
        # 获取人脸数据
        up = gf.Face_Register()
        # 数量为0，创建文件夹
        if session['num'] == 0:
            pre_work_mkdir(path)
        # 至少要五张人脸图片
        if session['num'] == 5:
            session['num'] = 0
        session['num'] += 1
        # 图片路径
        current_face_path = path + "/" + str(session['num']) + '.jpg'
        # 写入图片文件
        with open(current_face_path, "wb") as f:
            f.write(imgdata)
        # 是否符合要求
        flag = up.single_pocess(current_face_path)
        if flag != 'right':
            session['num'] -= 1
        msg = [{"result": flag, "code": session['num']}]
        return {"result": flag, "code": session['num']}
    return render_template("student/get_faces.html")


# 计算特征值存数据库
@student.route('/upload_faces', methods=['POST'])
def upload_faces():
    try:
        # 读取图片
        path_images_from_camera = "app/static/data/data_faces_from_camera/"
        path = path_images_from_camera + session['id']
        # 获取平均特征值
        features_mean_personX = fc.return_features_mean_personX(path)
        features = str(features_mean_personX[0])
        for i in range(1, 128):
            features = features + ',' + str(features_mean_personX[i])
        # 存储特征值数据
        student = Faces.query.filter(Faces.s_id == session['id']).first()
        # 是否已经录入过人脸，有则更新，无则添加
        if student:
            student.feature = features
        else:
            face = Faces(s_id=session['id'], feature=features)
            db.session.add(face)
        db.session.commit()
        print(" >> 特征均值:", list(features_mean_personX), '\n')
        msg = 'success'
        # 修改学生flag
        student = Student.query.filter(Student.s_id == session['id']).first()
        student.flag = 0  # 已录入人脸
        db.session.commit()
        flash("提交成功！")
        return redirect(url_for('student.home'))
    except Exception as e:
        print('Error:', e)
        flash("提交不合格照片，请拍摄合格后再重试")
        return redirect(url_for('student.home'))


# 学生人脸数据
@student.route('/my_faces')
def my_faces():
    current_face_path = "app/static/data/data_faces_from_camera/" + session['id'] + "/"
    face_path = "static/data/data_faces_from_camera/" + session['id'] + "/"
    photos_list = os.listdir(current_face_path)
    num = len(photos_list)
    paths = []
    for i in range(num):
        path = face_path + str(i + 1) + '.jpg'
        paths.append(path)
    return render_template('student/my_faces.html', face_paths=paths)


# 查询签到记录
@student.route('/my_records', methods=['GET', 'POST'])
def my_records():
    sid = session['id']
    dict = {}
    # 有条件查询
    if request.method == 'POST':
        # 课程id
        cid = str(request.form.get('course_id'))
        # 时间
        time = str(request.form.get('time'))
        if cid != '' and time != '':
            # 课程信息
            course = Course.query.filter(Course.c_id == cid).first()
            # 课程签到记录
            one_course_records = db.session.query(Attendance).filter(Attendance.s_id == sid, Attendance.c_id == cid,
                                                                     Attendance.time.like(time + '%')).all()
            dict[course] = one_course_records
            courses = db.session.query(Course).join(SC).filter(SC.s_id == sid).order_by("c_id").all()
            return render_template('student/my_records.html', dict=dict, courses=courses)
        elif cid != '' and time == '':
            course = Course.query.filter(Course.c_id == cid).first()
            one_course_records = db.session.query(Attendance).filter(Attendance.s_id == sid,
                                                                     Attendance.c_id == cid).all()
            dict[course] = one_course_records
            courses = db.session.query(Course).join(SC).filter(SC.s_id == sid).order_by("c_id").all()
            return render_template('student/my_records.html', dict=dict, courses=courses)
        elif cid == '' and time != '':
            courses = db.session.query(Course).join(SC).filter(SC.s_id == sid).order_by("c_id").all()
            for course in courses:
                one_course_records = db.session.query(Attendance).filter(
                    Attendance.s_id == sid, Attendance.c_id == course.c_id,
                    Attendance.time.like(time + '%')).order_by("c_id").all()
                dict[course] = one_course_records
            courses = db.session.query(Course).join(SC).filter(SC.s_id == sid).order_by("c_id").all()
            return render_template('student/my_records.html', dict=dict, courses=courses)
        else:
            pass
    # 签到的课程信息
    courses = db.session.query(Course).join(SC).filter(SC.s_id == sid).order_by("c_id").all()
    for course in courses:
        one_course_records = db.session.query(Attendance).filter(Attendance.s_id == sid,
                                                                 Attendance.c_id == course.c_id).order_by("c_id").all()
        dict[course] = one_course_records
    return render_template('student/my_records.html', dict=dict, courses=courses)


# 选课
@student.route('/choose_course', methods=['GET', 'POST'])
def choose_course():
    try:
        sid = session['id']
        dict = {}
        if request.method == 'POST':
            # 课程id
            cid = request.form.get('cid')
            # 添加选课
            sc = SC(s_id=sid, c_id=cid)
            db.session.add(sc)
            db.session.commit()
        # 已选课程
        now_have_courses_sc = SC.query.filter(SC.s_id == sid).all()
        cids = []
        for sc in now_have_courses_sc:
            cids.append(sc.c_id)
        # 没选的可选课程
        not_hava_courses = Course.query.filter(Course.c_id.notin_(cids), Course.flag == '可选课').all()
        for ncourse in not_hava_courses:
            teacher = Teacher.query.filter(Teacher.t_id == ncourse.t_id).first()
            dict[ncourse] = teacher
        return render_template('student/choose_course.html', dict=dict)
    except Exception as e:
        print('Error:', e)
        flash("操作异常")
        return redirect(url_for('student.home'))


# 退课
@student.route('/unchoose_course', methods=['GET', 'POST'])
def unchoose_course():
    try:
        sid = session['id']
        dict = {}
        if request.method == 'POST':
            # 课程id
            cid = request.form.get('cid')
            # 选课信息
            sc = SC.query.filter(SC.c_id == cid, SC.s_id == sid).first()
            # 删除选课
            db.session.delete(sc)
            db.session.commit()
        # 已选课程
        now_have_courses_sc = SC.query.filter(SC.s_id == sid).all()
        cids = []
        for sc in now_have_courses_sc:
            cids.append(sc.c_id)
        # 可选课程
        hava_courses = Course.query.filter(Course.c_id.in_(cids), Course.flag == '可选课').all()
        for course in hava_courses:
            teacher = Teacher.query.filter(Teacher.t_id == course.t_id).first()
            dict[course] = teacher
        return render_template('student/unchoose_course.html', dict=dict)
    except Exception as e:
        print('Error:', e)
        flash("操作异常")
        return redirect(url_for('student.home'))


# 修改密码
@student.route('/update_password', methods=['GET', 'POST'])
def update_password():
    # 学习信息
    sid = session['id']
    student = Student.query.filter(Student.s_id == sid).first()
    if request.method == 'POST':
        # 旧密码
        old = request.form.get('old')
        # 旧密码正确，可修改
        if old == student.s_password:
            new = request.form.get('new')
            student.s_password = new
            db.session.commit()
            flash('修改成功！')
        else:
            flash('旧密码错误，请重试')
    return render_template('student/update_password.html', student=student)
