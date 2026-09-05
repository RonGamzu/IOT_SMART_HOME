import os
#from sqlite3.dbapi2 import Date
import sys
import random
# pip install pyqt5-tools
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from matplotlib.pyplot import get
BASE_PATH = os.path.abspath(os.path.dirname(__file__))
from init import *
from agent import Mqtt_client 
import time
from icecream import ic
from datetime import datetime 
import data_acq as da
# pip install pyqtgraph
#from pyqtgraph import PlotWidget, plot
import pyqtgraph as pg

import logging

# Gets or creates a logger
logger = logging.getLogger(__name__)  

# set log level
logger.setLevel(logging.WARNING)

# define file handler and set formatter
file_handler = logging.FileHandler('logfile_gui.log')
formatter    = logging.Formatter('%(asctime)s : %(levelname)s : %(name)s : %(message)s')
file_handler.setFormatter(formatter)

# add file handler to logger
logger.addHandler(file_handler)

# Logs
# logger.debug('A debug message')
# logger.info('An info message')
# logger.warning('Something is not right.')
# logger.error('A Major error has happened.')
# logger.critical('Fatal error. Cannot continue')


global WatMet
WatMet=True
def time_format():
    return f'{datetime.now()}  GUI|> '
ic.configureOutput(prefix=time_format)
ic.configureOutput(includeContext=False) # use True for including script file context file 
# Creating Client name - should be unique 
global clientname
r=random.randrange(1,10000) # for creating unique client ID
clientname="IOT_clientId-nXLMZeDcjH"+str(r)

def check(fnk):    
    try:
        rz=fnk
    except:
        rz='NA'
    return rz        

class MC(Mqtt_client):
    def __init__(self):
        super().__init__()
    def on_message(self, client, userdata, msg):
            global WatMet
            topic=msg.topic            
            m_decode=str(msg.payload.decode("utf-8","ignore"))
            ic("message from:"+topic, m_decode)
            if 'Room_1' in topic:
                mainwin.airconditionDock.update_temp_Room(check(m_decode.split('Temperature: ')[1].split(' Humidity: ')[0]))
            if 'Common' in topic:            
                mainwin.airconditionDock.update_temp_Room(check(m_decode.split('Temperature: ')[1].split(' Humidity: ')[0]))
            if 'Home' in topic:               
                if WatMet:
                    mainwin.graphsDock.update_electricity_meter(check(m_decode.split('Electricity: ')[1].split(' Sensitivity: ')[0]))
                    WatMet = False
                else:
                    mainwin.graphsDock.update_Sensitivity_meter(check(m_decode.split(' Sensitivity: ')[1]))
                    WatMet = True
            if 'sound' in topic:            
                mainwin.statusDock.update_mess_win(da.timestamp()+': ' + m_decode)
            if 'motion' in topic:
                mainwin.statusDock.motionTemp.setText(check(m_decode.split('Temperature: ')[1]))

   
class ConnectionDock(QDockWidget):
    """Main """
    def __init__(self,mc):
        QDockWidget.__init__(self)        
        self.mc = mc
        self.topic = comm_topic+'#'        
        self.mc.set_on_connected_to_form(self.on_connected)        
        self.eHostInput=QLineEdit()
        self.eHostInput.setInputMask('999.999.999.999')
        self.eHostInput.setText(broker_ip)        
        self.ePort=QLineEdit()
        self.ePort.setValidator(QIntValidator())
        self.ePort.setMaxLength(4)
        self.ePort.setText(broker_port)        
        self.eClientID=QLineEdit()
        global clientname
        self.eClientID.setText(clientname)        
        self.eConnectButton=QPushButton("Connect", self)
        self.eConnectButton.setToolTip("click me to connect")
        self.eConnectButton.clicked.connect(self.on_button_connect_click)
        self.eConnectButton.setStyleSheet("background-color: red")        
        formLayot=QFormLayout()
        formLayot.addRow("Host",self.eHostInput )
        formLayot.addRow("Port",self.ePort )        
        formLayot.addRow("",self.eConnectButton)
        widget = QWidget(self)
        widget.setLayout(formLayot)
        self.setTitleBarWidget(widget)
        self.setWidget(widget)     
        self.setWindowTitle("Connect") 
        
    def on_connected(self):
        self.eConnectButton.setStyleSheet("background-color: green")
        self.eConnectButton.setText('Connected')
            
    def on_button_connect_click(self):
        self.mc.set_broker(self.eHostInput.text())
        self.mc.set_port(int(self.ePort.text()))
        self.mc.set_clientName(self.eClientID.text())           
        self.mc.connect_to()        
        self.mc.start_listening()
        time.sleep(1)
        if not self.mc.subscribed:
            self.mc.subscribe_to(self.topic)
            
class StatusDock(QDockWidget):
    """Status """
    def __init__(self,mc):
        QDockWidget.__init__(self)        
        self.mc = mc
        self.motionTemp = QLabel()
        self.motionTemp.setText("80")
        self.motionTemp.setStyleSheet("color: red")
        self.wifi = QLabel()
        self.wifi.setText("Normal")
        self.wifi.setStyleSheet("color: green")
        self.door = QLabel()
        self.door.setText("Closed")
        self.door.setStyleSheet("color: green")
        self.eRecMess=QTextEdit()
        self.eSubscribeButton = QPushButton("Subscribe",self)
        self.eSubscribeButton.clicked.connect(self.on_button_subscribe_click)       
        formLayot=QFormLayout()
        formLayot.addRow("Motion distance:", self.motionTemp)
        formLayot.addRow("WI-Fi status:",self.wifi)
        formLayot.addRow("Main Door:",self.door)        
        formLayot.addRow("Sound Messages:",self.eRecMess)
        formLayot.addRow("",self.eSubscribeButton)                
        widget = QWidget(self)
        widget.setLayout(formLayot)
        self.setTitleBarWidget(widget)
        self.setWidget(widget)     
        self.setWindowTitle("Status") 
        
    def on_button_subscribe_click(self):        
        self.mc.subscribe_to(comm_topic+'sound')
        self.eSubscribeButton.setStyleSheet("background-color: green")
    
    # create function that update text in received message window
    def update_mess_win(self,text):
        self.eRecMess.append(text)              
       
    def on_button_publish_click(self):
        self.mc.publish_to(self.ePublisherTopic.text(), self.eMessageBox.toPlainText())
        self.ePublishButton.setStyleSheet("background-color: yellow")
        
class GraphsDock(QDockWidget):
    """Graphs """
    def __init__(self,mc):
        QDockWidget.__init__(self)        
        self.mc = mc        
        self.eElectricityButton = QPushButton("Show",self)
        self.eElectricityButton.clicked.connect(self.on_button_Elec_click)        
        self.eElectricityText=QLineEdit()
        self.eElectricityText.setText(" ")
        self.eSensitivityButton = QPushButton("Show",self)
        self.eSensitivityButton.clicked.connect(self.on_button_Sensitivity_click)
        self.eSensitivityText= QLineEdit()
        self.eSensitivityText.setText(" ")
        self.eStartDate= QLineEdit()
        self.eEndDate= QLineEdit()
        self.eStartDate.setText("2021-05-10")
        self.eEndDate.setText("2021-05-25")
        self.eDateButton=QPushButton("Insert", self)
        self.eDateButton.clicked.connect(self.on_button_date_click)
        self.date=self.on_button_date_click
        formLayot=QFormLayout()       
        formLayot.addRow("Electricity meter",self.eElectricityButton)
        formLayot.addRow(" ", self.eElectricityText)
        formLayot.addRow("Sensitivity meter",self.eDateButton)
        formLayot.addRow(" ", self.eSensitivityText)
        formLayot.addRow("Start date: ", self.eStartDate)
        formLayot.addRow("End date: ", self.eEndDate)
        formLayot.addRow("", self.eDateButton)
        widget = QWidget(self)
        widget.setLayout(formLayot)
        self.setWidget(widget)
        self.setWindowTitle("Graphs")

    def update_Sensitivity_meter(self, text):
        self.eSensitivityText.setText(text)

    def update_electricity_meter(self, text):
        self.eElectricityText.setText(text) 

    def on_button_date_click (self):
        self.startDateStr= self.eStartDate.text()
        self.endDateStr= self.eEndDate.text()        

    def on_button_Sensitivity_click(self):
       self.update_plot(self.startDateStr, self.endDateStr, 'SensitivityMeter')
       self.eSensitivityButton.setStyleSheet("background-color: yellow")

    def on_button_Elec_click(self):
        self.update_plot(self.startDateStr, self.endDateStr, 'ElecMeter')
        self.eElectricityButton.setStyleSheet("background-color: yellow")

    def update_plot(self,date_st,date_end, meter):
        rez= da.filter_by_date('data',date_st,date_end, meter)
        temperature = []  
        timenow = []       
        for row in rez:
            timenow.append(row[1])
            temperature.append(float("{:.2f}".format(float(row[2]))))
        print(timenow)
        print(temperature)
        mainwin.plotsDock.plot(timenow, temperature) 

class TempDock(QDockWidget):
    """Temp """
    def __init__(self,mc):
        QDockWidget.__init__(self)        
        self.mc = mc    
        
        self.tMotion = QComboBox()
        self.tMotion.addItems(["Auto", "ON", "OFF"])
        self.tMotion.currentIndexChanged.connect(self.tb_selectionchange)
        self.tsetButton = QPushButton("SET(UPDATE)",self)
        self.tsetButton.clicked.connect(self.on_tsetButton_click)
        formLayot=QFormLayout()       
        formLayot.addRow("Motion sensor",self.tMotion)
        formLayot.addRow("",self.tsetButton)
        widget = QWidget(self)
        widget.setLayout(formLayot)
        self.setWidget(widget)
        self.setWindowTitle("Set Temperature")
    def on_tsetButton_click(self):
        self.tsetButton.setStyleSheet("background-color: green")
        time.sleep(0.2)
        if "ON" in self.tMotion.currentText():
            self.tMotion.setStyleSheet("color: green")
            self.mc.publish_to(comm_topic+'Motion/sub','Set temperature to: ON')

    def tb_selectionchange(self,i):
        print ("Current index",i,"selection changed ",self.tMotion.currentText())
        if "ON" in self.tMotion.currentText():
            self.tMotion.setStyleSheet("color: green")
            # self.mc.publish_to('pr/Smart/Motion/sub','Set temperature to: ')
        elif "OFF" in self.tMotion.currentText():
            self.tMotion.setStyleSheet("color: red")
        else:
            self.tMotion.setStyleSheet("color: none")

class AirconditionDock(QDockWidget):
    """Aircondition """
    def __init__(self,mc):
        QDockWidget.__init__(self)        
        self.mc = mc
        # Line #1
        self.l1 = QLabel()
        self.l1.setText("PLACE:")
        self.l1.setFont(QFont('Arial', 10))
        self.l1.setStyleSheet("color: rgb(0, 0, 255);")
        # self.l1.setAlignment(Qt.AlignCenter)
        self.cb = QComboBox()        
        self.cb.addItems(["Store", "Dressing room 1", "Dressing room 2"])
        self.cb.currentIndexChanged.connect(self.selectionchange)
		# Line #2
        self.l21 = QLabel()
        self.l21.setText("Temperature: Current")
        self.cRoomTemp=QLineEdit()
        self.cRoomTemp.setText(" ")
        self.l22 = QLabel()
        self.l22.setText("Target")        
        self.tRoomTemp = QComboBox()        
        self.tRoomTemp.addItems(["min", "17", "18", "19", "20", "21", "22", "23", "24", "25", "26", "27", "28", "29", "30", "max"])
        self.tRoomTemp.currentIndexChanged.connect(self.tr_selectionchange)    
        self.settemp='22'
        self.topic_sub = comm_topic+'air-1/sub'
        self.topic_pub = comm_topic+'air-1/pub'

        # Line #3
        self.l31 = QLabel()
        self.l31.setText("Mode")
        self.md = QComboBox()        
        self.md.addItems(["Cool", "Heat", "Dry","Fan"])
        self.md.currentIndexChanged.connect(self.md_selectionchange)
        self.l32 = QLabel()
        self.l32.setText("Fan")
        self.fn = QComboBox()        
        self.fn.addItems(["High", "Middle", "Low"])
        self.fn.currentIndexChanged.connect(self.fn_selectionchange)
        # Line #4
        self.l41 = QLabel()
        self.l41.setText("ON\\OFF:")
        self.od = QComboBox()        
        self.od.addItems(["AUTO", "OFF", "ON"])        
        self.od.currentIndexChanged.connect(self.od_selectionchange)
        self.l42 = QLabel()
        self.l42.setText("Status:")
        self.st = QComboBox()        
        self.st.addItems(["Unknown", "Failure", "Normal"])
        self.st.currentIndexChanged.connect(self.st_selectionchange)
        # Line #5
        self.setButton = QPushButton("SET(UPDATE)",self)
        self.setButton.clicked.connect(self.on_setButton_click)
        layout = QGridLayout()
        # Add widgets to the layout
        # Line #1
        layout.addWidget(self.l1, 0,1)
        layout.addWidget(self.cb, 0,2)
        # Line #2 
        layout.addWidget(self.l21, 1,0)
        layout.addWidget(self.cRoomTemp, 1,1)
        layout.addWidget(self.l22, 1,2)
        layout.addWidget(self.tRoomTemp, 1,3)
        # Line #3 
        layout.addWidget(self.l31, 2,0)
        layout.addWidget(self.md, 2,1)
        layout.addWidget(self.l32, 2,2)
        layout.addWidget(self.fn, 2,3)
        # Line #4 
        layout.addWidget(self.l41, 3,0)
        layout.addWidget(self.od, 3,1)
        layout.addWidget(self.l42, 3,2)
        layout.addWidget(self.st, 3,3)
        # Line #5 
        layout.addWidget(self.setButton, 4,1,4,2)       
        # Set the layout on the application's window
        # self.setLayout(layout)
        widget = QWidget(self)
        widget.setLayout(layout)
        self.setWidget(widget)
        self.setWindowTitle("Aircondition")

    def update_temp_Room(self, text):
        self.cRoomTemp.setText(text)  

    def selectionchange(self,i):
        print ("Current index",i,"selection changed ",self.cb.currentText())

    def md_selectionchange(self,i):
        print ("Current index",i,"selection changed ",self.md.currentText())

    def fn_selectionchange(self,i):
        print ("Current index",i,"selection changed ",self.fn.currentText())

    def od_selectionchange(self,i):
        print ("Current index",i,"selection changed ",self.od.currentText())
        if "ON" in self.od.currentText():
            self.od.setStyleSheet("color: green")
        elif "OFF" in self.od.currentText():
            self.od.setStyleSheet("color: red")
        else:
            self.od.setStyleSheet("color: none") 

        #setStyleSheet("color: blue;"
        #                "background-color: yellow;"
        #                "selection-color: yellow;"
        #                "selection-background-color: blue;");    

    def st_selectionchange(self,i):
        print ("Current index",i,"selection changed ",self.st.currentText())  

    def tr_selectionchange(self,i):
        print ("Current index",i,"selection changed ",self.tRoomTemp.currentText())  
        self.settemp=self.tRoomTemp.currentText()

    def on_setButton_click(self):
        self.setButton.setStyleSheet("background-color: green")             
        self.mc.publish_to(self.topic_sub,'Set temperature to: '+ self.settemp)

class PlotDock(QDockWidget):
    """Plots """
    def __init__(self):
        QDockWidget.__init__(self)        
        self.setWindowTitle("Plots")
        self.graphWidget = pg.PlotWidget()
        self.setWidget(self.graphWidget)
        rez= da.filter_by_date('data','2021-05-16','2021-05-18', 'ElecMeter')        
        datal = []  
        timel = []        
        for row in rez:
            timel.append(row[1])
            datal.append(float("{:.2f}".format(float(row[2]))))
        self.graphWidget.setBackground('b')
        # Add Title
        self.graphWidget.setTitle("Consuption Timeline", color="w", size="15pt")
        # Add Axis Labels
        styles = {"color": "#f00", "font-size": "20px"}
        self.graphWidget.setLabel("left", "Value (°C/m3)", **styles)
        self.graphWidget.setLabel("bottom", "Date (dd.hh/hh.mm)", **styles)
        #Add legend
        self.graphWidget.addLegend()
        #Add grid
        self.graphWidget.showGrid(x=True, y=True)
        #Set Range
        #self.graphWidget.setXRange(0, 10, padding=0)
        #self.graphWidget.setYRange(20, 55, padding=0)            
        pen = pg.mkPen(color=(255, 0, 0))
        self.data_line=self.graphWidget.plot( datal,  pen=pen)

    def plot(self, timel, datal):
        self.data_line.setData( datal)  # Update the data.

class MainWindow(QMainWindow):    
    def __init__(self, parent=None):
        QMainWindow.__init__(self, parent)                
        # Init of Mqtt_client class
        # self.mc=Mqtt_client()
        self.mc=MC()        
        # general GUI settings
        self.setUnifiedTitleAndToolBarOnMac(True)
        # set up main window
        self.setGeometry(30, 100, 800, 600)
        self.setWindowTitle('System GUI')
        # Init QDockWidget objects        
        self.connectionDock = ConnectionDock(self.mc)        
        self.statusDock = StatusDock(self.mc)
        self.tempDock = TempDock(self.mc)
        self.graphsDock = GraphsDock(self.mc)
        self.airconditionDock= AirconditionDock(self.mc)
        self.plotsDock = PlotDock()
        self.addDockWidget(Qt.TopDockWidgetArea, self.connectionDock)
        self.addDockWidget(Qt.TopDockWidgetArea, self.tempDock)
        self.addDockWidget(Qt.TopDockWidgetArea, self.airconditionDock)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.statusDock)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.graphsDock)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.plotsDock)       

if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        mainwin = MainWindow()
        mainwin.show()
        app.exec_()

    except:
        logger.exception("GUI Crash!")
