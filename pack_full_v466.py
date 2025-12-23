import os
import sys
import shutil
import subprocess

def clear_dist_directory():
    """清理dist目录"""
    dist_path = "dist"
    if os.path.exists(dist_path):
        print("清理dist目录...")
        try:
            shutil.rmtree(dist_path)
            print("dist目录清理完成")
        except Exception as e:
            print(f"清理dist目录失败: {e}")
            return False
    return True

def build_executable():
    """使用PyInstaller打包exe"""
    print("开始打包WeLearn学习助手V4.6.6...")
    
    # PyInstaller命令
    cmd = [
        "pyinstaller",
        "--onefile",
        "--windowed",
        "--name=WeLearn学习助手V4.6.6",
        "--icon=ZR.ico",
        f"--version-file=version_info.txt",
        "--add-data=ZR.ico;.",
        "--hidden-import=core.account_manager",
        "--hidden-import=core.api",
        "--hidden-import=core.batch_manager",
        "--hidden-import=core.config",
        "--hidden-import=core.logger",
        "--hidden-import=ui.main_window",
        "--hidden-import=ui.account_detail",
        "--hidden-import=ui.workers",
        "--hidden-import=ui.account_view",
        "--hidden-import=PyQt5",
        "--hidden-import=PyQt5.QtCore",
        "--hidden-import=PyQt5.QtGui",
        "--hidden-import=PyQt5.QtWidgets",
        "--hidden-import=requests",
        "--hidden-import=bs4",
        "--hidden-import=lxml",
        "--hidden-import=queue",
        "--hidden-import=threading",
        "--hidden-import=time",
        "--hidden-import=random",
        "--hidden-import=json",
        "--hidden-import=os",
        "--hidden-import=sys",
        "--hidden-import=uuid",
        "--hidden-import=hashlib",
        "--hidden-import=base64",
        "--hidden-import=datetime",
        "--hidden-import=re",
        "--hidden-import=typing",
        "--hidden-import=typing_extensions",
        "--hidden-import=dataclasses",
        "--hidden-import=pathlib",
        "--hidden-import=urllib3",
        "--hidden-import=certifi",
        "--hidden-import=charset_normalizer",
        "--hidden-import=idna",
        "main.py"
    ]
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("打包成功!")
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"打包失败: {e}")
        print(f"错误输出: {e.stderr}")
        return False

def check_executable():
    """检查生成的exe文件"""
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

if __name__ == "__main__":
    print("=== WeLearn学习助手V4.6.6 打包脚本 ===")
    
    # 清理dist目录
    if not clear_dist_directory():
        print("清理dist目录失败，终止打包")
        sys.exit(1)
    
    # 打包exe
    if not build_executable():
        print("打包失败，请检查错误信息")
        sys.exit(1)
    
    # 检查生成的exe文件
    if not check_executable():
        print("生成的exe文件可能有问题")
        sys.exit(1)
    
    print("\n=== 打包完成 ===")
    print("生成的exe文件位于: dist/WeLearn学习助手V4.6.6.exe")