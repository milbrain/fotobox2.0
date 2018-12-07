#!/usr/bin/python3
# -*- coding: utf-8 -*-
from PyQt5 import QtCore
from http.server import BaseHTTPRequestHandler, HTTPServer
from PyQt5.QtCore import *#QObject, pyqtSignal
from PyQt5.QtWidgets import QWidget, QApplication

import Server, GUI
import sys, logging, threading, argparse

class Controls(QObject):
    
    def initServer(self):
        ''' Inits the server that is used to communicate with the webapp, sets up
        the signals needed for the communication and starts the server thread. '''
        port = 1337
        ip = '127.0.0.222'
        server_address = (ip, port)
        self.server = Server.MyServer(server_address, Server.RequestHandler)
        self.server.handler = Server.RequestHandler
        self.server.handler.mainref = self
        
        # signals for safe inter-thread communication
        #self.server.returnSignal.connect(self.i_plotterReturn)
        #self.server.changePrintModeSignal.connect(self.i_changePrintMode)
        #self.server.plotterDrawSignal.connect(self.i_plotterDraw)
        #self.server.plotterGotoSignal.connect(self.i_plotterGotoXY)
        
        self.server.startThread()
        print("Server started and listening on port %s." % port)
        
    def initForm(self):
        self.gui = GUI.GUI(self)
    
if __name__ == '__main__':
    app = QApplication(sys.argv)
    controls = Controls()
    controls.initServer()
    controls.initForm()
    sys.exit(app.exec_())