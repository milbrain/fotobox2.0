#!/usr/bin/python3
# -*- coding: utf-8 -*-
import logging, qrcode, os.path

from PyQt5 import QtCore, QtGui, QtWidgets, QtSvg
from PyQt5.QtGui import QPainter, QColor, QBrush, QFont, QImage
from PyQt5.QtWidgets import QWidget, QApplication, QMainWindow, QInputDialog, QMessageBox
from PyQt5.QtWidgets import QPushButton, QComboBox, QGroupBox, QLabel, QFrame
from PyQt5.QtWidgets import QGraphicsItem, QGraphicsScene, QGraphicsView
from PyQt5.QtSvg import QGraphicsSvgItem, QSvgWidget
from PyQt5.QtCore import QRect, QPoint, QRectF, QDir
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.Qt import *

from qrcode.image.pure import PymagingImage
from png import *
import pymaging
from pymaging import *

from enum import Enum

class GUI(QMainWindow):
    
    log = logging.getLogger(__name__)   # the logger
    
    qrFilepath = 'res/qr/'
    imageFilepath = 'res/img/'
    previewFilepath = 'res/preview/'
    
    formSize = QPoint(1000,700)                # main form
    previewImageSize = QPoint(165, 165)
    
    currentBigImage = 2                 # ImageNr from current bigImage
    
    def __init__(self, cont):
        super().__init__()
        self.controls = cont          
        self.initUI()
        self.setupSignals()


    def initUI(self):
        ''' Inits all the UI elements on the main form . '''
        # Params start 
        canvasSize = QPoint(100,100)        # canvas to draw on
        # Params end 
        
        # Main Window
        self.resize(self.formSize.x(), self.formSize.y())
        self.setGeometry(QtWidgets.QStyle.alignedRect(QtCore.Qt.LeftToRight, QtCore.Qt.AlignCenter,
                                                      self.size(), QApplication.desktop().availableGeometry()))
        self.setWindowTitle('Fotobox v2.0')
        self.show()
        
        self._setupPreviewImages()
        self._setupBigImage()
        self._setupQRCode()
        
        
    def _setupBigImage(self):
        bigWidth = self.formSize.x() - 165 - 10 - 20 # qrWidth, border, inBetweenSpace
        bigHeight = self.formSize.y() - self.previewImageSize.y() - 10 - 20
        
        size = QRect(10, 10, bigWidth, bigHeight)
        self.bigLabel = QLabel(self)
        self.bigLabel.setGeometry(size)
        self.bigLabel.setAlignment(Qt.AlignCenter | Qt.AlignVCenter)
        self.bigLabel.show()
        print(self.loadBigImage(self.currentBigImage, bigWidth, bigHeight))
        
        
    def loadBigImage(self, imgNr, w, h):
        # If permance is too low, change QtSmoothTransformation
        filepath = self.imageFilepath + 'P' + str(imgNr) + '.jpg'
        if not os.path.isfile(filepath):
            return False
        
        img = QImage(filepath)
        pixmap = QtGui.QPixmap.fromImage(img.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.bigLabel.setPixmap(pixmap)
        return True
        
        
    def _setupPreviewImages(self):
        formWidth = self.formSize.x()
        formHeigth = self.formSize.y()
        preWidth = self.previewImageSize.x()
        preHeight = self.previewImageSize.y()
        existingImages = 0
        totalPreviewImages = 5
        
        imgDir = QDir(self.imageFilepath)
        existingImages = imgDir.count() - 2
        
        self.preLabels = []
        inBetweenSpace = (formWidth - 20 - preWidth*totalPreviewImages) / (totalPreviewImages-1)
        
        for i in range(0,totalPreviewImages,1):
            size = QRect(10 + i*preWidth + inBetweenSpace*i, formHeigth - preHeight - 10,
                         preWidth, preHeight)
            self.preLabels.append((QtWidgets.QLabel(self), i+1))
            self.preLabels[i][0].setGeometry(size)
            self.preLabels[i][0].setAlignment(Qt.AlignCenter)
            
            pixmap = self.generatePreviewImage(i+1)
            if not pixmap:
                break
            
            self.preLabels[i][0].setPixmap(pixmap)
            self.preLabels[i][0].show()
        #self.preLabels[0][0].setLineWidth(1)
        #self.preLabels[0][0].setFrameShape(QFrame.Panel)
        
        
    def generatePreviewImage(self, imgNr):
        ''' Generates the preview Image according to the parameter imgNr. Returns the generated pixmap or False
        if the generation failed'''
        prePath = self.previewFilepath + 'p' + str(imgNr) + '.jpg'
        fullImgPath = self.imageFilepath + 'P' + str(imgNr) + '.jpg'
        if not os.path.isfile(fullImgPath):
            return False
        if os.path.isfile(prePath):
            pixmap = QtGui.QPixmap(prePath)
            return pixmap
        
        img = QImage(fullImgPath)
        pixmap = QtGui.QPixmap.fromImage(img.scaled(self.previewImageSize.x(), self.previewImageSize.y(),
                                                    Qt.KeepAspectRatio, Qt.SmoothTransformation))
        pixmap.save(prePath)
        return pixmap
        
    
    def _setupQRCode(self):
        ''' Create the label to show the QR Code for and load the first QR-Code (if at least
        one image exists in the image folder already). '''
        # Label for display of QR code
        qrSize = QPoint(165,165)
        size = QRect(self.formSize.x() - qrSize.x() - 10, 10, qrSize.x(), qrSize.y())
        self.qrlabel = QtWidgets.QLabel(self)
        self.qrlabel.setGeometry(size)
        
        self.generateOrLoadQR(self.currentBigImage)
        self.qrlabel.show()
        
    
    def generateOrLoadQR(self, imgNr):
        ''' Loads an existing QR-Code into the UI or generates the QR Code first and
        loads it afterwards. Parameter denotes the image number to load the QR code for.'''
        # https://ourcodeworld.com/articles/read/554/how-to-create-a-qr-code-image-or-svg-in-python
        print('start')
        filepath = self.qrFilepath + 'Q' + str(imgNr) + '.png'
        if not os.path.isfile(filepath):
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=5,
                border=2,
            )   # with these options => size = 165px x 165px
            qr.add_data(r"http://127.0.0.1:8000/?getImageNr="+str(imgNr))
            qr.make(fit=True)
            img = qr.make_image()
            img.save(filepath)
        
        pixmap = QtGui.QPixmap(filepath)
        self.qrlabel.setPixmap(pixmap)
                

    def setupSignals(self):
        pass