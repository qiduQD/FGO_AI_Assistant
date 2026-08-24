# ui/app.py
import sys
import os
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QLineEdit,
                             QPushButton, QComboBox, QVBoxLayout, QHBoxLayout)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QPixmap
from ui.expression_compositor import ExpressionCompositor

# 引入我们写好的 Agent 模块
from perception.llm_client import call_ollama
from agent.core import AgentService, record_explicit_profile
from agent.prompts import is_repeated_reply, parse_chat_response, sanitize_reply
from agent.memory import MemoryStore
from agent.vector_store import VectorStore
from config import VECTOR_COLLECTION, VECTOR_DB_PATH

# --- 后台 Agent 线程 ---
class AgentWorker(QThread):
    # 定义信号：向 UI 线程传递人设回复与结束通知
    signal_reply = pyqtSignal(str)
    signal_emotion = pyqtSignal(str)
    signal_finished = pyqtSignal()

    def __init__(self, user_goal: str, mode: str, memory: MemoryStore, max_steps: int = 5):
        super().__init__()
        self.user_goal = user_goal
        self.mode = mode
        self.memory = memory
        self.max_steps = max_steps

    def run(self):
        try:
            service = AgentService(self.memory)
            if self.mode == "chat":
                response = service.chat(
                    self.user_goal,
                    cancelled=self.isInterruptionRequested,
                    on_emotion=self.signal_emotion.emit,
                )
                self.signal_reply.emit(response or "模型没有返回内容，请确认 Ollama 正在运行。")
                return

            final_reply = service.run_agent(
                self.user_goal,
                self.max_steps,
                cancelled=self.isInterruptionRequested,
                on_emotion=self.signal_emotion.emit,
            )
            if final_reply:
                self.signal_reply.emit(final_reply)
        except Exception as error:
            self.signal_reply.emit(f"任务执行失败：{error}")
        finally:
            self.signal_finished.emit()


# --- 前端透明挂件 GUI ---
class DesktopAgentUI(QWidget):
    def __init__(self):
        super().__init__()
        self.memory = MemoryStore()
        self.init_ui()

    def init_ui(self):
        # 1. 窗口无边框、背景透明、永远置顶
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.SubWindow)
        self.setAttribute(Qt.WA_TranslucentBackground)

        layout = QVBoxLayout()

        # 右上角关闭按钮
        top_bar = QHBoxLayout()
        top_bar.addStretch()
        close_button = QPushButton("X", self)
        close_button.setFixedSize(28, 28)
        close_button.setToolTip("关闭")
        close_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(30, 30, 40, 210);
                color: #00FFCC;
                border: 1px solid #00FFCC;
                border-radius: 5px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #00FFCC;
                color: #1E1E28;
            }
        """)
        close_button.clicked.connect(self.close)
        top_bar.addWidget(close_button)
        clear_button = QPushButton("清空", self)
        clear_button.setToolTip("清除短期记忆、长期画像、摘要和向量索引")
        clear_button.clicked.connect(self.clear_memory)
        top_bar.insertWidget(0, clear_button)
        layout.addLayout(top_bar)

        self.mode_selector = QComboBox(self)
        self.mode_selector.addItem("纯对话", "chat")
        self.mode_selector.addItem("Agent 操作", "agent")
        self.mode_selector.setCurrentIndex(0)
        self.mode_selector.setToolTip("选择普通聊天或电脑操作模式")
        self.mode_selector.setStyleSheet("""
            QComboBox {
                background-color: rgba(20, 20, 20, 220);
                color: white;
                border: 1px solid #555;
                border-radius: 5px;
                padding: 5px;
            }
        """)
        layout.addWidget(self.mode_selector)

        # 2. 角色立绘 Label
        self.char_label = QLabel(self)
        img_path = os.path.join("ui", "assets", "BB_channel.png")
        if os.path.exists(img_path):
            self.expression_compositor = ExpressionCompositor(img_path)
            self.set_expression("neutral")
        else:
            self.char_label.setText("【请放置 BB_channel.png】")
            self.char_label.setStyleSheet("color: white;")
        layout.addWidget(self.char_label, alignment=Qt.AlignCenter)

        # 3. 对话气泡框
        self.dialog_label = QLabel("哼，有什么任务要本助手处理的吗？", self)
        self.dialog_label.setStyleSheet("""
            QLabel {
                background-color: rgba(30, 30, 40, 210);
                color: #00FFCC;
                border: 2px solid #00FFCC;
                border-radius: 10px;
                padding: 10px;
                font-size: 13px;
                font-family: 'Microsoft YaHei';
            }
        """)
        self.dialog_label.setWordWrap(True)
        self.dialog_label.setMinimumWidth(320)
        self.dialog_label.setMaximumWidth(340)
        self.dialog_label.setMinimumHeight(64)
        layout.addWidget(self.dialog_label)

        # 4. 指令输入框
        self.input_field = QLineEdit(self)
        self.input_field.setPlaceholderText("输入指令按回车...")
        self.input_field.setStyleSheet("""
            QLineEdit {
                background-color: rgba(20, 20, 20, 220);
                color: white;
                border: 1px solid #555;
                border-radius: 5px;
                padding: 5px;
            }
        """)
        self.input_field.returnPressed.connect(self.start_agent_task)
        layout.addWidget(self.input_field)

        self.setLayout(layout)
        # 初始化位置在屏幕右下角附近
        self.resize(360, 900)
        screen_geometry = QApplication.primaryScreen().availableGeometry()
        self.move(
            screen_geometry.right() - self.width() - 20,
            screen_geometry.bottom() - self.height() - 20
        )

    # 支持鼠标按住角色拖动窗口位置
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.drag_position)
            event.accept()

    # 启动后台 Agent 线程
    def start_agent_task(self):
        user_text = self.input_field.text().strip()
        if not user_text or getattr(self, "worker", None) is not None and self.worker.isRunning():
            return

        self.input_field.clear()
        self.input_field.setEnabled(False)
        self.dialog_label.setText("任务接收，处理中...")
        record_explicit_profile(self.memory, user_text)

        # 创建并启动 Worker 线程
        mode = self.mode_selector.currentData()
        self.worker = AgentWorker(user_text, mode, self.memory)
        self.worker.signal_reply.connect(self.update_dialog)
        self.worker.signal_emotion.connect(self.set_expression)
        self.worker.signal_finished.connect(self.on_task_finished)
        self.worker.start()

    def update_dialog(self, text):
        self.dialog_label.setText(text)

    def set_expression(self, emotion):
        compositor = getattr(self, "expression_compositor", None)
        if compositor is None:
            return
        image = compositor.compose(emotion)
        pixmap = QPixmap.fromImage(image).scaled(320, 520, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.char_label.setPixmap(pixmap)

    def on_task_finished(self):
        self.input_field.setEnabled(True)

    def clear_memory(self):
        if getattr(self, "worker", None) is not None and self.worker.isRunning():
            self.dialog_label.setText("当前任务完成后才能清空记忆。")
            return
        self.memory.clear()
        VectorStore(VECTOR_DB_PATH, VECTOR_COLLECTION).clear()
        self.dialog_label.setText("记忆、画像、摘要和向量索引已清空。")

    def closeEvent(self, event):
        worker = getattr(self, "worker", None)
        if worker is not None and worker.isRunning():
            worker.requestInterruption()
            worker.finished.connect(QApplication.instance().quit)
            self.hide()
        else:
            QApplication.instance().quit()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DesktopAgentUI()
    window.show()
    sys.exit(app.exec_())