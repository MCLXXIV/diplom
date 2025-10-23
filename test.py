import sys
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QSlider, QComboBox, QGroupBox, QGridLayout)
from PyQt5.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

from vispy import scene
from vispy.scene import visuals

import sys
import os


class SlicePlot(QWidget):
    def __init__(self, data, axis, axis_name, vmin, vmax):
        super().__init__()
        self.data = data
        self.axis = axis
        self.axis_name = axis_name
        self.max_index = data.shape[axis] - 1
        self.current_index = 0

        self.vmin = vmin
        self.vmax = vmax
        self.current_cmap = "RdBu"

        layout = QVBoxLayout(self)
        self.setLayout(layout)

        # Matplotlib figure без colorbar (он будет в отдельной ячейке)
        self.fig = Figure(figsize=(4, 4))
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvas(self.fig)
        layout.addWidget(self.canvas)

        self.img = None
        self.update_image(0)

        # Slider
        slider_layout = QHBoxLayout()
        layout.addLayout(slider_layout)

        self.label = QLabel(f"{self.axis_name}:")
        slider_layout.addWidget(self.label)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(self.max_index)
        self.slider.setValue(0)
        self.slider.valueChanged.connect(self.on_slide)
        slider_layout.addWidget(self.slider)

        self.value_label = QLabel("0")
        slider_layout.addWidget(self.value_label)

        # Pixel value label
        self.pixel_label = QLabel("Наведи на график")
        layout.addWidget(self.pixel_label)

        self.canvas.mpl_connect("motion_notify_event", self.on_mouse_move)

    def update_image(self, index):
        if self.axis == 0:
            slice_data = self.data[index, :, :]
        elif self.axis == 1:
            slice_data = self.data[:, index, :]
        else:
            slice_data = self.data[:, :, index]

        if self.img is None:
            self.img = self.ax.imshow(slice_data, cmap=self.current_cmap,
                                      vmin=self.vmin, vmax=self.vmax, aspect='equal')
            self.ax.set_title(f"{self.axis_name} = {index}", fontsize=11, fontweight='bold')
            self.ax.set_xlabel("Координата", fontsize=9)
            self.ax.set_ylabel("Координата", fontsize=9)
            self.fig.tight_layout()
        else:
            self.img.set_data(slice_data)
            self.ax.set_title(f"{self.axis_name} = {index}", fontsize=11, fontweight='bold')
        self.canvas.draw_idle()

    def update_colormap(self, cmap_name):
        """Обновляет colormap для среза"""
        self.current_cmap = cmap_name
        if self.img is not None:
            self.img.set_cmap(cmap_name)
            self.canvas.draw_idle()

    def on_slide(self, value):
        index = int(value)
        if index != self.current_index:
            self.current_index = index
            self.update_image(index)
            self.value_label.setText(str(index))

    def on_mouse_move(self, event):
        if event.inaxes == self.ax and event.xdata is not None and event.ydata is not None:
            x = int(event.xdata + 0.5)
            y = int(event.ydata + 0.5)
            value = None
            try:
                if self.axis == 0 and 0 <= x < self.data.shape[2] and 0 <= y < self.data.shape[1]:
                    value = self.data[self.current_index, y, x]
                elif self.axis == 1 and 0 <= x < self.data.shape[2] and 0 <= y < self.data.shape[0]:
                    value = self.data[y, self.current_index, x]
                elif self.axis == 2 and 0 <= x < self.data.shape[1] and 0 <= y < self.data.shape[0]:
                    value = self.data[y, x, self.current_index]
                if value is not None:
                    self.pixel_label.setText(f"Пиксель ({x},{y})={value:.3f}")
                else:
                    self.pixel_label.setText("За пределами данных")
            except:
                self.pixel_label.setText("Ошибка чтения данных")
        else:
            self.pixel_label.setText("Наведи на график")


class ColorbarWidget(QWidget):
    """Виджет с colorbar и настройками"""

    def __init__(self, vmin, vmax, parent_window):
        super().__init__()
        self.vmin = vmin
        self.vmax = vmax
        self.parent_window = parent_window
        self.current_cmap = "RdBu"

        layout = QVBoxLayout(self)
        self.setLayout(layout)

        # Заголовок
        title = QLabel("Настройки")
        title.setStyleSheet("QLabel { font-size: 14pt; font-weight: bold; }")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Colorbar
        self.fig = Figure(figsize=(4, 4))
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvas(self.fig)
        layout.addWidget(self.canvas)

        self.create_colorbar()

        # Выбор colormap
        cmap_group = QGroupBox("Colormap для срезов")
        cmap_layout = QVBoxLayout()
        cmap_group.setLayout(cmap_layout)

        self.cmap_label = QLabel("Выбрать colormap:")
        self.cmap_combo = QComboBox()
        self.cmap_combo.addItems(['RdBu', 'viridis', 'plasma', 'inferno', 'magma',
                                  'cividis', 'hot', 'cool', 'rainbow', 'seismic',
                                  'coolwarm', 'bwr', 'jet', 'turbo'])
        self.cmap_combo.setCurrentText('RdBu')
        self.cmap_combo.currentTextChanged.connect(self.on_colormap_change)

        cmap_layout.addWidget(self.cmap_label)
        cmap_layout.addWidget(self.cmap_combo)

        layout.addWidget(cmap_group)

        # Информация о диапазоне
        info_label = QLabel(f"Диапазон значений:\nМин: {vmin:.3f}\nМакс: {vmax:.3f}")
        info_label.setStyleSheet(
            "QLabel { font-size: 10pt; padding: 10px; background-color: #f0f0f0; border-radius: 5px; }")
        layout.addWidget(info_label)

        layout.addStretch()

    def create_colorbar(self):
        """Создает colorbar"""
        self.ax.clear()

        # Создаем градиент
        gradient = np.linspace(self.vmin, self.vmax, 256).reshape(256, 1)

        self.img = self.ax.imshow(gradient, aspect='auto', cmap=self.current_cmap,
                                  vmin=self.vmin, vmax=self.vmax,
                                  extent=[0, 1, self.vmin, self.vmax])

        self.ax.set_xlim(0, 1)
        self.ax.set_ylim(self.vmin, self.vmax)
        self.ax.set_xticks([])
        self.ax.set_ylabel('Значение', fontsize=11, fontweight='bold')
        self.ax.yaxis.tick_right()
        self.ax.yaxis.set_label_position("right")

        self.fig.tight_layout()
        self.canvas.draw_idle()

    def on_colormap_change(self, cmap_name):
        """Обрабатывает изменение colormap"""
        self.current_cmap = cmap_name
        self.img.set_cmap(cmap_name)
        self.canvas.draw_idle()

        # Обновляем colormap у всех срезов
        self.parent_window.change_slice_colormap(cmap_name)


class TripleSliceWindow(QMainWindow):
    def __init__(self, data):
        super().__init__()
        self.setWindowTitle("3D Volume Viewer")
        self.resize(1400, 800)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout()
        central_widget.setLayout(main_layout)

        # Левая часть: сетка 2x2 для срезов
        left_widget = QWidget()
        grid_layout = QGridLayout()
        left_widget.setLayout(grid_layout)

        # Устанавливаем равные пропорции для строк и столбцов
        grid_layout.setRowStretch(0, 1)
        grid_layout.setRowStretch(1, 1)
        grid_layout.setColumnStretch(0, 1)
        grid_layout.setColumnStretch(1, 1)
        grid_layout.setSpacing(5)

        main_layout.addWidget(left_widget, 1)

        # Вычисляем общие границы для всех срезов
        self.vmin = np.min(data)
        self.vmax = np.max(data)

        # Создаём три слайсера
        self.slice_x = SlicePlot(data, axis=0, axis_name="X", vmin=self.vmin, vmax=self.vmax)
        self.slice_y = SlicePlot(data, axis=1, axis_name="Y", vmin=self.vmin, vmax=self.vmax)
        self.slice_z = SlicePlot(data, axis=2, axis_name="Z", vmin=self.vmin, vmax=self.vmax)

        # Виджет с colorbar и настройками
        self.colorbar_widget = ColorbarWidget(self.vmin, self.vmax, self)

        # Размещаем в сетке 2x2
        grid_layout.addWidget(self.slice_x, 0, 0)  # Верхний левый
        grid_layout.addWidget(self.slice_y, 0, 1)  # Верхний правый
        grid_layout.addWidget(self.slice_z, 1, 0)  # Нижний левый
        grid_layout.addWidget(self.colorbar_widget, 1, 1)  # Нижний правый

        # Правая часть: 3D volume
        right_column = QVBoxLayout()
        main_layout.addLayout(right_column, 1)

        self.vispy_group = QGroupBox("3D Volume (VisPy)")
        vispy_layout = QVBoxLayout()
        self.vispy_group.setLayout(vispy_layout)
        right_column.addWidget(self.vispy_group)

        self.canvas = scene.SceneCanvas(keys='interactive', bgcolor='white', parent=self.vispy_group)
        self.canvas.create_native()
        vispy_layout.addWidget(self.canvas.native)

        self.view = self.canvas.central_widget.add_view()
        self.view.camera = 'arcball'

        self.volume = visuals.Volume(data, parent=self.view.scene, method='mip', cmap='viridis')
        self.view.camera.set_range()

        # Панель управления 3D
        volume_controls = QWidget()
        volume_controls_layout = QVBoxLayout()
        volume_controls.setLayout(volume_controls_layout)

        # Colormap для 3D
        volume_cmap_layout = QHBoxLayout()
        self.volume_cmap_label = QLabel("Colormap для 3D:")
        self.volume_cmap_combo = QComboBox()
        self.volume_cmap_combo.addItems(['viridis', 'plasma', 'inferno', 'magma', 'cividis',
                                         'hot', 'cool', 'rainbow', 'grays', 'turbo'])
        self.volume_cmap_combo.setCurrentText('viridis')
        self.volume_cmap_combo.currentTextChanged.connect(self.change_volume_colormap)
        volume_cmap_layout.addWidget(self.volume_cmap_label)
        volume_cmap_layout.addWidget(self.volume_cmap_combo)
        volume_controls_layout.addLayout(volume_cmap_layout)

        # Тип камеры
        camera_layout = QHBoxLayout()
        self.camera_label = QLabel("Тип камеры:")
        self.camera_combo = QComboBox()
        self.camera_combo.addItems(['arcball', 'turntable', 'fly'])
        self.camera_combo.setCurrentText('arcball')
        self.camera_combo.currentTextChanged.connect(self.change_camera)
        camera_layout.addWidget(self.camera_label)
        camera_layout.addWidget(self.camera_combo)
        volume_controls_layout.addLayout(camera_layout)

        vispy_layout.addWidget(volume_controls)

        # Инструкции
        instructions = QLabel(
            "Управление 3D:\n"
            "• ЛКМ - вращение\n"
            "• ПКМ или колесо - приближение\n"
            "• Shift+ЛКМ - перемещение"
        )
        instructions.setStyleSheet("QLabel { font-size: 9pt; color: #555; padding: 10px; }")
        vispy_layout.addWidget(instructions)

    def change_slice_colormap(self, cmap_name):
        """Изменяет colormap для всех срезов одновременно"""
        self.slice_x.update_colormap(cmap_name)
        self.slice_y.update_colormap(cmap_name)
        self.slice_z.update_colormap(cmap_name)

    def change_volume_colormap(self, cmap_name):
        """Изменяет colormap для 3D volume"""
        self.volume.cmap = cmap_name
        self.canvas.update()

    def change_camera(self, camera_type):
        """Изменяет тип камеры для 3D визуализации"""
        self.view.camera = camera_type
        self.view.camera.set_range()
        self.canvas.update()


def read_file(filepath: str) -> np.ndarray:
    try:
        with open(filepath) as file:
            for _ in range(6):
                file.readline()
            number_matrices = int(file.readline().strip())
            matrix_data = []
            for i in range(number_matrices):
                for _ in range(4):
                    file.readline()
                number_rows = int(file.readline().strip())
                file.readline()
                number_cols = int(file.readline().strip())
                file.readline()
                file.readline()
                row_data = []
                for j in range(number_rows):
                    row = [float(x) for x in file.readline().strip().split()]
                    row_data.append(row)
                matrix_data.append(row_data)
        return np.array(matrix_data, dtype=np.float32)
    except Exception as e:
        print(f'Ошибка обработки файла: {e}')
        return None


if __name__ == "__main__":
    # Определяем где находится приложение
    if getattr(sys, 'frozen', False):
        # Приложение упаковано
        app_path = os.path.dirname(sys.executable)
    else:
        # Запуск как обычный скрипт
        app_path = os.path.dirname(os.path.abspath(__file__))

    # Ищем файл рядом с приложением
    data_folder = os.path.join(app_path, 'data')
    FILEPATH = os.path.join(data_folder, 'GRF_sinxds.out')

    print(f"Ищу файл: {FILEPATH}")
    print(f"Файл существует: {os.path.exists(FILEPATH)}")

    if not os.path.exists(FILEPATH):
        print(f"⚠️ Файл не найден в {data_folder}")
        sys.exit(f"Положи файл GRF_sinxds.out в папку {data_folder}")

    data = read_file(FILEPATH)
    if data is None:
        sys.exit("Не удалось прочитать данные.")

    app = QApplication(sys.argv)
    window = TripleSliceWindow(data)
    window.show()
    sys.exit(app.exec_())
