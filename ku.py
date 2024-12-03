import sys
import time
import os
import requests
import pygetwindow as gw
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QLabel, QMessageBox
from PyQt5.QtCore import QThread, pyqtSignal

class TimeTracker(QThread):
    update_time = pyqtSignal(str)
    report_ready = pyqtSignal(str)

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
        print("Хронометраж начат.")

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
        formatted_time = self.format_time(self.total_time)
        print(f"Общее время: {formatted_time}.")
        report_file = self.save_report()
        self.send_telegram_message(formatted_time, report_file)

    def save_report(self):
        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        report_file = os.path.join(desktop_path, "time_tracker_report.txt")

        with open(report_file, 'w', encoding='utf-8') as file:
            file.write(f"Общее время: {self.format_time(self.total_time)}.\n")
            file.write("Хронометраж по приложениям:\n")
            # Сортировка приложений по времени
            sorted_apps = sorted(self.app_times.items(), key=lambda x: x[1], reverse=True)
            for app, time_spent in sorted_apps:
                file.write(f"- {app}: {self.format_time(time_spent)}.\n")

        print(f"Отчет сохранен: {report_file}")
        return report_file

    def send_telegram_message(self, formatted_time, report_file):
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
            else:
                print(f"Не удалось отправить сообщение: {response.text}")

            with open(report_file, 'rb') as file:
                files = {'document': file}
                url = f"https://api.telegram.org/bot{self.bot_token}/sendDocument"
                response = requests.post(url, data={'chat_id': self.chat_id}, files=files)
                if response.status_code == 200:
                    print("Отчет отправлен в Telegram.")
                else:
                    print(f"Не удалось отправить отчет: {response.text}")

        except Exception as e:
            print(f"Ошибка при отправке сообщения в Telegram: {e}")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.tracker = None
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Таймер Хронометража")
        self.setGeometry(100, 100, 300, 200)

        layout = QVBoxLayout()

        self.start_button = QPushButton("Начать отсчет")
        self.start_button.clicked.connect(self.start_tracking)
        layout.addWidget(self.start_button)

        self.stop_button = QPushButton("Закончить отсчет")
        self.stop_button.clicked.connect(self.stop_tracking)
        layout.addWidget(self.stop_button)

        self.send_button = QPushButton("Отправить отчет")
        self.send_button.clicked.connect(self.send_report)
        layout.addWidget(self.send_button)

        self.label = QLabel("Статус: Ожидание...")
        layout.addWidget(self.label)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def start_tracking(self):
        if not self.tracker or not self.tracker.isRunning():
            bot_token = "8034481563:AAH0rv09GLUq27P3PuztOIS8f9X6PxUFitk"  # Укажите токен вашего бота
            chat_id = "1092865250"  # Укажите ваш chat_id
            self.tracker = TimeTracker(bot_token, chat_id)
            self.tracker.update_time.connect(self.update_label)
            self.tracker.start()
            self.label.setText("Статус: Хронометраж начат.")

    def update_label(self, formatted_time):
        self.label.setText(f"Статус: Время - {formatted_time}")

    def stop_tracking(self):
        if self.tracker:
            self.tracker.stop_tracking()
            self.label.setText("Статус: Хронометраж завершен.")

    def send_report(self):
        if self.tracker and not self.tracker.running:
            report_file = self.tracker.save_report()
            self.tracker.send_telegram_message(self.tracker.format_time(self.tracker.total_time), report_file)
            self.label.setText("Статус: Отчет отправлен.")
        else:
            QMessageBox.warning(self, "Ошибка", "Сначала завершите отсчет, чтобы отправить отчет.")

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()