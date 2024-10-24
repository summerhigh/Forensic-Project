import os
import sys
import json
from datetime import datetime
import subprocess

# 두 계층 상위 경로를 sys.path에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Finger 서비스 비활성화 여부를 점검하는 함수
def check_finger_service_status():
    try:
        # 시스템에서 finger 서비스 상태 확인 (finger 데몬이 실행 중인지 확인)
        finger_service_active = False
        
        # 리눅스 시스템에서는 systemctl이나 service로 finger 서비스 상태 확인
        if os.path.exists('/bin/systemctl') or os.path.exists('/usr/sbin/service'):
            finger_status = subprocess.run(['systemctl', 'is-active', 'finger'], capture_output=True, text=True)
            
            # 서비스가 존재하지 않거나 비활성화된 경우 처리
            if 'could not be found' in finger_status.stderr or 'inactive' in finger_status.stdout:
                return {"status": "양호", "message": "Finger 서비스가 존재하지 않거나 비활성화되었습니다."}
            elif 'active' in finger_status.stdout:
                finger_service_active = True

        # inetd 또는 xinetd 설정에서 finger 서비스 상태 확인
        if not finger_service_active:
            inetd_check = subprocess.run(['grep', '-i', 'finger', '/etc/inetd.conf'], capture_output=True, text=True)
            xinetd_check = subprocess.run(['grep', '-i', 'finger', '/etc/xinetd.d/finger'], capture_output=True, text=True, stderr=subprocess.DEVNULL)

            # inetd나 xinetd에 finger 서비스 설정이 없으면 비활성화 처리
            if not inetd_check.stdout and not xinetd_check.stdout:
                return {"status": "양호", "message": "Finger 서비스가 존재하지 않거나 비활성화되었습니다."}

            # finger 서비스 설정이 존재하면 활성화 상태로 처리
            if inetd_check.stdout or xinetd_check.stdout:
                finger_service_active = True
        
        # Finger 서비스가 활성화된 경우
        if finger_service_active:
            return {"status": "취약", "message": "Finger 서비스가 활성화되어 있습니다."}
        else:
            # Finger 서비스가 비활성화된 경우
            return {"status": "양호", "message": "Finger 서비스가 비활성화되어 있습니다."}

    except Exception as e:
        return {"status": "점검불가", "message": "Finger 서비스 상태 점검 중 오류가 발생했습니다."}

if __name__ == "__main__":
    # 진단 담당자 입력 받기 (런처에서 전달받음)
    담당자 = sys.argv[1] if len(sys.argv) > 1 else "Unknown"
    
    # Finger 서비스 상태 점검
    status = check_finger_service_status()
    
    # 진단 결과 JSON 형식으로 생성
    result = {
        "카테고리": "서비스 관리",
        "항목 설명": "Finger 서비스 비활성화",
        "중요도": "상",
        "진단 결과": status["status"], 
        "메시지": status["message"],
        "진단 파일명": "19.py",
        "진단 담당자": 담당자,
        "진단 시각": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "코드": "U-19"  
    }

    # 진단 결과 JSON 형식으로 출력
    print(json.dumps(result, ensure_ascii=False, indent=4))
