#!/usr/bin/python3
#Copyright Bail 2024
#cycheckin 学在重邮签到三方 v1.4.1_7
#2024.11.15-2024.12.6

import requests,json,sys,os,threading,uuid

device_id = str(uuid.uuid4())

class Account:
    def __init__(self,sessionid:str):
        self.sessionid = sessionid
        self.rollcalls = []
        self.headers = {
              'User-Agent': "BailCycheckin/1.4.1_7",
              'Accept': "application/json, text/plain, */*",
              'Accept-Encoding': "gzip, deflate",
              'X-Requested-With': "XMLHttpRequest",
              'X-SESSION-ID': self.sessionid,
              'Accept-Language': "zh-Hans",
              'Origin': "http://mobile.tc.cqupt.edu.cn",
              'Referer': "http://mobile.tc.cqupt.edu.cn/",
              'Content-Type': "application/json"
        }
    def search_rollcalls(self):
        url = "http://lms.tc.cqupt.edu.cn/api/radar/rollcalls"
        params = {
          'api_version': "1.1.0"
        }
        response = requests.get(url, params=params, headers=self.headers)

        if response.status_code != 200:
            raise RuntimeError(f'{response.status_code}: {response.text}(session已过期或不正确?)')
        raw_rollcalls = response.json()['rollcalls']
        for i in raw_rollcalls:
            self.rollcalls.append(Rollcall(i,self))
class Rollcall:
    def __init__(self,data:dict,account:Account):
        self.raw_data:dict = data
        self.id:int = data['rollcall_id']
        self.course_id:int = data['course_id']
        self.name:str = data['course_title']
        self.teacher_name:str = data['created_by_name']
        self.type:str = data['source']  # 签到类型 备选项：qr(二维码签到),number(数字签到),radar(雷达签到)
        self.account = account
    def checkin(self,data:str|dict):
        match self.type:
            case 'qr':
                resp = self.qr_checkin(data)
            case 'number':
                resp = self.number_checkin(data)
            case 'radar':
                resp = self.radar_checkin(data)
            case _:
                raise ValueError('未知的签到类型: {self.type}')
        return resp
    def qr_checkin(self,code:str):
        url = f"http://lms.tc.cqupt.edu.cn/api/rollcall/{self.id}/answer_qr_rollcall"
        payload = {
          "data": code,
          "deviceId": device_id
        }
        response = requests.put(url, data=json.dumps(payload), headers=self.account.headers)
        return response
    def number_checkin(self,num:str):
        url = f"http://lms.tc.cqupt.edu.cn/api/rollcall/{self.id}/answer_number_rollcall"
        payload = {
          "deviceId": device_id,
          "numberCode": num
        }
        response = requests.put(url, data=json.dumps(payload), headers=self.account.headers)
        return response
    def radar_checkin(self,location_data:dict):
        url = f"http://lms.tc.cqupt.edu.cn/api/rollcall/{self.id}/answer"
        payload = {"deviceId":device_id} | location_data
        response = requests.put(url, data=json.dumps(payload), headers=self.account.headers)
        return response

def baopo_number_checkin(rollcall:Rollcall):
    # 排除非数字签到
    if rollcall.type != 'number':
        raise ValueError('你传入的签到不是数字签到')
    # 每个线程爆破函数
    success = False
    def try_checkin(num:str):
        nonlocal success
        if success:
            return
        resp = rollcall.checkin(num)
        if resp.status_code == 200:
            success = True
            print(f'\n爆破成功！签到码为：{num}')
        else:
            print(num,resp.status_code,resp.json()['message'],end='\r')
    # 进行爆破
    for i in range(0,10000,200):
        # 如果成功则跳出
        if success:
            break
        # 输出爆破进度
        print(f'当前爆破：{i}-{i+199}')
        # 多线程爆破
        threads = []
        for j in range(i,i+200):
            t = threading.Thread(target=try_checkin,args=('%04d'%j,))
            threads.append(t)
            t.start()
        for t in threads:
            t.join()

'''    # 单线程爆破
    num = 0
    while True:
        resp = rollcall.check(num)
        if resp.status_code == 200:
            print()
            print(num)
            break
        else:
            print(num,resp.status_code,resp.json(),end='\r')
        num += 1
    print(resp.text)'''
def main():
    sessionid = os.getenv('CYSESSION')
    if not sessionid:
        sessionid = input('sessionid >')
    account = Account(sessionid)
    account.search_rollcalls()
    for i in account.rollcalls:
        print(f"[{i.id}] {i.name}({i.teacher_name}): { {'qr':'二维码','number':'数字','radar':'雷达'}[i.type]}签到")
        match i.type:
            case 'qr':  # 二维码签到
                code = input('code >')
                resp = i.checkin(code)
            case 'number':  # 数字签到
               num = input('num >')
               if not num:
                   baopo_number_checkin(i)
                   continue
               resp = i.checkin(num)
            case 'radar':    # 雷达签到
                input('Press Enter to check in')
                location_data = json.loads(os.popen('termux-location -p network').read())
                resp = i.checkin(location_data)
            case _:
                print('W: 发现未知签到类型: '+i.raw_data)
                continue
        if resp.status_code != 200:
            raise RuntimeError(f'{resp.status_code}: {resp.text}')
        res = resp.json()
        if res['status'] == 'on_call':
            print('签到成功')
        else:
            print(resp.json())

if __name__ == '__main__':
    sys.exit(main())
