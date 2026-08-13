from PyQt6.QtWidgets import QWidget, QPlainTextEdit
from PyQt6.QtGui import QPainter, QColor
from PyQt6.QtCore import Qt, QRect, QSize

class LineNumberArea(QWidget):
    """
    Вспомогательный виджет (холст) для отрисовки номеров строк.
    """
    def __init__(self, editor):
        super().__init__(editor)
        self.code_editor = editor

    def sizeHint(self):
        return QSize(self.code_editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        # Делегируем логику отрисовки обратно в редактор для доступа к блокам текста
        self.code_editor.line_number_area_paint_event(event)

class CodeEditor(QPlainTextEdit):
    """
    Расширенный редактор кода с нумерацией строк и отключенным переносом.
    """
    def __init__(self):
        super().__init__()
        self.line_number_area = LineNumberArea(self)

        # Отключаем перенос слов; появляется горизонтальный скроллбар
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

        # Подключаем сигналы ядра текстового документа для синхронизации панели
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.update_line_number_area_width(0)

    def line_number_area_width(self):
        """Динамический расчет ширины панели в зависимости от количества цифр в номере последней строки."""
        digits = 1
        max_value = max(1, self.blockCount())
        while max_value >= 10:
            max_value //= 10
            digits += 1
        
        # 3 пикселя — базовый отступ, плюс ширина символа '9' умноженная на количество разрядов
        space = 3 + self.fontMetrics().horizontalAdvance('9') * digits
        return space

    def update_line_number_area_width(self, _):
        # Сдвигаем область редактирования текста вправо на ширину панели нумерации
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        """Синхронизация прокрутки текста и панели нумерации."""
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())

        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, event):
        """Перерасчет геометрии при изменении размеров окна эмулятора."""
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height()))

    def line_number_area_paint_event(self, event):
        """Физическая отрисовка чисел на холсте."""
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QColor("lightgray"))

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        
        # Вычисление Y-координат для текущего блока текста
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(Qt.GlobalColor.black)
                painter.drawText(0, top, self.line_number_area.width() - 2, self.fontMetrics().height(),
                                 Qt.AlignmentFlag.AlignRight, number)

            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            block_number += 1