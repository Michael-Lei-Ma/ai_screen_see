import os
import sys
from PIL import ImageGrab
from PySide6.QtWidgets import (QApplication, QMainWindow, QLabel, QSystemTrayIcon, QMenu)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QMouseEvent, QIcon


class CaptureWindow(QMainWindow):
    def __init__(self, image_path: str):
        super().__init__()
        self.image_path = image_path
        self.setWindowTitle("双击截屏")
        self.setFixedSize(400, 300)
        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignCenter)
        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            self.label.setText("图片加载失败")
        else:
            self.label.setPixmap(pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.setCentralWidget(self.label)

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        img = ImageGrab.grab()
        timestamp = os.path.join(os.getcwd(), f"screenshot_{event.timestamp()}.png")
        img.save(timestamp)
        self.setWindowTitle(f"已保存：{timestamp}")


class TrayApp(QApplication):
    def __init__(self, argv):
        super().__init__(argv)
        # 主窗口
        self.window = CaptureWindow("background.png")  # 换成你的图
        # 系统托盘
        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(QIcon("icon.png"))  # 换成你的图标
        self.tray.setToolTip("双击截屏工具")
        # 托盘菜单
        menu = QMenu()
        menu.addAction("截屏", self.capture)
        menu.addSeparator()
        menu.addAction("退出", self.quit)
        self.tray.setContextMenu(menu)
        # 左键单击：显示/隐藏
        self.tray.activated.connect(self.on_tray_click)
        # 默认隐藏
        self.window.hide()
        self.tray.show()

    def on_tray_click(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:  # 左键
            if self.window.isVisible():
                self.window.hide()
            else:
                self.window.show()
                self.window.raise_()
                self.window.activateWindow()

    def capture(self):
        # 托盘菜单“截屏”
        img = ImageGrab.grab()
        timestamp = os.path.join(os.getcwd(), f"screenshot_{QTimer.singleShot(0, lambda: None)}.png")
        img.save(timestamp)
        self.tray.showMessage("已保存", f"截图已保存到\n{timestamp}", QSystemTrayIcon.MessageIcon.Information, 2000)


if __name__ == '__main__':
    app = TrayApp(sys.argv)
    sys.exit(app.exec())