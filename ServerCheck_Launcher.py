import os
import subprocess
import json
import socket
import platform
import sys 
from datetime import datetime

# 운영체제에 따라 설정하기 위한 변수 초기화
base_dir = None
result_base_dir = None
log_dir = None
python_cmd = "python"

# HWID 가져오는 함수
def get_hwid():
    try:
        if platform.system() == "Windows":
            # wmic 명령어 실행 (Windows)
            gethwid = subprocess.run(
                ["wmic", "diskdrive", "get", "serialnumber"],
                capture_output=True,
                text=True
            )
            
            output_lines = gethwid.stdout.strip().splitlines()

            # 빈 라인과 불필요한 공백 제거
            output_lines = [line.strip() for line in output_lines if line.strip()]

            if len(output_lines) > 1:
                hwid = output_lines[1].strip().rstrip(".")  # 끝의 . 제거
                return hwid
            else:
                return "Unknown-HWID"

        elif platform.system() == "Linux":
            # Linux에서 product_uuid 가져오기 (root 권한 필요)
            gethwid = subprocess.run(
                ["sudo", "cat", "/sys/class/dmi/id/product_uuid"],
                capture_output=True,
                text=True
            )
            
            if gethwid.returncode == 0:
                hwid = gethwid.stdout.strip()
                return hwid
            else:
                return "Unknown-HWID"

    except Exception as e:
        print(f"HWID를 가져오는 중 오류 발생: {str(e)}")
        return "Unknown-HWID"
    
# 로그 파일명 생성
def create_log_file_path(result_dir):
    # 진단결과 디렉토리명 추출
    dir_name = os.path.basename(result_dir)
    parts = dir_name.split('_')
    if len(parts) == 2:
        진단일자 = parts[0]
        체크번호 = parts[1]
        log_file_name = f"log_{진단일자}_{체크번호}.txt"
    else:
        log_file_name = "log_Unknown.txt"

    return os.path.join(log_dir, log_file_name)

# 로그 기록
def log_message(log_file_path, message):
    with open(log_file_path, 'a', encoding='utf-8') as log_file:
        log_file.write(f"{datetime.now()} - {message}\n")
    print(message)

# 진단 파일 실행
def run_diagnosis_script(script_path, json_output_path, 담당자, log_file_path):
    try:
        # 진단 파일을 실행하는 명령어 (python or python3)
        result = subprocess.run([python_cmd, script_path, 담당자], capture_output=True, text=True, check=True)
        diagnosis_result = json.loads(result.stdout)

        with open(json_output_path, 'w', encoding='utf-8') as json_file:
            json.dump(diagnosis_result, json_file, ensure_ascii=False, indent=4)

        log_message(log_file_path, f"진단 성공: {script_path}")
        return diagnosis_result
    
    except Exception as e:
        log_message(log_file_path, f"진단 실패: {script_path} - 오류: {str(e)}")
        return None

# 진단 범위 선택
def get_diagnosis_range():
    current_os = platform.system()  # 운영체제 확인

    if current_os == "Windows":
        max_range = 45
        print(f"현재 운영체제는 Windows입니다. 1~{max_range} 항목에서 진단할 범위를 선택하세요.")
    elif current_os == "Linux":
        max_range = 43
        print(f"현재 운영체제는 Linux입니다. 1~{max_range} 항목에서 진단할 범위를 선택하세요.")
    else:
        sys.exit("지원되지 않는 운영체제입니다. 프로그램을 종료합니다.")

    선택 = input("진단 방식을 선택하세요. 1. 전체 2. 부분: ").strip()

    if 선택 == '1':
        return "전체", []
    elif 선택 == '2':
        범위 = input(f"1~{max_range} 항목에서 진단할 범위를 설정해주세요. (예시: 1,2,5-10): ").strip()
        범위_리스트 = parse_range(범위, max_range)
        return "부분", 범위_리스트
    else:
        print("잘못된 입력입니다. 다시 시도하세요.")
        return get_diagnosis_range()

# 범위 파싱 (예: '1,2,5-10'을 리스트로 변환, max_range를 넘지 않도록 제한)
def parse_range(range_str, max_range):
    result = []
    ranges = range_str.split(',')
    for r in ranges:
        if '-' in r:
            start, end = map(int, r.split('-'))
            if start > max_range or end > max_range:
                print(f"범위 {start}-{end}는 허용된 범위를 초과합니다. (최대 {max_range})")
                continue
            result.extend(range(start, end + 1))
        else:
            num = int(r)
            if num > max_range:
                print(f"항목 {num}은 허용된 범위를 초과합니다. (최대 {max_range})")
                continue
            result.append(num)
    return result

# 진단항목파일 존재여부 체크
def check_files_exist(file_numbers):
    global base_dir 

    # 파일 번호를 정수로 변환하여 정렬
    file_numbers = sorted(file_numbers, key=lambda x: int(x))

    while True:
        existing_files = []
        missing_files = []

        # base_dir에 진단 파일들이 제대로 있는지 확인
        for num in file_numbers:
            file_path = os.path.join(base_dir, f"{num}.py")

            if os.path.exists(file_path):
                existing_files.append(num)
            else:
                missing_files.append(num)

        # 모든 항목이 존재하지 않을 경우 다시 선택
        if len(existing_files) == 0:
            print("선택한 모든 항목이 존재하지 않습니다. \n잘못된 입력입니다. 다시 시도하세요.")
            진단_방식, file_numbers = get_diagnosis_range()  # 새 항목을 선택하게 하는 함수
            continue  

        # 일부 파일이 존재하지 않을 때 사용자에게 진단을 계속할지 질문
        if missing_files:
            print(f"항목 {', '.join(map(str, missing_files))}가 없습니다.")
            응답 = input(f"항목 {', '.join(map(str, existing_files))}을(를) 진단하시겠습니까? (y/n): ").strip().lower()
            if 응답 == 'y' or 응답 == '':
                return sorted(existing_files, key=lambda x: int(x)) 
            else:
                return []

        return sorted(existing_files, key=lambda x: int(x))  

# 디렉토리 이름 생성
def create_unique_directory_name(base_dir):
    timestamp = datetime.now().strftime("%Y%m%d")
    check_number = 1
    dir_name = f"{timestamp}_check{check_number}"
    result_dir = os.path.join(base_dir, dir_name)

    # 동일한 이름이 존재할 경우 시퀀스 상승
    while os.path.exists(result_dir):
        check_number += 1
        dir_name = f"{timestamp}_check{check_number}"
        result_dir = os.path.join(base_dir, dir_name)
    
    os.makedirs(result_dir)
    return result_dir

# info.json 생성
def generate_info_json(result_dir, log_file_path):
    hwid = get_hwid()  # HWID 가져오기
    system_info = {
        "시설명": "주요정보통신기반시설1",  # To-do : 시설명 입력받기
        "진단 시작일자": "",
        "진단 종료일자": "",
        "시스템 목록": [
            {
                "시스템 이름": socket.gethostname(),
                "IP 주소": socket.gethostbyname(socket.gethostname()),
                "운영 체제": platform.system(), 
                "운영 체제 버전": platform.version(),
                "HWID": hwid,
                "지역": "서울"      
            }
        ]
    }

    info_json_path = os.path.join(result_dir, "info.json")
    with open(info_json_path, 'w', encoding='utf-8') as json_file:
        json.dump(system_info, json_file, ensure_ascii=False, indent=4)

    log_message(log_file_path, f"info.json 생성 완료: {info_json_path}")
    return info_json_path

# 통합 JSON 파일 생성
def make_json(result_dir, log_file_path, log_message):
    combined_result = {}

    # info.json 파일 읽기
    info_json_path = os.path.join(result_dir, "info.json")
    with open(info_json_path, 'r', encoding='utf-8') as info_file:
        combined_result = json.load(info_file)

    diagnosis_results = {}
    earliest_time = None
    latest_time = None

    # 진단 결과 파일들을 읽어서 저장
    for file_name in os.listdir(result_dir):
        if file_name.endswith('.json') and file_name != 'info.json':
            with open(os.path.join(result_dir, file_name), 'r', encoding='utf-8') as json_file:
                diagnosis_result = json.load(json_file)
                diagnosis_time = diagnosis_result.get("진단 시각")

                code = diagnosis_result.get("코드")
                diagnosis_results[code] = {
                    "카테고리": diagnosis_result.get("카테고리"),
                    "항목 설명": diagnosis_result.get("항목 설명"),
                    "중요도": diagnosis_result.get("중요도"),
                    "진단 결과": diagnosis_result.get("진단 결과"),
                    "진단 파일명": diagnosis_result.get("진단 파일명"),
                    "진단 담당자": diagnosis_result.get("진단 담당자"),
                    "진단 시각": diagnosis_time
                }

                if diagnosis_time:
                    diagnosis_time_obj = datetime.strptime(diagnosis_time, "%Y-%m-%d %H:%M:%S")

                    if earliest_time is None or diagnosis_time_obj < earliest_time:
                        earliest_time = diagnosis_time_obj

                    if latest_time is None or diagnosis_time_obj > latest_time:
                        latest_time = diagnosis_time_obj

    # 코드 기준으로 진단 결과 정렬
    diagnosis_results_sorted = dict(sorted(diagnosis_results.items(), key=lambda x: int(x[0].split('-')[-1])))

    # 시스템 목록에 정렬된 진단 항목 추가
    if combined_result.get("시스템 목록"):
        combined_result["시스템 목록"][0]["진단 항목"] = diagnosis_results_sorted

    # 진단 시작일자와 종료일자 설정
    if earliest_time:
        combined_result["진단 시작일자"] = earliest_time.strftime("%Y-%m-%d %H:%M:%S")
    if latest_time:
        combined_result["진단 종료일자"] = latest_time.strftime("%Y-%m-%d %H:%M:%S")

    # 통합 진단 결과 파일 저장
    combined_output_path = os.path.join(result_dir, f"{datetime.now().strftime('%Y%m%d')}_진단결과통합.json")
    with open(combined_output_path, 'w', encoding='utf-8') as json_file:
        json.dump(combined_result, json_file, ensure_ascii=False, indent=4)

    # 로그 메시지 기록
    log_message(log_file_path, f"통합 JSON 파일 생성 완료: {combined_output_path}")

# 메인 메소드
def main():
    # 전역 변수 설정
    global base_dir, result_base_dir, log_dir, python_cmd

    # 현재 운영체제 확인
    current_os = platform.system()

    # 현재 프로그램이 위치한 디렉토리 경로
    current_dir = os.path.dirname(__file__)

    # 운영체제에 따른 파일 경로 설정
    if current_os == "Windows":
        base_dir = os.path.join(current_dir, "1. 진단항목", "Windows")
        result_base_dir = os.path.join(current_dir, "3. 진단결과", "Windows")
        python_cmd = "python"  # Windows에서는 python 사용
    elif current_os == "Linux":
        base_dir = os.path.join(current_dir, "1. 진단항목", "Linux")
        result_base_dir = os.path.join(current_dir, "3. 진단결과", "Linux")
        python_cmd = "python3"  # Linux에서는 python3 사용
    else:
        sys.exit(f"지원되지 않는 운영체제입니다: {current_os}. \n프로그램을 종료합니다.")

    log_dir = os.path.join(result_base_dir, "Log")

    # 운영체제에 따라 사용자 응답
    while True:
        if current_os == "Windows":
            응답 = input("현재 운영체제는 Windows입니다. 진단하시겠습니까? (y/n): ").strip().lower()
        elif current_os == "Linux":
            응답 = input("현재 운영체제는 Linux입니다. 진단하시겠습니까? (y/n): ").strip().lower()
        else:
            sys.exit("지원되지 않는 운영체제입니다. 프로그램을 종료합니다.") 

        # 올바른 입력인지 확인
        if 응답 in ['y', '', 'n']:
            break
        else:
            print("잘못된 입력입니다. 다시 시도하세요.")

    # 'n'을 선택한 경우 프로그램 종료
    if 응답 == 'n':
        sys.exit("진단 프로그램을 종료합니다.") 

    # 진단 담당자 이름 입력
    진단자 = input("진단 담당자의 이름을 입력하세요: ").strip()

    # 진단 방식 및 범위 선택
    진단_방식, 진단_범위 = get_diagnosis_range()

    # 운영체제에 따른 진단 범위 설정
    if 진단_방식 == "전체":
        if current_os == "Windows":
            진단_범위 = list(range(1, 46))  # Windows에서는 1~45번 항목까지 진단
        elif current_os == "Linux":
            진단_범위 = list(range(1, 44))  # Linux에서는 1~43번 항목까지 진단

    # 진단할 파일 확인
    valid_files = check_files_exist(진단_범위)

    if not valid_files:
        print("유효한 진단 파일이 없습니다.")
        return

    # 결과 디렉터리 생성
    result_dir = create_unique_directory_name(result_base_dir)

    # 로그 파일명, 경로 지정
    log_file_path = create_log_file_path(result_dir)

    # 로그 디렉터리가 없을 경우 생성
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # info.json 파일 생성
    generate_info_json(result_dir, log_file_path)

    # 진단 스크립트 실행 및 결과 저장
    for file_num in valid_files:
        script_path = os.path.join(base_dir, f"{file_num}.py")
        json_output_path = os.path.join(result_dir, f"{file_num}.json")
        run_diagnosis_script(script_path, json_output_path, 진단자, log_file_path)

    # 통합 JSON 생성 여부 묻기
    while True:
        통합_응답 = input("통합 JSON 파일을 생성하시겠습니까? (y/n): ").strip().lower()

        # 올바른 입력인지 확인
        if 통합_응답 in ['y', 'n', '']:
            break
        else:
            print("잘못된 입력입니다. 다시 시도하세요.")

    if 통합_응답 == 'y' or 통합_응답 == '':
        make_json(result_dir, log_file_path, log_message)
        log_message(log_file_path, f"진단 완료. \n결과는 {result_dir}에 저장되었습니다.")
    else:
        log_message(log_file_path, f"통합 JSON 파일 생성을 건너뜁니다. \n진단 완료. \n결과는 {result_dir}에 저장되었습니다.")

if __name__ == "__main__":
    main()
