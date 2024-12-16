import sys
import time
import os
import requests
import pygetwindow as gw
import matplotlib.pyplot as plt
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QLabel
from PyQt5.QtCore import QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QIcon, QColor
from PyQt5.QtWidgets import QHBoxLayout

class TimeTracker(QThread):
    update_time = pyqtSignal(str)
    send_report_signal = pyqtSignal()

    def __init__(self, bot_token, chat_id):
        super().__init__()
        self.total_time = 0
        self.running = False
        self.app_times = {}
        self.bot_token = bot_token
        self.chat_id = chat_id

    def get_active_window(self):
        active_window = gw.getActiveWindow()
        return active_window.title if active_window else None

    def format_time(self, total_seconds):
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = total_seconds % 60
        return f"{hours} ч. {minutes} мин. {seconds:.2f} сек."

    def run(self):
        self.running = True
        start_time = time.time()

        while self.running:
            current_time = time.time()
            elapsed_time = current_time - start_time
            self.total_time += elapsed_time

            active_app = self.get_active_window()
            if active_app and active_app not in self.app_times:
                self.app_times[active_app] = 0
            if active_app:
                self.app_times[active_app] += elapsed_time

            formatted_time = self.format_time(self.total_time)
            self.update_time.emit(formatted_time)

            start_time = current_time
            time.sleep(1)

    def stop_tracking(self):
        self.running = False
        self.send_final_report()

    def save_report(self):
        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        report_file = os.path.join(desktop_path, "time_tracker_report.txt")

        with open(report_file, 'w', encoding='utf-8') as file:
            file.write(f"Общее время: {self.format_time(self.total_time)}.\n")
            file.write("Хронометраж по приложениям:\n")
            sorted_apps = sorted(self.app_times.items(), key=lambda x: x[1], reverse=True)
            for app, time_spent in sorted_apps:
                file.write(f"- {app}: {self.format_time(time_spent)}.\n")

        return report_file

    def create_chart(self):
        apps = list(self.app_times.keys())
        times = [self.app_times[app] for app in apps]

        plt.figure(figsize=(8, 8))
        plt.pie(times, labels=apps, autopct='%1.1f%%', startangle=140, colors=plt.cm.Paired.colors)
        plt.title('Время, проведенное в приложениях')
        plt.axis('equal')

        chart_file = os.path.join(os.path.expanduser("~"), "Desktop", "time_tracker_chart.png")
        plt.savefig(chart_file)
        plt.close()
        return chart_file

    def send_final_report(self):
        report_file = self.save_report()
        chart_file = self.create_chart()
        self.send_telegram_message(self.format_time(self.total_time), report_file, chart_file)

    def send_periodic_report(self):
        report_file = self.save_report()
        chart_file = self.create_chart()
        self.send_telegram_message(self.format_time(self.total_time), report_file, chart_file)

    def send_telegram_message(self, formatted_time, report_file, chart_file):
        message = f"Общее время: {formatted_time}."
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            'chat_id': self.chat_id,
            'text': message
        }

        try:
            response = requests.post(url, data=payload)
            if response.status_code == 200:
                print("Сообщение отправлено в Telegram.")

            with open(report_file, 'rb') as file:
                files = {'document': file}
                url = f"https://api.telegram.org/bot{self.bot_token}/sendDocument"
                response = requests.post(url, data={'chat_id': self.chat_id}, files=files)

            with open(chart_file, 'rb') as file:
                files = {'document': file}
                url = f"https://api.telegram.org/bot{self.bot_token}/sendDocument"
                response = requests.post(url, data={'chat_id': self.chat_id}, files=files)

        except Exception as e:
            print(f"Ошибка при отправке сообщения в Telegram: {e}")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.tracker = None
        self.initUI()
        self.timer = QTimer()
        self.timer.timeout.connect(self.send_periodic_report)

    def initUI(self):
        self.setWindowTitle("Таймер Хронометража")
        self.setGeometry(100, 100, 400, 300)
        self.setWindowIcon(QIcon('icon.png'))  # Укажите путь к иконке

        layout = QVBoxLayout()

        self.start_button = QPushButton("Начать отсчет")
        self.start_button.setStyleSheet("background-color: #4CAF50; color: white; font-size: 16px;")
        self.start_button.clicked.connect(self.start_tracking)
        layout.addWidget(self.start_button)

        self.stop_button = QPushButton("Закончить отсчет")
        self.stop_button.setStyleSheet("background-color: #f44336; color: white; font-size: 16px;")
        self.stop_button.clicked.connect(self.stop_tracking)
        layout.addWidget(self.stop_button)

        self.label = QLabel("Статус: Ожидание...")
        self.label.setFont(QFont("Arial", 12))
        layout.addWidget(self.label)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.setStyleSheet("background-color: #2E2E2E; color: white;")  # Основной цвет фона

    def start_tracking(self):
        if not self.tracker or not self.tracker.isRunning():
            bot_token = "YOUR_BOT_TOKEN"  # Укажите токен вашего бота
            chat_id = "YOUR_CHAT_ID"  # Укажите ваш chat_id
            self.tracker = TimeTracker(bot_token, chat_id)
            self.tracker.update_time.connect(self.update_label)
            self.tracker.start()
            self.label.setText("Статус: Хронометраж начат.")
            self.timer.start(300000)  # Запуск таймера на 10 минут

    def update_label(self, formatted_time):
        self.label.setText(f"Статус: Время - {formatted_time}")

    def stop_tracking(self):
        if self.tracker:
            self.tracker.stop_tracking()
            self.label.setText("Статус: Хронометраж завершен.")
            self.timer.stop()

    def send_periodic_report(self):
        if self.tracker:
            self.tracker.send_periodic_report()

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
