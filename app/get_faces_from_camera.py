"""
@author:赵鸣宇
@project_name:考勤系统
@time:2025/3/06
@remarks:从摄像头获取人脸录入
"""

import os

import cv2
import dlib
import numpy as np

# Dlib 正向人脸检测器
detector = dlib.get_frontal_face_detector()


# 人脸识别、提取、保存
class Face_Register:
    def __init__(self):
        pass

    # 将录入的图片文件夹下所有图片进行人脸检测，截取人脸部分
    def process(self, path):
        photos_list = os.listdir(path)
        if photos_list:
            for i in range(len(photos_list)):
                # 调用 return_128d_features() 得到 128D 特征
                current_face_path = path + photos_list[i]
                print("%-40s %-20s" % (" >> 正在检测的人脸图像:", current_face_path))
                img_rd = cv2.imread(current_face_path)
                faces = detector(img_rd, 0)  # Dlib人脸检测器
                # 遇到没有检测出人脸的图片跳过
                if len(faces) == 0:
                    i += 1
                else:
                    for k, d in enumerate(faces):
                        # 计算人脸区域矩形框大小
                        height = (d.bottom() - d.top())
                        width = (d.right() - d.left())
                        hh = int(height / 2)
                        ww = int(width / 2)

                        # 判断人脸矩形框是否超出 480x640
                        if (d.right() + ww) > 640 or (d.bottom() + hh > 480) or (d.left() - ww < 0) or (
                                d.top() - hh < 0):
                            print("%-40s %-20s" % (" >>超出范围，该图作废", current_face_path))
                        else:
                            img_blank = np.zeros((int(height * 2), width * 2, 3), np.uint8)
                            for ii in range(height * 2):
                                for jj in range(width * 2):
                                    img_blank[ii][jj] = img_rd[d.top() - hh + ii][d.left() - ww + jj]
                            cv2.imwrite(path + str(i + 1) + ".jpg", img_blank)
                            print("写入本地:", str(path) + str(i + 1) + ".jpg")
        else:
            print(" >> 文件夹内图像文件为空" + path, '\n')

    # 单张图片处理
    def single_pocess(self, path):
        # 读取人脸图像
        img_rd = cv2.imread(path)
        # Dlib的人脸检测器
        faces = detector(img_rd, 0)
        # 遇到没有检测出人脸的图片跳过
        if len(faces) == 0:
            print("未检测到人脸！")
            return "none"
        else:
            for k, d in enumerate(faces):
                # 计算人脸区域矩形框大小
                height = (d.bottom() - d.top())
                width = (d.right() - d.left())
                hh = int(height / 2)
                ww = int(width / 2)
                print(height, width, hh, ww)
                print(d.right() + ww, d.bottom() + hh, d.left() - ww, d.top() - hh)
                # 6. 判断人脸矩形框是否超出 480x640
                if (d.right() + ww) > 640 or (d.bottom() + hh > 480) or (d.left() - ww < 0) or (d.top() - hh < 0):
                    print("人脸超出范围，该图作废", path)
                    return "big"
                else:
                    img_blank = np.zeros((int(height * 2), width * 2, 3), np.uint8)
                    for ii in range(height * 2): # 300
                        for jj in range(width * 2): # 300
                            img_blank[ii][jj] = img_rd[d.top() - hh + ii][d.left() - ww + jj]
                    cv2.imwrite(path, img_blank)
                    print("图片合格，写入本地：", path)
                    return "right"
