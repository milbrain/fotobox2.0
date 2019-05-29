#!/usr/bin/python3
# -*- coding: utf-8 -*-
import logging, qrcode, os.path, math, lorem, time, threading

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtGui import QImage
from PyQt5.QtWidgets import QLabel, QFrame
from PyQt5.QtCore import QRect, QPoint, QDir, pyqtSignal
from PyQt5.Qt import *

import RPi.GPIO as GPIO
from picamera import PiCamera
import picamera
from gpiozero import Button

class Record:
    pass

# TODO:
'''
- Farbe der Schrift ändern, sodass gute Sichtbarkeit
- Fotoauflösung so hoch wie möglich
- WiFi aufmachen und DNS hinpfuschen
- Akutalisieren der neuen Bilder (leer setzen der beiden neuen beim reload)
- Verstehen warum bei ScrollRight der eine Fall abgefangen wird (das Fill(0,0,0,0)) und der andere
  zu dem -1 -1 führt
'''

class GUI(QMainWindow):

    log = logging.getLogger(__name__)   # the logger

    qrFilepath      = 'res/qr/'
    imageFilepath   = 'res/img/'
    previewFilepath = 'res/preview/'

    formSize = QPoint(1000,700)         # main form

    previewImageSize = QPoint(165, 165)
    totalPreviewImages = 5

    bigImageSize    = None              # is only set after the first call to _setupBigImage

    bigLabel        = None              # Record with reference to a QLabel and the ImageNr currently stored there
                                        # only available after _setupBigImage
    preLabels       = []                # List of tuples of the same form as bigLabel, just for the preview labels
                                        # only available after _setupPreviewImages
    
    #pyQtSignal(str)

    def __init__(self, cont):
        super().__init__()
        self.controls = cont
        self.initUI()
        self.setupSignals()

    def setupSignals(self):
        GPIO.setmode(GPIO.BCM)
        self.gpioPhoto = 17
        self.gpioR = 27
        self.gpioL = 22
        bounceTBig = 8000
        bounceT = 1000
        
        # Kamera
        self.camera = PiCamera()
        self.previewRes = (1280, 1020)
        self.fotoRes = (2800, 2100) #(3200, 2400)
        self.camera.annotate_text_size = 150
        self.camera.framerate = 15
        self.camera.rotation = 0
        self.camLock = threading.Lock()
        self.imgCount = QDir(self.imageFilepath).count() - 2
        #print('total: %d' % (self.imgCount))
        
        # Fototaster
        GPIO.setup(self.gpioPhoto, GPIO.IN)
        GPIO.add_event_detect(self.gpioPhoto, GPIO.RISING, callback=self.doPhoto, bouncetime=bounceTBig)
        
        # Links-Rechts Schalter
        GPIO.setup(self.gpioR, GPIO.IN)
        GPIO.add_event_detect(self.gpioR, GPIO.RISING, callback=self.scrollRight, bouncetime=bounceT)
        GPIO.setup(self.gpioL, GPIO.IN)
        GPIO.add_event_detect(self.gpioL, GPIO.RISING, callback=self.scrollLeft, bouncetime=bounceT)

    def doPhoto(self, event):
        if self.camLock.acquire(blocking=False):
            self.camera.resolution = self.previewRes
            #self.annotate_background = picamera.color.Color('#000')
            #self.annotate_foreground = picamera.color.Color('#000')
            self.camera.start_preview(fullscreen=True)
            
            self.camera.annotate_text = '3'
            time.sleep(1)
            self.camera.annotate_text = '2'
            time.sleep(1)
            self.camera.annotate_text = '1'
            time.sleep(1)
            self.camera.annotate_text = ''
            #self.annotate_background = None
            self.camera.stop_preview()
            self.camera.resolution = self.fotoRes
            
            self.imgCount = self.imgCount + 1
            self.camera.capture(self.imageFilepath + 'P' + str(self.imgCount) + '.jpg')
            
            print("Foto gemacht: Nr. %d" % (self.imgCount))

            self.camLock.release()
            self.generatePreviewImage(self.imgCount)
            print('aktuelles großes bild (vor dem scrollRight) ist gerade: ' + str(self.bigLabel.imageNr))
            
            self.ReloadAllPreviews()
            #self.scrollRight('hier könnte ihre werbung stehen')
            
        else:
            return

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

        self._setupBigImage()
        self._setupPreviewImages()
        self._setupQRCode()
        self._setupExplanation()

        self.grabKeyboard()     # grabs all keyboard inputs to be handled for scrolling through preview images

    def _setupExplanation(self):
        ''' Sets up the HOWTO connect to the Pi to download a picture via QR code. '''
        expSize = QPoint(165,250)
        size = QRect(self.qrlabel.pos().x(), self.qrlabel.pos().y() + self.qrlabel.size().height() + 10 , expSize.x(), expSize.y())
        self.explabel = QtWidgets.QLabel(self)
        self.explabel.setGeometry(size)
        self.explabel.setAlignment(Qt.AlignJustify)
        self.explabel.setWordWrap(True)
        asdf = lorem.paragraph()
        self.explabel.setText("passwd: catchfoto \n" + asdf)


        self.explabel.show()

    def keyPressEvent(self, event):
        #if event.key() == QtCore.Qt.Key_Left:
        #    self.scrollLeft()
        #elif event.key() == QtCore.Qt.Key_Right:
        #    self.scrollRight(1)
        if GPIO.event_detected(17):
            print('Picture-Button pressed!')
        if GPIO.event_detected(27):
            print('Right-Scroll-Button pressed!')
        if GPIO.event_detected(22):
            print('Left-Scroll-Button pressed!')

    def _setupPreviewImages(self):
        ''' Loads all preview images into the form. '''
        formWidth = self.formSize.x()
        formHeigth = self.formSize.y()
        preWidth = self.previewImageSize.x()
        preHeight = self.previewImageSize.y()
        existingImages = 0

        imgDir = QDir(self.previewFilepath)
        existingImages = imgDir.count() - 2

        self.preLabels = []
        inBetweenSpace = (formWidth - 20 - preWidth*self.totalPreviewImages) / (self.totalPreviewImages-1)

        # Which image should be loaded first starting from left to right?
        imgToGenerate = existingImages - math.floor(self.totalPreviewImages/2)
        if imgToGenerate < 1:
            # Only few images exist in preview folder (in standard configuration: 2 or less)
            # We work with what we've got
            imgToGenerate = 1

        for i in range(0,self.totalPreviewImages,1):
            # Create as many labels as requested in totalPreviewImages
            size = QRect(10 + i*preWidth + inBetweenSpace*i, formHeigth - preHeight - 10,
                         preWidth, preHeight)

            preview = Record()
            preview.label = QtWidgets.QLabel(self)
            preview.imageNr = 0

            self.preLabels.append(preview)
            self.preLabels[i].label.setGeometry(size)
            self.preLabels[i].label.setAlignment(Qt.AlignCenter)
            self.preLabels[i].label.setFrameShape(QFrame.NoFrame)
            self.preLabels[i].label.setLineWidth(0)

            # Iteratively try to generate the next picture
            pixmap = self.generatePreviewImage(imgToGenerate)
            if pixmap:
                self.preLabels[i].label.setPixmap(pixmap)
                self.preLabels[i].imageNr = imgToGenerate
            else:
                # No more pictures left to load
                self.preLabels[i].imageNr = 0

            self.preLabels[i].label.show()
            imgToGenerate += 1

        self._highlightActivePreview()

        # === DEBUG ===
        pstr = ""
        for i in range(len(self.preLabels)):
            pstr += str(self.preLabels[i].imageNr) + " "
        print("Setting up preview finished. Position is: " + pstr)

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

    def _setupBigImage(self):
        ''' Load newest picture into the bigLabel. '''
        bigWidth = self.formSize.x() - 165 - 10 - 20 # qrWidth, border, inBetweenSpace
        bigHeight = self.formSize.y() - self.previewImageSize.y() - 10 - 20
        size = QRect(10, 10, bigWidth, bigHeight)
        self.bigImageSize = QPoint(bigWidth, bigHeight)

        imgDir = QDir(self.previewFilepath)
        existingImages = imgDir.count() - 2

        self.bigLabel = Record()
        self.bigLabel.label = QLabel(self)
        self.bigLabel.imageNr = 0
        self.bigLabel.label.setGeometry(size)
        self.bigLabel.label.setAlignment(Qt.AlignCenter | Qt.AlignVCenter)
        self.bigLabel.label.show()
        self.loadBigImage(existingImages, bigWidth, bigHeight)

    def loadBigImage(self, imgNr, w, h):
        ''' Loads the big preview label with the existing image referenced by imgNr. '''
        # If permance is too low, change QtSmoothTransformation
        filepath = self.imageFilepath + 'P' + str(imgNr) + '.jpg'
        if not os.path.isfile(filepath):
            return False

        img = QImage(filepath)
        pixmap = QtGui.QPixmap.fromImage(img.scaled(w, h, Qt.KeepAspectRatio, Qt.FastTransformation))
        self.bigLabel.label.setPixmap(pixmap)
        self.bigLabel.imageNr = imgNr
        return True

    def _highlightActivePreview(self):
        ''' Change the border of the preview labels to adequately highlight the image
        currently beeing displayed in bigLabel. '''
        highlightWidth = 3
        noHighlightWidth = 0

        for i in range(self.totalPreviewImages):
            # If the current image is not highlighted, but should be
            if (self.preLabels[i].label.lineWidth() == noHighlightWidth and
                    self.bigLabel.imageNr == self.preLabels[i].imageNr):
                self.preLabels[i].label.setLineWidth(highlightWidth)
                self.preLabels[i].label.setFrameShape(QFrame.Panel)

            # If the current image is highlighted, but shouldn't be
            if (self.preLabels[i].label.lineWidth() == highlightWidth and not
                    self.bigLabel.imageNr == self.preLabels[i].imageNr):
                self.preLabels[i].label.setLineWidth(noHighlightWidth)
                self.preLabels[i].label.setFrameShape(QFrame.NoFrame)

    def _setupQRCode(self):
        ''' Create the label to show the QR Code for and load the first QR-Code (if at least
        one image exists in the image folder already). '''
        # Label for display of QR code
        qrSize = QPoint(165,165)
        size = QRect(self.formSize.x() - qrSize.x() - 10, 10, qrSize.x(), qrSize.y())
        self.qrlabel = QtWidgets.QLabel(self)
        self.qrlabel.setGeometry(size)

        self.generateOrLoadQR(self.bigLabel.imageNr)
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

    def scrollLeft(self, event):
        newImgNr = self.bigLabel.imageNr - 1

        # bigPreviewImage
        if newImgNr <= 0 or not self.loadBigImage(newImgNr, self.bigImageSize.x(), self.bigImageSize.y()):
            return

        # QR-Code
        self.generateOrLoadQR(newImgNr)

        # set new Image Number because everything worked out
        self.bigLabel.imageNr = newImgNr

        # Realign small preview images (if neccessary)
        imgDir = QDir(self.imageFilepath)
        existingImages = imgDir.count() - 2
        if (newImgNr < math.ceil(self.totalPreviewImages/2) or
            existingImages <= self.totalPreviewImages):
            self._highlightActivePreview()
            return

        for i in range(self.totalPreviewImages-1, 0,-1):
            pixmap = self.preLabels[i-1].label.pixmap()
            if pixmap:
                self.preLabels[i].label.setPixmap(pixmap)
                self.preLabels[i].imageNr = self.preLabels[i-1].imageNr

        # Load new picture into leftmost preview label
        pixmap = self.generatePreviewImage(newImgNr - math.floor(self.totalPreviewImages/2))
        if pixmap:
            self.preLabels[0].label.setPixmap(pixmap)
            self.preLabels[0].imageNr = newImgNr - math.floor(self.totalPreviewImages/2)

        self._highlightActivePreview()

        # === DEBUG ===
        pstr = ""
        for i in range(len(self.preLabels)):
            pstr += str(self.preLabels[i].imageNr) + " "
        print("Scrolling finished. Position is: " + pstr)

    def scrollRight(self, event):
        newImgNr = self.bigLabel.imageNr + 1

        # bigPreviewImage
        if newImgNr <= 0 or not self.loadBigImage(newImgNr, self.bigImageSize.x(), self.bigImageSize.y()):
            print('es soll nichts verändert werden, da es nichts zu scrollen gibt')
            return

        # QR-Code
        self.generateOrLoadQR(newImgNr)

        # set new Image Number because everything worked out
        #self.bigLabel.imageNr = newImgNr

        # Realign small preview images (if neccessary)
        imgDir = QDir(self.imageFilepath)
        existingImages = imgDir.count() - 2
        if (newImgNr <= math.ceil(self.totalPreviewImages/2) or
            existingImages <= self.totalPreviewImages):
            self._highlightActivePreview()
            print('zu früh')
            return

        for i in range(0,self.totalPreviewImages-1, 1):
            pixmap = self.preLabels[i+1].label.pixmap()
            if pixmap:
                self.preLabels[i].label.setPixmap(pixmap)
                self.preLabels[i].imageNr = self.preLabels[i+1].imageNr
            else:
                pix = QPixmap(self.previewImageSize.x(), self.previewImageSize.y())
                pix.fill(QColor(0,0,0,0))
                self.preLabels[i].label.setPixmap(pix)
                self.preLabels[i].imageNr = 0

        # Decide where to load the new picture. Start assuming it is the rightmost preview label
        imgToLoad = newImgNr + math.floor(self.totalPreviewImages/2)
        emptyLabels = 0
        # Formula only holds if normal scrolling is performed. We need an extra check if a picture
        # was just made
        if (self.preLabels[self.totalPreviewImages-1] 
                and self.preLabels[self.totalPreviewImages-1].imageNr == 0):
            print('-1')
            imgToLoad = imgToLoad - 1
            emptyLabels = emptyLabels + 1
        if (self.preLabels[self.totalPreviewImages-1] 
                and self.preLabels[self.totalPreviewImages-1].imageNr == 0):
            print('-1')
            imgToLoad = imgToLoad - 1
            emptyLabels = emptyLabels + 1
        
        print('Should generate img number ' + str(imgToLoad))
        
        pixmap = self.generatePreviewImage(imgToLoad)
        if pixmap:
            self.preLabels[self.totalPreviewImages - 1 - emptyLabels].label.setPixmap(pixmap)
            self.preLabels[self.totalPreviewImages - 1 - emptyLabels].imageNr = imgToLoad
        else:
            print('Dieser Fall darf ab und zu auftreten')
            pix = QPixmap(self.previewImageSize.x(), self.previewImageSize.y())
            pix.fill(QColor(0,0,0,0))
            self.preLabels[self.totalPreviewImages-1].label.setPixmap(pix)
            self.preLabels[self.totalPreviewImages-1].imageNr = 0

        self._highlightActivePreview()

        # === DEBUG ===
        pstr = ""
        for i in range(len(self.preLabels)):
            pstr += str(self.preLabels[i].imageNr) + " "
        print("Scrolling finished. Position is: " + pstr)
        
    def ReloadAllPreviews(self):
        ''' Reload all previews and jump to newest picture. '''
        imgDir = QDir(self.imageFilepath)
        existingImages = imgDir.count() - 2
        self.bigLabel.imageNr = existingImages
        
        self.loadBigImage(self.bigLabel.imageNr, self.bigImageSize.x(), self.bigImageSize.y())
        
        for i in range(round(self.totalPreviewImages/2)+1):     
            pixmap = self.generatePreviewImage(self.bigLabel.imageNr - math.floor(self.totalPreviewImages/2) + i)
            if pixmap:
                self.preLabels[i].label.setPixmap(pixmap)
                self.preLabels[i].imageNr = self.bigLabel.imageNr - math.floor(self.totalPreviewImages/2) + i
                print('loaded img nr. ' + str(self.bigLabel.imageNr - math.floor(self.totalPreviewImages/2) + i) + ' into label nr. ' + str(i))
