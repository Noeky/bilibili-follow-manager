#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import time
import os
import sys
import requests
import qrcode
from typing import Dict, Optional

def get_app_dir():
    """获取应用程序目录"""
    if getattr(sys, 'frozen', False):
        # 打包后的可执行文件
        return os.path.dirname(sys.executable)
    else:
        # 开发环境
        return os.path.dirname(os.path.abspath(__file__))

class BilibiliAutoLogin:
    
    def __init__(self):
        self.session = requests.Session()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://www.bilibili.com/"
        }
    
    def get_qrcode(self):
        """获取登录二维码URL和key"""
        url = "https://passport.bilibili.com/x/passport-login/web/qrcode/generate"
        try:
            resp = self.session.get(url, headers=self.headers).json()
            if resp['code'] == 0:
                return resp['data']['url'], resp['data']['qrcode_key']
        except Exception as e:
            print(f"获取二维码失败: {e}")
        return None, None

    def check_qrcode(self, qrcode_key):
        """检查二维码扫描状态"""
        url = "https://passport.bilibili.com/x/passport-login/web/qrcode/poll"
        params = {"qrcode_key": qrcode_key}
        try:
            resp = self.session.get(url, params=params, headers=self.headers).json()
            return resp
        except Exception:
            return None

    def manual_login_bilibili(self) -> Optional[Dict]:
        """执行扫码登录流程"""
        try:
            print("正在获取登录二维码...")
            url, qrcode_key = self.get_qrcode()
            if not url:
                print("无法获取二维码URL")
                return None
            
            # 生成二维码图片
            try:
                qr = qrcode.QRCode(version=1, box_size=10, border=5)
                qr.add_data(url)
                qr.make(fit=True)
                img = qr.make_image(fill_color="black", back_color="white")
                
                # 保存并打开图片
                img_path = os.path.join(get_app_dir(), 'login_qrcode.png')
                with open(img_path, "wb") as f:
                    img.save(f)
                print(f"二维码已生成: {img_path}")
                
                # 尝试自动打开图片
                try:
                    if sys.platform.startswith('win'):
                        os.startfile(img_path)
                    elif sys.platform == 'darwin':
                        os.system(f'open "{img_path}"')
                    else:
                        os.system(f'xdg-open "{img_path}"')
                except Exception as e:
                    print(f"无法自动打开图片，请手动打开: {e}")
                    
            except ImportError:
                print("错误: 缺少必要库。请运行: pip install qrcode Pillow")
                print(f"或者手动打开此链接生成二维码: {url}")
                return None
            
            print("请扫描二维码登录 (二维码有效期约3分钟)...")
            
            # 轮询状态
            max_wait_time = 180
            start_time = time.time()
            
            while time.time() - start_time < max_wait_time:
                data = self.check_qrcode(qrcode_key)
                if not data:
                    time.sleep(2)
                    continue
                
                code = data['data']['code']
                
                if code == 0: # 登录成功
                    print("登录成功！正在保存凭据...")
                    # 清理图片
                    try:
                        if os.path.exists(img_path):
                            os.remove(img_path)
                    except:
                        pass
                    
                    # 提取 Cookies
                    cookies = requests.utils.dict_from_cookiejar(self.session.cookies)
                    
                    if 'SESSDATA' in cookies and 'bili_jct' in cookies:
                        return cookies
                    else:
                        # 如果自动获取不到，可能需要处理 data.url
                        # 但通常 requests session 会自动处理 Set-Cookie
                        return cookies
                        
                elif code == 86038: # 二维码失效
                    print("二维码已失效，请重试")
                    break
                
                time.sleep(2)
                
            else:
                print("登录超时")
                return None
                
        except Exception as e:
            print(f"登录过程出错: {e}")
            return None
            
        return None

    def create_config_file(self, cookies: Dict) -> bool:
        try:
            config_template = {
                "cookies": {
                    "SESSDATA": "",
                    "bili_jct": "",
                    "DedeUserID": ""
                },
                "headers": {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Referer": "https://www.bilibili.com/"
                },
                "settings": {
                    "delay_between_requests": 1.0,
                    "max_retries": 3,
                    "batch_size": 50,
                    "test_mode": False,
                    "max_test_operations": 5
                }
            }
            
            config_template["cookies"]["SESSDATA"] = cookies.get("SESSDATA", "")
            config_template["cookies"]["bili_jct"] = cookies.get("bili_jct", "")
            config_template["cookies"]["DedeUserID"] = cookies.get("DedeUserID", "")
            
            # 确保保存到正确的位置
            app_dir = get_app_dir()
            config_file_path = os.path.join(app_dir, 'config.json')
            
            with open(config_file_path, 'w', encoding='utf-8') as f:
                json.dump(config_template, f, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            print(f"创建配置文件失败: {e}")
            return False

def auto_login_setup() -> bool:
    print("程序将生成登录二维码，请使用B站App扫描...")
    
    login_tool = BilibiliAutoLogin()
    cookies = login_tool.manual_login_bilibili()
    
    if cookies and login_tool.create_config_file(cookies):
        return True
    else:
        print("登录失败或取消")
        # 清理可能残留的图片
        try:
            img_path = os.path.join(get_app_dir(), 'login_qrcode.png')
            if os.path.exists(img_path):
                os.remove(img_path)
        except:
            pass
        return False

if __name__ == "__main__":
    auto_login_setup()
