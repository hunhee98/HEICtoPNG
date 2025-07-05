import sys
import os
import shutil
import subprocess
import winreg
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import multiprocessing
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QListWidget, QFileDialog, QLabel, QProgressBar, QMessageBox, QLineEdit,
    QMenu, QAction, QListWidgetItem
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QKeySequence, QIcon, QPixmap
from pillow_heif import register_heif_opener
from PIL import Image

# HEIF 지원 활성화
register_heif_opener()

def resource_path(relative_path):
    """PyInstaller로 빌드된 exe에서 리소스 파일 경로 반환"""
    try:
        # PyInstaller가 생성한 임시 폴더 경로
        base_path = sys._MEIPASS
    except Exception:
        # 개발 환경에서는 현재 폴더
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

class ConverterThread(QThread):
    progress = pyqtSignal(int, int)  # 현재, 전체
    finished = pyqtSignal(list, str)  # 실패 목록, 출력 폴더

    def __init__(self, files, output_dir):
        super().__init__()
        self.files = files
        self.output_dir = output_dir
        self.failed = []
        # CPU 코어 수에 따라 워커 스레드 수 결정 (최대 4개)
        self.max_workers = min(4, max(2, multiprocessing.cpu_count()))

    def convert_single_file(self, file_info):
        """단일 파일 변환 (멀티스레딩용)"""
        idx, file_path = file_info
        try:
            # pillow-heif를 사용한 최적화된 변환
            with Image.open(file_path) as img:
                base = os.path.splitext(os.path.basename(file_path))[0]
                out_path = os.path.join(self.output_dir, base + ".png")
                # PNG 최적화 옵션 적용
                img.save(out_path, format="PNG", optimize=True, compress_level=6)
            return idx, None  # 성공
        except Exception as e:
            return idx, file_path  # 실패

    def run(self):
        total = len(self.files)
        completed = 0
        
        # 파일 목록을 인덱스와 함께 준비
        file_info_list = [(i, file_path) for i, file_path in enumerate(self.files)]
        
        # ThreadPoolExecutor로 병렬 처리
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 모든 작업 제출
            future_to_info = {
                executor.submit(self.convert_single_file, file_info): file_info 
                for file_info in file_info_list
            }
            
            # 작업 완료를 기다리며 진행률 업데이트
            for future in future_to_info:
                try:
                    idx, failed_file = future.result()
                    if failed_file:
                        self.failed.append(failed_file)
                    
                    completed += 1
                    self.progress.emit(completed, total)
                    
                except Exception as e:
                    # 예외 발생 시 해당 파일을 실패 목록에 추가
                    file_info = future_to_info[future]
                    self.failed.append(file_info[1])
                    completed += 1
                    self.progress.emit(completed, total)
        
        self.finished.emit(self.failed, self.output_dir)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HEIC → PNG 변환기")
        self.resize(600, 400)
        
        # 애플리케이션 아이콘 설정
        self.set_application_icon()
        
        self.files = []
        self.default_output_dir = self.get_default_output_dir()
        self.init_ui()

    def set_application_icon(self):
        """애플리케이션 아이콘 설정 (타이틀바, 작업표시줄용)"""
        icon_files = [
            "icon.png",      # 고품질 PNG 파일 (우선)
            "app_icon.ico",  # ICO 파일 (대체)
        ]
        
        for icon_file in icon_files:
            # PyInstaller 환경에서 리소스 경로 확인
            icon_path = resource_path(icon_file)
            
            if os.path.exists(icon_path):
                try:
                    # 고품질 아이콘 로딩
                    if icon_file.endswith('.png'):
                        pixmap = QPixmap(icon_path)
                        if not pixmap.isNull():
                            icon = QIcon(pixmap)
                            self.setWindowIcon(icon)
                            print(f"✅ PNG 아이콘 설정 성공: {icon_path}")
                            return
                    else:
                        icon = QIcon(icon_path)
                        if not icon.isNull():
                            self.setWindowIcon(icon)
                            print(f"✅ ICO 아이콘 설정 성공: {icon_path}")
                            return
                except Exception as e:
                    print(f"❌ 아이콘 설정 실패 ({icon_path}): {e}")
                    continue
        
        print("⚠️ 사용 가능한 아이콘 파일을 찾을 수 없습니다.")

    def get_default_output_dir(self):
        """사용자 폴더에 heic_to_png_YYYYMMDD_HHMMSS 폴더 경로 반환"""
        userprofile = os.environ.get('USERPROFILE', os.path.expanduser("~"))
        now = datetime.now().strftime("%Y%m%d_%H%M%S")
        folder_name = f"heic_to_png_{now}"
        return os.path.join(userprofile, folder_name)

    def init_ui(self):
        central = QWidget()
        main_layout = QHBoxLayout()

        # 왼쪽: 파일 리스트 영역
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        
        left_layout.addWidget(QLabel("선택된 HEIC 파일들:"))
        
        # 파일 리스트
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.ExtendedSelection)
        self.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self.show_context_menu)
        self.list_widget.keyPressEvent = self.list_key_press_event
        
        # 가이드 아이템 생성 시 hover 효과 완전 제거
        self.list_widget.setStyleSheet("""
            QListWidget {
                background-color: white;
                border: 1px solid #ccc;
            }
            QListWidget::item {
                padding: 5px;
                border-bottom: 1px solid #eee;
            }
            QListWidget::item:hover {
                background-color: #f0f0f0;
            }
            QListWidget::item:selected {
                background-color: #0078d4;
                color: white;
            }
            QListWidget::item[guide="true"] {
                color: #888;
                background: transparent !important;
                border: none !important;
                padding: 30px;
                font-size: 14px;
            }
            QListWidget::item[guide="true"]:hover {
                background: transparent !important;
            }
            QListWidget::item[guide="true"]:selected {
                background: transparent !important;
                color: #888 !important;
            }
        """)
        
        # 가이드 라벨 (파일 리스트가 비어있을 때 표시)
        self.guide_label = QLabel("폴더나 파일을 드래그해서 추가하세요")
        self.guide_label.setAlignment(Qt.AlignCenter)
        self.guide_label.setStyleSheet("color: #888; font-size: 14px; padding: 50px;")
        
        left_layout.addWidget(self.list_widget)
        left_widget.setLayout(left_layout)

        # 오른쪽: 컨트롤 패널
        right_widget = QWidget()
        right_widget.setFixedWidth(200)
        right_layout = QVBoxLayout()

        # 출력 폴더 설정
        right_layout.addWidget(QLabel("출력 폴더:"))
        self.out_edit = QLineEdit(self.default_output_dir)  # 항상 기본값 사용
        self.out_edit.setPlaceholderText(f"기본 경로: {self.default_output_dir}")
        right_layout.addWidget(self.out_edit)
        
        out_btn = QPushButton("폴더 선택")
        out_btn.clicked.connect(self.select_output_dir)
        right_layout.addWidget(out_btn)

        right_layout.addWidget(QLabel(""))  # 간격

        # 변환 시작 버튼
        self.convert_btn = QPushButton("변환하기")
        self.convert_btn.setFixedHeight(25)  # 높이를 25px로 조정
        self.convert_btn.clicked.connect(self.start_conversion)
        right_layout.addWidget(self.convert_btn)

        # 적당한 간격 추가
        right_layout.addWidget(QLabel(""))  
        
        # 스트레치로 위쪽 정렬 (덜 강하게)
        right_layout.addStretch(1)
        right_widget.setLayout(right_layout)

        # 메인 레이아웃에 추가
        main_layout.addWidget(left_widget, 3)  # 3:1 비율로 왼쪽이 더 넓음
        main_layout.addWidget(right_widget, 1)
        
        central.setLayout(main_layout)
        self.setCentralWidget(central)

        # 드래그 앤 드롭 활성화
        self.setAcceptDrops(True)
        
        # 초기 가이드 표시 업데이트
        self.update_guide_visibility()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        try:
            paths = [url.toLocalFile() for url in event.mimeData().urls()]
            if paths:  # paths가 비어있지 않은 경우에만 처리
                self.add_files(paths)
        except Exception as e:
            print(f"드래그 앤 드롭 오류: {e}")

    def update_guide_visibility(self):
        """파일 리스트가 비어있을 때 가이드 표시"""
        if len(self.files) == 0:
            # 리스트가 비어있으면 가이드 표시
            if self.list_widget.count() == 0:
                item = QListWidgetItem("📁 폴더나 파일을 드래그해서 추가하세요")
                # 완전히 비활성화
                item.setFlags(Qt.NoItemFlags)
                item.setTextAlignment(Qt.AlignCenter)
                # 가이드 아이템임을 표시하는 속성 추가
                item.setData(Qt.UserRole, "guide")
                self.list_widget.addItem(item)
        else:
            # 파일이 있으면 가이드 제거
            if self.list_widget.count() > 0:
                first_item = self.list_widget.item(0)
                if first_item and first_item.data(Qt.UserRole) == "guide":
                    self.list_widget.takeItem(0)

    def list_key_press_event(self, event):
        """리스트 위젯에서 키 이벤트 처리"""
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            self.remove_selected()
        else:
            # 기본 키 이벤트 처리
            QListWidget.keyPressEvent(self.list_widget, event)

    def show_context_menu(self, position):
        """우클릭 컨텍스트 메뉴 표시"""
        item = self.list_widget.itemAt(position)
        # 가이드 아이템이 아닌 실제 파일 아이템에서만 메뉴 표시
        if item and item.data(Qt.UserRole) != "guide":
            menu = QMenu()
            
            delete_action = QAction("🗑️ 삭제", self)
            delete_action.triggered.connect(self.remove_selected)
            menu.addAction(delete_action)
            
            if len(self.files) > 1:
                clear_action = QAction("🗑️ 전체 삭제", self)
                clear_action.triggered.connect(self.clear_all)
                menu.addAction(clear_action)
            
            menu.exec_(self.list_widget.mapToGlobal(position))

    def add_files(self, paths):
        """파일/폴더 경로 리스트를 받아서 HEIC 파일들을 추가"""
        if not paths:
            return
            
        heic_files = []
        try:
            for path in paths:
                if os.path.isdir(path):
                    # 폴더인 경우 재귀적으로 HEIC 파일 찾기
                    for root, _, files in os.walk(path):
                        for f in files:
                            if f.lower().endswith(('.heic', '.HEIC')):
                                heic_files.append(os.path.join(root, f))
                elif path.lower().endswith(('.heic', '.HEIC')):
                    # HEIC 파일인 경우 직접 추가
                    heic_files.append(path)
            
            # 가이드 텍스트 제거 (있는 경우)
            if self.list_widget.count() > 0:
                first_item = self.list_widget.item(0)
                if first_item and first_item.data(Qt.UserRole) == "guide":
                    self.list_widget.takeItem(0)
            
            # 중복 제거하고 리스트에 추가
            added_count = 0
            for f in heic_files:
                if f not in self.files:
                    self.files.append(f)
                    self.list_widget.addItem(f)
                    added_count += 1
            
            # 가이드 표시 업데이트
            self.update_guide_visibility()
            
            if added_count > 0:
                QMessageBox.information(self, "파일 추가 완료", f"{added_count}개의 HEIC 파일이 추가되었습니다.")
            elif heic_files:
                QMessageBox.information(self, "알림", "선택한 파일들이 이미 목록에 있습니다.")
            else:
                QMessageBox.warning(self, "경고", "HEIC 파일을 찾을 수 없습니다.")
        except Exception as e:
            QMessageBox.critical(self, "오류", f"파일 추가 중 오류가 발생했습니다:\n{str(e)}")

    def remove_selected(self):
        """선택된 항목들을 목록에서 제거"""
        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            return
        
        # 가이드 텍스트가 아닌 실제 파일만 제거
        items_to_remove = []
        for item in selected_items:
            if item.data(Qt.UserRole) != "guide":
                items_to_remove.append(item)
        
        if not items_to_remove:
            return
        
        # 역순으로 제거 (인덱스 변화 방지)
        for item in reversed(items_to_remove):
            row = self.list_widget.row(item)
            self.list_widget.takeItem(row)
            if row < len(self.files):  # 인덱스 범위 확인
                del self.files[row]
        
        # 가이드 표시 업데이트
        self.update_guide_visibility()

    def clear_all(self):
        """모든 파일 목록 지우기"""
        if self.files:
            reply = QMessageBox.question(
                self, "확인", "모든 파일을 목록에서 제거하시겠습니까?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.list_widget.clear()
                self.files = []
                # 가이드 표시 업데이트
                self.update_guide_visibility()

    def select_output_dir(self):
        """출력 폴더 선택"""
        dir_ = QFileDialog.getExistingDirectory(
            self, "출력 폴더 선택", self.out_edit.text() or ""
        )
        if dir_:
            self.out_edit.setText(dir_)

    def start_conversion(self):
        """변환 시작 (멀티스레딩)"""
        if not self.files:
            QMessageBox.warning(self, "경고", "변환할 HEIC 파일을 추가해주세요.")
            return
        
        output_dir = self.out_edit.text().strip()
        if not output_dir:
            output_dir = self.default_output_dir
            self.out_edit.setText(output_dir)
        
        try:
            os.makedirs(output_dir, exist_ok=True)
        except Exception as e:
            QMessageBox.critical(self, "오류", f"출력 폴더를 생성할 수 없습니다:\n{str(e)}")
            return
        
        # 변환 시작 정보 표시
        file_count = len(self.files)
        self.convert_btn.setEnabled(False)
        self.convert_btn.setText("변환 중 0%")
        
        # 변환 시작 시간 기록
        self.start_time = datetime.now()
        
        self.thread = ConverterThread(self.files, output_dir)
        self.thread.progress.connect(self.update_progress)
        self.thread.finished.connect(self.conversion_finished)
        self.thread.start()

    def update_progress(self, current, total):
        """진행률 업데이트"""
        percentage = int((current / total) * 100)
        self.convert_btn.setText(f"변환 중 {percentage}%")

    def conversion_finished(self, failed, output_dir):
        """변환 완료 처리"""
        self.convert_btn.setEnabled(True)
        self.convert_btn.setText("변환 완료")
        
        total = len(self.files)
        success = total - len(failed)
        
        # 결과 메시지 표시
        if failed:
            failed_list = "\n".join(failed[:5])  # 최대 5개만 표시
            if len(failed) > 5:
                failed_list += f"\n... 외 {len(failed) - 5}개"
            QMessageBox.warning(
                self, "변환 완료", 
                f"총 {total}개 중 {success}개 성공, {len(failed)}개 실패\n\n실패한 파일들:\n{failed_list}"
            )
        else:
            QMessageBox.information(
                self, "변환 완료", 
                f"총 {total}개 파일이 모두 성공적으로 변환되었습니다!"
            )
        
        # 결과 폴더 열기
        self.open_output_folder(output_dir)
        
        # 리스트 초기화
        self.clear_files()
        
        # 버튼 텍스트 원래대로
        self.convert_btn.setText("변환하기")

    def open_output_folder(self, folder_path):
        """결과 폴더 열기"""
        try:
            if os.name == 'nt':  # Windows
                os.startfile(folder_path)
            elif os.name == 'posix':  # macOS, Linux
                subprocess.run(['open', folder_path] if sys.platform == 'darwin' else ['xdg-open', folder_path])
        except Exception as e:
            print(f"폴더 열기 실패: {e}")

    def clear_files(self):
        """파일 리스트 초기화"""
        self.list_widget.clear()
        self.files = []
        self.update_guide_visibility()

def main():
    try:
        app = QApplication(sys.argv)
        
        # 애플리케이션 전체에 아이콘 설정 (고품질)
        icon_files = [
            "icon.png",      # 고품질 PNG 파일 (우선)
            "app_icon.ico",  # ICO 파일 (대체)
        ]
        
        for icon_file in icon_files:
            # PyInstaller 환경에서 리소스 경로 확인
            icon_path = resource_path(icon_file)
            
            if os.path.exists(icon_path):
                try:
                    if icon_file.endswith('.png'):
                        pixmap = QPixmap(icon_path)
                        if not pixmap.isNull():
                            app_icon = QIcon(pixmap)
                            app.setWindowIcon(app_icon)
                            print(f"✅ 앱 전체 PNG 아이콘 설정 성공: {icon_path}")
                            break
                    else:
                        app_icon = QIcon(icon_path)
                        if not app_icon.isNull():
                            app.setWindowIcon(app_icon)
                            print(f"✅ 앱 전체 ICO 아이콘 설정 성공: {icon_path}")
                            break
                except Exception as e:
                    print(f"❌ 앱 아이콘 설정 실패 ({icon_path}): {e}")
                    continue
        
        # Windows 특화 설정
        if os.name == 'nt':  # Windows
            try:
                import ctypes
                # 작업 표시줄 그룹화 ID 설정 (Windows 7+)
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('HEIC.Converter.1.0')
            except:
                pass
        
        win = MainWindow()
        win.show()
        sys.exit(app.exec_())
    except Exception as e:
        print(f"앱 실행 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
