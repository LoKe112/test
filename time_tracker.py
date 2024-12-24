import time
import os
import requests
import pygetwindow as gw
import matplotlib.pyplot as plt
from PyQt5.QtCore import QThread, pyqtSignal
import tkinter as tk
from tkinter import messagebox

class TimeTracker(QThread):
    update_time = pyqtSignal(str)
    send_report_signal = pyqtSignal()

    def __init__(self, bot_token, chat_id):
        super().__init__()
        self.total_time = 0
        self.running = False
        self.paused = False  # Флаг для отслеживания состояния паузы
        self.app_times = {}
        self.tasks = []  # Задачи будут храниться в виде словарей
        self.task_times = {}  # Словарь для хранения реального времени задач
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.auto_report_enabled = True  # Флаг для авторассылки отчетов
        self.report_interval = 5  # Интервал в минутах по умолчанию
        self.threshold_percentage = 5  # Пороговый процент по умолчанию
        self.elements_threshold = 10  # Инициализация порогового количества элементов по умолчанию
        self.elapsed_during_pause = 0  # Время, проведенное в паузе
        self.triggerd_count = 0
        self.elapsed_during_pause_temp = 0
        self.warning_shown = False  # Инициализация переменной

    def get_active_window(self):
        active_window = gw.getActiveWindow()
        return active_window.title if active_window else None

    def format_time(self, total_seconds):
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = total_seconds % 60
        return f"{hours} ч. {minutes} мин. {seconds:.0f} сек."
    
    def check_active_app_for_tasks(self, elapsed_time):
        active_app = self.get_active_window()
        if active_app:
            for task in self.tasks:
                task_name = task['name']
                # Проверяем, есть ли хотя бы одно слово из названия задачи в названии активного приложения
                if any(word in active_app for word in task_name.split()):
                    if task_name not in self.task_times:
                        self.task_times[task_name] = 0  # Инициализируем, если еще не было
                    self.task_times[task_name] += elapsed_time  # Увеличиваем реальное время задачи на прошедшее время
                    
                    # Проверяем, достигнуто ли запланированное время
                    planned_time = task['planned_time']
                    if self.task_times[task_name] >= planned_time:
                        self.task_times[task_name] = planned_time  # Ограничиваем время задач до запланированного
                        self.show_warning(task_name)  # Вызываем функцию для отображения предупреждения

    def show_warning(self, task_name):
        global warning_shown  # Используем глобальный флаг
        if not warning_shown:  # Проверяем, показано ли уже предупреждение
            # Создаем скрытое основное окно
            root = tk.Tk()
            root.withdraw()  # Скрываем основное окно
            messagebox.showwarning("Внимание", f"Задача достигла запланированного времени: {task_name}")
            root.destroy()  # Закрываем основное окно после показа предупреждения
            warning_shown = True  # Устанавливаем флаг в True
    
    def run(self):
        self.running = True
        start_time = time.time()

        while self.running:
            if not self.paused:  # Проверяем, не приостановлен ли отсчет
                current_time = time.time()
                elapsed_time = current_time - start_time
                self.total_time += elapsed_time

                self.check_active_app_for_tasks(elapsed_time)  # Передаем прошедшее время

                active_app = self.get_active_window()
                if active_app and active_app not in self.app_times:
                    self.app_times[active_app] = 0
                if active_app:
                    self.app_times[active_app] += elapsed_time

                formatted_time = self.format_time(self.total_time)
                self.update_time.emit(formatted_time)

                start_time = current_time
            else:
                time.sleep(1)  # Если приостановлено, просто ждем
                
    def pause_tracking(self):
        if not self.paused:  # Проверяем, не приостановлен ли отсчет
            self.paused = True
            self.pause_start_time = time.time()  # Запоминаем время начала паузы

    def resume_tracking(self):
        if self.paused:  # Проверяем, действительно ли отсчет приостановлен
            self.elapsed_during_pause += time.time() - self.pause_start_time  # Вычисляем время, проведенное в паузе
            self.elapsed_during_pause_temp = self.elapsed_during_pause
            self.total_time -= self.elapsed_during_pause
            self.elapsed_during_pause = 0            
            self.triggerd_count = 1
            self.paused = False

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
                if real_time >= planned_time:
                    file.write(f"- {task['name']}: Задача выполнена\n")
                else:
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
            
    def show_warning(self, task_name):
        if not self.warning_shown:  # Используем атрибут класса
            # Создаем скрытое основное окно
            root = tk.Tk()
            root.withdraw()  # Скрываем основное окно
            messagebox.showwarning("Внимание", f"Задача достигла запланированного времени: {task_name}")
            root.destroy()  # Закрываем основное окно после показа предупреждения
            self.warning_shown = True  # Устанавливаем флаг в True