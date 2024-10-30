import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QAction,
                             QFileDialog, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QListWidget, QListWidgetItem,
                             QMessageBox, QLabel, QLineEdit, QFormLayout,
                             QDialog, QDialogButtonBox, QTextEdit,
                             QGraphicsView, QGraphicsScene, QGraphicsPixmapItem,
                             QGraphicsItem, QGraphicsRectItem, QMenu, QSplitter)
from PyQt5.QtGui import QPixmap, QIcon, QImage, QPainter, QTransform, QCursor, QPainterPath, QPen, QFont
from PyQt5.QtCore import Qt, QMimeData, QPointF, QSize, QDataStream, QRectF, QVariant, QBuffer, QByteArray, QIODevice
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base
import math
import fitz
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from collections import Counter
from io import BytesIO  # Do przechowywania obrazu w pamięci
from reportlab.lib.utils import ImageReader  # Do wczytywania obrazu z pamięci


# Ustawienia bazy danych
Base = declarative_base()

class Component(Base):
    __tablename__ = 'components'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    manufacturer = Column(String)
    cost = Column(Integer)
    type = Column(String)
    icon_path = Column(String)  # Ścieżka do ikony

engine = create_engine('sqlite:///components.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

# Główne okno aplikacji
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("System Wspomagający Projektowanie Sieci Teleinformatycznych")
        self.resize(1000, 800)
        self.initUI()

    def initUI(self):
        # Menu
        menubar = self.menuBar()
        fileMenu = menubar.addMenu('Menu')

        loadPlanAction = QAction('Wgraj Plan Budynku', self)
        loadPlanAction.triggered.connect(self.loadBuildingPlan)
        fileMenu.addAction(loadPlanAction)

        viewDatabaseAction = QAction('Baza Danych Komponentów', self)
        viewDatabaseAction.triggered.connect(self.viewComponentDatabase)
        fileMenu.addAction(viewDatabaseAction)

        userManualAction = QAction('Instrukcja Obsługi', self)
        userManualAction.triggered.connect(self.openUserManual)
        fileMenu.addAction(userManualAction)

        # Centralny widget z przyciskami
        centralWidget = QWidget()
        self.setCentralWidget(centralWidget)

        layout = QVBoxLayout()
        centralWidget.setLayout(layout)

        # Odstępy, aby wyśrodkować przyciski pionowo
        layout.addStretch()

        # Układ dla przycisków
        buttonsLayout = QHBoxLayout()
        layout.addLayout(buttonsLayout)

        # Odstępy, aby wyśrodkować przyciski poziomo
        buttonsLayout.addStretch()

        # Tworzenie przycisków
        loadPlanButton = QPushButton("Wgraj Plan Budynku")
        loadPlanButton.setFixedSize(200, 100)
        loadPlanButton.setFont(QFont("Arial", 12, QFont.Bold))
        loadPlanButton.clicked.connect(self.loadBuildingPlan)

        viewDatabaseButton = QPushButton("Baza Danych Komponentów")
        viewDatabaseButton.setFixedSize(300, 100)
        viewDatabaseButton.setFont(QFont("Arial", 12, QFont.Bold))
        viewDatabaseButton.clicked.connect(self.viewComponentDatabase)

        userManualButton = QPushButton("Instrukcja Obsługi")
        userManualButton.setFixedSize(200, 100)
        userManualButton.setFont(QFont("Arial", 12, QFont.Bold))
        userManualButton.clicked.connect(self.openUserManual)

        # Dodawanie przycisków do układu
        buttonsLayout.addWidget(loadPlanButton)
        buttonsLayout.addSpacing(20)  # Odstęp między przyciskami
        buttonsLayout.addWidget(viewDatabaseButton)
        buttonsLayout.addSpacing(20)
        buttonsLayout.addWidget(userManualButton)

        # Odstępy, aby wyśrodkować przyciski poziomo
        buttonsLayout.addStretch()

        # Odstępy, aby wyśrodkować przyciski pionowo
        layout.addStretch()

    def loadBuildingPlan(self):
        options = QFileDialog.Options()
        options |= QFileDialog.ReadOnly
        fileName, _ = QFileDialog.getOpenFileName(
            self, "Wybierz Plan Budynku", "",
            "Pliki obrazów (*.png *.jpg *.bmp *.pdf)", options=options)
        if fileName:
            self.planEditorWindow = PlanEditorWindow(fileName)
            self.planEditorWindow.show()

    def viewComponentDatabase(self):
        self.databaseWindow = ComponentDatabaseWindow()
        self.databaseWindow.show()

    def openUserManual(self):
        self.userManualWindow = UserManualWindow()
        self.userManualWindow.show()

# Klasa reprezentująca komponent na scenie z możliwością obracania i skalowania
class DraggablePixmapItem(QGraphicsPixmapItem):
    def __init__(self, comp, parent=None):
        super().__init__(QPixmap(comp.icon_path))
        self.comp = comp
        self.setFlags(
            QGraphicsItem.ItemIsMovable |
            QGraphicsItem.ItemIsSelectable |
            QGraphicsItem.ItemSendsGeometryChanges |
            QGraphicsItem.ItemIsFocusable
        )
        self.setAcceptHoverEvents(True)
        self.setAcceptedMouseButtons(Qt.LeftButton | Qt.RightButton)  # Dodano tę linię
        self.setTransformationMode(Qt.SmoothTransformation)
        self.setCursor(Qt.OpenHandCursor)
        self.setAcceptTouchEvents(True)
        self.rotation_angle = 0
        self.scale_factor = 1.0  # Dodano do śledzenia skali
        self.setToolTip(f"{comp.name}\n{comp.type}\n{comp.manufacturer}\nKoszt: {comp.cost} zł")

        # Ustawienie zValue na 1, aby komponent był nad planem budynku
        self.setZValue(1)

        # Załaduj ikonę obrotu i zmniejsz jej rozmiar
        self.rotate_icon_pixmap = QPixmap('rotate_icon.png').scaled(16, 16, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.rotate_icon_item = RotateIconItem(self)
        self.rotate_icon_item.setPixmap(self.rotate_icon_pixmap)
        self.rotate_icon_item.setTransformationMode(Qt.SmoothTransformation)
        self.updateRotateIconPosition()
        self.rotate_icon_item.setFlag(QGraphicsItem.ItemIgnoresTransformations)
        self.rotate_icon_item.setZValue(2)  # Ustawienie zValue ikonki obrotu wyżej niż komponent
        self.rotate_icon_item.setOpacity(1)
        self.rotate_icon_item.hide()  # Ukryj ikonę na początku

        # Stwórz uchwyty do zmiany rozmiaru w rogach
        self.resize_handles = []
        for position in ['top-left', 'top-right', 'bottom-left', 'bottom-right']:
            handle = ResizeHandleItem(self, position)
            handle.setParentItem(self)
            handle.setZValue(2)
            handle.hide()
            self.resize_handles.append(handle)

        self.updateResizeHandles()

    def updateRotateIconPosition(self):
        # Aktualizacja pozycji ikonki obrotu względem rozmiaru komponentu
        offset_x = self.boundingRect().width() / 2 - self.rotate_icon_pixmap.width() / 2
        offset_y = -self.rotate_icon_pixmap.height() - 5  # Odstęp od góry komponentu
        self.rotate_icon_item.setPos(offset_x, offset_y)

    def updateResizeHandles(self):
        # Aktualizacja pozycji uchwytów do zmiany rozmiaru
        rect = self.boundingRect()
        positions = {
            'top-left': (rect.left(), rect.top()),
            'top-right': (rect.right(), rect.top()),
            'bottom-left': (rect.left(), rect.bottom()),
            'bottom-right': (rect.right(), rect.bottom()),
        }
        for handle in self.resize_handles:
            x, y = positions[handle.position]
            handle.setPos(x, y)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemSelectedChange:
            if value == True:
                # Komponent został wybrany
                self.rotate_icon_item.show()
                for handle in self.resize_handles:
                    handle.show()
            else:
                # Komponent został odznaczony
                self.rotate_icon_item.hide()
                for handle in self.resize_handles:
                    handle.hide()
        elif change in (QGraphicsItem.ItemPositionChange, QGraphicsItem.ItemTransformChange):
            self.updateRotateIconPosition()
            self.updateResizeHandles()
        return super().itemChange(change, value)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.setCursor(Qt.ClosedHandCursor)
            self._drag_start_position = event.screenPos()
            self._is_dragging = False
            super().mousePressEvent(event)
        elif event.button() == Qt.RightButton:
            # Upewnij się, że komponent pozostaje wybrany
            self.setSelected(True)
            event.accept()
        else:
            super().mousePressEvent(event)

    def contextMenuEvent(self, event):
        menu = QMenu()
        delete_action = QAction("Usuń komponent", menu)
        delete_action.triggered.connect(self.deleteComponent)
        menu.addAction(delete_action)
        menu.exec_(event.screenPos())
        event.accept() 

    def deleteComponent(self):
        self.scene().removeItem(self)

    def shape(self):
        # Zwracamy kształt obejmujący cały pixmap
        path = QPainterPath()
        path.addRect(self.boundingRect())
        return path

    def setRotationAngle(self, angle):
        self.rotation_angle = angle % 360
        self.setRotation(self.rotation_angle)
        self.updateRotateIconPosition()
        self.updateResizeHandles()

    def setScaleFactor(self, factor):
        self.scale_factor = factor
        self.setScale(self.scale_factor)
        self.updateRotateIconPosition()
        self.updateResizeHandles()

# Klasa uchwytu do zmiany rozmiaru
class ResizeHandleItem(QGraphicsRectItem):
    def __init__(self, parent_item, position):
        size = 8  # Rozmiar uchwytu
        super().__init__(-size/2, -size/2, size, size)
        self.parent_item = parent_item
        self.position = position  # 'top-left', 'top-right', etc.
        self.setBrush(Qt.black)
        self.setPen(QPen(Qt.NoPen))  # Poprawka błędu
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setAcceptHoverEvents(True)
        if self.position in ['top-left', 'bottom-right']:
            self.setCursor(Qt.SizeFDiagCursor)
        else:
            self.setCursor(Qt.SizeBDiagCursor)

    def mousePressEvent(self, event):
        self.original_pos = event.scenePos()
        self.original_scale = self.parent_item.scale_factor
        event.accept()

    def mouseMoveEvent(self, event):
        # Oblicz nowy współczynnik skalowania na podstawie ruchu myszy
        new_pos = event.scenePos()
        delta = new_pos - self.original_pos

        # Współrzędne w lokalnym układzie współrzędnych
        if self.position == 'bottom-right':
            scale_change = 1 + delta.x() / self.parent_item.boundingRect().width()
        elif self.position == 'bottom-left':
            scale_change = 1 - delta.x() / self.parent_item.boundingRect().width()
        elif self.position == 'top-right':
            scale_change = 1 - delta.y() / self.parent_item.boundingRect().height()
        elif self.position == 'top-left':
            scale_change = 1 - delta.x() / self.parent_item.boundingRect().width()
        else:
            scale_change = 1.0

        new_scale = self.original_scale * scale_change
        if new_scale < 0.1:
            new_scale = 0.1
        elif new_scale > 10:
            new_scale = 10

        self.parent_item.setScaleFactor(new_scale)
        event.accept()

    def mouseReleaseEvent(self, event):
        event.accept()

# Klasa ikonki obrotu
class RotateIconItem(QGraphicsPixmapItem):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent_item = parent
        self.setCursor(Qt.SizeAllCursor)
        self.setAcceptedMouseButtons(Qt.LeftButton)
        self.is_rotating = False

    def shape(self):
        # Zwracamy obszar obejmujący cały prostokąt ikony
        path = QPainterPath()
        path.addEllipse(self.boundingRect())
        return path

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_rotating = True
            self.last_mouse_pos = event.scenePos()
            self.setOpacity(0)  # Ukryj ikonę podczas obracania
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.is_rotating:
            current_pos = event.scenePos()
            center_pos = self.parent_item.mapToScene(self.parent_item.boundingRect().center())
            angle = math.degrees(math.atan2(current_pos.y() - center_pos.y(), current_pos.x() - center_pos.x()))
            self.parent_item.setRotationAngle(angle)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.is_rotating:
            self.is_rotating = False
            self.setOpacity(1)  # Pokaż ikonę po zakończeniu obracania
            event.accept()
        else:
            super().mouseReleaseEvent(event)

# Okno edytora planu
class PlanEditorWindow(QMainWindow):
    def __init__(self, planFile):
        super().__init__()
        self.setWindowTitle("Edytor Planu Budynku")
        self.resize(1200, 900)
        self.planFile = planFile
        self.initUI()
        self.placedComponents = []

    def initUI(self):
        centralWidget = QWidget()
        self.setCentralWidget(centralWidget)

        # Główny układ pionowy
        mainLayout = QVBoxLayout()
        centralWidget.setLayout(mainLayout)

        # Tworzymy QSplitter
        splitter = QSplitter(Qt.Horizontal)
        mainLayout.addWidget(splitter)

        self.componentList = QListWidget()
        self.componentList.setIconSize(QSize(50, 50))
        self.componentList.setDragEnabled(True)
        self.loadComponents()

        self.scene = QGraphicsScene()
        self.view = GraphicsView(self.scene, self)
        self.view.setAcceptDrops(True)

        self.loadPlan()

        # Dodajemy listę komponentów i obszar roboczy do QSplitter
        splitter.addWidget(self.componentList)
        splitter.addWidget(self.view)

        # Ustawiamy minimalne szerokości
        self.componentList.setMinimumWidth(200)
        self.view.setMinimumWidth(400)

        # Ustawiamy proporcje początkowe
        total_width = self.width()
        splitter.setSizes([int(total_width * 0.33), int(total_width * 0.66)])

        # Przyciski akcji
        buttonLayout = QHBoxLayout()
        mainLayout.addLayout(buttonLayout)

        # Odstęp, aby przyciski były wyrównane do prawej
        buttonLayout.addStretch()

        saveButton = QPushButton("Zapisz Projekt")
        saveButton.clicked.connect(self.saveProject)
        buttonLayout.addWidget(saveButton)

        # Dodajemy nowy przycisk "Generuj Raport"
        reportButton = QPushButton("Generuj Raport")
        reportButton.clicked.connect(self.generateReport)
        buttonLayout.addWidget(reportButton)

    def loadPlan(self):
        if self.planFile.lower().endswith('.pdf'):
            # Wczytanie pliku PDF i renderowanie pierwszej strony jako obraz
            try:
                doc = fitz.open(self.planFile)
                page = doc.load_page(0)  # Wczytaj pierwszą stronę
                pix = page.get_pixmap()
                image_bytes = pix.tobytes("png")  # Użyj tonytes("png") zamiast getPNGData()
                pixmap = QPixmap()
                pixmap.loadFromData(image_bytes)
                self.planItem = self.scene.addPixmap(pixmap)
                self.planItem.setZValue(-1)
            except Exception as e:
                QMessageBox.critical(self, "Błąd", f"Nie można wczytać pliku PDF: {e}")
        else:
            # Wczytanie obrazu tak jak wcześniej
            pixmap = QPixmap(self.planFile)
            self.planItem = self.scene.addPixmap(pixmap)
            self.planItem.setZValue(-1)  # Ustaw plan na tło

    def loadComponents(self):
        components = session.query(Component).all()
        for comp in components:
            item = QListWidgetItem(comp.name)
            item.setData(Qt.UserRole, comp)
            icon = QIcon(comp.icon_path)
            item.setIcon(icon)
            self.componentList.addItem(item)

    def saveProject(self):
        fileName, _ = QFileDialog.getSaveFileName(
            self, "Zapisz Projekt", "", "PNG Files (*.png)")
        if fileName:
            # Dopasuj rozmiar obrazu do zawartości sceny
            rect = self.scene.itemsBoundingRect()
            image = QImage(rect.size().toSize(), QImage.Format_ARGB32)
            image.fill(Qt.white)
            painter = QPainter(image)
            self.scene.render(painter, target=QRectF(image.rect()), source=rect)
            painter.end()
            image.save(fileName)
            QMessageBox.information(
                self, "Zapisano", "Projekt został zapisany.")

    def generateReport(self):
        if not self.placedComponents:
            QMessageBox.warning(self, "Brak danych", "Nie dodano żadnych komponentów do planu.")
            return

        fileName, _ = QFileDialog.getSaveFileName(
            self, "Zapisz Raport", "", "PDF Files (*.pdf)")
        if fileName:
            try:
                # Tworzenie dokumentu PDF
                c = canvas.Canvas(fileName, pagesize=letter)
                width, height = letter

                c.setFont("Helvetica-Bold", 16)
                c.drawString(50, height - 50, "Raport z projektu sieci teleinformatycznej")

                c.setFont("Helvetica", 12)
                c.drawString(50, height - 80, f"Nazwa projektu: {self.planFile}")

                # --- Dodanie obrazu projektu ---
                # Renderowanie sceny do obrazu
                rect = self.scene.itemsBoundingRect()
                image = QImage(rect.size().toSize(), QImage.Format_ARGB32)
                image.fill(Qt.white)
                painter = QPainter(image)
                self.scene.render(painter, target=QRectF(image.rect()), source=rect)
                painter.end()

                # Konwersja QImage do QByteArray
                byte_array = QByteArray()
                buffer = QBuffer(byte_array)
                buffer.open(QIODevice.WriteOnly)
                image.save(buffer, 'PNG')
                buffer.close()

                # Wczytanie obrazu do ReportLab
                image_data = byte_array.data()
                project_image = ImageReader(BytesIO(image_data))

                # Obliczenie skali obrazu, aby pasował do strony
                img_width, img_height = project_image.getSize()
                max_width = width - 100  # Marginesy
                max_height = height - 300  # Odjęcie miejsca na tekst

                scale = min(max_width / img_width, max_height / img_height, 1.0)
                img_width *= scale
                img_height *= scale

                # Pozycja obrazu
                img_x = (width - img_width) / 2
                img_y = height - img_height - 120  # Odjęcie miejsca na nagłówek

                # Rysowanie obrazu
                c.drawImage(project_image, img_x, img_y, width=img_width, height=img_height)

                y_position = img_y - 20  # Ustawienie pozycji poniżej obrazu

                # --- Kontynuacja generowania raportu ---

                # Grupowanie komponentów
                component_counts = Counter()
                total_cost = 0

                for comp in self.placedComponents:
                    component_counts[comp.name] += 1
                    total_cost += comp.cost

                c.setFont("Helvetica-Bold", 14)
                c.drawString(50, y_position, "Uzyte komponenty:")
                y_position -= 20

                c.setFont("Helvetica", 12)
                for comp_name, count in component_counts.items():
                    comp = session.query(Component).filter_by(name=comp_name).first()
                    line = f"- {comp_name} (Producent: {comp.manufacturer}, Typ: {comp.type}) x {count}, Cena jednostkowa: {comp.cost} zl, Lacznie: {comp.cost * count} zl"
                    c.drawString(60, y_position, line)
                    y_position -= 20
                    total_cost += comp.cost * (count - 1)  # Dodajemy koszt dodatkowych sztuk

                    # Sprawdzamy, czy nie wychodzimy poza stronę
                    if y_position < 50:
                        c.showPage()
                        y_position = height - 50

                # Szacunkowy koszt wykonania pracy (np. 20% kosztów sprzętu)
                labor_cost = total_cost * 0.2
                total_project_cost = total_cost + labor_cost

                y_position -= 20
                c.setFont("Helvetica-Bold", 12)
                c.drawString(50, y_position, f"Laczny koszt komponentów: {total_cost} zl")
                y_position -= 20
                c.drawString(50, y_position, f"Szacunkowy koszt wykonania pracy (20%): {labor_cost:.2f} zl")
                y_position -= 20
                c.drawString(50, y_position, f"Laczny koszt projektu: {total_project_cost:.2f} zl")

                # Zakończenie i zapis pliku PDF
                c.save()
                QMessageBox.information(self, "Raport zapisany", "Raport został pomyślnie zapisany.")
            except Exception as e:
                QMessageBox.critical(self, "Błąd", f"Wystąpił błąd podczas generowania raportu: {e}")


# Niestandardowy QGraphicsView do obsługi przeciągania i upuszczania
class GraphicsView(QGraphicsView):
    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHint(QPainter.Antialiasing)
        self._pan = False
        self._panStartX = 0
        self._panStartY = 0
        self.setDragMode(QGraphicsView.NoDrag)
        self.setInteractive(True)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.parentWindow = parent  # Referencja do PlanEditorWindow

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            item = self.itemAt(event.pos())
            if item is None:
                # Rozpocznij przesuwanie widoku
                self.setCursor(Qt.ClosedHandCursor)
                self._pan = True
                self._panStartX = event.x()
                self._panStartY = event.y()
                event.accept()
            else:
                super().mousePressEvent(event)
        else:
            super().mousePressEvent(event)

    # Upewnij się, że nie nadpisujemy innych zdarzeń, które mogą blokować menu kontekstowe

    def mouseMoveEvent(self, event):
        if self._pan:
            # Przesuwanie widoku
            deltaX = event.x() - self._panStartX
            deltaY = event.y() - self._panStartY
            self._panStartX = event.x()
            self._panStartY = event.y()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - deltaX)
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - deltaY)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._pan:
            # Zakończ przesuwanie widoku
            self.setCursor(Qt.ArrowCursor)
            self._pan = False
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        # Zoomowanie
        zoomInFactor = 1.25
        zoomOutFactor = 0.8
        oldPos = self.mapToScene(event.pos())

        if event.angleDelta().y() > 0:
            zoomFactor = zoomInFactor
        else:
            zoomFactor = zoomOutFactor

        self.scale(zoomFactor, zoomFactor)

        newPos = self.mapToScene(event.pos())
        delta = newPos - oldPos
        self.translate(delta.x(), delta.y())

    def dragEnterEvent(self, event):
        event.accept()

    def dragMoveEvent(self, event):
        event.accept()

    def dropEvent(self, event):
        mime = event.mimeData()
        if mime.hasFormat('application/x-qabstractitemmodeldatalist'):
            data = mime.data('application/x-qabstractitemmodeldatalist')
            stream = QDataStream(data)
            while not stream.atEnd():
                row = stream.readInt32()
                column = stream.readInt32()
                mapItems = stream.readInt32()
                for i in range(mapItems):
                    role = stream.readInt32()
                    value = stream.readQVariant()
                    if role == Qt.UserRole:
                        comp = value
                        self.addComponentToScene(comp, event.pos())
            event.accept()
        else:
            event.ignore()

    def addComponentToScene(self, comp, position):
        item = DraggablePixmapItem(comp)
        self.scene().addItem(item)
        item.setPos(self.mapToScene(position))
        item.setFocus()

        # Dodajemy komponent do listy w PlanEditorWindow
        if self.parentWindow:
            self.parentWindow.placedComponents.append(comp)

# Okno bazy danych komponentów
class ComponentDatabaseWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Baza Danych Komponentów")
        self.resize(600, 400)
        self.initUI()

    def initUI(self):
        mainLayout = QVBoxLayout()
        self.setLayout(mainLayout)

        self.componentList = QListWidget()
        self.loadComponents()
        mainLayout.addWidget(self.componentList)

        buttonLayout = QHBoxLayout()
        addButton = QPushButton("Dodaj Komponent")
        addButton.clicked.connect(self.addComponent)
        editButton = QPushButton("Edytuj Komponent")
        editButton.clicked.connect(self.editComponent)
        deleteButton = QPushButton("Usuń Komponent")
        deleteButton.clicked.connect(self.deleteComponent)
        buttonLayout.addWidget(addButton)
        buttonLayout.addWidget(editButton)
        buttonLayout.addWidget(deleteButton)
        mainLayout.addLayout(buttonLayout)

    def loadComponents(self):
        self.componentList.clear()
        components = session.query(Component).all()
        for comp in components:
            item = QListWidgetItem(f"{comp.name} ({comp.type})")
            item.setData(Qt.UserRole, comp)
            icon = QIcon(comp.icon_path)
            item.setIcon(icon)
            self.componentList.addItem(item)

    def addComponent(self):
        dialog = ComponentDialog()
        if dialog.exec_():
            new_comp = Component(
                name=dialog.nameEdit.text(),
                manufacturer=dialog.manufacturerEdit.text(),
                cost=int(dialog.costEdit.text()),
                type=dialog.typeEdit.text(),
                icon_path=dialog.iconPath)
            session.add(new_comp)
            session.commit()
            self.loadComponents()

    def editComponent(self):
        selected = self.componentList.currentItem()
        if selected:
            comp = selected.data(Qt.UserRole)
            dialog = ComponentDialog(comp)
            if dialog.exec_():
                comp.name = dialog.nameEdit.text()
                comp.manufacturer = dialog.manufacturerEdit.text()
                comp.cost = int(dialog.costEdit.text())
                comp.type = dialog.typeEdit.text()
                comp.icon_path = dialog.iconPath
                session.commit()
                self.loadComponents()
        else:
            QMessageBox.warning(self, "Brak wyboru",
                                "Wybierz komponent do edycji.")

    def deleteComponent(self):
        selected = self.componentList.currentItem()
        if selected:
            comp = selected.data(Qt.UserRole)
            reply = QMessageBox.question(
                self, 'Potwierdzenie',
                f"Czy na pewno usunąć komponent {comp.name}?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                session.delete(comp)
                session.commit()
                self.loadComponents()
        else:
            QMessageBox.warning(self, "Brak wyboru",
                                "Wybierz komponent do usunięcia.")

# Dialog dodawania/edycji komponentu
class ComponentDialog(QDialog):
    def __init__(self, component=None):
        super().__init__()
        self.setWindowTitle("Dodaj/Edytuj Komponent")
        self.resize(400, 300)
        self.component = component
        self.iconPath = ""
        self.initUI()
        if component:
            self.loadComponentData()

    def initUI(self):
        layout = QFormLayout()
        self.setLayout(layout)

        self.nameEdit = QLineEdit()
        self.manufacturerEdit = QLineEdit()
        self.costEdit = QLineEdit()
        self.typeEdit = QLineEdit()
        self.iconButton = QPushButton("Wybierz ikonę")
        self.iconButton.clicked.connect(self.selectIcon)

        layout.addRow("Nazwa:", self.nameEdit)
        layout.addRow("Producent:", self.manufacturerEdit)
        layout.addRow("Koszt:", self.costEdit)
        layout.addRow("Typ:", self.typeEdit)
        layout.addRow("Ikona:", self.iconButton)

        buttonBox = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        layout.addWidget(buttonBox)

    def selectIcon(self):
        options = QFileDialog.Options()
        options |= QFileDialog.ReadOnly
        fileName, _ = QFileDialog.getOpenFileName(
            self, "Wybierz ikonę", "",
            "Image Files (*.png *.jpg *.bmp)", options=options)
        if fileName:
            self.iconPath = fileName

    def loadComponentData(self):
        self.nameEdit.setText(self.component.name)
        self.manufacturerEdit.setText(self.component.manufacturer)
        self.costEdit.setText(str(self.component.cost))
        self.typeEdit.setText(self.component.type)
        self.iconPath = self.component.icon_path

# Okno instrukcji obsługi
class UserManualWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Instrukcja Obsługi")
        self.resize(600, 400)
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        self.textEdit = QTextEdit()
        self.textEdit.setReadOnly(True)
        layout.addWidget(self.textEdit)

        self.loadUserManual()

    def loadUserManual(self):
        try:
            with open('user_manual.txt', 'r', encoding='utf-8') as f:
                manualText = f.read()
                self.textEdit.setPlainText(manualText)
        except FileNotFoundError:
            self.textEdit.setPlainText("Brak pliku z instrukcją obsługi.")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
