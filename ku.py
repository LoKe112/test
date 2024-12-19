import sys
import time
import os
import requests
import pygetwindow as gw
import matplotlib.pyplot as plt
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QLabel, QInputDialog, QMessageBox, QDialog, QCheckBox, QSpinBox
from PyQt5.QtCore import QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QIcon

class TimeTracker(QThread):
    update_time = pyqtSignal(str)
    send_report_signal = pyqtSignal()

    def __init__(self, bot_token, chat_id):
        super().__init__()
        self.total_time = 0
        self.running = False
        self.app_times = {}
        self.tasks = []  # Задачи будут храниться в виде словарей
        self.task_times = {}  # Словарь для хранения реального времени задач
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.auto_report_enabled = True  # Флаг для авторассылки отчетов
        self.report_interval = 5  # Интервал в минутах по умолчанию
        self.threshold_percentage = 5  # Пороговый процент по умолчанию
        self.elements_threshold = 10  # Инициализация порогового количества элементов по умолчанию

    def get_active_window(self):
        active_window = gw.getActiveWindow()
        return active_window.title if active_window else None

    def format_time(self, total_seconds):
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = total_seconds % 60
        return f"{hours} ч. {minutes} мин. {seconds:.2f} сек."
    
    def check_active_app_for_tasks(self):
            active_app = self.get_active_window()
            if active_app:
                for task in self.tasks:
                    task_name = task['name']
                    # Проверяем, есть ли хотя бы одно слово из названия задачи в названии активного приложения
                    if any(word in active_app for word in task_name.split()):
                        if task_name not in self.task_times:
                            self.task_times[task_name] = 0  # Инициализируем, если еще не было
                        self.task_times[task_name] += 1  # Увеличиваем реальное время задачи на 1 секунду

    def run(self):
            self.running = True
            start_time = time.time()

            while self.running:
                current_time = time.time()
                elapsed_time = current_time - start_time
                self.total_time += elapsed_time

                # Проверяем активное приложение на соответствие задачам
                self.check_active_app_for_tasks()

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
        self.tasks.clear()  # Очистка задач при завершении отсчета

    def save_report(self):
        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        report_file = os.path.join(desktop_path, "time_tracker_report.txt")

        with open(report_file, 'w', encoding='utf-8') as file:
            file.write(f"Общее время: {self.format_time(self.total_time)}.\n")
            file.write("Хронометраж по приложениям:\n")
            sorted_apps = sorted(self.app_times.items(), key=lambda x: x[1], reverse=True)
            for app, time_spent in sorted_apps:
                file.write(f"- {app}: {self.format_time(time_spent)}.\n")

            file.write("\nЗадачи на сессию:\n")
            for task in self.tasks:
                planned_time = task['planned_time']
                real_time = self.task_times.get(task['name'], 0)
                file.write(f"- {task['name']}: {self.format_time(planned_time)} // {self.format_time(real_time)}\n")

        return report_file

    def create_chart(self):
        apps = list(self.app_times.keys())
        times = [self.app_times[app] for app in apps]

        if len(apps) > self.elements_threshold:
            threshold = self.total_time * (self.threshold_percentage / 100)
            other_time = sum(time for time in times if time < threshold)
            filtered_apps = [app for app, time in zip(apps, times) if time >= threshold]
            filtered_times = [time for time in times if time >= threshold]

            if other_time > 0:
                filtered_apps.append("Остальное")
                filtered_times.append(other_time)

            apps = filtered_apps
            times = filtered_times

        plt.figure(figsize=(8, 8))
        plt.pie(times, labels=apps, autopct='%1.1f%%', startangle=140, colors=plt.cm.Paired.colors)
        plt.title('Время, проведенное в приложениях')
        plt.axis('equal')

        chart_file = os.path.join(os.path.expanduser("~"), "Desktop", "time_tracker_chart.png")
        plt.savefig(chart_file)
        plt.close()
        return chart_file

        #plt.figure(figsize=(8, 8))
        #plt.pie(times, labels=apps, autopct='%1.1f%%', startangle=140, colors=plt.cm.Paired.colors)
        #plt.title('Время, проведенное в приложениях')
        #plt.axis('equal')

        #chart_file = os.path.join(os.path.expanduser("~"), "Desktop", "time_tracker_chart.png")
        #plt.savefig(chart_file)
        #plt.close()
        #return chart_file

    def send_final_report(self):
        report_file = self.save_report()
        chart_file = self.create_chart()  # Создание диаграммы для финального отчета
        self.send_telegram_message(self.format_time(self.total_time), report_file, chart_file)

    def send_periodic_report(self):
        report_file = self.save_report()
        chart_file = self.create_chart()  # Создание диаграммы для автоотчетов
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

class SettingsDialog(QDialog):
    def __init__(self, tracker):
        super().__init__()
        self.tracker = tracker
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Настройки")
        self.setGeometry(100, 100, 300, 300)

        layout = QVBoxLayout()

        self.auto_report_checkbox = QCheckBox("Включить авторассылку отчетов")
        self.auto_report_checkbox.setChecked(self.tracker.auto_report_enabled)
        layout.addWidget(self.auto_report_checkbox)

        self.interval_label = QLabel("Интервал рассылки (минуты):")
        layout.addWidget(self.interval_label)

        self.interval_spinner = QSpinBox()
        self.interval_spinner.setRange(1, 60)
        self.interval_spinner.setValue(self.tracker.report_interval)
        self.interval_spinner.setFixedWidth(80)
        layout.addWidget(self.interval_spinner)

        self.threshold_label = QLabel("Выберите пороговой процент n:")
        layout.addWidget(self.threshold_label)

        self.threshold_spinner = QSpinBox()
        self.threshold_spinner.setRange(1, 100)
        self.threshold_spinner.setValue(self.tracker.threshold_percentage)
        self.threshold_spinner.setFixedWidth(80)
        layout.addWidget(self.threshold_spinner)

        self.elements_threshold_label = QLabel("Пороговое количество элементов для 'Остальное':")
        layout.addWidget(self.elements_threshold_label)

        self.elements_threshold_spinner = QSpinBox()
        self.elements_threshold_spinner.setRange(1, 20)
        self.elements_threshold_spinner.setValue(10)  # Устанавливаем значение по умолчанию
        layout.addWidget(self.elements_threshold_spinner)

        self.save_button = QPushButton("Сохранить настройки")
        self.save_button.setStyleSheet("background-color: #4CAF50; color: white; font-size: 12px;")
        self.save_button.clicked.connect(self.save_settings)
        layout.addWidget(self.save_button)

        self.setLayout(layout)
        self.setStyleSheet("background-color: #2E2E2E; color: white;")

    def save_settings(self):
        self.tracker.auto_report_enabled = self.auto_report_checkbox.isChecked()
        self.tracker.report_interval = self.interval_spinner.value()
        self.tracker.threshold_percentage = self.threshold_spinner.value()
        self.tracker.elements_threshold = self.elements_threshold_spinner.value()  # Сохраняем пороговое количество элементов
        self.close()



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

        self.task_button = QPushButton("Добавить задачу")
        self.task_button.setStyleSheet("background-color: #2196F3; color: white; font-size: 16px;")
        self.task_button.clicked.connect(self.add_task)
        layout.addWidget(self.task_button)

        self.label = QLabel("Статус: Ожидание...")
        self.label.setFont(QFont("Arial", 12))
        layout.addWidget(self.label)

        self.settings_button = QPushButton("⚙️ Настройки")
        self.settings_button.setStyleSheet("background-color: #FFC107; color: black; font-size: 16px;")
        self.settings_button.clicked.connect(self.open_settings)
        layout.addWidget(self.settings_button)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.setStyleSheet("background-color: #2E2E2E; color: white;")  # Основной цвет фона

    def start_tracking(self):
        if not self.tracker or not self.tracker.isRunning():
            bot_token = "8034481563:AAH0rv09GLUq27P3PuztOIS8f9X6PxUFitk"  # Укажите токен вашего бота
            chat_id = "1092865250"  # Укажите ваш chat_id
            self.tracker = TimeTracker(bot_token, chat_id)
            self.tracker.update_time.connect(self.update_label)
            self.tracker.start()
            self.label.setText("Статус: Хронометраж начат.")
            self.task_button.setEnabled(True)  # Разблокируем кнопку добавления задач

            # Запускаем таймер для автоотчетов, если включен
            if self.tracker.auto_report_enabled:
                self.timer.start(self.tracker.report_interval * 60000)  # Устанавливаем интервал в миллисекундах

    def update_label(self, formatted_time):
        self.label.setText(f"Статус: Время - {formatted_time}")

    def stop_tracking(self):
        if self.tracker:
            self.tracker.stop_tracking()
            self.label.setText("Статус: Хронометраж завершен.")
            self.timer.stop()
            self.task_button.setEnabled(False)  # Блокируем кнопку добавления задач при завершении отсчета

    def add_task(self):
        if self.tracker is None:
            QMessageBox.warning(self, "Ошибка", "Сначала начните отсчет.")
            return

        task_name, ok = QInputDialog.getText(self, "Добавить задачу", "Введите название задачи:")
        if ok and task_name:
            planned_time_str, ok = QInputDialog.getText(self, "Запланированное время", "Введите запланированное время в секундах:")
            if ok and planned_time_str.isdigit():
                planned_time = int(planned_time_str)
                self.tracker.tasks.append({'name': task_name, 'planned_time': planned_time})
                self.tracker.task_times[task_name] = 0  # Сохраняем время начала задачи
            else:
                QMessageBox.warning(self, "Ошибка", "Некорректное запланированное время.")
        elif not ok:
            QMessageBox.information(self, "Информация", "Добавление задачи отменено.")

    def open_settings(self):
        if self.tracker is None:
            QMessageBox.warning(self, "Ошибка", "Сначала начните отсчет.")
            return
        settings_dialog = SettingsDialog(self.tracker)
        settings_dialog.exec_()  # Открываем диалог настроек

        # После закрытия окна настроек обновляем таймер
        if self.tracker.auto_report_enabled:
            self.timer.start(self.tracker.report_interval * 60000)  # Устанавливаем интервал в миллисекундах
        else:
            self.timer.stop()  # Останавливаем таймер, если автоотчеты отключены

    def send_periodic_report(self):
        if self.tracker and self.tracker.auto_report_enabled:
            self.tracker.send_periodic_report()

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
