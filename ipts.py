#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pyoncat
import getpass

import numpy as np

import sys
import traceback

from qtpy.QtWidgets import QApplication, QMainWindow, QMessageBox, QWidget, QLabel, QLineEdit, QPushButton, QListWidget, QGridLayout, QVBoxLayout, QComboBox
from qtpy.QtGui import QIntValidator
from qtpy.QtCore import Qt

import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator, MultipleLocator

inst_param_directory = '/SNS/software/scd/garnet/src/garnet/config/'
sys.path.insert(0,inst_param_directory)
from instruments import *

theme = False

try:
    import qdarktheme
    
    qdarktheme.enable_hi_dpi()
    theme = True
    
except ImportError:
    #print('Default theme')
    pass
    
class View(QWidget):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        
        self.layout = QGridLayout()
        self.setLayout(self.layout)
        
        login_label = QLabel('ONCat Login')
        user_label = QLabel('Username: ')
        pass_label = QLabel('Password: ')
        self.user_line = QLineEdit()
        self.pass_line = QLineEdit()
        self.pass_line.setEchoMode(QLineEdit.Password)
        self.login_button = QPushButton('Sign In')
        self.message_label = QLabel('Not Signed In')
        self.message_label.setStyleSheet("color: red;")
        self.message_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        self.layout.addWidget(login_label,0,0)
        self.layout.addWidget(user_label,0,1)
        self.layout.addWidget(self.user_line,0,2,1,3)
        self.layout.addWidget(pass_label,0,5)
        self.layout.addWidget(self.pass_line,0,6,1,1)
        self.layout.addWidget(self.login_button,0,8)
        self.layout.addWidget(self.message_label,0,7)
        self.layout.setColumnMinimumWidth(7,350)
        
        
        instrument_cbox_label = QLabel('Instrument: ')
        self.instrument_cbox = QComboBox(self)
        instruments = ['SNAP','CORELLI','TOPAZ','MANDI','WAND²','DEMAND']
        self.instrument_cbox.addItems(instruments)
        self.layout.addWidget(instrument_cbox_label,1,0)
        self.layout.addWidget(self.instrument_cbox,1,1,1,8)
        
        
        ipts_label = QLabel('IPTS: ')
        self.ipts_field = QLineEdit()
        ipts_validator = QIntValidator(0,1000000000,self)
        self.ipts_field.setValidator(ipts_validator)
        self.layout.addWidget(ipts_label,2,0)
        self.layout.addWidget(self.ipts_field,2,1,1,8)
        
        
        self.name_list = QListWidget()
        self.layout.addWidget(self.name_list,3,0,3,4)
        
        
        runs_label = QLabel('Run Numbers: ')
        self.runs_list = QLineEdit()
        #self.runs_list.setReadOnly(True)
        self.layout.addWidget(runs_label,7,0)
        self.layout.addWidget(self.runs_list,7,1,1,8)
        
        
        self.plot = FigureCanvas(Figure(figsize=(8,6)))#,tight_layout=True))
        self.layout.addWidget(self.plot,3,4,2,5)
        self.layout.addWidget(NavigationToolbar(self.plot,self),5,4,1,5)
        
        
        
    def ipts_entered(self):
        if self.ipts_field.hasAcceptableInput():
            self.update()
    
    def get_instrument(self):
        return self.instrument_cbox.currentText()
    
    def get_name(self):
        return self.name_list.currentItem().text()

    def get_ipts(self):
        return self.ipts_field.text()
    
    def get_runs(self):
        return self.runs_list.text()
        
    def connect_ipts(self,update):
        self.ipts_field.editingFinished.connect(update)
    
    def connect_switch_instrument(self,update):
        self.instrument_cbox.activated.connect(update)
        
    def connect_select_name(self,update):
        self.name_list.itemSelectionChanged.connect(update)
        self.name_list.itemClicked.connect(update)
        
    def connect_adjust_runs(self,update):
        self.runs_list.editingFinished.connect(update)
    
    def connect_login_button(self,update):
        self.login_button.clicked.connect(update)
        self.pass_line.returnPressed.connect(update)

        
        
        
        
class Presenter:
    def __init__(self,view,model):
        self.view = view
        self.model = model
        
        self.view.connect_switch_instrument(self.switch_instrument)
        self.view.connect_select_name(self.select_name)
        self.view.connect_ipts(self.set_ipts)
        self.view.connect_adjust_runs(self.adjust_runs_list)
        self.view.connect_login_button(self.sign_in)
        
        self.switch_instrument()
        self.login = None
        self.data_files = None

        
        
    def switch_instrument(self):
        instrument = self.view.get_instrument()
        self.clear()
        self.view.ipts_field.setText('')
        
        inst_params = self.model.beamline_info(instrument)
        #print(inst_params['Name'])
        #print(inst_params['Goniometer'])
        
        self.inst_params = inst_params

    def set_ipts(self):
        ipts = self.view.get_ipts()
        self.clear()
        try:
            self.data_files = self.model.retrieve_data_files(self.login,self.inst_params,ipts)
            self.names = self.model.run_title_dictionary(self.data_files,self.inst_params)
            self.view.name_list.addItems(list(self.names.keys()))
        except AttributeError:
            self.view.message_label.setText('Not Signed In')
            self.view.message_label.setStyleSheet("color: red;")
        except pyoncat.InvalidRefreshTokenError:
            self.view.message_label.setText('Login Expired')
            self.view.message_label.setStyleSheet("color: orange;")



    def select_name(self):
        name = self.view.get_name()
        self.runs = self.names[name]
        self.view.runs_list.setText(self.runs)
        #print(name)
        
        run_numbers_list, data_indices = self.model.run_numbers_indices(name,self.data_files,self.names,self.inst_params)
        gonio_values, gonio_names = self.model.goniometer_values(self.data_files,data_indices,self.inst_params)
        scale_values = self.model.scale_values(self.data_files,data_indices,self.inst_params)

        self.plot(gonio_values,gonio_names,run_numbers_list,scale_values)
        
    def adjust_runs_list(self):
        rs = self.view.get_runs()
        try:
            runs_list = self.model.run_numbers_list(rs)
        except:
            #print('Invalid run numbers')
            return
        
        if self.data_files is None:
            return
        
        run_numbers_list, data_indices = self.model.run_numbers_indices_1(self.data_files,runs_list,self.inst_params)
        gonio_values, gonio_names = self.model.goniometer_values(self.data_files,data_indices,self.inst_params)
        scale_values = self.model.scale_values(self.data_files,data_indices,self.inst_params)
        
        self.plot(gonio_values,gonio_names,run_numbers_list,scale_values)
        
        
        
    def clear(self):
        
        self.view.name_list.clear()
        self.view.runs_list.setText('')
        self.view.plot.figure.clf()
        self.view.plot.figure.canvas.draw()
        
        
    def plot(self,gonio_values,gonio_names,run_numbers_list,scale_values):
        self.view.plot.figure.clf()
        self.view.plot.figure.canvas.draw()
        self.view.plot.figure.subplots_adjust(wspace=0.1,top=0.85,bottom=0.1)
       
        if len(self.model.subplot_limits) == 1:
            ax1 = self.view.plot.figure.subplots()
            for val, lab in zip(gonio_values,gonio_names):
                ax1.plot(run_numbers_list,val,'.',label=lab)
            ax1.set_ylabel('Goniometer Values (degrees)')
            ax1.set_xlabel('Run Number')
            ax1.set_xlim(self.model.subplot_limits[0][0]-1,self.model.subplot_limits[0][1]+1)
            ax1.legend(fontsize='x-small',loc='upper left',bbox_to_anchor=(0,1.2))
            ax1.xaxis.set_major_locator(MaxNLocator(integer=True))
            ax1.ticklabel_format(style='plain',axis='x',useOffset=False)
    
            ax2 = ax1.twinx()
            color='r'
            ax2.set_ylabel(f'Scale ({self.inst_params["Scale"].split(".")[-1]})',color=color)
            ax2.plot(run_numbers_list,scale_values,'.',color=color)
            ax2.tick_params(axis='y',labelcolor=color)
            
        else:
            axs = self.view.plot.figure.subplots(1,len(self.model.subplot_limits),sharey=True,width_ratios=[l[1]-l[0] + 2 for l in self.model.subplot_limits])
            
            self.view.plot.figure.supxlabel('Run Number',fontsize='medium')
            spacing = len(run_numbers_list) // 6
            
            d = 0.5
            kwargs = dict(marker=[(-d,-1),(d,1)],markersize=12,linestyle='none',color='k',mec='k',mew=1,clip_on=False)
            
            for i, ax in enumerate(axs):
                lim = self.model.subplot_limits[i]
                lim_range = 1#(lim[1]-lim[0] + 1)*0.2
                ax.set_xlim(lim[0]-lim_range,lim[1]+lim_range)
                ax.set_ylim(np.min(gonio_values)-10,np.max(gonio_values)+10)
                if lim[0] != lim[1]:
                    xt = np.arange(lim[0],lim[1]+1)
                    mask = xt % spacing == 0
                    if len(xt[mask]) == 0:
                        ax.set_xticks([lim[0]])
                    else:
                        ax.set_xticks(xt[mask])
                else:
                    ax.set_xticks([lim[0]])
                #ax.set_aspect(0.5)
                #ax.tick_params(axis='x',labelrotation=15)
                
                if i == 0:
                    ax.set_ylabel('Goniometer Values (degrees)')
                    for val, lab in zip(gonio_values,gonio_names):
                        ax.plot(run_numbers_list,val,'.',label=lab)
                    ax.legend(fontsize='x-small',loc='upper left',bbox_to_anchor=(0,1.2))
                    #ax.xaxis.set_major_locator(MaxNLocator(integer=True))
                    ax.ticklabel_format(style='plain',axis='x',useOffset=False)
                    ax.spines.right.set_visible(False)
                    ax.plot([1,1],[0,1],transform=ax.transAxes,**kwargs)
                else:
                    for val, lab in zip(gonio_values,gonio_names):
                        ax.plot(run_numbers_list,val,'.')
                    #ax.xaxis.set_major_locator(MaxNLocator(integer=True))
                    ax.ticklabel_format(style='plain',axis='x',useOffset=False)
                    ax.spines.left.set_visible(False)
                    ax.tick_params(labelleft=False)
                    #ax.set_yticks([])
                    if i != len(self.model.subplot_limits) - 1:
                        ax.spines.right.set_visible(False)
                        ax.tick_params(labelright=False)
                        ax.tick_params(axis='y',length=0)
                        ax.plot([0,0,1,1],[0,1,0,1],transform=ax.transAxes,**kwargs)
                    else: 
                        ax.spines.right.set_visible(False)
                        ax.tick_params(axis='y',length=0)
                        #ax.yaxis.tick_right()
                        ax.plot([0,0],[0,1],transform=ax.transAxes,**kwargs)
                        
                ax2 = ax.twinx()
                color='r'
                ax2.plot(run_numbers_list,scale_values,'.',color=color)
                ax2.tick_params(axis='y',labelcolor=color)  
                if i != len(self.model.subplot_limits) - 1:
                    ax2.spines.right.set_visible(False)
                    ax2.spines.left.set_visible(False)
                    ax2.tick_params(labelright=False)
                    ax2.tick_params(labelleft=False)
                    ax2.tick_params(axis='y',length=0)
                else:
                    ax2.tick_params(labelright=True)
                    ax2.spines.left.set_visible(False)
                    ax2.tick_params(labelleft=False)
                    ax2.tick_params(axis='y',color=color,labelright=True)
                    #ax2.spines.right.set_color(color)
                    ax2.set_ylabel(f'Scale ({self.inst_params["Scale"].split(".")[-1]})',color=color)
                
                

        self.view.plot.figure.canvas.draw()
        
    def sign_in(self):
        user = self.view.user_line.text()
        pw = self.view.pass_line.text()
        
        ONCAT_URL = 'https://oncat.ornl.gov'
        CLIENT_ID = '99025bb3-ce06-4f4b-bcf2-36ebf925cd1d'

        oncat = pyoncat.ONCat(ONCAT_URL, 
                              client_id=CLIENT_ID,
                              flow=pyoncat.RESOURCE_OWNER_CREDENTIALS_FLOW)

        try:
            oncat.login(user,pw)
        except:
            self.view.message_label.setText('Incorrect Username or Password')
            self.view.message_label.setStyleSheet("color: red;")
            self.view.pass_line.setText('')
            return
        
        self.login = oncat
        self.view.message_label.setText('Signed In')
        self.view.message_label.setStyleSheet("color: green;")
        #self.view.user_line.setText('')
        #self.view.pass_line.setText('')
        
        
    
    
    
    
class Model:
    def __init__(self):
        pass
        
    
    def goniometer_entries(self,inst_params):
        
        goniometer = inst_params['Goniometer']
        goniometer_engry = inst_params['GoniometerEntry']
        
        projection = []
        for name in goniometer.keys():
            entry='.'.join([goniometer_engry, name.lower(), 'average_value'])
            projection.append(entry)
            
        return projection
    
    def retrieve_data_files(self, login, inst_params, ipts_number):
        
        facility = inst_params['Facility']
        instrument = inst_params['Name']
        
        projection = [inst_params['RunNumber'],
                      inst_params['Title'],
                      inst_params['Scale']]
        
        projection += self.goniometer_entries(inst_params)
        
        exts = [inst_params['Extension']]
        
        data_files = login.Datafile.list(facility=facility, 
                                         instrument=instrument,
                                         experiment='IPTS-{}'.format(ipts_number),
                                         projection=projection,
                                         exts=exts,
                                         tags=['type/raw'])
        return data_files
    
    def run_title_dictionary(self,data_files, inst_params):
        
        title_entry = inst_params['Title']
        run_number_entry = inst_params['RunNumber']
        
        titles = np.array([df[title_entry] for df in data_files])
        run_numbers = np.array([int(df[run_number_entry]) for df in data_files])
        
        unique_titles = np.unique(titles)
        
        run_title_dict = {}
        for unique_title in unique_titles:
            runs = run_numbers[titles == unique_title]
            run_seq = np.split(runs.astype(str), np.where(np.diff(runs) > 1)[0] + 1)
            rs = ','.join([s[0]+':'+s[-1] if len(s)-1 else s[0] for s in run_seq])
            run_title_dict[unique_title] = rs
            
        return run_title_dict
    
    
    def run_numbers_list(self,rs):
        
        run_seq = [np.array(s.split(':')).astype(int) for s in rs.split(',')]
        run_list = [np.arange(r[0],r[-1]+1) if len(r)-1 else r for r in run_seq]
    
        return np.array([r for sub_list in run_list for r in sub_list])
    
    def prepare_runs_for_multiple_plots(self,run_number_list):
        rs = run_number_list.copy()
        
        rs.sort(0)
        
        out_list = []
        breaks = [0]
        for i in range(1,len(rs)):
            if rs[i] - rs[i-1] > 1:
                breaks.append(i)
                
        if len(breaks) == 1:
            out_list.append([rs[0],rs[-1]])
            
        else:            
            for i in range(len(breaks)-1):
                out_list.append([rs[breaks[i]],rs[breaks[i+1]-1]])
            out_list.append([rs[breaks[-1]],rs[-1]])
        
        self.subplot_limits = out_list
        #print(len(self.subplot_limits))
    
    
    def beamline_info(self,bl):
        
        inst_params = beamlines[bl]

        
        return inst_params
    
    def run_numbers_indices(self,name,data_files,run_title_dict,inst_params):
        run_number_entry = inst_params['RunNumber']
        this_run_numbers = self.run_numbers_list(run_title_dict[name])
        run_numbers = np.array([int(df[run_number_entry]) for df in data_files])
        indices = np.arange(len(data_files))
        
        mask = np.array([i in this_run_numbers for i in run_numbers])
        
        self.prepare_runs_for_multiple_plots(run_numbers[mask])
        
        return run_numbers[mask], indices[mask]
    
    def run_numbers_indices_1(self,data_files,run_number_list,inst_params):
        run_number_entry = inst_params['RunNumber']
        run_numbers = np.array([int(df[run_number_entry]) for df in data_files])
        indices = np.arange(len(data_files))
        
        mask = np.array([i in run_number_list for i in run_numbers])
        
        self.prepare_runs_for_multiple_plots(run_numbers[mask])
        
        return run_numbers[mask], indices[mask]

    def goniometer_values(self,data_files,indices,inst_params):
        a = []
        gonio_entry = inst_params['Goniometer']

        for entry in gonio_entry:
            b = []
            values = np.array([float(df[inst_params['GoniometerEntry']+'.'+entry.lower()+'.average_value']) for df in data_files])
            b.append([values[i] for i in indices])
            b = np.array(b).T
            #print(b.shape)
            a.append(b)
            

        return a, [i.lower() for i in gonio_entry]


    def scale_values(self,data_files,indices,inst_params):
        scale_entry = inst_params['Scale']

        values = np.array([float(df[scale_entry]) for df in data_files])
        a = [values[i] for i in indices]
        a = np.array(a).T

        return a

    

class ExperimentBrowser(QMainWindow):
    __instance = None
    
    def __new__(cls):
        if ExperimentBrowser.__instance is None:
            ExperimentBrowser.__instance = QMainWindow.__new__(cls)
        return ExperimentBrowser.__instance 
    
    def __init__(self,parent=None):
        super().__init__(parent)
        
        name = 'ipts-data-view'
        self.setWindowTitle(name)
        self.setGeometry(0,0,1024,635)
        
        main_window = QWidget(self)
        self.setCentralWidget(main_window)
        layout = QVBoxLayout(main_window)

        view = View()
        model = Model()
        self.form = Presenter(view,model)
        layout.addWidget(view)
        



def handle_exception(exc_type, exc_value, exc_traceback):
    error_message = "".join(
        traceback.format_exception(exc_type, exc_value, exc_traceback)
    )

    msg_box = QMessageBox()
    msg_box.setWindowTitle("Application Error")
    msg_box.setText("An unexpected error occurred. Please see details below:")
    msg_box.setDetailedText(error_message)
    msg_box.setIcon(QMessageBox.Critical)
    msg_box.exec_()

        
        
if __name__ == "__main__":
    sys.excepthook = handle_exception
    app = QApplication(sys.argv)
    if theme: qdarktheme.setup_theme('light')
    window=ExperimentBrowser()#yaml)    
    window.show()
    sys.exit(app.exec_())  
