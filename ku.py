
import time
import psutil
import pygetwindow as gw
import keyboard
import os
import requests

class TimeTracker:
    def __init__(self, bot_token, chat_id):
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

    def start_tracking(self):
        self.running = True
        start_time = time.time()
        print("Хронометраж начат. Нажмите '`' для завершения.")

        while self.running:
            current_time = time.time()
            elapsed_time = current_time - start_time
            self.total_time += elapsed_time

            active_app = self.get_active_window()
            if active_app and active_app not in self.app_times:
                self.app_times[active_app] = 0
            if active_app:
                self.app_times[active_app] += elapsed_time

            start_time = current_time

            if active_app:
                formatted_time = self.format_time(self.total_time)
                print(f"Время: {formatted_time}. Активное приложение: {active_app}")
            else:
                formatted_time = self.format_time(self.total_time)
                print(f"Время: {formatted_time}. Нет активного приложения.")

            # Проверяем, нажата ли клавиша '`'
            if keyboard.is_pressed('`'):
                self.stop_tracking()

            time.sleep(1)

    def stop_tracking(self):
        self.running = False
        formatted_time = self.format_time(self.total_time)
        print(f"Общее время: {formatted_time}.")
        report_file = self.save_report()
        self.send_telegram_message(formatted_time, report_file)

    def save_report(self):
        # Получаем путь к рабочему столу
        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        report_file = os.path.join(desktop_path, "time_tracker_report.txt")

        # Сохраняем отчет в файл с кодировкой utf-8
        with open(report_file, 'w', encoding='utf-8') as file:
            file.write(f"Общее время: {self.format_time(self.total_time)}.\n")
            file.write("Хронометраж по приложениям:\n")
            for app, time_spent in self.app_times.items():
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
            # Отправка текстового сообщения
            response = requests.post(url, data=payload)
            if response.status_code == 200:
                print("Сообщение отправлено в Telegram.")
            else:
                print(f"Не удалось отправить сообщение: {response.text}")

            # Отправка файла отчета
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

def main():
    bot_token = "8034481563:AAH0rv09GLUq27P3PuztOIS8f9X6PxUFitk"  # Укажите токен вашего бота
    chat_id = "1092865250"  # Укажите ваш chat_id
    tracker = TimeTracker(bot_token, chat_id)

    while True:
        command = input("Введите 'start' для начала хронометража или 'exit' для выхода: ").strip().lower()
        if command == 'start' and not tracker.running:
            tracker.start_tracking()
        elif command == 'exit':
            if tracker.running:
                tracker.stop_tracking()
            print("Выход из программы.")
            break
        else:
            print("Неверная команда. Пожалуйста, используйте 'start' или 'exit'.")

if __name__ == "__main__":
    main()