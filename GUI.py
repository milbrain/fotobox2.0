#!/usr/bin/python3
# -*- coding: utf-8 -*-
import logging, qrcode, os.path, math

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtGui import QImage
from PyQt5.QtWidgets import QLabel, QFrame
from PyQt5.QtCore import QRect, QPoint, QDir#, pyqtSignal
from PyQt5.Qt import *


class GUI(QMainWindow):
    
    log = logging.getLogger(__name__)   # the logger
    
    qrFilepath      = 'res/qr/'
    imageFilepath   = 'res/img/'
    previewFilepath = 'res/preview/'
    
    formSize = QPoint(1000,700)                # main form
    
    previewImageSize = QPoint(165, 165)
    totalPreviewImages = 5
    
    currentBigImage = 6                 # ImageNr from current bigImage
    bigImageSize    = None              # is only set after the first call to _setupBigImage
    
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
        self.grabKeyboard()     # grabs all keyboard inputs to be handled for scrolling through preview images
        
    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Left:
            self.scrollLeft()
        elif event.key() == QtCore.Qt.Key_Right:
            self.scrollRight()
            
        
    def scrollLeft(self):
        newImgNr = self.currentBigImage - 1
        
        # bigPreviewImage
        if newImgNr <= 0 or not self.loadBigImage(newImgNr, self.bigImageSize.x(), self.bigImageSize.y()):
            return
        
        # QR-Code
        self.generateOrLoadQR(newImgNr)
        
        # set new Image Number because everything worked out
        self.currentBigImage = newImgNr
        
        # Realign small preview images (if neccessary
        imgDir = QDir(self.imageFilepath)
        existingImages = imgDir.count() - 2
        if (newImgNr < math.ceil(self.totalPreviewImages/2) or
            existingImages <= self.totalPreviewImages):
            return
        
        for i in range(self.totalPreviewImages-1, 0,-1):
            pixmap = self.preLabels[i-1][0].pixmap()
            print('Assigning pixmap from ', i-1, ' to ', i)
            if pixmap:
                self.preLabels[i][0].setPixmap(pixmap)

        pixmap = self.generatePreviewImage(newImgNr - math.floor(self.totalPreviewImages/2))
        if pixmap:
            self.preLabels[0][0].setPixmap(pixmap)
        
        print('scrolledLeft')

    def scrollRight(self):
        #TODO: Adjust scrolling to fit the initially loaded view
        newImgNr = self.currentBigImage + 1
        
        # bigPreviewImage
        if newImgNr <= 0 or not self.loadBigImage(newImgNr, self.bigImageSize.x(), self.bigImageSize.y()):
            return
        
        # QR-Code
        self.generateOrLoadQR(newImgNr)
        
        # set new Image Number because everything worked out
        self.currentBigImage = newImgNr
        
        # Realign small preview images (if neccessary
        imgDir = QDir(self.imageFilepath)
        existingImages = imgDir.count() - 2
        if (newImgNr > (existingImages - math.floor(self.totalPreviewImages/2)) or
            existingImages <= self.totalPreviewImages):
            return
        
        for i in range(0,self.totalPreviewImages-1, 1):
            pixmap = self.preLabels[i+1][0].pixmap()
            print('Assigning pixmap from ', i+1, ' to ', i)
            if pixmap:
                self.preLabels[i][0].setPixmap(pixmap)

        pixmap = self.generatePreviewImage(newImgNr + math.floor(self.totalPreviewImages/2))
        if pixmap:
            self.preLabels[self.totalPreviewImages-1][0].setPixmap(pixmap)
        else:
            #TODO: Set clear pixmap
            #self.preLabels[self.totalPreviewImages-1][0]
            pass
        
        print('scrolledRight')
        
    def _setupBigImage(self):
        bigWidth = self.formSize.x() - 165 - 10 - 20 # qrWidth, border, inBetweenSpace
        bigHeight = self.formSize.y() - self.previewImageSize.y() - 10 - 20
        self.bigImageSize = QPoint(bigWidth, bigHeight)
        
        size = QRect(10, 10, bigWidth, bigHeight)
        self.bigLabel = QLabel(self)
        self.bigLabel.setGeometry(size)
        self.bigLabel.setAlignment(Qt.AlignCenter | Qt.AlignVCenter)
        self.bigLabel.show()
        self.loadBigImage(self.currentBigImage, bigWidth, bigHeight)
        
        
    def loadBigImage(self, imgNr, w, h):
        ''' Loads the big preview label with the existing image referenced by imgNr. '''
        # If permance is too low, change QtSmoothTransformation
        filepath = self.imageFilepath + 'P' + str(imgNr) + '.jpg'
        if not os.path.isfile(filepath):
            return False
        
        img = QImage(filepath)
        pixmap = QtGui.QPixmap.fromImage(img.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.bigLabel.setPixmap(pixmap)
        return True
        
        
    def _setupPreviewImages(self):
        ''' Generates all preview images in the form. '''
        formWidth = self.formSize.x()
        formHeigth = self.formSize.y()
        preWidth = self.previewImageSize.x()
        preHeight = self.previewImageSize.y()
        existingImages = 0
        
        imgDir = QDir(self.imageFilepath)
        existingImages = imgDir.count() - 2
        
        self.preLabels = []
        inBetweenSpace = (formWidth - 20 - preWidth*self.totalPreviewImages) / (self.totalPreviewImages-1)
        
        imgToGenerate = self.currentBigImage - math.floor(self.totalPreviewImages/2)
        if imgToGenerate < 1:
            imgToGenerate = 1
        for i in range(0,self.totalPreviewImages,1):
            size = QRect(10 + i*preWidth + inBetweenSpace*i, formHeigth - preHeight - 10,
                         preWidth, preHeight)
            self.preLabels.append((QtWidgets.QLabel(self), i+1))
            self.preLabels[i][0].setGeometry(size)
            self.preLabels[i][0].setAlignment(Qt.AlignCenter)
            
            pixmap = self.generatePreviewImage(imgToGenerate)
            if pixmap:
                self.preLabels[i][0].setPixmap(pixmap)
            
            self.preLabels[i][0].show()
            imgToGenerate += 1
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
        filepath = self.qrFilepath + 'Q' + str(imgNr) + '.png'
        if not os.path.isfile(filepath):
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=5,
                border=2,
            )   # with these options => size = 165px x 165px
            qrstring = "http://" + self.controls.dnsString + "/?getImageNr=" + str(imgNr)
            qr.add_data(qrstring)
            qr.make(fit=True)
            img = qr.make_image()
            img.save(filepath)
        
        pixmap = QtGui.QPixmap(filepath)
        self.qrlabel.setPixmap(pixmap)
                

    def setupSignals(self):
        pass