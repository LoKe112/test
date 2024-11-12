import time
import psutil
import pygetwindow as gw

def get_fullscreen_windows():
    fullscreen_windows = []
    for window in gw.getAllWindows():
        if window.isMaximized:
            fullscreen_windows.append(window.title)
    return fullscreen_windows

def main():
    total_time = 0
    start_time = time.time()

    try:
        print("Запуск хронометража. Нажмите Ctrl+C для остановки.")
        while True:
            current_time = time.time()
            elapsed_time = current_time - start_time
            total_time += elapsed_time
            start_time = current_time

            fullscreen_apps = get_fullscreen_windows()
            if fullscreen_apps:
                print(f"Время: {total_time:.2f} секунд. Полноэкранные приложения: {fullscreen_apps}")
            else:
                print(f"Время: {total_time:.2f} секунд. Нет полноэкранных приложений.")

            time.sleep(1)

    except KeyboardInterrupt:
        print(f"\nОбщее время: {total_time:.2f} секунд.")
        print("Программа завершена.")

if __name__ == "__main__":
    main()