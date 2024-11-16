import sys
import mysql.connector

from PyQt6.QtWidgets import (QApplication, QWidget, QMainWindow, QLabel, QLineEdit,
                             QVBoxLayout, QPushButton, QMessageBox, QTableWidget, QTableWidgetItem, QStackedLayout,
                             QStackedWidget)
from PyQt6.QtGui import QIcon, QAction


class DatabaseConnect:
    def __init__(self, host="localhost", user="root", password="keX7-?&rl2!", database="bmic"):
        self.host = host
        self.user = user
        self.password = password
        self.database = database

    def connect(self):
        return mysql.connector.connect(host=self.host, user=self.user, password=self.password, database=self.database)


class BMICalculator:
    def __init__(self, height_cm, weight_kg):
        self.height_cm = height_cm
        self.weight_kg = weight_kg

    def calculate_bmi(self):
        height_m = self.height_cm / 100
        self.bmi = self.weight_kg / (height_m ** 2)
        return self.bmi

    def get_bmi_category(self):
        if self.bmi < 18.5:
            return "You are underweight"
        elif 18.5 <= self.bmi < 24.9:
            return "You are in normal condition"
        elif 25 <= self.bmi < 30:
            return "You are overweight"
        else:
            return "You are in the obesity range"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BMI Calculator")
        self.setWindowIcon(QIcon("icons/bmi.png"))
        self.setFixedHeight(500)
        self.setFixedWidth(500)


        self.db_connector = DatabaseConnect()


        menu_bar = self.menuBar()
        home_action = QAction("Home", self)
        records_action = QAction("Records", self)

        home_action.triggered.connect(self.show_home)
        records_action.triggered.connect(self.show_records)

        menu_bar.addAction(home_action)
        menu_bar.addAction(records_action)


        self.bmi_form = self.create_bmi_form()
        self.records_table = self.create_records_table()


        self.setCentralWidget(self.bmi_form)

    def create_bmi_form(self):

        form_widget = QWidget()
        layout = QVBoxLayout()

        name_label = QLabel("Enter your name: ")
        self.name_input = QLineEdit()
        layout.addWidget(name_label)
        layout.addWidget(self.name_input)

        height_label = QLabel("Enter your height in cm:")
        self.height_input = QLineEdit()
        layout.addWidget(height_label)
        layout.addWidget(self.height_input)

        weight_label = QLabel("Enter your weight in Kg:")
        self.weight_input = QLineEdit()
        layout.addWidget(weight_label)
        layout.addWidget(self.weight_input)

        calculate_button = QPushButton("Calculate")
        calculate_button.clicked.connect(self.calculate_bmi)
        layout.addWidget(calculate_button)

        form_widget.setLayout(layout)
        return form_widget

    def create_records_table(self):

        table = QStackedWidget()
        table.setColumnCount(7)
        table.setHorizontalHeaderLabels(
            ("Id", "Name", "Height (cm)", "Weight (kg)", "BMI Score", "Conclusion", "Record Time")
        )
        return table

    def show_home(self):

        self.setCentralWidget(self.bmi_form)

    def show_records(self):

        try:
            connection = self.db_connector.connect()
            cursor = connection.cursor()
            cursor.execute("SELECT * FROM bmi_records")
            results = cursor.fetchall()

            self.records_table.setRowCount(0)
            for row_number, row_data in enumerate(results):
                self.records_table.insertRow(row_number)
                for column_number, data in enumerate(row_data):
                    self.records_table.setItem(row_number, column_number, QTableWidgetItem(str(data)))

            cursor.close()
            connection.close()

            self.setCentralWidget(self.records_table)
        except mysql.connector.Error as e:
            QMessageBox.critical(self, "Database Error", f"Error: {str(e)}")

    def calculate_bmi(self):

        try:
            name = self.name_input.text().strip()
            height_cm = float(self.height_input.text())
            weight_kg = float(self.weight_input.text())

            bmi_calculator = BMICalculator(height_cm, weight_kg)
            bmi = bmi_calculator.calculate_bmi()
            category = bmi_calculator.get_bmi_category()

            connection = self.db_connector.connect()
            cursor = connection.cursor()
            sql = """
                INSERT INTO bmi_records (name, height_cm, weight_kg, bmi, category)
                VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (name, height_cm, weight_kg, bmi, category))
            connection.commit()
            cursor.close()
            connection.close()

            QMessageBox.information(self, "BMI Result", f"Your BMI is: {bmi:.2f}\n{category}")
        except ValueError:
            QMessageBox.warning(self, "Input Error", "Please enter valid numeric values.")
        except mysql.connector.Error as e:
            QMessageBox.critical(self, "Database Error", f"Database error: {str(e)}")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())