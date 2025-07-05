@echo off
echo HEIC to PNG 변환기 아이콘 수정 빌드...

REM 기존 파일들 정리
echo 기존 빌드 파일 정리 중...
if exist "dist" rmdir /s /q "dist"
if exist "build" rmdir /s /q "build"
if exist "*.spec" del "*.spec"

REM 고품질 아이콘 생성
echo 고품질 아이콘 생성 중...
python png_to_ico.py

REM 아이콘 파일 확인
echo 생성된 아이콘 파일:
dir app_icon.ico

REM PyInstaller로 exe 파일 생성 (아이콘 강제 적용)
echo exe 파일 생성 중... (아이콘 포함)
pyinstaller ^
    --onefile ^
    --windowed ^
    --icon="app_icon.ico" ^
    --name="HEIC_to_PNG_Converter" ^
    --clean ^
    --noconfirm ^
    --add-data="app_icon.ico;." ^
    --add-data="icon.png;." ^
    main.py

echo.
echo 빌드 완료!
echo.
echo 생성된 파일:
dir dist\HEIC_to_PNG_Converter.exe
echo.
echo 참고: exe 파일의 아이콘이 바로 반영되지 않을 수 있습니다.
echo Windows 아이콘 캐시를 새로고침하려면:
echo 1. 파일 탐색기에서 F5 키 누르기
echo 2. 또는 컴퓨터 재시작
echo.
pause
