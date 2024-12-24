from PyQt5.QtWidgets import QMainWindow, QPushButton, QVBoxLayout, QWidget, QLabel, QMessageBox, QInputDialog
from time_tracker import TimeTracker
from settings import SettingsDialog
import webbrowser
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QFont, QIcon

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
        self.setWindowIcon(QIcon('icon.png'))

        layout = QVBoxLayout()

        self.start_button = QPushButton("Начать отсчет")
        self.start_button.setStyleSheet("background-color: #4CAF50; color: white; font-size: 16px;")
        self.start_button.clicked.connect(self.start_tracking)
        layout.addWidget(self.start_button)

        self.stop_button = QPushButton("Закончить отсчет")
        self.stop_button.setStyleSheet("background-color: #f44336; color: white; font-size: 16px;")
        self.stop_button.clicked.connect(self.stop_tracking)
        layout.addWidget(self.stop_button)
        
        

        # Кнопка для приостановки/возобновления отсчета
        self.pause_resume_button = QPushButton("Приостановить")
        self.pause_resume_button.setStyleSheet("background-color: #8b00ff; color: white; font-size: 16px;")
        self.pause_resume_button.clicked.connect(self.toggle_pause_resume)
        layout.addWidget(self.pause_resume_button)

        self.task_button = QPushButton("Добавить задачу")
        self.task_button.setStyleSheet("background-color: #2196F3; color: white; font-size: 16px;")
        self.task_button.clicked.connect(self.add_task)
        layout.addWidget(self.task_button)
        
        self.bot_button = QPushButton("Получать информацию онлайн")
        self.bot_button.setStyleSheet("background-color: #2196F3; color: white; font-size: 16px;")
        self.bot_button.clicked.connect(self.open_bot_link)  # Подключаем обработчик события
        layout.addWidget(self.bot_button)

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
        
    def open_bot_link(self):
        # Открываем ссылку на бота в Telegram
        webbrowser.open("https://t.me/TimeAtTheComputerBot")

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
                
    def toggle_pause_resume(self):
        if self.tracker:
            if self.tracker.paused:
                self.tracker.resume_tracking()
                self.pause_resume_button.setText("Приостановить")
                self.label.setText("Статус: Хронометраж возобновлен.")
            else:
                self.tracker.pause_tracking()
                self.pause_resume_button.setText("Возобновить")
                self.label.setText("Статус: Хронометраж приостановлен.")


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