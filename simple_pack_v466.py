#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的WeLearn学习助手V4.6.6打包脚本
"""

import os
import sys
import subprocess
import shutil

def main():
    print("=== WeLearn学习助手V4.6.6 打包脚本 ===")
    
    # 清理dist目录
    dist_path = "dist"
    if os.path.exists(dist_path):
        print("清理dist目录...")
        try:
            shutil.rmtree(dist_path)
            print("dist目录清理完成")
        except Exception as e:
            print(f"清理dist目录失败: {e}")
            return False
    
    # PyInstaller命令
    cmd = [
        "pyinstaller",
        "--onefile",
        "--windowed",
        "--name=WeLearn学习助手V4.6.6",
        "--icon=ZR.ico",
        "--version-file=version_info.txt",
        "--add-data=ZR.ico;.",
        "--hidden-import=ui.account_view",
        "--hidden-import=core.account_manager",
        "--hidden-import=core.api",
        "--hidden-import=core.batch_manager",
        "--hidden-import=core.config",
        "--hidden-import=core.logger",
        "--hidden-import=ui.main_window",
        "--hidden-import=ui.account_detail",
        "--hidden-import=ui.workers",
        "--hidden-import=PyQt5",
        "--hidden-import=requests",
        "--hidden-import=bs4",
        "--hidden-import=lxml",
        "main.py"
    ]
    
    print("开始打包WeLearn学习助手V4.6.6...")
    try:
        result = subprocess.run(cmd, check=True, text=True)
        print("打包成功!")
        
        # 检查生成的exe文件
        exe_path = "dist/WeLearn学习助手V4.6.6.exe"
        if os.path.exists(exe_path):
            file_size = os.path.getsize(exe_path) / (1024 * 1024)  # MB
            print(f"生成的exe文件: {exe_path}")
            print(f"文件大小: {file_size:.2f} MB")
            
            if file_size > 50:  # 预期大小应该大于50MB
                print("✅ 文件大小符合预期")
                return True
            else:
                print("❌ 文件大小小于预期，可能缺少依赖")
                return False
        else:
            print("❌ 未找到生成的exe文件")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"打包失败: {e}")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n=== 打包完成 ===")
        print("生成的exe文件位于: dist/WeLearn学习助手V4.6.6.exe")
    else:
        print("\n=== 打包失败 ===")
    
    sys.exit(0 if success else 1)