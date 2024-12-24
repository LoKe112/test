from PyQt5.QtWidgets import QDialog, QVBoxLayout, QCheckBox, QSpinBox, QPushButton, QLabel

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