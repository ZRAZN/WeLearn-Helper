"""
网络诊断与修复工具箱
自动检测网络问题并提供一键修复功能
"""
import os
import subprocess
import ctypes
import sys
import winreg
import re
from typing import List, Tuple, Dict
from core.logger import get_logger

logger = get_logger("NetworkFixer")


def is_admin():
    """检查是否以管理员身份运行"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def run_cmd(cmd: str) -> Tuple[bool, str]:
    """执行命令并返回结果"""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        )
        return True, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return False, "命令执行超时"
    except Exception as e:
        return False, str(e)


def run_cmd_as_admin(cmd: str) -> Tuple[bool, str]:
    """以管理员身份执行命令"""
    try:
        result = subprocess.run(
            f'powershell -Command "Start-Process cmd -ArgumentList \'/c {cmd}\' -Verb RunAs -Wait"',
            shell=True, capture_output=True, text=True, timeout=60
        )
        return True, result.stdout + result.stderr
    except Exception as e:
        return False, str(e)


class NetworkDiagnostics:
    """网络诊断类"""
    
    def __init__(self):
        self.results: List[Dict] = []
    
    def diagnose_all(self) -> List[Dict]:
        """执行所有诊断"""
        self.results = []
        
        self.check_network_adapter()
        self.check_ip_config()
        self.check_dhcp()
        self.check_dns()
        self.check_hosts_file()
        self.check_lsp()
        self.check_proxy()
        self.check_internet()
        
        return self.results
    
    def add_result(self, name: str, status: str, detail: str):
        """添加诊断结果"""
        self.results.append({
            "name": name,
            "status": status,  # ok, warning, error
            "detail": detail
        })
    
    def check_network_adapter(self):
        """检查网络适配器"""
        logger.info("检查网络适配器...")
        ok, output = run_cmd("netsh interface show interface")
        if ok and "已启用" in output:
            self.add_result("网络适配器", "ok", "网络适配器正常")
        elif ok:
            self.add_result("网络适配器", "warning", "可能存在适配器问题")
        else:
            self.add_result("网络适配器", "error", f"无法检测: {output}")
    
    def check_ip_config(self):
        """检查IP配置"""
        logger.info("检查IP配置...")
        ok, output = run_cmd("ipconfig /all")
        if ok:
            if "IPv4 地址" in output or "IPv4 Address" in output:
                if "169.254" in output:
                    self.add_result("IP配置", "error", "获得APIPA地址(169.254.x.x)，DHCP可能有问题")
                else:
                    self.add_result("IP配置", "ok", "IP配置正常")
            else:
                self.add_result("IP配置", "warning", "未获取到IP地址")
        else:
            self.add_result("IP配置", "error", f"无法检测: {output}")
    
    def check_dhcp(self):
        """检查DHCP服务"""
        logger.info("检查DHCP服务...")
        ok, output = run_cmd("sc query dhcp")
        if ok and "RUNNING" in output:
            self.add_result("DHCP服务", "ok", "DHCP服务正在运行")
        elif ok:
            self.add_result("DHCP服务", "warning", "DHCP服务未运行")
        else:
            self.add_result("DHCP服务", "warning", "无法检测DHCP服务状态")
    
    def check_dns(self):
        """检查DNS配置"""
        logger.info("检查DNS配置...")
        ok, output = run_cmd("ipconfig /all")
        if ok:
            dns_match = re.findall(r'DNS 服务器[：:]\s*(\d+\.\d+\.\d+\.\d+)', output)
            if dns_match:
                self.add_result("DNS服务", "ok", f"DNS服务器: {', '.join(dns_match)}")
            else:
                # 检查是否有互联网连接，如果有则可能是VPN接管DNS
                inet_ok, inet_output = run_cmd("ping -n 1 -w 3000 baidu.com")
                if inet_ok and "TTL=" in inet_output:
                    self.add_result("DNS服务", "ok", "未检测到DNS服务器（可能由VPN/代理接管）")
                else:
                    self.add_result("DNS服务", "warning", "未配置DNS服务器")
        else:
            self.add_result("DNS服务", "error", f"无法检测: {output}")
    
    def check_proxy(self):
        """检查IE代理配置"""
        logger.info("检查代理配置...")
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                r"Software\Microsoft\Windows\CurrentVersion\Internet Settings")
            proxy_enable, _ = winreg.QueryValueEx(key, "ProxyEnable")
            winreg.CloseKey(key)
            
            if proxy_enable:
                # 检查是否有互联网连接，如果有则代理是正常使用的
                inet_ok, inet_output = run_cmd("ping -n 1 -w 3000 baidu.com")
                if inet_ok and "TTL=" in inet_output:
                    self.add_result("代理配置", "ok", "系统代理已启用（网络正常，可能是VPN/梯子使用中）")
                else:
                    self.add_result("代理配置", "warning", "系统代理已启用，可能影响连接")
            else:
                self.add_result("代理配置", "ok", "系统代理未启用")
        except:
            self.add_result("代理配置", "ok", "未检测到代理配置")
    
    def check_hosts_file(self):
        """检查HOSTS文件"""
        logger.info("检查HOSTS文件...")
        hosts_path = r"C:\Windows\System32\drivers\etc\hosts"
        try:
            with open(hosts_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            custom_lines = [line for line in content.split('\n') 
                          if line.strip() and not line.startswith('#')]
            if len(custom_lines) > 0:
                self.add_result("HOSTS文件", "warning", f"HOSTS文件有 {len(custom_lines)} 条自定义记录")
            else:
                self.add_result("HOSTS文件", "ok", "HOSTS文件正常")
        except Exception as e:
            self.add_result("HOSTS文件", "error", f"无法读取HOSTS文件: {str(e)}")
    
    def check_lsp(self):
        """检查LSP协议"""
        logger.info("检查LSP协议...")
        ok, output = run_cmd("netsh winsock show catalog")
        if ok and output.strip():
            self.add_result("LSP协议", "ok", "Winsock目录正常")
        else:
            self.add_result("LSP协议", "warning", "Winsock目录可能有问题")
    
    def check_internet(self):
        """检查互联网连接"""
        logger.info("检查互联网连接...")
        ok, output = run_cmd("ping -n 1 -w 3000 baidu.com")
        if ok and "TTL=" in output:
            self.add_result("互联网连接", "ok", "网络连接正常")
        else:
            self.add_result("互联网连接", "error", "无法连接互联网")


class NetworkFixer:
    """网络修复类"""
    
    def reset_winsock(self) -> Tuple[bool, str]:
        """重置Winsock"""
        logger.info("重置Winsock...")
        ok, output = run_cmd("netsh winsock reset")
        if ok:
            return True, "Winsock已重置，需要重启电脑生效"
        return False, f"重置失败: {output}"
    
    def reset_tcp_ip(self) -> Tuple[bool, str]:
        """重置IP/TCP协议栈"""
        logger.info("重置IP/TCP协议栈...")
        ok, output = run_cmd("netsh int ip reset")
        if ok:
            return True, "IP/TCP协议栈已重置，需要重启电脑生效"
        return False, f"重置失败: {output}"
    
    def flush_dns(self) -> Tuple[bool, str]:
        """刷新DNS缓存"""
        logger.info("刷新DNS缓存...")
        ok, output = run_cmd("ipconfig /flushdns")
        if ok:
            return True, "DNS缓存已刷新"
        return False, f"刷新失败: {output}"
    
    def reset_dhcp(self) -> Tuple[bool, str]:
        """释放并重新获取DHCP地址"""
        logger.info("重置DHCP...")
        run_cmd("ipconfig /release")
        ok, output = run_cmd("ipconfig /renew")
        if ok:
            return True, "DHCP地址已重新获取"
        return False, f"重置失败: {output}"
    
    def reset_proxy(self) -> Tuple[bool, str]:
        """重置代理配置"""
        logger.info("重置代理配置...")
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                r"Software\Microsoft\Windows\CurrentVersion\Internet Settings", 
                winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 0)
            winreg.CloseKey(key)
            return True, "代理配置已重置"
        except Exception as e:
            return False, f"重置失败: {str(e)}"
    
    def fix_hosts(self) -> Tuple[bool, str]:
        """修复HOSTS文件（恢复默认）"""
        logger.info("修复HOSTS文件...")
        hosts_path = r"C:\Windows\System32\drivers\etc\hosts"
        default_hosts = """# Copyright (c) 1993-2009 Microsoft Corp.
#
# This is a sample HOSTS file used by Microsoft TCP/IP for Windows.
#
# localhost name resolution is handled within DNS itself.
#	127.0.0.1       localhost
#	::1             localhost
"""
        try:
            with open(hosts_path, 'w', encoding='utf-8') as f:
                f.write(default_hosts)
            return True, "HOSTS文件已恢复默认"
        except Exception as e:
            return False, f"修复失败: {str(e)}"
    
    def reset_all(self) -> List[Tuple[str, bool, str]]:
        """执行全部修复"""
        results = []
        results.append(("重置Winsock", *self.reset_winsock()))
        results.append(("重置IP/TCP", *self.reset_tcp_ip()))
        results.append(("刷新DNS", *self.flush_dns()))
        results.append(("重置DHCP", *self.reset_dhcp()))
        results.append(("重置代理", *self.reset_proxy()))
        results.append(("修复HOSTS", *self.fix_hosts()))
        return results
