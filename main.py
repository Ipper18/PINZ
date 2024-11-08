import sys
import os
from collections import Counter
from io import BytesIO
import math
import fitz
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QAction, QFileDialog, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QListWidget, QListWidgetItem, QMessageBox, QLabel, QLineEdit, QFormLayout,
    QDialog, QDialogButtonBox, QTextEdit, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem,
    QGraphicsItem, QGraphicsRectItem, QGraphicsLineItem, QMenu, QSplitter, QComboBox,
    QTreeWidget, QTreeWidgetItem, QShortcut, QGraphicsObject
)
from PyQt5.QtGui import (
    QPixmap, QIcon, QImage, QPainter, QTransform, QCursor, QPainterPath, QPen, QFont,
    QPainterPathStroker, QKeySequence, QBrush 
)
from PyQt5.QtCore import (
    Qt, QMimeData, QPointF, QSize, QDataStream, QRectF, QVariant, QBuffer, QByteArray,
    QIODevice, QEvent, QLineF, pyqtSignal
)
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas



# Ustawienia bazy danych
Base = declarative_base()
component_types = ["Router", "Switch", "Access Point", "Firewall", "Server", "Centrala", "Gniazdko", "Czujnik temperatury", "Czujnik ruchu", "Czujnik zalania", "Wlacznik", "Alarm", "Czujnik dymu", "Oswielenie"]


class Component(Base):
    __tablename__ = 'components'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    manufacturer = Column(String)
    cost = Column(Integer)
    type = Column(String)
    icon_path = Column(String)  # scieżka do ikony

engine = create_engine('sqlite:///components.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

engine = create_engine('sqlite:///components.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

# Glówne okno aplikacji
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("System Wspomagajacy Projektowanie Sieci Teleinformatycznych")
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

        userManualAction = QAction('Instrukcja Obslugi', self)
        userManualAction.triggered.connect(self.openUserManual)
        fileMenu.addAction(userManualAction)

        # Centralny widget z przyciskami
        centralWidget = QWidget()
        self.setCentralWidget(centralWidget)

        layout = QVBoxLayout()
        centralWidget.setLayout(layout)

        # Odstępy, aby wysrodkowac przyciski pionowo
        layout.addStretch()

        # Uklad dla przycisków
        buttonsLayout = QHBoxLayout()
        layout.addLayout(buttonsLayout)

        # Odstępy, aby wysrodkowac przyciski poziomo
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

        userManualButton = QPushButton("Instrukcja Obslugi")
        userManualButton.setFixedSize(200, 100)
        userManualButton.setFont(QFont("Arial", 12, QFont.Bold))
        userManualButton.clicked.connect(self.openUserManual)

        # Dodawanie przycisków do ukladu
        buttonsLayout.addWidget(loadPlanButton)
        buttonsLayout.addSpacing(20)  # Odstęp między przyciskami
        buttonsLayout.addWidget(viewDatabaseButton)
        buttonsLayout.addSpacing(20)
        buttonsLayout.addWidget(userManualButton)

        # Odstępy, aby wysrodkowac przyciski poziomo
        buttonsLayout.addStretch()

        # Odstępy, aby wysrodkowac przyciski pionowo
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

# Klasa reprezentujaca komponent na scenie z możliwoscia obracania i skalowania
class DraggablePixmapItem(QGraphicsObject):
    positionChanged = pyqtSignal()

    def __init__(self, comp, parent=None):
        super().__init__(parent)
        self.comp = comp
        self.pixmap = QPixmap(comp.icon_path)
        self.setFlags(
            QGraphicsItem.ItemIsMovable |
            QGraphicsItem.ItemIsSelectable |
            QGraphicsItem.ItemSendsGeometryChanges |
            QGraphicsItem.ItemIsFocusable
        )
        self.setAcceptHoverEvents(True)
        self.setAcceptedMouseButtons(Qt.LeftButton | Qt.RightButton)
        self.setCursor(Qt.OpenHandCursor)
        self.setAcceptTouchEvents(True)
        self.rotation_angle = 0
        self.scale_factor = 1.0
        self.setToolTip(f"{comp.name}\n{comp.type}\n{comp.manufacturer}\nKoszt: {comp.cost} zl")
        self.setZValue(1)

        # Inicjalizacja ikonki obrotu
        self.rotate_icon_pixmap = QPixmap('rotate_icon.png').scaled(16, 16, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.rotate_icon_item = RotateIconItem(self)
        self.rotate_icon_item.setPixmap(self.rotate_icon_pixmap)
        self.updateRotateIconPosition()
        self.rotate_icon_item.setFlag(QGraphicsItem.ItemIgnoresTransformations)
        self.rotate_icon_item.setZValue(2)
        self.rotate_icon_item.setOpacity(1)
        self.rotate_icon_item.hide()

        # Uchwyty do zmiany rozmiaru
        self.resize_handles = []
        for position in ['top-left', 'top-right', 'bottom-left', 'bottom-right']:
            handle = ResizeHandleItem(self, position)
            handle.setParentItem(self)
            handle.setZValue(2)
            handle.hide()
            self.resize_handles.append(handle)

        self.updateResizeHandles()

    def boundingRect(self):
        return QRectF(0, 0, self.pixmap.width(), self.pixmap.height())

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.drawPixmap(0, 0, self.pixmap)

    def updateRotateIconPosition(self):
        rect = self.boundingRect()
        offset_x = rect.width() / 2 - self.rotate_icon_pixmap.width() / 2
        offset_y = -self.rotate_icon_pixmap.height() - 5
        self.rotate_icon_item.setPos(offset_x, offset_y)

    def updateResizeHandles(self):
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
                self.rotate_icon_item.show()
                for handle in self.resize_handles:
                    handle.show()
            else:
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
            self.setSelected(True)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        self.positionChanged.emit()

    def contextMenuEvent(self, event):
        menu = QMenu()
        delete_action = QAction("Usuń komponent", menu)
        delete_action.triggered.connect(self.deleteComponent)
        menu.addAction(delete_action)

        add_link_action = QAction("Dodaj lacze", menu)
        add_link_action.triggered.connect(self.addLink)
        menu.addAction(add_link_action)

        menu.exec_(event.screenPos())
        event.accept()

    def addLink(self):
        plan_editor = self.scene().views()[0].parentWindow
        plan_editor.startLinking(self)

    def deleteComponent(self):
        # Usuń powiazane linie
        plan_editor = self.scene().views()[0].parentWindow
        links_to_remove = [link for link in plan_editor.links if self in (link.start_item, link.end_item)]
        for link in links_to_remove:
            plan_editor.scene.removeItem(link)
            plan_editor.links.remove(link)
        self.scene().removeItem(self)

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
        # Inicjujemy tryb laczenia w glównym oknie edytora planu
        plan_editor = self.scene().views()[0].parentWindow
        plan_editor.startLinking(self)

# Klasa uchwytu do zmiany rozmiaru
class ResizeHandleItem(QGraphicsRectItem):
    def __init__(self, parent_item, position):
        size = 8  # Rozmiar uchwytu
        super().__init__(-size/2, -size/2, size, size)
        self.parent_item = parent_item
        self.position = position  # 'top-left', 'top-right', etc.
        self.setBrush(Qt.black)
        self.setPen(QPen(Qt.NoPen))  # Poprawka blędu
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
        # Oblicz nowy wspólczynnik skalowania na podstawie ruchu myszy
        new_pos = event.scenePos()
        delta = new_pos - self.original_pos

        # Wspólrzędne w lokalnym ukladzie wspólrzędnych
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
        super().__init__(parent=parent)
        self.parent_item = parent
        self.setCursor(Qt.SizeAllCursor)
        self.setAcceptedMouseButtons(Qt.LeftButton)
        self.is_rotating = False

    def shape(self):
        # Zwracamy obszar obejmujacy caly prostokat ikony
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

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        super().paint(painter, option, widget)

# Okno edytora planu
class PlanEditorWindow(QMainWindow):
    def __init__(self, planFile):
        super().__init__()
        self.setWindowTitle("Edytor Planu Budynku")
        self.resize(1200, 900)
        self.planFile = planFile
        self.placedComponents = []
        self.target_plan_width = 1200  # Ustawienie docelowej szerokosci planu
        self.plan_scale_factor = 1.0  # Inicjalizacja wspólczynnika skalowania planu
        self.component_scale_factor = 0.5  # Dodatkowy wspólczynnik skalowania komponentów
        self.linking = False
        self.first_component = None
        self.links = []  # Lista przechowujaca informacje o laczach
        self.initUI()

        self.delete_shortcut = QShortcut(QKeySequence(Qt.Key_Delete), self)
        self.delete_shortcut.activated.connect(self.deleteSelectedItems)


    def initUI(self):
        centralWidget = QWidget()
        self.setCentralWidget(centralWidget)

        # Glówny uklad pionowy
        mainLayout = QVBoxLayout()
        centralWidget.setLayout(mainLayout)

        # Tworzymy QSplitter
        splitter = QSplitter(Qt.Horizontal)
        mainLayout.addWidget(splitter)

        # Zamiast QListWidget używamy QTreeWidget
        self.componentTree = QTreeWidget()
        self.componentTree.setHeaderHidden(True)  # Ukrywamy naglówek
        self.componentTree.setIconSize(QSize(50, 50))
        self.componentTree.setDragEnabled(True)
        self.loadComponents()

        self.scene = QGraphicsScene()
        self.view = GraphicsView(self.scene, self)
        self.view.setAcceptDrops(True)

        self.loadPlan()

        # Dodajemy drzewo komponentów i obszar roboczy do QSplitter
        splitter.addWidget(self.componentTree)
        splitter.addWidget(self.view)

        # Ustawiamy minimalne szerokosci
        self.componentTree.setMinimumWidth(200)
        self.view.setMinimumWidth(400)

        # Ustawiamy proporcje poczatkowe
        total_width = self.width()
        splitter.setSizes([int(total_width * 0.33), int(total_width * 0.66)])

        # Przyciski akcji
        buttonLayout = QHBoxLayout()
        mainLayout.addLayout(buttonLayout)

        # Odstęp, aby przyciski byly wyrównane do prawej
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

                # Ustawienie wysokiej rozdzielczości renderowania
                zoom_x = zoom_y = 3.0  # Możesz dostosować ten współczynnik
                mat = fitz.Matrix(zoom_x, zoom_y)
                pix = page.get_pixmap(matrix=mat)

                image_bytes = pix.tobytes("png")
                pixmap = QPixmap()
                pixmap.loadFromData(image_bytes)
            except Exception as e:
                QMessageBox.critical(self, "Błąd", f"Nie można wczytać pliku PDF: {e}")
                return
        else:
            # Wczytanie obrazu bez skalowania
            pixmap = QPixmap(self.planFile)

        # Ustawienie tła sceny na plan budynku
        self.scene.setBackgroundBrush(QBrush(pixmap))

        # Ustawienie rozmiaru sceny na rozmiar planu budynku
        self.scene.setSceneRect(QRectF(pixmap.rect()))

    def scalePixmap(self, pixmap, target_width):
        # Obliczenie wspólczynnika skalowania
        original_width = pixmap.width()
        original_height = pixmap.height()
        scale_factor = target_width / original_width
        new_width = int(original_width * scale_factor)
        new_height = int(original_height * scale_factor)
        # Skalowanie pixmapy
        scaled_pixmap = pixmap.scaled(new_width, new_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        return scaled_pixmap, scale_factor

    def loadComponents(self):
        # Pobieramy wszystkie komponenty z bazy danych
        components = session.query(Component).all()

        # Tworzymy slownik kategorii
        categories = {}
        for comp in components:
            if comp.type not in categories:
                # Tworzymy nowy element kategorii
                categoryItem = QTreeWidgetItem([comp.type])
                categoryItem.setFlags(categoryItem.flags() & ~Qt.ItemIsDragEnabled)  # Wylaczamy przeciaganie dla kategorii
                self.componentTree.addTopLevelItem(categoryItem)
                categories[comp.type] = categoryItem

        # Dodajemy komponenty do odpowiednich kategorii
        for comp in components:
            item = QTreeWidgetItem([comp.name])
            item.setData(0, Qt.UserRole, comp)
            icon = QIcon(comp.icon_path)
            item.setIcon(0, icon)
            categories[comp.type].addChild(item)

    def deleteSelectedItems(self):
        for item in self.scene.selectedItems():
            if isinstance(item, ConnectionLine):
                item.deleteLink()
            elif isinstance(item, DraggablePixmapItem):
                item.deleteComponent()
    
    def startLinking(self, component):
        self.linking = True
        self.first_component = component
        self.view.setCursor(Qt.CrossCursor)  # Zmieniamy kursor, aby wskazac tryb laczenia

    def finishLinking(self, second_component):
        if self.first_component and second_component and self.first_component != second_component:
            # Tworzymy linię między komponentami
            link = ConnectionLine(self.first_component, second_component)
            self.scene.addItem(link)
            self.links.append(link)  # Dodajemy link do listy
        self.linking = False
        self.first_component = None
        self.view.setCursor(Qt.ArrowCursor)  # Przywracamy domyslny kursor

    def calculateCableLengths(self):
        total_length_pixels = 0
        for link in self.links:
            start_point = link.start_item.sceneBoundingRect().center()
            end_point = link.end_item.sceneBoundingRect().center()
            length = QLineF(start_point, end_point).length()
            total_length_pixels += length
        # Przeliczenie pikseli na metry
        # Zalóżmy skalę: 1 piksel = 0.05 metra (musisz dostosowac to do rzeczywistej skali planu)
        total_length_meters = total_length_pixels * 0.05
        # Zalóżmy koszt kabla: 2 zl za metr (dostosuj wedlug potrzeb)
        cable_cost_per_meter = 2
        total_cable_cost = total_length_meters * cable_cost_per_meter
        return total_length_meters, total_cable_cost

    def saveProject(self):
        fileName, _ = QFileDialog.getSaveFileName(
            self, "Zapisz Projekt", "", "PNG Files (*.png)")
        if fileName:
            # Dopasuj rozmiar obrazu do zawartosci sceny
            rect = self.scene.itemsBoundingRect()
            image = QImage(rect.size().toSize(), QImage.Format_ARGB32)
            image.fill(Qt.white)
            painter = QPainter(image)
            self.scene.render(painter, target=QRectF(image.rect()), source=rect)
            painter.end()
            image.save(fileName)
            QMessageBox.information(
                self, "Zapisano", "Projekt zostal zapisany.")

    def generateReport(self):
        if not self.placedComponents:
            QMessageBox.warning(self, "Brak danych", "Nie dodano żadnych komponentów do planu.")
            return

        fileName, _ = QFileDialog.getSaveFileName(
            self, "Zapisz Raport", "", "PDF Files (*.pdf)")
        if fileName:
            try:
                # Ustawienia dokumentu
                doc = SimpleDocTemplate(
                    fileName,
                    pagesize=letter,
                    rightMargin=50,
                    leftMargin=50,
                    topMargin=50,
                    bottomMargin=50
                )
                Story = []

                styles = getSampleStyleSheet()
                styles.add(ParagraphStyle(name='Justify', alignment=1))

                # Dodajemy styl dla komórek tabeli
                styles.add(ParagraphStyle(
                    name='TableCell',
                    fontName='Helvetica',
                    fontSize=10,
                    leading=12,
                    alignment=0,  # Wyrównanie do lewej
                    spaceAfter=0,
                ))

                # Tytuł raportu
                Story.append(Paragraph("Raport z projektu sieci teleinformatycznej", styles['Title']))
                Story.append(Spacer(1, 12))

                # Nazwa projektu
                Story.append(Paragraph(f"Nazwa projektu: {os.path.basename(self.planFile)}", styles['Normal']))
                Story.append(Spacer(1, 12))

                # Data wygenerowania raportu
                current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                Story.append(Paragraph(f"Data wygenerowania raportu: {current_datetime}", styles['Normal']))
                Story.append(Spacer(1, 12))

                # Dodanie obrazu projektu
                # Renderowanie sceny do obrazu
                rect = self.scene.sceneRect()  # Zmienione z itemsBoundingRect() na sceneRect()
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
                image_stream = BytesIO(image_data)
                report_image = Image(image_stream)
                report_image._restrictSize(doc.width, doc.height / 1.5)  # Dostosuj wysokość obrazu w raporcie

                Story.append(report_image)
                Story.append(Spacer(1, 12))

                # Grupowanie komponentów
                component_counts = Counter()
                total_cost = 0

                for comp in self.placedComponents:
                    component_counts[comp.name] += 1
                    total_cost += comp.cost

                # Sekcja "Użyte komponenty"
                Story.append(Paragraph("Uzyte komponenty:", styles['Heading2']))
                Story.append(Spacer(1, 12))

                # Przygotowanie danych do tabeli
                data = [
                    [
                        Paragraph('Nazwa', styles['TableCell']),
                        Paragraph('Producent', styles['TableCell']),
                        Paragraph('Typ', styles['TableCell']),
                        'Ilosc',
                        'Cena jedn.',
                        'Łaczny koszt'
                    ]
                ]
                total_components_cost = 0

                for comp_name, count in component_counts.items():
                    comp = session.query(Component).filter_by(name=comp_name).first()
                    line_total_cost = comp.cost * count
                    data.append([
                        Paragraph(comp_name, styles['TableCell']),
                        Paragraph(comp.manufacturer, styles['TableCell']),
                        Paragraph(comp.type, styles['TableCell']),
                        str(count),
                        f"{comp.cost} zl",
                        f"{line_total_cost} zl"
                    ])
                    total_components_cost += line_total_cost

                # Definiujemy szerokości kolumn
                col_widths = [
                    doc.width * 0.25,  # 25% szerokości dla Nazwy
                    doc.width * 0.15,  # 15% dla Producenta
                    doc.width * 0.15,  # 15% dla Typu
                    doc.width * 0.1,   # 10% dla Ilości
                    doc.width * 0.15,  # 15% dla Cena jedn.
                    doc.width * 0.2    # 20% dla Łączny koszt
                ]

                # Styl tabeli
                table_style = TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),  # Wyrównanie do lewej
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 12),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ])

                component_table = Table(data, colWidths=col_widths, repeatRows=1)
                component_table.setStyle(table_style)
                Story.append(component_table)
                Story.append(Spacer(1, 12))

                # Koszty
                labor_cost = total_components_cost * 0.2
                total_length_meters, total_cable_cost = self.calculateCableLengths()
                total_project_cost = total_components_cost + labor_cost + total_cable_cost

                # Sekcja podsumowania kosztów
                Story.append(Paragraph("Podsumowanie kosztow:", styles['Heading2']))
                Story.append(Spacer(1, 12))

                costs_data = [
                    ['Pozycja', 'Koszt'],
                    ['Laczny koszt komponentow', f"{total_components_cost:.2f} zl"],
                    ['Koszt wykonania pracy (20%)', f"{labor_cost:.2f} zl"],
                    [f"Koszt kabli ({total_length_meters:.2f} m)", f"{total_cable_cost:.2f} zl"],
                    ['Laczny koszt projektu', f"{total_project_cost:.2f} zl"],
                ]

                costs_table = Table(costs_data, colWidths=[doc.width / 2.0] * 2)
                costs_table_style = TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),  # Wyrównanie do lewej
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 12),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ])
                costs_table.setStyle(costs_table_style)
                Story.append(costs_table)
                Story.append(Spacer(1, 12))

                # Zapis dokumentu
                doc.build(Story)
                QMessageBox.information(self, "Raport zapisany", "Raport został pomyślnie zapisany.")
            except Exception as e:
                QMessageBox.critical(self, "Błąd", f"Wystąpił błąd podczas generowania raportu: {e}")




# Niestandardowy QGraphicsView do obslugi przeciagania i upuszczania
class GraphicsView(QGraphicsView):
    def __init__(self, scene, parent=None):
        super().__init__(scene)
        self.setParent(parent)
        self.setRenderHint(QPainter.Antialiasing)
        self._pan = False
        self._panStartX = 0
        self._panStartY = 0
        self.setDragMode(QGraphicsView.NoDrag)
        self.setInteractive(True)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.parentWindow = parent  # Reference to PlanEditorWindow

    def mousePressEvent(self, event):
        if self.parentWindow.linking:
            item = self.itemAt(event.pos())
            if isinstance(item, DraggablePixmapItem):
                self.parentWindow.finishLinking(item)
                event.accept()
            else:
                # Kliknięto w miejsce bez komponentu
                self.parentWindow.linking = False
                self.parentWindow.first_component = None
                self.setCursor(Qt.ArrowCursor)
                event.accept()
        elif event.button() == Qt.LeftButton:
            item = self.itemAt(event.pos())
            if item is None:
                # Rozpocznij przesuwanie widoku
                self._pan = True
                self._panStartX = event.x()
                self._panStartY = event.y()
                self.setCursor(Qt.ClosedHandCursor)
                event.accept()
            else:
                super().mousePressEvent(event)
        else:
            super().mousePressEvent(event)

    # Upewnij się, że nie nadpisujemy innych zdarzeń, które moga blokowac menu kontekstowe

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
            self._pan = False
            self.setCursor(Qt.ArrowCursor)
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
                comp = None
                for i in range(mapItems):
                    role = stream.readInt32()
                    value = stream.readQVariant()
                    if role == Qt.UserRole:
                        comp = value
                if comp:
                    self.addComponentToScene(comp, event.pos())
            event.accept()
        else:
            event.ignore()

    def addComponentToScene(self, comp, position):
        item = DraggablePixmapItem(comp)
        # Skalowanie komponentu z uwzględnieniem dodatkowego wspólczynnika
        if self.parentWindow and hasattr(self.parentWindow, 'component_scale_factor'):
            total_scale = self.parentWindow.component_scale_factor
            item.setScale(total_scale)
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
                type=dialog.typeComboBox.currentText(),
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
                comp.type = dialog.typeComboBox.currentText()
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
                f"Czy na pewno usunac komponent {comp.name}?",
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
        self.resize(400, 500)
        self.component = component
        self.iconPath = ""
        self.initUI()
        if component:
            self.loadComponentData()

    def initUI(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        formLayout = QFormLayout()
        layout.addLayout(formLayout)

        self.nameEdit = QLineEdit()
        self.manufacturerEdit = QLineEdit()
        self.costEdit = QLineEdit()

        # Zmieniamy pole typu na QComboBox
        self.typeComboBox = QComboBox()
        self.typeComboBox.addItems(component_types)

        # Zmieniamy wybór ikony na QListWidget
        self.iconListWidget = QListWidget()
        self.iconListWidget.setIconSize(QSize(64, 64))
        self.iconListWidget.setViewMode(QListWidget.IconMode)
        self.iconListWidget.setSelectionMode(QListWidget.SingleSelection)
        self.loadIcons()

        formLayout.addRow("Nazwa:", self.nameEdit)
        formLayout.addRow("Producent:", self.manufacturerEdit)
        formLayout.addRow("Koszt:", self.costEdit)
        formLayout.addRow("Typ:", self.typeComboBox)
        formLayout.addRow("Ikona:", self.iconListWidget)

        buttonBox = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        layout.addWidget(buttonBox)

    def loadIcons(self):
        icons_dir = 'icons/'
        if not os.path.exists(icons_dir):
            QMessageBox.critical(self, "Blad", f"Folder z ikonami '{icons_dir}' nie istnieje.")
            return

        for filename in os.listdir(icons_dir):
            if filename.lower().endswith(('.png', '.jpg', '.bmp')):
                full_path = os.path.join(icons_dir, filename)
                icon = QIcon(full_path)
                item = QListWidgetItem(icon, filename)
                item.setData(Qt.UserRole, full_path)
                self.iconListWidget.addItem(item)

    def loadComponentData(self):
        self.nameEdit.setText(self.component.name)
        self.manufacturerEdit.setText(self.component.manufacturer)
        self.costEdit.setText(str(self.component.cost))

        # Ustawiamy wartosc w typeComboBox
        index = self.typeComboBox.findText(self.component.type)
        if index >= 0:
            self.typeComboBox.setCurrentIndex(index)

        # Ustawiamy zaznaczenie w iconListWidget
        for i in range(self.iconListWidget.count()):
            item = self.iconListWidget.item(i)
            if item.data(Qt.UserRole) == self.component.icon_path:
                item.setSelected(True)
                self.iconListWidget.scrollToItem(item)
                break

    def accept(self):
        # Sprawdzamy, czy wszystkie pola sa wypelnione
        if not self.nameEdit.text() or not self.manufacturerEdit.text() or not self.costEdit.text():
            QMessageBox.warning(self, "Blad", "Proszę wypelnic wszystkie pola.")
            return

        # Pobieramy wybrana ikonę
        selected_items = self.iconListWidget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Blad", "Proszę wybrac ikonę.")
            return
        self.iconPath = selected_items[0].data(Qt.UserRole)

        super().accept()

class ConnectionLine(QGraphicsLineItem):
    def __init__(self, start_item, end_item):
        super().__init__()
        self.start_item = start_item
        self.end_item = end_item
        self.setZValue(0.5)  # Ustawiamy zValue między planem a komponentami
        pen = QPen(Qt.black, 1, Qt.DashLine)
        self.setPen(pen)
        self.updatePosition()
        self.setAcceptHoverEvents(True)  # Umożliwiamy obslugę zdarzeń najechania


        # Polacz sygnaly zmiany pozycji z metoda aktualizacji
        self.start_item.positionChanged.connect(self.updatePosition)
        self.end_item.positionChanged.connect(self.updatePosition)

        # Ustawiamy flagi, aby linia mogla odbierac zdarzenia myszy
        self.setFlags(QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsFocusable)
        self.setAcceptHoverEvents(True)

    def shape(self):
        path = QPainterPath()
        pen_width = self.pen().width() + 6  # Dodajemy dodatkowy margines do szerokosci pióra
        path.moveTo(self.line().p1())
        path.lineTo(self.line().p2())
        path_stroker = QPainterPathStroker()
        path_stroker.setWidth(pen_width)
        stroked_path = path_stroker.createStroke(path)
        return stroked_path

    def updatePosition(self):
        start_point = self.start_item.sceneBoundingRect().center()
        end_point = self.end_item.sceneBoundingRect().center()
        self.setLine(QLineF(start_point, end_point))

    # Dodajemy metody obslugi zdarzeń myszy
    def contextMenuEvent(self, event):
        menu = QMenu()
        delete_action = QAction("Usuń lacze", menu)
        delete_action.triggered.connect(self.deleteLink)
        menu.addAction(delete_action)
        menu.exec_(event.screenPos())
        event.accept()

    def deleteLink(self):
        # Usuń lacze z sceny i z listy w PlanEditorWindow
        plan_editor = self.scene().views()[0].parentWindow
        if self in plan_editor.links:
            plan_editor.links.remove(self)
        self.scene().removeItem(self)

    def hoverEnterEvent(self, event):
        pen = self.pen()
        pen.setColor(Qt.red)  # Zmieniamy kolor na czerwony
        self.setPen(pen)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        pen = self.pen()
        pen.setColor(Qt.black)  # Przywracamy oryginalny kolor
        self.setPen(pen)
        super().hoverLeaveEvent(event)

# Okno instrukcji obslugi
class UserManualWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Instrukcja Obslugi")
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
            self.textEdit.setPlainText("Brak pliku z instrukcja obslugi.")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
