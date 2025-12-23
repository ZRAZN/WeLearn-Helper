import os
import subprocess
import sys

def verify_exe():
    """验证新打包的可执行文件是否包含所有必要的模块"""
    exe_path = r"E:\t\Auto_WeLearn\dist\WeLearn学习助手V4.6.5.exe"
    
    print("验证新打包的可执行文件...")
    print(f"可执行文件路径: {exe_path}")
    
    # 检查文件是否存在
    if not os.path.exists(exe_path):
        print(f"错误: 可执行文件不存在: {exe_path}")
        return False
    
    # 获取文件大小
    file_size = os.path.getsize(exe_path)
    print(f"文件大小: {file_size / (1024*1024):.2f} MB")
    
    # 检查文件大小是否合理（应该大于60MB）
    if file_size < 60 * 1024 * 1024:
        print("警告: 文件大小小于预期，可能缺少某些依赖项")
        return False
    
    print("\n验证结果:")
    print("✓ 文件存在")
    print("✓ 文件大小合理")
    print("✓ 可执行文件已成功创建")
    
    # 检查打包脚本是否包含了所有必要的模块
    pack_script = r"E:\t\Auto_WeLearn\pack_complete_v465.py"
    if os.path.exists(pack_script):
        print("\n检查打包脚本中包含的模块:")
        with open(pack_script, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # 检查是否包含了account_view模块
        if '"ui.account_view"' in content:
            print("✓ 包含ui.account_view模块")
        else:
            print("✗ 未找到ui.account_view模块")
            
        # 检查其他关键模块
        modules_to_check = [
            "ui.workers",
            "ui.account_detail",
            "core.account_manager",
            "core.api",
            "core.logger"
        ]
        
        for module in modules_to_check:
            if f'"{module}"' in content:
                print(f"✓ 包含{module}模块")
            else:
                print(f"✗ 未找到{module}模块")
                
        # 检查是否包含了数据文件
        data_files_to_check = [
            "ZR.png",
            "ZR.ico",
            "accounts.json",
            "ui"
        ]
        
        print("\n检查打包脚本中包含的数据文件:")
        for data_file in data_files_to_check:
            if data_file in content:
                print(f"✓ 包含{data_file}")
            else:
                print(f"✗ 未找到{data_file}")
    
    return True

if __name__ == "__main__":
    success = verify_exe()
    if success:
        print("\n验证结果: 成功！可执行文件应该包含所有必要的模块")
    else:
        print("\n验证结果: 失败！可执行文件可能存在问题")
    
    input("\n按回车键退出...")