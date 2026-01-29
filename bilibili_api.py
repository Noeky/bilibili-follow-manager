import requests
import json
import time
import os
import sys
from typing import List, Dict, Optional
import logging

def get_app_dir():
    """获取应用程序目录"""
    if getattr(sys, 'frozen', False):
        # 打包后的可执行文件
        return os.path.dirname(sys.executable)
    else:
        # 开发环境
        return os.path.dirname(os.path.abspath(__file__))

class BilibiliAPI:
    """Bilibili API 客户端"""
    
    def __init__(self, config_path: str = "config.json"):
        """初始化 API 客户端
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = os.path.join(get_app_dir(), config_path)
        self.session = requests.Session()
        self.config = self._load_config(self.config_path)
        self._setup_session()
        
        # 设置日志
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)
    
    def _load_config(self, config_path: str) -> Dict:
        """加载配置文件"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"配置文件 {config_path} 不存在，请先设置登录")
        except json.JSONDecodeError:
            raise ValueError(f"配置文件 {config_path} 格式错误")
    
    def _setup_session(self):
        """设置会话"""
        self.session.cookies.update(self.config['cookies'])
        self.session.headers.update(self.config['headers'])
    
    def _make_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """发送请求并处理重试"""
        max_retries = self.config['settings']['max_retries']
        delay = self.config['settings']['delay_between_requests']
        
        for attempt in range(max_retries + 1):
            try:
                response = self.session.request(method, url, **kwargs)
                if response.status_code == 200:
                    return response
                elif response.status_code == 412:
                    self.logger.warning("请求被限制，等待更长时间...")
                    time.sleep(delay * 3)
                else:
                    self.logger.warning(f"请求失败，状态码: {response.status_code}")
                    
            except requests.RequestException as e:
                self.logger.warning(f"请求异常: {e}")
            
            if attempt < max_retries:
                self.logger.info(f"重试第 {attempt + 1} 次...")
                time.sleep(delay)
        
        raise Exception(f"请求失败，已重试 {max_retries} 次")
    
    def get_following_list(self, pn: int = 1, ps: int = 50) -> Dict:
        """获取关注列表
        
        Args:
            pn: 页码
            ps: 每页数量
            
        Returns:
            关注列表数据
        """
        url = "https://api.bilibili.com/x/relation/followings"
        params = {
            'vmid': self.config['cookies']['DedeUserID'],
            'pn': pn,
            'ps': ps,
            'order': 'desc'
        }
        
        response = self._make_request('GET', url, params=params)
        data = response.json()
        
        if data['code'] != 0:
            raise Exception(f"获取关注列表失败: {data['message']}")
        
        return data['data']
    

    def get_all_following(self) -> List[Dict]:
        """获取所有关注用户
        
        Returns:
            所有关注用户列表
        """
        all_following = []
        pn = 1
        ps = self.config['settings']['batch_size']
        
        self.logger.info("开始获取关注列表...")
        
        while True:
            try:
                data = self.get_following_list(pn, ps)
                following_list = data.get('list', [])
                
                if not following_list:
                    break
                
                # 处理每个用户的数据
                for user in following_list:
                    # 转换时间戳为可读时间
                    if 'mtime' in user and user['mtime']:
                        try:
                            import datetime
                            mtime = datetime.datetime.fromtimestamp(user['mtime'])
                            user['mtime_str'] = mtime.strftime('%Y-%m-%d %H:%M')
                        except:
                            user['mtime_str'] = '未知'
                    else:
                        user['mtime_str'] = '未知'
                
                all_following.extend(following_list)
                self.logger.info(f"已获取 {len(all_following)} 个关注用户")
                
                # 检查是否还有更多数据
                if len(following_list) < ps:
                    break
                
                pn += 1
                time.sleep(self.config['settings']['delay_between_requests'])
                
            except Exception as e:
                self.logger.error(f"获取关注列表失败: {e}")
                break
        
        self.logger.info(f"总共获取到 {len(all_following)} 个关注用户")
        return all_following
    
    def follow_user(self, fid: int) -> bool:
        """关注用户
        
        Args:
            fid: 用户ID
            
        Returns:
            是否成功
        """
        # 测试模式：只模拟操作，不实际执行
        if self.config['settings'].get('test_mode', False):
            time.sleep(0.1)  # 模拟网络延迟
            return True
        
        url = "https://api.bilibili.com/x/relation/modify"
        data = {
            'fid': fid,
            'act': 1,  # 1表示关注
            'csrf': self.config['cookies']['bili_jct']
        }
        
        try:
            response = self._make_request('POST', url, data=data)
            result = response.json()
            
            if result['code'] == 0:
                return True
            elif result['code'] == 22013:
                self.logger.warning(f"用户已关注 (用户ID: {fid})")
                return True  # 已关注也算成功
            else:
                self.logger.error(f"关注失败 (用户ID: {fid}): {result['message']}")
                return False
                
        except Exception as e:
            self.logger.error(f"关注异常 (用户ID: {fid}): {e}")
            return False

    def unfollow_user(self, fid: int) -> bool:
        """取消关注用户
        
        Args:
            fid: 用户ID
            
        Returns:
            是否成功
        """
        # 测试模式：只模拟操作，不实际执行
        if self.config['settings'].get('test_mode', False):
            time.sleep(0.1)  # 模拟网络延迟
            return True
        
        url = "https://api.bilibili.com/x/relation/modify"
        data = {
            'fid': fid,
            'act': 2,  # 2表示取消关注
            'csrf': self.config['cookies']['bili_jct']
        }
        
        try:
            response = self._make_request('POST', url, data=data)
            result = response.json()
            
            if result['code'] == 0:
                return True
            elif result['code'] == -352:
                self.logger.error(f"取消关注失败: 触发风控校验 (-352)，请稍后重试")
                raise Exception("RISK_CONTROL_352")
            else:
                self.logger.error(f"取消关注失败 (用户ID: {fid}): {result['message']}")
                return False
                
        except Exception as e:
            if str(e) == "RISK_CONTROL_352":
                raise e
            self.logger.error(f"取消关注异常 (用户ID: {fid}): {e}")
            return False
    
    def batch_unfollow_all(self, confirm_callback=None) -> Dict:
        """批量取消所有关注
        
        Args:
            confirm_callback: 确认回调函数
            
        Returns:
            操作结果统计
        """
        # 获取所有关注用户
        all_following = self.get_all_following()
        
        if not all_following:
            return {'total': 0, 'success': 0, 'failed': 0}
        
        total_count = len(all_following)
        is_test_mode = self.config['settings'].get('test_mode', False)
        max_test_ops = self.config['settings'].get('max_test_operations', 5)
        
        # 测试模式限制操作数量（内部逻辑，用户不感知）
        if is_test_mode:
            original_count = total_count
            total_count = min(total_count, max_test_ops)
            all_following = all_following[:total_count]
            # 内部日志，不向用户显示测试模式信息
            self.logger.debug(f"测试模式：限制操作数量为 {total_count}")
        
        # 确认操作
        if confirm_callback and not confirm_callback(total_count):
            self.logger.info("用户取消操作")
            return {'total': total_count, 'success': 0, 'failed': 0, 'cancelled': True}
        
        
        self.logger.info(f"开始批量取消关注，共 {total_count} 个用户")
        
        success_count = 0
        failed_count = 0
        risk_control_triggered = False
        delay = self.config['settings']['delay_between_requests']
        
        # 测试模式下减少延迟
        if is_test_mode:
            delay = min(delay, 0.2)
        
        for i, user in enumerate(all_following, 1):
            if risk_control_triggered:
                break
                
            fid = user['mid']
            uname = user['uname']
            
            self.logger.info(f"[{i}/{total_count}] 正在取消关注: {uname} (ID: {fid})")
            
            try:
                if self.unfollow_user(fid):
                    success_count += 1
                    self.logger.info(f"✓ 成功取消关注: {uname}")
                else:
                    failed_count += 1
                    self.logger.error(f"✗ 取消关注失败: {uname}")
            except Exception as e:
                if str(e) == "RISK_CONTROL_352":
                    self.logger.error("检测到风控限制 (-352)，停止后续操作。请等待几小时后再试，或在网页端手动验证。")
                    failed_count += 1
                    risk_control_triggered = True
                else:
                    failed_count += 1
            
            # 延迟以避免请求过快
            if i < total_count and not risk_control_triggered:
                time.sleep(delay)
        
        result = {
            'total': total_count,
            'success': success_count,
            'failed': failed_count,
            'test_mode': is_test_mode,
            'risk_control': risk_control_triggered
        }
        
        if risk_control_triggered:
             self.logger.warning(f"批量取消关注因风控中止! 已成功: {success_count}, 失败: {failed_count}")
        else:
             self.logger.info(f"批量取消关注完成! 总计: {total_count}, 成功: {success_count}, 失败: {failed_count}")
        return result
    
    def get_user_info(self) -> Dict:
        """获取当前用户信息"""
        url = "https://api.bilibili.com/x/web-interface/nav"
        
        try:
            response = self._make_request('GET', url)
            data = response.json()
            
            if data['code'] == 0:
                return data['data']
            else:
                raise Exception(f"获取用户信息失败: {data['message']}")
                
        except Exception as e:
            self.logger.error(f"获取用户信息异常: {e}")
            return {}
