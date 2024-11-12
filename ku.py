import time
import psutil
import pygetwindow as gw
import keyboard
import os

class TimeTracker:
    def __init__(self):
        self.total_time = 0
        self.running = False
        self.app_times = {}

    def get_fullscreen_windows(self):
        fullscreen_windows = []
        for window in gw.getAllWindows():
            if window.isMaximized:
                fullscreen_windows.append(window.title)
        return fullscreen_windows

    def start_tracking(self):
        self.running = True
        start_time = time.time()
        print("Хронометраж начат. Нажмите 'Q' для завершения.")

        while self.running:
            current_time = time.time()
            elapsed_time = current_time - start_time
            self.total_time += elapsed_time

            fullscreen_apps = self.get_fullscreen_windows()
            for app in fullscreen_apps:
                if app not in self.app_times:
                    self.app_times[app] = 0
                self.app_times[app] += elapsed_time

            start_time = current_time

            if fullscreen_apps:
                print(f"Время: {self.total_time:.2f} секунд. Полноэкранные приложения: {fullscreen_apps}")
            else:
                print(f"Время: {self.total_time:.2f} секунд. Нет полноэкранных приложений.")

            # Проверяем, нажата ли клавиша 'Q'
            if keyboard.is_pressed('q'):
                self.stop_tracking()

            time.sleep(1)

    def stop_tracking(self):
        self.running = False
        print(f"Общее время: {self.total_time:.2f} секунд.")
        self.save_report()

    def save_report(self):
        # Получаем путь к рабочему столу
        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        report_file = os.path.join(desktop_path, "time_tracker_report.txt")

        # Сохраняем отчет в файл
        with open(report_file, 'w') as file:
            file.write(f"Общее время: {self.total_time:.2f} секунд.\n")
            file.write("Хронометраж по приложениям:\n")
            for app, time_spent in self.app_times.items():
                file.write(f"- {app}: {time_spent:.2f} секунд.\n")

        print(f"Отчет сохранен: {report_file}")

def main():
    tracker = TimeTracker()

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