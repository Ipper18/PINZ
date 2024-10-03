import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QGraphicsView, QGraphicsScene
from PIL import Image
import matplotlib.pyplot as plt
import numpy as np
import cv2 as cv
import sqlite3
import sqlalchemy
import pickle
import json
import ezdxf
import logging
import pytest
from threading import Thread


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("System Wspomagający Projektowanie Sieci Teleinformatycznych")
        self.resize(600, 600)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
