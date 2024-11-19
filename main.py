import sys
import mysql.connector
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (
    QApplication, QWidget, QMainWindow, QLabel, QLineEdit,
    QVBoxLayout, QPushButton, QMessageBox, QTableWidget,
    QTableWidgetItem, QStackedWidget, QHBoxLayout, QComboBox,
    QDateEdit
)
from PyQt6.QtGui import QIcon, QAction, QDoubleValidator, QRegularExpressionValidator
from PyQt6.QtCore import Qt, QDate, QRegularExpression
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class DatabaseConnector:
    def __init__(self, host, user, password, database):
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self._create_tables()

    def connect(self):
        return mysql.connector.connect(
            host=self.host,
            user=self.user,
            password=self.password,
            database=self.database
        )

    def _create_tables(self):
        """Create necessary tables if they don't exist"""
        try:
            connection = self.connect()
            cursor = connection.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bmi_records (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    height_cm FLOAT NOT NULL,
                    weight_kg FLOAT NOT NULL,
                    bmi FLOAT NOT NULL,
                    category VARCHAR(50) NOT NULL,
                    record_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            connection.commit()
        except mysql.connector.Error as e:
            print(f"Database Error: {e}")
        finally:
            if 'connection' in locals() and connection.is_connected():
                cursor.close()
                connection.close()


class VisualizationWidget(QWidget):
    def __init__(self, db_connector):
        super().__init__()
        self.db_connector = db_connector
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        # Controls for filtering
        filter_layout = QHBoxLayout()

        # Name filter
        self.name_filter = QComboBox()
        self.update_name_list()

        # Date range filters
        self.date_from = QDateEdit()
        self.date_to = QDateEdit()
        self.date_from.setDate(QDate.currentDate().addMonths(-6))
        self.date_to.setDate(QDate.currentDate())

        filter_layout.addWidget(QLabel("Select Name:"))
        filter_layout.addWidget(self.name_filter)
        filter_layout.addWidget(QLabel("From:"))
        filter_layout.addWidget(self.date_from)
        filter_layout.addWidget(QLabel("To:"))
        filter_layout.addWidget(self.date_to)

        update_btn = QPushButton("Update Graph")
        update_btn.clicked.connect(self.update_graph)
        filter_layout.addWidget(update_btn)

        layout.addLayout(filter_layout)

        # Setup matplotlib figure
        self.figure = Figure(figsize=(8, 6))
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)

        # Add statistics panel
        self.stats_label = QLabel()
        layout.addWidget(self.stats_label)

        self.setLayout(layout)

    def update_name_list(self):
        try:
            connection = self.db_connector.connect()
            cursor = connection.cursor()
            cursor.execute("SELECT DISTINCT name FROM bmi_records ORDER BY name")
            names = [row[0] for row in cursor.fetchall()]
            self.name_filter.clear()
            self.name_filter.addItems(names)
        except mysql.connector.Error as e:
            QMessageBox.critical(self, "Database Error", f"Error loading names: {str(e)}")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    def update_graph(self):
        try:
            if self.name_filter.currentText() == "":
                return

            connection = self.db_connector.connect()
            cursor = connection.cursor()

            query = """
                SELECT record_time, bmi, category 
                FROM bmi_records 
                WHERE name = %s 
                AND record_time BETWEEN %s AND %s 
                ORDER BY record_time
            """

            cursor.execute(query, (
                self.name_filter.currentText(),
                self.date_from.date().toPyDate(),
                self.date_to.date().toPyDate()
            ))

            results = cursor.fetchall()

            if not results:
                QMessageBox.information(self, "No Data", "No data available for selected criteria")
                return

            dates = [row[0] for row in results]
            bmis = [row[1] for row in results]
            categories = [row[2] for row in results]

            # Clear the figure
            self.figure.clear()

            # Create subplot for BMI trend
            ax = self.figure.add_subplot(111)

            # Plot BMI trend
            ax.plot(dates, bmis, 'b-o', label='BMI')

            # Add reference lines for BMI categories
            ax.axhline(y=18.5, color='r', linestyle='--', alpha=0.5, label='Underweight (<18.5)')
            ax.axhline(y=24.9, color='g', linestyle='--', alpha=0.5, label='Normal (18.5-24.9)')
            ax.axhline(y=29.9, color='y', linestyle='--', alpha=0.5, label='Overweight (25-29.9)')

            ax.set_xlabel('Date')
            ax.set_ylabel('BMI')
            ax.set_title(f'BMI Trend for {self.name_filter.currentText()}')
            ax.legend()

            # Rotate x-axis labels for better readability
            plt.setp(ax.get_xticklabels(), rotation=45)

            # Adjust layout to prevent label cutoff
            self.figure.tight_layout()

            # Update the canvas
            self.canvas.draw()

            # Update statistics
            self.update_statistics(bmis, categories)

        except mysql.connector.Error as e:
            QMessageBox.critical(self, "Database Error", f"Error updating graph: {str(e)}")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    def update_statistics(self, bmis, categories):
        if not bmis:
            return

        stats_text = f"""
        Statistics:
        - Latest BMI: {bmis[-1]:.1f}
        - Average BMI: {sum(bmis) / len(bmis):.1f}
        - Lowest BMI: {min(bmis):.1f}
        - Highest BMI: {max(bmis):.1f}
        - Latest Category: {categories[-1]}
        - Number of Records: {len(bmis)}
        """
        self.stats_label.setText(stats_text)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BMI Calculator")
        self.setMinimumSize(800, 600)

        self.db_connector = DatabaseConnector(
            host="localhost",
            user="root",
            password="keX7-?&rl2!",
            database="bmic"
        )

        self.setup_ui()
        self.setup_menu()

    def setup_menu(self):
        menu_bar = self.menuBar()

        # Create menu items
        home_action = QAction("Calculator", self)
        records_action = QAction("Records", self)
        viz_action = QAction("Visualization", self)

        # Connect actions
        home_action.triggered.connect(lambda: self.stacked_widget.setCurrentIndex(0))
        records_action.triggered.connect(lambda: self.show_records())
        viz_action.triggered.connect(lambda: self.show_visualization())

        # Add actions to menu bar
        menu_bar.addAction(home_action)
        menu_bar.addAction(records_action)
        menu_bar.addAction(viz_action)

    def setup_ui(self):
        self.stacked_widget = QStackedWidget()

        # Create pages
        self.bmi_form = self.create_bmi_form()
        self.records_table = self.create_records_table()
        self.visualization = VisualizationWidget(self.db_connector)

        # Add pages to stacked widget
        self.stacked_widget.addWidget(self.bmi_form)
        self.stacked_widget.addWidget(self.records_table)
        self.stacked_widget.addWidget(self.visualization)

        self.setCentralWidget(self.stacked_widget)

    def create_bmi_form(self):
        form_widget = QWidget()
        layout = QVBoxLayout()

        # Name input with proper validator
        name_label = QLabel("Enter your name:")
        self.name_input = QLineEdit()
        name_regex = QRegularExpression("[A-Za-z\\s]{1,50}")
        name_validator = QRegularExpressionValidator(name_regex)
        self.name_input.setValidator(name_validator)

        # Height input
        height_label = QLabel("Enter your height (cm):")
        self.height_input = QLineEdit()
        height_validator = QDoubleValidator(50.0, 300.0, 1)
        height_validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        self.height_input.setValidator(height_validator)

        # Weight input
        weight_label = QLabel("Enter your weight (kg):")
        self.weight_input = QLineEdit()
        weight_validator = QDoubleValidator(20.0, 500.0, 1)
        weight_validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        self.weight_input.setValidator(weight_validator)

        # Add help text
        help_label = QLabel(
            "Please enter valid values:\n- Name: letters only\n- Height: 50-300 cm\n- Weight: 20-500 kg")
        help_label.setStyleSheet("color: gray;")

        # Add widgets to layout
        for widget in [
            name_label, self.name_input,
            height_label, self.height_input,
            weight_label, self.weight_input,
            help_label
        ]:
            layout.addWidget(widget)

        # Calculate button
        calculate_button = QPushButton("Calculate BMI")
        calculate_button.clicked.connect(self.calculate_bmi)
        layout.addWidget(calculate_button)

        # Add some stretching space
        layout.addStretch()

        form_widget.setLayout(layout)
        return form_widget

    def create_records_table(self):
        table = QTableWidget()
        table.setColumnCount(7)
        table.setHorizontalHeaderLabels([
            "ID", "Name", "Height (cm)", "Weight (kg)",
            "BMI Score", "Category", "Record Time"
        ])

        # Enable sorting
        table.setSortingEnabled(True)

        # Adjust column widths
        header = table.horizontalHeader()
        header.setStretchLastSection(True)

        return table

    def show_records(self):
        try:
            connection = self.db_connector.connect()
            cursor = connection.cursor()
            cursor.execute("SELECT * FROM bmi_records ORDER BY record_time DESC")
            results = cursor.fetchall()

            self.records_table.setRowCount(len(results))
            for row_number, row_data in enumerate(results):
                for column_number, data in enumerate(row_data):
                    item = QTableWidgetItem(str(data))
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.records_table.setItem(row_number, column_number, item)

            self.stacked_widget.setCurrentIndex(1)

        except mysql.connector.Error as e:
            QMessageBox.critical(self, "Database Error", f"Error: {str(e)}")
        finally:
            if 'connection' in locals() and connection.is_connected():
                cursor.close()
                connection.close()

    def show_visualization(self):
        self.visualization.update_name_list()
        self.stacked_widget.setCurrentIndex(2)
        self.visualization.update_graph()

    def calculate_bmi(self):
        try:
            # Validate inputs
            name = self.name_input.text().strip()
            if not name:
                raise ValueError("Please enter your name")

            height_text = self.height_input.text().replace(',', '.')
            weight_text = self.weight_input.text().replace(',', '.')

            if not height_text or not weight_text:
                raise ValueError("Please fill in all fields")

            height_cm = float(height_text)
            weight_kg = float(weight_text)

            if not (50 <= height_cm <= 300):
                raise ValueError("Height must be between 50 and 300 cm")
            if not (20 <= weight_kg <= 500):
                raise ValueError("Weight must be between 20 and 500 kg")

            # Calculate BMI
            height_m = height_cm / 100
            bmi = round(weight_kg / (height_m ** 2), 2)

            # Determine category
            if bmi < 18.5:
                category = "Underweight"
            elif 18.5 <= bmi < 24.9:
                category = "Normal Weight"
            elif 25 <= bmi < 29.9:
                category = "Overweight"
            else:
                category = "Obese"

            # Save to database
            connection = self.db_connector.connect()
            cursor = connection.cursor()

            sql = """
                INSERT INTO bmi_records 
                (name, height_cm, weight_kg, bmi, category)
                VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (name, height_cm, weight_kg, bmi, category))
            connection.commit()

            # Show result
            QMessageBox.information(
                self,
                "BMI Result",
                f"Name: {name}\n"
                f"BMI: {bmi:.2f}\n"
                f"Category: {category}"
            )

            # Clear inputs
            self.name_input.clear()
            self.height_input.clear()
            self.weight_input.clear()

        except ValueError as e:
            QMessageBox.warning(self, "Input Error", str(e))
        except mysql.connector.Error as e:
            QMessageBox.critical(self, "Database Error", f"Error: {str(e)}")
        finally:
            if 'connection' in locals() and connection.is_connected():
                cursor.close()
                connection.close()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())