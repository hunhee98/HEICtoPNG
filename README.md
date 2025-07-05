# HEIC to PNG 변환기

윈도우용 HEIC → PNG 일괄 변환 프로그램입니다.

## 기능
- 드래그 앤 드롭으로 HEIC 파일 추가
- 폴더째 드래그 시 HEIC 파일 자동 검색
- 일괄 변환 및 진행률 표시
- 자동 출력 폴더 생성 (heic_to_png_YYYYMMDD_HHMMSS)
- 변환 완료 후 폴더 자동 열기

## 실행 파일 빌드 방법

### 1. 패키지 설치
```bash
pip install -r requirements.txt
```

### 2. 간단한 빌드 (배치 파일 사용)
```bash
build.bat
```

### 3. 수동 빌드
```bash
# 아이콘 변환
python png_to_ico.py

# exe 파일 생성
pyinstaller --onefile --windowed --icon=app_icon.ico --name="HEIC_to_PNG_Converter" main.py
```

### 4. 고급 빌드 (spec 파일 사용)
```bash
python png_to_ico.py
pyinstaller main.spec
```

## 빌드 결과
- `dist` 폴더에 `HEIC_to_PNG_Converter.exe` 파일이 생성됩니다.
- 이 exe 파일은 다른 컴퓨터에서도 실행 가능합니다 (Python 설치 불필요).

## 사용법
1. 프로그램 실행
2. HEIC 파일들을 왼쪽 영역에 드래그 앤 드롭
3. 필요시 출력 폴더 변경
4. "변환 시작" 버튼 클릭
5. 변환 완료 후 자동으로 출력 폴더가 열립니다

## 요구사항
- Windows 7 이상
- 최초 빌드 시에만 Python 3.7+ 필요 (사용자는 불필요)

## 문제해결

### 🛡️ Windows Defender SmartScreen 경고 (가장 흔함)
**증상**: "Windows에서 PC를 보호했습니다" 또는 "인식할 수 없는 앱입니다"
**해결방법**:
1. "추가 정보" 클릭
2. "실행" 버튼 클릭
3. 또는 파일 우클릭 → 속성 → 차단 해제 체크

### 🦠 바이러스 백신 프로그램 차단
**증상**: 파일이 삭제되거나 실행이 차단됨
**해결방법**:
1. 바이러스 백신 프로그램 열기
2. 예외/화이트리스트에 `HEIC_to_PNG_Converter.exe` 추가
3. 또는 실시간 보호 일시 해제 후 실행

### 🔒 권한 문제
**증상**: "액세스가 거부되었습니다" 오류
**해결방법**:
1. exe 파일 우클릭
2. "관리자 권한으로 실행" 선택
3. 또는 프로그램을 Documents 폴더로 이동

### 📚 시스템 라이브러리 누락
**증상**: "VCRUNTIME140.dll을 찾을 수 없습니다" 등의 DLL 오류
**해결방법**:
1. Microsoft Visual C++ 재배포 패키지 설치
   - [다운로드 링크](https://docs.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist)
2. Windows Update 실행

### 🐌 느린 실행 속도
**증상**: 프로그램 시작이 매우 느림 (10초 이상)
**원인**: 실시간 바이러스 검사
**해결방법**:
1. 바이러스 백신 예외 목록에 추가
2. SSD가 아닌 경우 SSD로 이동

### 💾 메모리 부족 오류
**증상**: "메모리가 부족합니다" 오류
**해결방법**:
1. 다른 프로그램 종료
2. 대용량 파일(100MB 이상) 처리 시 소량씩 나누어 변환

### 🔧 일반적인 해결 순서
문제 발생 시 다음 순서로 시도해보세요:
1. **관리자 권한으로 실행**
2. **Windows Defender 예외 추가**
3. **바이러스 백신 일시 해제**
4. **파일을 다른 폴더로 이동**
5. **컴퓨터 재시작**
