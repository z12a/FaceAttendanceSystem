# FaceAttendanceSystem

基于Python的学生人脸识别系统（后端部分）

## 项目简介

FaceAttendanceSystem 是一个基于 Python 实现的学生人脸识别考勤系统的后端部分。该系统使用了先进的人脸识别技术来实现自动化的学生考勤管理。

## 技术栈
<span > <img src="https://img.shields.io/badge/-Python-blue?style=flat-square&logo=python" /> <img src="https://img.shields.io/badge/-Django-green?style=flat-square&logo=django" /> <img src="https://img.shields.io/badge/-MySQL-orange?style=flat-square&logo=mysql" /> <img src="https://img.shields.io/badge/-dlib-yellow?style=flat-square&logo=python" /> <img src="https://img.shields.io/badge/-Bootstrap-purple?style=flat-square&logo=bootstrap" /> <img src="https://img.shields.io/badge/-OpenCV-lightgrey?style=flat-square&logo=opencv" /> <img src="https://img.shields.io/badge/-face_recognition-red?style=flat-square&logo=python" />
## 功能

- 学生人脸注册
- 自动人脸识别与考勤打卡
- 查询考勤记录
- 管理学生信息

## 安装与运行

### 环境要求

- Python 3.7

### 安装步骤

1. 克隆仓库

   ```bash
   git clone https://github.com/z12a/FaceAttendanceSystem.git
   cd FaceAttendanceSystem
   ```

2. 安装依赖

   ```bash
   pip install -r requirements.txt
   ```

3. 运行项目

   ```bash
   python main.py
   ```

## 使用说明

1. 启动后，系统会提供一个 RESTful API 接口，可以通过 HTTP 请求与系统交互。
2. 注册新学生时，需要上传学生的照片。
3. 每次考勤时，系统会自动识别上传的学生照片，并记录考勤结果。

## 文件结构

```plaintext
FaceAttendanceSystem/
│
├── app/                 # 应用程序目录
│   ├── __init__.py      # 初始化文件
│   ├── models.py        # 数据库模型
│   ├── views.py         # 视图函数
│   └── ...              # 其他模块
│
├── migrations/          # 数据库迁移文件
│
├── tests/               # 测试文件
│
├── requirements.txt     # 项目依赖
├── main.py              # 主程序入口
└── README.md            # 项目说明文件
```

## 贡献指南

欢迎任何形式的贡献！请遵循以下步骤：

1. Fork 这个仓库
2. 创建一个新的分支 (`git checkout -b feature-branch`)
3. 提交你的修改 (`git commit -am 'Add some feature'`)
4. 推送到分支 (`git push origin feature-branch`)
5. 创建一个新的 Pull Request

## 许可

本项目采用 MIT 许可，详细信息请参阅 [LICENSE](LICENSE) 文件。

## 联系方式

如果有任何问题或建议，请通过 [issues](https://github.com/z12a/FaceAttendanceSystem/issues) 提交。
觉得好的话点个⭐
