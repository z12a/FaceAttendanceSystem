"""
@author:赵鸣宇
@project_name:合肥经济学院考勤系统
@time:2024/5/02
@remarks:教师功能业务逻辑
"""

import os
import time
from io import BytesIO
from urllib.parse import quote

import cv2
import dlib
import numpy as np
import pandas as pd
import pymysql
from PIL import Image, ImageDraw, ImageFont
from flask import Blueprint, render_template, redirect, request, Response, session, flash, jsonify, url_for
from flask import send_file

from app import db
from .models import Teacher, Faces, Course, SC, Attendance, Time_id, Student

# 注册蓝图
teacher = Blueprint('teacher', __name__, static_folder="static")

# 本次签到的所有人员信息
attend_records = []
# 本次签到的开启时间
the_now_time = ''


# 首页
@teacher.route('/home')
def home():
    flag = session['id'][0]  # 教师账号的第一个数字为0表示管理员，非0是教师账号
    courses = {}
    # 当前教师的所有课程
    course = db.session.query(Course).filter(Course.t_id == session['id']).all()
    # 所有课程数量
    for c in course:
        num = db.session.query(SC).filter(SC.c_id == c.c_id).count()
        courses[c] = num
    return render_template('teacher/teacher_home.html', before=session['time'], flag=flag, name=session['name'],
                           courses=courses)


# Dlib 正向人脸检测器
detector = dlib.get_frontal_face_detector()
# Dlib 人脸 landmark 特征点检测器
predictor = dlib.shape_predictor('app/static/data_dlib/shape_predictor_68_face_landmarks.dat')

# Dlib Resnet 人脸识别模型，提取 128D 的特征矢量
face_reco_model = dlib.face_recognition_model_v1("app/static/data_dlib/dlib_face_recognition_resnet_model_v1.dat")


# 摄像头调用
class VideoCamera(object):
    def __init__(self):
        self.font = cv2.FONT_ITALIC
        # 通过opencv获取实时视频流
        self.video = cv2.VideoCapture(0)

        # 统计 FPS
        self.frame_time = 0
        self.frame_start_time = 0
        self.fps = 0

        # 统计帧数
        self.frame_cnt = 0

        # 存储所有录入人脸特征的数组
        self.features_known_list = []
        # 存储录入人脸名字
        self.name_known_list = []

        # 存储上一帧和当前帧 ROI 的质心坐标
        self.last_frame_centroid_list = []
        self.current_frame_centroid_list = []

        # 存储当前帧检测出目标的名字
        self.current_frame_name_list = []

        # 上一帧和当前帧中人脸数的计数器
        self.last_frame_faces_cnt = 0
        self.current_frame_face_cnt = 0

        # 存放进行识别时候对比的欧氏距离
        self.current_frame_face_X_e_distance_list = []

        # 存储当前摄像头中捕获到的所有人脸的坐标名字
        self.current_frame_face_position_list = []
        # 存储当前摄像头中捕获到的人脸特征
        self.current_frame_face_feature_list = []

        # 控制再识别的后续帧数
        # 如果识别出 "unknown" 的脸, 将在 reclassify_interval_cnt 计数到 reclassify_interval 后, 对于人脸进行重新识别
        self.reclassify_interval_cnt = 0
        self.reclassify_interval = 10

    # 释放摄像头
    def __del__(self):
        self.video.release()

    # 从数据库获取人脸数据
    def get_face_database(self, cid, faces):
        from_db_all_features = faces
        print('from_db_all_features:', from_db_all_features)
        if from_db_all_features:
            # 遍历所有的人脸特征
            for from_db_one_features in from_db_all_features:
                # 人脸特征值列表
                someone_feature_str = str(from_db_one_features.feature).split(',')
                # 学生
                self.name_known_list.append(from_db_one_features.s_id)
                features_someone_arr = []
                for one_feature in someone_feature_str:
                    if one_feature == '':
                        features_someone_arr.append('0')
                    else:
                        features_someone_arr.append(float(one_feature))
                self.features_known_list.append(features_someone_arr)
            return 1
        else:
            return 0

    # 更新 FPS
    def update_fps(self):
        now = time.time()
        self.frame_time = now - self.frame_start_time
        self.fps = 1.0 / self.frame_time
        self.frame_start_time = now

    # 计算两个128D向量间的欧式距离
    @staticmethod
    def return_euclidean_distance(feature_1, feature_2):
        feature_1 = np.array(feature_1)
        feature_2 = np.array(feature_2)
        dist = np.sqrt(np.sum(np.square(feature_1 - feature_2)))
        return dist

    # 生成的 cv2 window 上面添加说明文字显示
    def draw_note(self, img_rd):
        # 添加说明
        cv2.putText(img_rd, "One person at a time:  ", (20, 40), self.font, 1, (255, 255, 255), 1,
                    cv2.LINE_AA)
        cv2.putText(img_rd, "FPS:   " + str(self.fps.__round__(2)), (20, 100), self.font, 0.8, (0, 255, 0), 1,
                    cv2.LINE_AA)

    # 在人脸框下面写人脸名字
    def draw_name(self, img_rd):
        font = ImageFont.truetype("simsun.ttc", 30)
        img = Image.fromarray(cv2.cvtColor(img_rd, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(img)
        draw.text(xy=self.current_frame_face_position_list[0], text=self.current_frame_name_list[0], font=font)
        img_rd = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        return img_rd

    # 处理获取的视频流，进行人脸识别
    def get_frame(self, cid, faces):
        stream = self.video
        # 1. 读取存放所有人脸特征的 csv
        if self.get_face_database(cid, faces):
            while stream.isOpened():
                self.frame_cnt += 1
                flag, img_rd = stream.read()

                # 2. 检测人脸
                faces = detector(img_rd, 0)

                # 3. 更新帧中的人脸数
                self.last_frame_faces_cnt = self.current_frame_face_cnt
                self.current_frame_face_cnt = len(faces)
                filename = '../attendacnce.txt'
                with open(filename, 'a') as file:
                    # 4.1 当前帧和上一帧相比没有发生人脸数变化
                    if self.current_frame_face_cnt == self.last_frame_faces_cnt:
                        if "unknown" in self.current_frame_name_list:
                            self.reclassify_interval_cnt += 1

                        # 4.1.1 当前帧一张人脸
                        if self.current_frame_face_cnt == 1:
                            if self.reclassify_interval_cnt == self.reclassify_interval:

                                self.reclassify_interval_cnt = 0
                                self.current_frame_face_feature_list = []
                                self.current_frame_face_X_e_distance_list = []
                                self.current_frame_name_list = []

                                for i in range(len(faces)):
                                    shape = predictor(img_rd, faces[i])
                                    self.current_frame_face_feature_list.append(
                                        face_reco_model.compute_face_descriptor(img_rd, shape))

                                # a. 遍历捕获到的图像中所有的人脸
                                for k in range(len(faces)):
                                    self.current_frame_name_list.append("unknown")

                                    # b. 每个捕获人脸的名字坐标
                                    self.current_frame_face_position_list.append(tuple(
                                        [faces[k].left(),
                                         int(faces[k].bottom() + (faces[k].bottom() - faces[k].top()) / 4)]))

                                    # c. 对于某张人脸，遍历所有存储的人脸特征
                                    for i in range(len(self.features_known_list)):
                                        # 如果 person_X 数据不为空
                                        if str(self.features_known_list[i][0]) != '0.0':
                                            e_distance_tmp = self.return_euclidean_distance(
                                                self.current_frame_face_feature_list[k],
                                                self.features_known_list[i])
                                            self.current_frame_face_X_e_distance_list.append(e_distance_tmp)
                                        else:
                                            # 空数据 person_X
                                            self.current_frame_face_X_e_distance_list.append(999999999)

                                    # d. 寻找出最小的欧式距离匹配
                                    similar_person_num = self.current_frame_face_X_e_distance_list.index(
                                        min(self.current_frame_face_X_e_distance_list))

                                    if min(self.current_frame_face_X_e_distance_list) < 0.4:
                                        # 签到信息-学号
                                        self.current_frame_name_list[k] = self.name_known_list[similar_person_num]
                                        now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                                        mm = self.name_known_list[similar_person_num] + '  ' + now + '  已签到\n'
                                        file.write(self.name_known_list[similar_person_num] + '  ' + now + '     已签到\n')
                                        attend_records.append(mm)
                                    else:
                                        pass
                            else:
                                # 获取特征框坐标
                                for k, d in enumerate(faces):
                                    # 计算矩形框大小
                                    height = (d.bottom() - d.top())
                                    width = (d.right() - d.left())
                                    hh = int(height / 2)
                                    ww = int(width / 2)

                                    cv2.rectangle(img_rd,
                                                  tuple([d.left() - ww, d.top() - hh]),
                                                  tuple([d.right() + ww, d.bottom() + hh]),
                                                  (255, 255, 255), 2)

                                    self.current_frame_face_position_list[k] = tuple(
                                        [faces[k].left(),
                                         int(faces[k].bottom() + (faces[k].bottom() - faces[k].top()) / 4)])

                                    img_rd = self.draw_name(img_rd)

                    # 4.2 当前帧和上一帧相比发生人脸数变化
                    else:
                        self.current_frame_face_position_list = []
                        self.current_frame_face_X_e_distance_list = []
                        self.current_frame_face_feature_list = []

                        # 4.2.1 人脸数从 0->1
                        if self.current_frame_face_cnt == 1:
                            self.current_frame_name_list = []

                            for i in range(len(faces)):
                                shape = predictor(img_rd, faces[i])
                                self.current_frame_face_feature_list.append(
                                    face_reco_model.compute_face_descriptor(img_rd, shape))

                            # a. 遍历捕获到的图像中所有的人脸
                            for k in range(len(faces)):
                                self.current_frame_name_list.append("unknown")

                                # b. 每个捕获人脸的名字坐标
                                self.current_frame_face_position_list.append(tuple(
                                    [faces[k].left(),
                                     int(faces[k].bottom() + (faces[k].bottom() - faces[k].top()) / 4)]))

                                # c. 对于某张人脸，遍历所有存储的人脸特征
                                for i in range(len(self.features_known_list)):
                                    # 如果 person_X 数据不为空
                                    if str(self.features_known_list[i][0]) != '0.0':
                                        e_distance_tmp = self.return_euclidean_distance(
                                            self.current_frame_face_feature_list[k],
                                            self.features_known_list[i])
                                        self.current_frame_face_X_e_distance_list.append(e_distance_tmp)
                                    else:
                                        # 空数据 person_X
                                        self.current_frame_face_X_e_distance_list.append(999999999)

                                # d. 寻找出最小的欧式距离匹配
                                similar_person_num = self.current_frame_face_X_e_distance_list.index(
                                    min(self.current_frame_face_X_e_distance_list))

                                if min(self.current_frame_face_X_e_distance_list) < 0.4:
                                    # 签到信息-学号
                                    self.current_frame_name_list[k] = self.name_known_list[similar_person_num]
                                    now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                                    mm = self.name_known_list[similar_person_num] + '  ' + now + '  已签到\n'
                                    file.write(self.name_known_list[similar_person_num] + '  ' + now + '  已签到\n')
                                    attend_records.append(mm)
                                else:
                                    pass

                            if "unknown" in self.current_frame_name_list:
                                self.reclassify_interval_cnt += 1

                        # 4.2.1 人脸数从 1->0
                        elif self.current_frame_face_cnt == 0:
                            self.reclassify_interval_cnt = 0
                            self.current_frame_name_list = []
                            self.current_frame_face_feature_list = []

                # 5. 生成的窗口添加说明文字
                self.draw_note(img_rd)
                self.update_fps()
                ret, jpeg = cv2.imencode('.jpg', img_rd)
                return jpeg.tobytes()


# 老师端首页
@teacher.route('/reco_faces')
def reco_faces():
    return render_template('teacher/index.html')


# 输出视频流
def gen(camera, cid, faces):
    while True:
        frame = camera.get_frame(cid, faces)
        # 使用generator函数输出视频流， 每次请求输出的content类型是image/jpeg
        yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n'


#  这个地址返回视频流响应
@teacher.route('/video_feed', methods=['GET', 'POST'])
def video_feed():
    faces = Faces.query.all()
    return Response(gen(VideoCamera(), session['course'], faces),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


# 教师所有课程
@teacher.route('/all_course')
def all_course():
    flag = session['id'][0]  # 教师账号的第一个数字为0表示管理员，非0是教师账号
    if flag == '0':
        teacher_all_course = Course.query.filter().all()
    else:
        teacher_all_course = Course.query.filter(Course.t_id == session['id'])
    return render_template('teacher/course_attend.html', courses=teacher_all_course)


# 开启签到
@teacher.route('/records', methods=["POST"])
def records():
    # 开启签到后，开始单次的记录
    global attend_records
    attend_records = []
    now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    cid = request.form.get("id")
    session['course'] = cid
    session['now_time'] = now
    # 添加课程考勤记录
    course = Course.query.filter(Course.c_id == cid).first()
    course.times = course.times + '/' + str(now)
    db.session.commit()
    the_course_students = SC.query.filter(SC.c_id == cid)
    student_ids = []
    for sc in the_course_students:
        student_ids.append(sc.s_id)
    # 考勤记录初始化，所有人未签到
    all_students_attend = []
    for i in range(len(student_ids)):
        someone_addtend = Attendance(s_id=student_ids[i], c_id=cid, time=now, result='缺勤')
        all_students_attend.append(someone_addtend)
    db.session.add_all(all_students_attend)
    db.session.commit()
    return render_template("teacher/index.html")


# 实时显示当前签到人员
@teacher.route('/now_attend')
def now_attend():
    return jsonify(attend_records)


# 停止签到
@teacher.route('/stop_records', methods=['POST'])
def stop_records():
    all_sid = []
    all_cid = session['course']
    all_time = session['now_time']
    for someone_attend in attend_records:
        sid = someone_attend.split('  ')[0]
        all_sid.append(sid)
    # 已签到记录
    Attendance.query.filter(Attendance.time == all_time, Attendance.c_id == all_cid,
                            Attendance.s_id.in_(all_sid)).update({'result': '已签到'}, synchronize_session=False)
    db.session.commit()
    return redirect(url_for('teacher.all_course'))


# 签到记录
@teacher.route('/select_all_records', methods=['GET', 'POST'])
def select_all_records():
    tid = session['id']
    dict = {}
    num = 0
    # 筛选
    if request.method == 'POST':
        cid = request.form.get('course_id')
        sid = request.form.get('sid')
        select_time = request.form.get('time')
        print(cid, sid, select_time)
        if cid != '所有课程' and select_time != '':
            courses = db.session.query(Course).filter(Course.t_id == tid, Course.c_id == cid)
            num = 0
            for course in courses:
                times = course.times.split('/')
                one_course_all_time_attends = {}
                for i in range(1, len(times)):
                    one_time = times[i].split(' ')[0]
                    if one_time == select_time:
                        if sid != '':
                            one_time_attends = db.session.query(Attendance).filter(Attendance.c_id == course.c_id,
                                                                                   Attendance.time == times[i],
                                                                                   Attendance.s_id == sid).order_by(
                                's_id').all()
                        else:
                            one_time_attends = db.session.query(Attendance).filter(Attendance.c_id == course.c_id,
                                                                                   Attendance.time == times[
                                                                                       i]).order_by('s_id').all()
                        tt = Time_id(id=num, time=times[i])
                        num += 1
                        one_course_all_time_attends[tt] = one_time_attends
                dict[course] = one_course_all_time_attends
            courses = db.session.query(Course).filter(Course.t_id == tid)
            return render_template("teacher/show_records.html", dict=dict, courses=courses)
        elif cid != '所有课程' and select_time == '':
            courses = db.session.query(Course).filter(Course.t_id == tid, Course.c_id == cid)
            num = 0
            for course in courses:
                times = course.times.split('/')
                one_course_all_time_attends = {}
                for i in range(1, len(times)):
                    if sid == '':
                        one_time_attends = db.session.query(Attendance).filter(Attendance.c_id == course.c_id,
                                                                               Attendance.time == times[i]).order_by(
                            's_id').all()
                    else:
                        one_time_attends = db.session.query(Attendance).filter(Attendance.c_id == course.c_id,
                                                                               Attendance.time == times[i],
                                                                               Attendance.s_id == sid).order_by(
                            's_id').all()
                    tt = Time_id(id=num, time=times[i])
                    num += 1
                    one_course_all_time_attends[tt] = one_time_attends
                dict[course] = one_course_all_time_attends
            return render_template("teacher/show_records.html", dict=dict, courses=courses)
        elif cid == '所有课程' and select_time != '':
            courses = db.session.query(Course).filter(Course.t_id == tid)
            num = 0
            for course in courses:
                times = course.times.split('/')
                one_course_all_time_attends = {}
                for i in range(1, len(times)):
                    one_time = times[i].split(' ')[0]
                    if one_time == select_time:
                        if sid != '':
                            one_time_attends = db.session.query(Attendance).filter(Attendance.c_id == course.c_id,
                                                                                   Attendance.time == times[i],
                                                                                   Attendance.s_id == sid).order_by(
                                's_id').all()
                        else:
                            one_time_attends = db.session.query(Attendance).filter(Attendance.c_id == course.c_id,
                                                                                   Attendance.time == times[
                                                                                       i]).order_by('s_id').all()
                        tt = Time_id(id=num, time=times[i])
                        num += 1
                        one_course_all_time_attends[tt] = one_time_attends
                dict[course] = one_course_all_time_attends
            return render_template("teacher/show_records.html", dict=dict, courses=courses)
        else:
            print("没内容点击搜索")
            courses = db.session.query(Course).filter(Course.t_id == tid)
            num = 0
            for course in courses:
                times = course.times.split('/')
                one_course_all_time_attends = {}
                for i in range(1, len(times)):
                    if sid == '':
                        one_time_attends = db.session.query(Attendance).filter(Attendance.c_id == course.c_id,
                                                                               Attendance.time == times[i]).order_by(
                            's_id').all()
                    else:
                        one_time_attends = db.session.query(Attendance).filter(Attendance.c_id == course.c_id,
                                                                               Attendance.time == times[i],
                                                                               Attendance.s_id == sid).all()
                    tt = Time_id(id=num, time=times[i])
                    num += 1
                    one_course_all_time_attends[tt] = one_time_attends
                dict[course] = one_course_all_time_attends
            return render_template("teacher/show_records.html", dict=dict, courses=courses)

    # 未通过筛选
    courses = db.session.query(Course).filter(Course.t_id == tid)
    print(courses)
    num = 0
    for course in courses:
        times = course.times.split('/')
        one_course_all_time_attends = {}
        for i in range(1, len(times)):
            one_time_attends = db.session.query(Attendance).filter(Attendance.c_id == course.c_id,
                                                                   Attendance.time == times[i]).order_by('s_id').all()
            tt = Time_id(id=num, time=times[i])
            num += 1
            one_course_all_time_attends[tt] = one_time_attends
        print(one_course_all_time_attends)
        dict[course] = one_course_all_time_attends
    return render_template("teacher/show_records.html", dict=dict, courses=courses)


# 删除签到记录
@teacher.route('/delete_records', methods=['GET'])
def delete_records():
    record_id = request.args.get('record_id')
    attendance = Attendance.query.filter(Attendance.id == record_id).first()
    print(attendance)
    db.session.delete(attendance)
    db.session.commit()
    return redirect(url_for('teacher.select_all_records'))


# 修改签到信息
@teacher.route('/update_attend', methods=['POST'])
def update_attend():
    course = request.form.get('course_id')
    time = request.form.get('time')
    sid = request.form.get('sid')
    result = request.form.get('result')
    one_attend = Attendance.query.filter(Attendance.c_id == course, Attendance.s_id == sid,
                                         Attendance.time == time).first()
    one_attend.result = result
    db.session.commit()
    return redirect(url_for('teacher.select_all_records'))


# 课程管理
@teacher.route('/course_management', methods=['GET', 'POST'])
def course_management():
    flag = session['id'][0]  # 教师账号的第一个数字为0表示管理员，非0是教师账号
    dict = {}
    if request.method == 'POST':
        cid = request.form.get('course_id')
        cname = request.form.get('course_name')
        sid = request.form.get('sid')
        sc = SC.query.filter(SC.c_id == cid, SC.s_id == sid).first()
        db.session.delete(sc)
        db.session.commit()
    if flag == '0':
        teacher_all_course = Course.query.filter().all()
    else:
        teacher_all_course = Course.query.filter(Course.t_id == session['id'])
    for course in teacher_all_course:
        course_student = db.session.query(Student).join(SC).filter(Student.s_id == SC.s_id,
                                                                   SC.c_id == course.c_id).all()
        dict[course] = course_student
    return render_template('teacher/course_management.html', dict=dict)


# 添加课程
@teacher.route('/new_course', methods=['POST'])
def new_course():
    max = db.session.query(Course).order_by(Course.c_id.desc()).first()
    if max:
        cid = int(max.c_id) + 1
        cid = str(cid)
    else:
        cid = str(100001)
    course = Course(c_id=cid, c_name=request.form.get('cname'), t_id=session['id'])
    db.session.add(course)
    db.session.commit()
    return redirect(url_for('teacher.course_management'))


# 开启课程可选
@teacher.route('/open_course', methods=['POST'])
def open_course():
    cid = request.form.get('course_id')
    course = Course.query.filter(Course.c_id == cid).first()
    course.flag = '可选课'
    db.session.commit()
    return redirect(url_for('teacher.course_management'))


# 课程不可选
@teacher.route('/close_course', methods=['POST'])
def close_course():
    cid = request.form.get('course_id')
    course = Course.query.filter(Course.c_id == cid).first()
    course.flag = '不可选课'
    db.session.commit()
    return redirect(url_for('teacher.course_management'))


# 修改密码
@teacher.route('/update_password', methods=['GET', 'POST'])
def update_password():
    tid = session['id']
    teacher = Teacher.query.filter(Teacher.t_id == tid).first()
    if request.method == 'POST':
        old = request.form.get('old')
        if old == teacher.t_password:
            new = request.form.get('new')
            teacher.t_password = new
            db.session.commit()
            flash('修改成功！')
        else:
            flash('旧密码错误，请重试')
    return render_template('teacher/update_password.html', teacher=teacher)


# 查询选课
@teacher.route('/select_sc', methods=['GET', 'POST'])
def select_sc():
    dict = {}
    teacher_all_course = Course.query.filter(Course.t_id == session['id'])
    if request.method == 'POST':
        cid = request.form.get('course_id')
        sid = request.form.get('sid')
        if cid != '' and sid != '':
            course = Course.query.filter(Course.c_id == cid).first()
            dict[course] = db.session.query(Student).join(SC).filter(Student.s_id == SC.s_id,
                                                                     SC.c_id == course.c_id, SC.s_id == sid).all()
        elif cid != '' and sid == '':
            course = Course.query.filter(Course.c_id == cid).first()
            dict[course] = db.session.query(Student).join(SC).filter(Student.s_id == SC.s_id,
                                                                     SC.c_id == cid).all()
        elif cid == '' and sid != '':
            for course in teacher_all_course:
                course_student = db.session.query(Student).join(SC).filter(Student.s_id == SC.s_id,
                                                                           SC.c_id == course.c_id, SC.s_id == sid).all()
                dict[course] = course_student
        else:
            for course in teacher_all_course:
                course_student = db.session.query(Student).join(SC).filter(Student.s_id == SC.s_id,
                                                                           SC.c_id == course.c_id).all()
                dict[course] = course_student
        return render_template('teacher/student_getFace.html', dict=dict, courses=teacher_all_course)
    for course in teacher_all_course:
        course_student = db.session.query(Student).join(SC).filter(Student.s_id == SC.s_id,
                                                                   SC.c_id == course.c_id).all()
        dict[course] = course_student
    return render_template('teacher/student_getFace.html', dict=dict, courses=teacher_all_course)


# 开启学生人脸录入权限
@teacher.route('/open_getFace', methods=['POST'])
def open_getFace():
    sid = request.form.get('sid')
    student = Student.query.filter(Student.s_id == sid).first()
    student.flag = 1
    db.session.commit()
    return redirect(url_for('teacher.select_sc'))


# 关闭人脸录入权限
@teacher.route('/close_getFace', methods=['POST'])
def close_getFace():
    sid = request.form.get('sid')
    student = Student.query.filter(Student.s_id == sid).first()
    student.flag = 0
    db.session.commit()
    return redirect(url_for('teacher.select_sc'))


# 删除人脸
@teacher.route('/delete_face', methods=['POST'])
def delete_face():
    sid = request.form.get('sid')
    student = Student.query.filter(Student.s_id == sid).first()
    student.flag = 1
    db.session.commit()
    os.remove('app/static/data/data_faces_from_camera/' + sid + '/1.jpg')
    os.remove('app/static/data/data_faces_from_camera/' + sid + '/2.jpg')
    os.remove('app/static/data/data_faces_from_camera/' + sid + '/3.jpg')
    os.remove('app/static/data/data_faces_from_camera/' + sid + '/4.jpg')
    os.remove('app/static/data/data_faces_from_camera/' + sid + '/5.jpg')
    return redirect(url_for('teacher.select_sc'))


# 允许上传的文件类型
def allowed_file(filename):
    ALLOWED_EXTENSIONS = set(['xlsx', 'xls'])
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


# 检测学号是否存在
def sid_if_exist(sid):
    num = Student.query.filter(Student.s_id.in_(sid)).count()
    return num


# 检测课程号是否存在
def cid_if_exist(cid):
    num = Course.query.filter(Course.c_id.in_(cid)).count()
    return num


# 检测工号是否存在
def tid_if_exist(tid):
    num = Teacher.query.filter(Teacher.t_id.in_(tid)).count()
    return num


# 批量上传选课
@teacher.route('upload_sc', methods=['POST'])
def upload_sc():
    sc_file = request.files.get('sc_file')
    msg = 'error'
    if sc_file:
        if allowed_file(sc_file.filename):
            sc_file.save(sc_file.filename)
            df = pd.DataFrame(pd.read_excel(sc_file.filename))
            df1 = df[['学号', '课程号']]
            sid = df1[['学号']].values.T.tolist()[:][0]
            cid = df1[['课程号']].values.T.tolist()[:][0]
            if df.isnull().values.any():
                flash('存在空信息')
            else:
                sid_diff = len(set(sid)) - sid_if_exist(sid)
                cid_diff = len(set(cid)) - cid_if_exist(cid)
                if sid_diff == 0 and cid_diff == 0:
                    flash('success')
                    for i in range(len(sid)):
                        sc = SC(s_id=sid[i], c_id=cid[i])
                        db.session.merge(sc)
                        i += 1
                    db.session.commit()

                elif sid_diff == 0 and cid_diff != 0:
                    flash('有课程号不存在')
                elif sid_diff != 0 and cid_diff == 0:
                    flash('有学号不存在')
                else:
                    flash('有学号、课程号不存在')
            os.remove(sc_file.filename)
        else:
            flash("只能识别'xlsx,xls'文件")
    else:
        flash('请选择文件')
    return redirect(url_for('teacher.course_management'))


# 选择所有老师
@teacher.route('/select_all_teacher', methods=['POST', 'GET'])
def select_all_teacher():
    if request.method == 'POST':
        try:
            id = request.form.get('id')
            flag = request.form.get('flag')
            teacher = Teacher.query.get(id)
            if flag:
                sc = db.session.query(SC).join(Course).filter(SC.c_id == Course.c_id, Course.t_id == id).all()
                [db.session.delete(u) for u in sc]
                Course.query.filter(Course.t_id == id).delete()
            db.session.delete(teacher)
            db.session.commit()
        except Exception as e:
            print('Error:', e)
            flash("操作异常")
            return redirect(url_for('teacher.home'))
    teachers = Teacher.query.all()
    dict = {}
    for t in teachers:
        tc = Course.query.filter(Course.t_id == t.t_id).all()
        if tc:
            dict[t] = 1
        else:
            dict[t] = 0
    return render_template('teacher/all_teacher.html', dict=dict)


# 所有学生信息
@teacher.route('/select_all_student', methods=['POST', 'GET'])
def select_all_student():
    if request.method == 'POST':
        try:
            id = request.form.get('id')
            flag = request.form.get('flag')
            student = Student.query.get(id)
            if flag:
                SC.query.filter(SC.s_id == id).delete()
            db.session.delete(student)
            db.session.commit()
        except Exception as e:
            print('Error:', e)
            flash("操作异常")
            return redirect(url_for('teacher.home'))
    students = Student.query.all()
    dict = {}
    for s in students:
        tc = SC.query.filter(SC.s_id == s.s_id).all()
        if tc:
            dict[s] = 1
        else:
            dict[s] = 0
    return render_template('teacher/all_student.html', dict=dict)


# 上传老师信息
@teacher.route('/upload_teacher', methods=['POST'])
def upload_teacher():
    file = request.files.get('teacher_file')
    msg = 'error'
    if file:
        if allowed_file(file.filename):
            file.save(file.filename)
            df = pd.DataFrame(pd.read_excel(file.filename))
            df1 = df[['工号', '姓名', '密码']]
            id = df1[['工号']].values.T.tolist()[:][0]
            name = df1[['姓名']].values.T.tolist()[:][0]
            pwd = df1[['密码']].values.T.tolist()[:][0]
            if df.isnull().values.any() or len(id) == 0:
                flash('存在空信息')
            else:
                tid_diff = tid_if_exist(id)
                if tid_diff != 0:
                    flash('工号存在重复')
                else:
                    flash('success')
                    for i in range(len(id)):
                        t = Teacher(t_id=id[i], t_name=name[i], t_password=pwd[i])
                        db.session.add(t)
                        i += 1
                    db.session.commit()
            os.remove(file.filename)

        else:
            flash("只能识别'xlsx,xls'文件")
    else:
        flash('请选择文件')
    return redirect(url_for('teacher.select_all_teacher'))


# 上传学生信息
@teacher.route('/upload_student', methods=['POST'])
def upload_student():
    file = request.files.get('student_file')
    msg = 'error'
    if file:
        if allowed_file(file.filename):
            file.save(file.filename)
            df = pd.DataFrame(pd.read_excel(file.filename))
            df1 = df[['学号', '姓名', '密码']]
            id = df1[['学号']].values.T.tolist()[:][0]
            name = df1[['姓名']].values.T.tolist()[:][0]
            pwd = df1[['密码']].values.T.tolist()[:][0]
            if df.isnull().values.any() or len(id) == 0:
                flash('存在空信息')
            else:
                sid_diff = sid_if_exist(id)
                if sid_diff != 0:
                    flash('学号存在重复')
                else:
                    flash('success')
                    for i in range(len(id)):
                        # 添加学生账号，存入数据库
                        s = Student(s_id=id[i], s_name=name[i], s_password=pwd[i], flag=0)
                        db.session.add(s)
                        i += 1
                    db.session.commit()
            os.remove(file.filename)
        else:
            flash("只能识别'xls'文件")
    else:
        flash('请选择文件')

    return redirect(url_for('teacher.select_all_student'))


# 下载考勤信息
@teacher.route('/download', methods=['POST'])
def download():
    cid = request.form.get('cid')
    cname = request.form.get('cname')
    time = request.form.get('time')
    # 建立数据库引擎
    conn = pymysql.connect(host='localhost', port=3306, user='root', password='123456', db='db_face_attendance')
    # 写一条sql
    sql = "select s_id ,time,result from attendance where c_id='" + str(cid) + "' and time='" + str(time) + "'"
    print(sql)
    # 建立dataframe
    df = pd.read_sql_query(sql, con=conn)
    out = BytesIO()
    writer = pd.ExcelWriter('out.xlsx', engine='xlsxwriter')
    df.to_excel(excel_writer=writer, sheet_name='Sheet1', index=False)
    writer.save()
    out.seek(0)
    # 文件名中文支持
    name = cname + time + '考勤.xlsx'
    file_name = quote(name)
    response = send_file(out, as_attachment=True, download_name=file_name)
    response.headers['Content-Disposition'] += "; filename*=utf-8''{}".format(file_name)
    return send_file('../out.xlsx', as_attachment=True, download_name=file_name)
