import sys
import time
import os
import requests
import pygetwindow as gw
import matplotlib.pyplot as plt
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QLabel, QLineEdit, QMessageBox
from PyQt5.QtCore import QThread, pyqtSignal

class TimeTracker(QThread):
    update_time = pyqtSignal(str)
    report_ready = pyqtSignal(str, str, str)
    
    def __init__(self, bot_token, chat_id):
        super().__init__()
        self.total_time = 0
        self.running = False
        self.app_times = {}
        self.goals = {}
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.current_app = None

    def get_active_window(self):
        active_window = gw.getActiveWindow()
        return active_window.title if active_window else None

    def format_time(self, total_seconds):
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = total_seconds % 60
        return f"{hours} ч. {minutes} мин. {seconds:.2f} сек."

    def run(self):
        start_time = time.time()
        while self.running:
            current_time = time.time()
            elapsed_time = current_time - start_time
            self.total_time += elapsed_time

            active_app = self.get_active_window()
            if active_app:
                # Проверка на совпадение с целями
                for app, goal in self.goals.items():
                    if any(word.lower() in active_app.lower() for word in app.split()):
                        if app not in self.app_times:
                            self.app_times[app] = 0
                        self.app_times[app] += elapsed_time

            self.update_time.emit(self.format_time(self.total_time))
            start_time = current_time
            time.sleep(1)

    def start_tracking(self):
        self.running = True
        self.start()

    def stop_tracking(self):
        self.running = False
        self.quit()
        self.wait()
        report_file, pie_chart_file = self.save_report_and_plot()
        self.report_ready.emit(self.format_time(self.total_time), report_file, pie_chart_file)

    def save_report_and_plot(self):
        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        report_file = os.path.join(desktop_path, "time_tracker_report.txt")
        pie_chart_file = os.path.join(desktop_path, "time_tracker_pie_chart.png")

        # Сохранение отчета
        with open(report_file, 'w', encoding='utf-8') as file:
            file.write(f"Общее время: {self.format_time(self.total_time)}.\n")
            file.write("Хронометраж по приложениям:\n")

            # Сортировка приложений по затраченному времени
            sorted_apps = sorted(self.app_times.items(), key=lambda x: x[1], reverse=True)
            for app, time_spent in sorted_apps:
                file.write(f"- {app}: {self.format_time(time_spent)}.\n")

            file.write("Цели:\n")
            for app, goal in self.goals.items():
                real_time = self.app_times.get(app, 0)
                file.write(f"- {app}: {self.format_time(goal)} / {self.format_time(real_time)}\n")
                # Сравнение реального времени с запланированным
                if real_time < goal:
                    file.write(f"  - Не достигнуто: {self.format_time(goal - real_time)} недостающее время.\n")
                elif real_time > goal:
                    file.write(f"  - Превышено: {self.format_time(real_time - goal)} лишнее время.\n")
                else:
                    file.write(f"  - Достигнуто: {self.format_time(real_time)} ровно по плану.\n")

        # Создание круговой гистограммы
        self.create_pie_chart(pie_chart_file)

        return report_file, pie_chart_file

    def create_pie_chart(self, pie_chart_file):
        labels = list(self.app_times.keys())
        sizes = [time_spent for time_spent in self.app_times.values()]
        colors = plt.cm.tab20.colors  # Цвета для графиков

        plt.figure(figsize=(8, 6))
        plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=140, colors=colors)
        plt.axis('equal')  # Равные оси для круговой диаграммы
        plt.title('Распределение времени по приложениям')
        plt.savefig(pie_chart_file)
        plt.close()

    def send_telegram_message(self, formatted_time, report_file, pie_chart_file):
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

            with open(pie_chart_file, 'rb') as file:
                files = {'document': file}
                url = f"https://api.telegram.org/bot{self.bot_token}/sendDocument"
                response = requests.post(url, data={'chat_id': self.chat_id}, files=files)
                if response.status_code == 200:
                    print("Гистограмма отправлена в Telegram.")
                else:
                    print(f"Не удалось отправить гистограмму: {response.text}")

        except Exception as e:
            print(f"Ошибка при отправке сообщения в Telegram: {e}")

    def set_goals(self, goals):
        for goal in goals:
            app, time_str = goal.split('-')
            seconds = self.parse_time(time_str.strip())
            if app and seconds is not None:
                self.goals[app.strip()] = seconds

    def parse_time(self, time_str):
        try:
            time_parts = time_str.strip().split('сек')
            seconds = float(time_parts[0].strip())
            return seconds
        except (ValueError, IndexError):
            return None

class GoalSettingWindow(QWidget):
    def __init__(self, tracker):
        super().__init__()
        self.tracker = tracker
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Установка целей")
        self.setGeometry(100, 100, 300, 150)

        layout = QVBoxLayout()

        self.input_line = QLineEdit()
        self.input_line.setPlaceholderText("Введите цели: Приложение - время(сек), например: VS Code - 20 сек")
        layout.addWidget(self.input_line)

        self.submit_button = QPushButton("Установить цели")
        self.submit_button.clicked.connect(self.submit_goals)
        layout.addWidget(self.submit_button)

        self.setLayout(layout)

    def submit_goals(self):
        goals_input = self.input_line.text()
        goals = [goal.strip() for goal in goals_input.split(',')]
        self.tracker.set_goals(goals)
        QMessageBox.information(self, "Успех", "Цели успешно установлены!")
        self.close()

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

        self.stop_button = QPushButton("Остановить отсчет")
        self.stop_button.clicked.connect(self.stop_tracking)
        layout.addWidget(self.stop_button)

        self.finish_button = QPushButton("Завершить отсчет")
        self.finish_button.clicked.connect(self.finish_tracking)
        layout.addWidget(self.finish_button)

        self.send_button = QPushButton("Отослать отчет")
        self.send_button.clicked.connect(self.send_report)
        layout.addWidget(self.send_button)

        self.set_goals_button = QPushButton("Установить цели")
        self.set_goals_button.clicked.connect(self.open_goal_setting_window)
        layout.addWidget(self.set_goals_button)

        self.label = QLabel("")
        layout.addWidget(self.label)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def start_tracking(self):
        if not self.tracker:
            bot_token = "8034481563:AAH0rv09GLUq27P3PuztOIS8f9X6PxUFitk"  # Укажите токен вашего бота
            chat_id = "1092865250"  # Укажите ваш chat_id
            self.tracker = TimeTracker(bot_token, chat_id)
            self.tracker.update_time.connect(self.update_label)
            self.tracker.report_ready.connect(self.auto_send_report)
            self.tracker.start_tracking()
            self.label.setText("Отсчет начат.")

    def update_label(self, formatted_time):
        self.label.setText(f"Общее время: {formatted_time}")

    def auto_send_report(self, formatted_time, report_file, pie_chart_file):
        self.tracker.send_telegram_message(formatted_time, report_file, pie_chart_file)
        self.label.setText("Отчет автоматически отправлен.")

    def stop_tracking(self):
        if self.tracker:
            self.tracker.stop_tracking()
            self.label.setText("Отсчет остановлен.")

    def finish_tracking(self):
        if self.tracker:
            self.tracker.stop_tracking()
            self.tracker = None
            self.label.setText("Отсчет завершен.")

    def send_report(self):
        if self.tracker:
            report_file, pie_chart_file = self.tracker.save_report_and_plot()
            self.tracker.send_telegram_message(self.tracker.format_time(self.tracker.total_time), report_file, pie_chart_file)
            self.label.setText("Отчет отправлен.")

    def open_goal_setting_window(self):
        if self.tracker:  # Проверяем, что tracker существует
            self.goal_setting_window = GoalSettingWindow(self.tracker)
            self.goal_setting_window.show()
        else:
            QMessageBox.warning(self, "Ошибка", "Сначала начните отсчет.")

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
