#!/usr/bin/python3
# -*- coding: utf-8 -*-
from http.server import BaseHTTPRequestHandler, HTTPServer
from PyQt5.QtCore import QObject, pyqtSignal
import urllib.parse
import json
import threading
import logging
from collections import namedtuple

class RequestHandler(BaseHTTPRequestHandler):
    
    mainref     = None
    log         = logging.getLogger(__name__)
    getImgStr   = "getImageNr="
    
    #returnSignal = pyqtSignal()
    
    def _set_headers(self, str):
        self.send_response(200)
        self.send_header('Content-type', str)
        self.end_headers()

    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        
        # GET-Parameter
        
        if parsed_path.path == "/" and self.getImgStr in parsed_path.query:
            params = parsed_path.query.split("&")
            idx = params[0].find(self.getImgStr)
            if idx >= 0:
                imgNum = params[0][idx + len(self.getImgStr):]
                if imgNum.isnumeric():
                    file = None
                    try:
                        file = open(self.mainref.gui.imageFilepath + 'P' + imgNum + '.jpg', "rb")
                        self._set_headers('image/jpeg')
                        print("Loading image nr.: " + imgNum)
                        self.wfile.write(file.read())
                        file.close()
                    except:
                        self.printError("404")
                        return
                    return
            self.printError('numeric')
            
        # Implizite Anfragen
        elif parsed_path.path == "/":
            self.printError()
        elif parsed_path.path == "/favicon.ico":
            self._set_headers('image/x-icon')
            file = open(r'res/favicon.ico', "rb")
            self.wfile.write(file.read())
            file.close()

    def do_HEAD(self):
        self._set_headers('text/html')
        
    def printError(self, which = 'general'):
        header = ("<!DOCTYPE html>"
                  "<html><head>"
                  '<meta charset="UTF-8">'
                  '</head><body>')
        footer = "</body></html>"
        if which == 'numeric':
            self._set_headers('text/html')
            wdata = "Geben Sie eine numerische Bildnummer ein."
            wdata = header + wdata + footer
            self.wfile.write(wdata.encode("utf-8"))
        elif which == "404":
            self._set_headers('text/html')
            wdata = "Bild mit angegebener Bildnummer nicht gefunden. Geben Sie eine gültige numerische Bildnummer ein."
            wdata = header + wdata + footer
            self.wfile.write(wdata.encode("utf-8"))
        else:
            self._set_headers('text/html')
            wdata =  "Bilder können angezeigt werden indem in der URL Leiste http://"
            wdata += "%s:8000?%s und dann eine Bildnummer eingegeben werden." % (self.client_address[0], self.getImgStr)
            wdata = header + wdata + footer
            self.wfile.write(wdata.encode("utf-8"))
        
#    def do_POST(self):
        
    
    def log_message(self, format, *args):
        print("%s - - [%s] %s" % (self.address_string(),self.log_date_time_string(),format%args))
        
    def log_error(self, format, *args):
        print("%s - - [%s] %s" % (self.address_string(),self.log_date_time_string(),format%args))
        
class MyServer(HTTPServer, QObject):
    ''' Server Class used for communication with the webapp. Signals are used for communication
    with Controls. Direct method calls are not possible because the server runs in it's own
    separate thread. '''
    thread = None
    handler = None
    
    #returnSignal = pyqtSignal()
    #changePrintModeSignal = pyqtSignal()
    plotterDrawSignal = pyqtSignal(str)
    #plotterGotoSignal = pyqtSignal(int, int, str)
    
    def startThread(self):
        ''' Server starts listening (in own thread). '''
        self.thread = threading.Thread(target=self.serve_forever)
        self.thread.daemon = True
        self.thread.start()
    
    def __init__(self, server_address, RequestHandlerClass):
        #super().__init__(server_address, RequestHandlerClass)
        HTTPServer.__init__(self, server_address, RequestHandlerClass)
        QObject.__init__(self)
    
        
def run(server_class=HTTPServer, handler_class=RequestHandler, port=8000):
    server_address = ('', port)
    self.httpd = server_class(server_address, handler_class)
    self.httpd.serve_forever()