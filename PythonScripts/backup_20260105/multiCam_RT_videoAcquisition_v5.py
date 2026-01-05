"""
CLARA toolbox
https://github.com/wryanw/CLARA
W Williamson, wallace.williamson@ucdenver.edu

"""

# reach-training-grant-fork-new-master (this is a direct copy of soles working version, however, i placed in my version of this file to get my new features)

from __future__ import print_function
from multiprocessing import Array, Queue, Value
import wx
import wx.lib.dialogs
import os
import numpy as np
import time, datetime
import ctypes
from matplotlib.figure import Figure
import matplotlib.patches as patches
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas

# Grant 8-29-25 changed import for pyspin from normal file
import multiCam_DLC_PySpin_v2_extStim as spin
#import multiCam_DLC_PySpin_v2 as spin

import multiCam_DLC_utils_v2 as clara
import arduinoCtrl_v5 as arduino
import compressVideos_v3 as compressVideos
import shutil
from pathlib import Path
import ruamel.yaml
import winsound


# ###########################################################################
# Log all prints to a file 
# ###########################################################################
import sys
import datetime
import io               # ← add this

        
def configure_logging(save_log_path):
    import logging
    import sys
    from pathlib import Path
    
    # set the path for the .log to save too, unique for each session and passed in from recordcam() function 
    SESSION_LOG = Path(save_log_path)
    
    # (TESTING NEW) 🔧 Remove any existing handlers before reconfiguring
    root_logger = logging.getLogger()
    if root_logger.handlers:
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
            handler.close()  # close file streams to prevent resource leaks
    
    # Basic logger set up
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(SESSION_LOG, mode='a', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    # Redirect print() to logging.info() globally
    global print
    print = lambda *args, **kwargs: logging.info(' '.join(str(a) for a in args))
# ###########################################################################
# Class for GUI MainFrame
# ###########################################################################
class ImagePanel(wx.Panel):

    def __init__(self, parent, gui_size, axesCt, **kwargs):
        wx.Panel.__init__(self, parent, -1,style=wx.SUNKEN_BORDER)
            
        self.figure = Figure()
        self.axes = list()
        if axesCt <= 3:
            if gui_size[0] > gui_size[1]:
                rowCt = 1
                colCt = axesCt
            else:
                colCt = 1
                rowCt = axesCt
            
        else:
            if gui_size[0] > gui_size[1]:
                rowCt = 2
                colCt = np.ceil(axesCt/2)
            else:
                colCt = 2
                rowCt = np.ceil(axesCt/2)
        a = 0
        for r in range(int(rowCt)):
            for c in range(int(colCt)):
                self.axes.append(self.figure.add_subplot(rowCt, colCt, a+1, frameon=True))
                self.axes[a].set_position([c*1/colCt+0.005,r*1/rowCt+0.005,1/colCt-0.01,1/rowCt-0.01])
                
        
                self.axes[a].xaxis.set_visible(False)
                self.axes[a].yaxis.set_visible(False)
                a+=1
            
        self.canvas = FigureCanvas(self, -1, self.figure)
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.canvas, 1, wx.LEFT | wx.TOP | wx.GROW)
        self.SetSizer(self.sizer)
        self.Fit()

    def getfigure(self):
        """
        Returns the figure, axes and canvas
        """
        return(self.figure,self.axes,self.canvas)
#    
class WidgetPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1,style=wx.SUNKEN_BORDER)

class MainFrame(wx.Frame):
    """Contains the main GUI and button boxes"""
    def __init__(self, parent):
        self.trial_line_printed = False
        self.hand_timing = None
        self.trial_delays = []  # store delays for this session, Grant Hughes, 8-11-25
        self.data_logging_enabled = False  # New Code 12-30-2025
        self.current_mode_tag = None       # New Code 12-30-2025 ("LIVE" or "REC")
        
        # These are for logging which trial number the event occured on, relative to ALL trials
        self.baseline_trials = []
        self.stim_allowed_trials = []  # store trial number when opto-stim is ON for this session, Grant Hughes, 11-13-25
        self.washout_trials = []
        
        # These are for logging which trial number the event occured on, relative to Tone-2 success counter
            # This Tone-2 Aligned matches reachCurators trial #, and also is eaiser for plotting since you dont want to plot trials with no tone-2 ie. no reach
        self.baseline_trials_tone2_aligned = []
        self.stim_allowed_trials_tone2_aligned = []  
        self.washout_trials_tone2_aligned = []

        self._need_new_delay_list = False #  Grant Hughes, 8-11-25 
        self.tone1_dur_ms = getattr(self, "tone1_dur_ms", 500)  # Grant Hughes, 8-11-25 , calibration, can move to user_cfg if desired


        
# Settting the GUI size and panels design
        displays = (wx.Display(i) for i in range(wx.Display.GetCount())) # Gets the number of displays
        screenSizes = [display.GetGeometry().GetSize() for display in displays] # Gets the size of each display
        index = 0 # For display 1.
        screenW = screenSizes[index][0]
        screenH = screenSizes[index][1]
        
        self.system_cfg = clara.read_config()
         # path to your YAML
        self.config_path = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            'systemdata.yaml'
        )
        # print it exactly once
        print(f"\n\n[INFO] handThreshold = {self.system_cfg['handThreshold']} "
              f"(from {self.config_path} → handThreshold)\n\n")
        print(f"[INFO] self.system_cfg[stimulusThreshold]: {self.system_cfg['stimulusThreshold']}")

        # ༼ つ ◕_◕ ༽つ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ☜༼ ◕_◕ ☜ ༽
        
        #--------- Grant Gughes, 08-15-2025  
        #--------- Working on getting a StimROI TTL to send an actual TTL
        #--------- This is after seeing that doing the following results in a clear TTL on the digital line 6. ( Arduino IDE > Arduino Leonardo \ COM5 > Serial Monitor + 'S' > stimROI TTL sent)
        
        # # New Code
        # self._stim_thr = self.system_cfg.get('stimulusThreshold',
        #                                      self.system_cfg.get('stimThreshold', 300))  # New Code
        # print(f"[INFO] stimulusThreshold used: {self._stim_thr}")  # New Code
        # self._stim_port = self.system_cfg.get('stim_ttl', {}).get('serial_port', 'COM5')  # New Code
        # self._stim_baud = int(self.system_cfg.get('stim_ttl', {}).get('baud', 9600))    # New Code
        # self._stim_ser = None      # New Code
        # self._stim_armed = False   # New Code
        # self._stim_fired = False   # New Code
        #         # New Code
        # self._stim_last_fire = 0.0
        
        # #--------- Grant Gughes, 08-19-2025  

        # # Fast stim serial (dedicated Arduino for optical TTL)
        # self._stim_ser = None
        # try:
        #     import serial  # pip install pyserial
        #     self._stim_ser = serial.Serial(self._stim_port, self._stim_baud,
        #                                    timeout=0, write_timeout=0)
        #     self._stim_ser.reset_input_buffer()
        #     self._stim_ser.reset_output_buffer()
        #     print(f"[StimSER] opened {self._stim_port} @ {self._stim_baud}")
        # except Exception as e:
        #     print(f"[StimSER] FAILED to open {self._stim_port}: {e}  (fallback to com=16)")
        
        # ༼ つ ◕_◕ ༽つ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈  ☜༼ ◕_◕ ☜ ༽
 

        key_list = list()
        for cat in self.system_cfg.keys():
            key_list.append(cat)
        self.camStrList = list()
        for key in key_list:
            if 'cam' in key:
                self.camStrList.append(key)
        self.slist = list()
        self.mlist = list()
        for s in self.camStrList:
            if not self.system_cfg[s]['ismaster']:
                self.slist.append(str(self.system_cfg[s]['serial']))
            else:
                self.mlist.append(str(self.system_cfg[s]['serial']))
        
        self.camCt = len(self.camStrList)
        
        self.gui_size = (1200,1750)
        if screenW > screenH:
            self.gui_size = (1950,850)
        wx.Frame.__init__ ( self, parent, id = wx.ID_ANY, title = 'RT Video Acquisition',
                            size = wx.Size(self.gui_size), pos = wx.DefaultPosition, style = wx.RESIZE_BORDER|wx.DEFAULT_FRAME_STYLE|wx.TAB_TRAVERSAL )
        self.statusbar = self.CreateStatusBar()
        self.statusbar.SetStatusText("")

        self.SetSizeHints(wx.Size(self.gui_size)) #  This sets the minimum size of the GUI. It can scale now!
        
###################################################################################################################################################
# Spliting the frame into top and bottom panels. Bottom panels contains the widgets. The top panel is for showing images and plotting!
        self.guiDim = 0
        if screenH > screenW:
            self.guiDim = 1
        topSplitter = wx.SplitterWindow(self)
        self.image_panel = ImagePanel(topSplitter,self.gui_size, self.camCt)
        self.widget_panel = WidgetPanel(topSplitter)
        if self.guiDim == 0:
            topSplitter.SplitVertically(self.image_panel, self.widget_panel,sashPosition=int(self.gui_size[0]*0.75))
        else:
            topSplitter.SplitHorizontally(self.image_panel, self.widget_panel,sashPosition=int(self.gui_size[1]*0.75))
        topSplitter.SetSashGravity(0.5)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(topSplitter, 1, wx.EXPAND)
        self.SetSizer(sizer)

###################################################################################################################################################
# Add Buttons to the WidgetPanel and bind them to their respective functions.
        
        

        wSpace = 0
        wSpacer = wx.GridBagSizer(5, 5)
        
        camctrlbox = wx.StaticBox(self.widget_panel, label="Camera Control")
        bsizer = wx.StaticBoxSizer(camctrlbox, wx.HORIZONTAL)
        camsizer = wx.GridBagSizer(5, 5)
        
        bw = 76
        vpos = 0
        
        self.reach_number = 0 # Grant Additon
        self.no_pellet_detect_count = 0  # Grant: count when no pellet appears in ROI

        
        self.init = wx.ToggleButton(self.widget_panel, id=wx.ID_ANY, label="Initialize", size=(bw,-1))
        camsizer.Add(self.init, pos=(vpos,0), span=(1,3), flag=wx.ALL, border=wSpace)
        self.init.Bind(wx.EVT_TOGGLEBUTTON, self.initCams)
        
        self.crop = wx.CheckBox(self.widget_panel, id=wx.ID_ANY, label="Crop")
        camsizer.Add(self.crop, pos=(vpos,3), span=(0,1), flag=wx.LEFT, border=wSpace)
        self.crop.SetValue(1)
        
        self.update_settings = wx.Button(self.widget_panel, id=wx.ID_ANY, label="Update Settings", size=(bw*2, -1))
        camsizer.Add(self.update_settings, pos=(vpos,6), span=(1,6), flag=wx.ALL, border=wSpace)
        self.update_settings.Bind(wx.EVT_BUTTON, self.updateSettings)
        self.update_settings.Enable(False)
        
        vpos+=1
        self.set_pellet_pos = wx.ToggleButton(self.widget_panel, id=wx.ID_ANY, label="Pellet", size=(bw, -1))
        camsizer.Add(self.set_pellet_pos, pos=(vpos,0), span=(0,3), flag=wx.TOP | wx.BOTTOM, border=3)
        self.set_pellet_pos.Bind(wx.EVT_TOGGLEBUTTON, self.setCrop)
        self.set_pellet_pos.Enable(False)
        
        
        self.set_roi = wx.ToggleButton(self.widget_panel, id=wx.ID_ANY, label="Hand ROI", size=(bw, -1))
        camsizer.Add(self.set_roi, pos=(vpos,3), span=(0,3), flag=wx.TOP, border=0)
        self.set_roi.Bind(wx.EVT_TOGGLEBUTTON, self.setCrop)
        self.set_roi.Enable(False)
        
        self.set_crop = wx.ToggleButton(self.widget_panel, id=wx.ID_ANY, label="Set Crop ROI", size=(bw*2, -1))
        camsizer.Add(self.set_crop, pos=(vpos,6), span=(0,6), flag=wx.TOP, border=0)
        self.set_crop.Bind(wx.EVT_TOGGLEBUTTON, self.setCrop)
        self.set_crop.Enable(False)
        
        vpos+=1
        self.play = wx.ToggleButton(self.widget_panel, id=wx.ID_ANY, label="Live", size=(bw, -1))
        camsizer.Add(self.play, pos=(vpos,0), span=(1,3), flag=wx.ALL, border=wSpace)
        self.play.Bind(wx.EVT_TOGGLEBUTTON, self.liveFeed)
        self.play.Enable(False)
        
        self.rec = wx.ToggleButton(self.widget_panel, id=wx.ID_ANY, label="Record", size=(bw, -1))
        camsizer.Add(self.rec, pos=(vpos,3), span=(1,3), flag=wx.ALL, border=wSpace)
        self.rec.Bind(wx.EVT_TOGGLEBUTTON, self.recordCam)
        self.rec.Enable(False)
        
        self.minRec = wx.SpinCtrl(self.widget_panel, value='20', size=(50, -1))
        self.minRec.Enable(False)
        min_text = wx.StaticText(self.widget_panel, label='M:')
        camsizer.Add(self.minRec, pos=(vpos,7), span=(1,2), flag=wx.ALL, border=wSpace)
        camsizer.Add(min_text, pos=(vpos,6), span=(1,1), flag=wx.TOP, border=5)
        self.minRec.SetMax(300)
        
        self.set_stim = wx.ToggleButton(self.widget_panel, id=wx.ID_ANY, label="Stim ROI", size=(bw, -1))
        camsizer.Add(self.set_stim, pos=(vpos,9), span=(0,3), flag=wx.TOP, border=0)
        self.set_stim.Bind(wx.EVT_TOGGLEBUTTON, self.setCrop)
        self.set_stim.Enable(False)
        
        camsize = 5
        vpos+=camsize
        bsizer.Add(camsizer, 1, wx.EXPAND | wx.ALL, 5)
        wSpacer.Add(bsizer, pos=(0, 0), span=(camsize,3),flag=wx.EXPAND|wx.TOP|wx.LEFT|wx.RIGHT, border=wSpace)
        # wSpacer.Add(bsizer, pos=(0, 0), span=(vpos,3),flag=wx.EXPAND|wx.TOP|wx.LEFT|wx.RIGHT, border=5)

        serctrlbox = wx.StaticBox(self.widget_panel, label="Serial Control")
        sbsizer = wx.StaticBoxSizer(serctrlbox, wx.HORIZONTAL)
        sersizer = wx.GridBagSizer(5, 5)
        
        vpos = 0
        
        self.send_home = wx.Button(self.widget_panel, id=wx.ID_ANY, label="Home", size=(bw, -1))
        sersizer.Add(self.send_home, pos=(vpos,0), span=(0,3), flag=wx.LEFT, border=wSpace)
        self.send_home.Bind(wx.EVT_BUTTON, self.comFun)
        
        self.load_pellet = wx.Button(self.widget_panel, id=wx.ID_ANY, label="Pellet", size=(bw, -1))
        sersizer.Add(self.load_pellet, pos=(vpos,3), span=(0,3), flag=wx.LEFT, border=wSpace)
        self.load_pellet.Bind(wx.EVT_BUTTON, self.comFun)
        
        self.send_pellet = wx.Button(self.widget_panel, id=wx.ID_ANY, label="Mouse", size=(bw, -1))
        sersizer.Add(self.send_pellet, pos=(vpos,6), span=(0,3), flag=wx.LEFT, border=wSpace)
        self.send_pellet.Bind(wx.EVT_BUTTON, self.comFun)
        
        self.trig_release = wx.Button(self.widget_panel, id=wx.ID_ANY, label="Release", size=(bw, -1))
        sersizer.Add(self.trig_release, pos=(vpos,9), span=(0,3), flag=wx.LEFT, border=wSpace)
        self.trig_release.Bind(wx.EVT_BUTTON, self.comFun)
        

        # -------------------- New Code: map keys H/P/M/R --- 12-14-2025 -----------------
        self.ID_KEY_HOME    = wx.NewIdRef().Id   # New Code
        self.ID_KEY_PELLET  = wx.NewIdRef().Id   # New Code
        self.ID_KEY_MOUSE   = wx.NewIdRef().Id   # New Code
        self.ID_KEY_RELEASE = wx.NewIdRef().Id   # New Code
        self.ID_KEY_INIT = wx.NewIdRef().Id  # New Code
        self.ID_KEY_LIVE   = wx.NewIdRef().Id   # New Code
        self.ID_KEY_RECORD = wx.NewIdRef().Id   # New Code

        self.Bind(wx.EVT_MENU, self._hotkey_home,    id=self.ID_KEY_HOME)     # New Code
        self.Bind(wx.EVT_MENU, self._hotkey_pellet,  id=self.ID_KEY_PELLET)   # New Code
        self.Bind(wx.EVT_MENU, self._hotkey_mouse,   id=self.ID_KEY_MOUSE)    # New Code
        self.Bind(wx.EVT_MENU, self._hotkey_release, id=self.ID_KEY_RELEASE)  # New Code
        self.Bind(wx.EVT_MENU, self._hotkey_init, id=self.ID_KEY_INIT)  # New Code
        self.Bind(wx.EVT_MENU, self._hotkey_live,   id=self.ID_KEY_LIVE)    # New Code
        self.Bind(wx.EVT_MENU, self._hotkey_record, id=self.ID_KEY_RECORD)  # New Code

        accel = wx.AcceleratorTable([                                      # New Code
            (0, ord('H'), self.ID_KEY_HOME),                                # New Code
            (0, ord('P'), self.ID_KEY_PELLET),                              # New Code
            (0, ord('M'), self.ID_KEY_MOUSE),                               # New Code
            (0, ord('R'), self.ID_KEY_RELEASE),                             # New Code
            (0, ord('I'), self.ID_KEY_INIT),  
            (0, ord('L'), self.ID_KEY_LIVE),     # New Code
            (0, ord('V'), self.ID_KEY_RECORD),   # New Code
        ])                                                                  # New Code
        self.SetAcceleratorTable(accel)                                    # New Code
        # --------------------------  12-14-2025  ----------------------------------------



        vpos+=1
        
        self.Xmag = wx.SpinCtrl(self.widget_panel, value=str(0), size=(bw, -1))
        min_text = wx.StaticText(self.widget_panel, label='X (mm):')
        sersizer.Add(min_text, pos=(vpos,0), span=(1,3), flag=wx.TOP, border=wSpace)
        sersizer.Add(self.Xmag, pos=(vpos,3), span=(1,3), flag=wx.ALL, border=wSpace)
        self.Xmag.SetMax(5)
        self.Xmag.SetMin(-5)
        self.Xmag.Bind(wx.EVT_SPINCTRL, self.comFun)
        
        self.Ymag = wx.SpinCtrl(self.widget_panel, value=str(0), size=(bw, -1))
        min_text = wx.StaticText(self.widget_panel, label='Y (mm):')
        sersizer.Add(min_text, pos=(vpos,6), span=(1,3), flag=wx.TOP, border=wSpace)
        sersizer.Add(self.Ymag, pos=(vpos,9), span=(1,3), flag=wx.ALL, border=wSpace)
        self.Ymag.SetMax(5)
        self.Ymag.SetMin(-5)
        self.Ymag.Bind(wx.EVT_SPINCTRL, self.comFun)
        
        vpos+=1
        
        self.Zmag = wx.SpinCtrl(self.widget_panel, value=str(0), size=(bw, -1))
        min_text = wx.StaticText(self.widget_panel, label='Z (mm):')
        sersizer.Add(min_text, pos=(vpos,0), span=(1,3), flag=wx.TOP, border=wSpace)
        sersizer.Add(self.Zmag, pos=(vpos,3), span=(1,3), flag=wx.ALL, border=wSpace)
        self.Zmag.SetMax(5)
        self.Zmag.SetMin(-5)
        self.Zmag.Bind(wx.EVT_SPINCTRL, self.comFun)
        
        self.send_stim = wx.Button(self.widget_panel, id=wx.ID_ANY, label="Send stim", size=(bw, -1))
        sersizer.Add(self.send_stim, pos=(vpos,6), span=(1,3), flag=wx.LEFT, border=wSpace)
        self.send_stim.Bind(wx.EVT_BUTTON, self.comFun)
        
        self.toggle_style = wx.Button(self.widget_panel, id=wx.ID_ANY, label=" ", size=(bw, -1))
        sersizer.Add(self.toggle_style, pos=(vpos,9), span=(1,3), flag=wx.LEFT, border=wSpace)
        self.toggle_style.Bind(wx.EVT_BUTTON, self.toggleStyle)
        
      
        
        vpos+=1
        
        self.tone_delay_min = wx.SpinCtrl(self.widget_panel, value=str(0), size=(bw, -1))
        min_text = wx.StaticText(self.widget_panel, label='Wait Min (ms):')
        sersizer.Add(min_text, pos=(vpos,0), span=(1,3), flag=wx.TOP, border=wSpace)
        sersizer.Add(self.tone_delay_min, pos=(vpos,3), span=(1,3), flag=wx.ALL, border=wSpace)
        self.tone_delay_min.SetMax(20000)
        self.tone_delay_min.SetMin(0)
        self.tone_delay_min.Bind(wx.EVT_SPINCTRL, self.comFun)
        
        self.tone_delay_max = wx.SpinCtrl(self.widget_panel, value=str(0), size=(bw, -1))
        min_text = wx.StaticText(self.widget_panel, label='Wait Max (ms):')
        sersizer.Add(min_text, pos=(vpos,6), span=(1,3), flag=wx.TOP, border=wSpace)
        sersizer.Add(self.tone_delay_max, pos=(vpos,9), span=(1,3), flag=wx.ALL, border=wSpace)
        self.tone_delay_max.SetMax(20000)
        self.tone_delay_max.SetMin(0)
        self.tone_delay_max.Bind(wx.EVT_SPINCTRL, self.comFun)
        
        vpos+=1
        
        self.delay_count = wx.SpinCtrl(self.widget_panel, value=str(0), size=(bw, -1))
        min_text = wx.StaticText(self.widget_panel, label='Interval #:')
        sersizer.Add(min_text, pos=(vpos,0), span=(1,3), flag=wx.TOP, border=wSpace)
        sersizer.Add(self.delay_count, pos=(vpos,3), span=(1,3), flag=wx.ALL, border=wSpace)
        self.delay_count.SetMax(50)
        self.delay_count.SetMin(1)
        self.delay_count.Bind(wx.EVT_SPINCTRL, self.comFun)

        self.auto_delay = wx.CheckBox(self.widget_panel, id=wx.ID_ANY, label="Delay pellet reveal", size=(bw*2, -1))
        sersizer.Add(self.auto_delay, pos=(vpos,6), span=(0,6), flag=wx.LEFT, border=wSpace)
        self.auto_delay.SetValue(0)
        self.auto_delay.Bind(wx.EVT_CHECKBOX, self.comFun)
        
        
        # New Code 11-10-2025  ⟶ immediately after the block above, before `sersize = vpos`
        vpos+=1  # New Code
        self.block_size_ctrl = wx.SpinCtrl(self.widget_panel, value=str(20), size=(bw, -1))  # New Code
        min_text = wx.StaticText(self.widget_panel, label='Trials Per Epoch:')  # New Code
        sersizer.Add(min_text, pos=(vpos,0), span=(1,3), flag=wx.TOP, border=wSpace)  # New Code
        sersizer.Add(self.block_size_ctrl, pos=(vpos,3), span=(1,3), flag=wx.ALL, border=wSpace)  # New Code
        self.block_size_ctrl.SetMin(1)  # New Code
        self.block_size_ctrl.SetMax(1000)  # New Code
        self.block_size_ctrl.Bind(wx.EVT_SPINCTRL, self.comFun)  # New Code
        # New Code 11-10-2025 
   
        sersize = vpos
        vpos = camsize
        sbsizer.Add(sersizer, 1, wx.EXPAND | wx.ALL, 5)
        wSpacer.Add(sbsizer, pos=(vpos, 0), span=(sersize,3),flag=wx.EXPAND|wx.TOP|wx.LEFT|wx.RIGHT, border=wSpace)
        
      #  self.serHlist = [self.send_home, self.auto_delay, self.load_pellet,
                          #self.trig_release, self.send_pellet, self.tone_delay_min,
                          #self.delay_count, self.tone_delay_max, self.send_stim,
                          #self.Xmag,self.Ymag,self.Zmag,self.toggle_style]
        # New Code 11-10-25
        self.serHlist = [self.send_home, self.auto_delay, self.load_pellet,
                          self.trig_release, self.send_pellet, self.tone_delay_min,
                          self.delay_count, self.tone_delay_max, self.send_stim,
                          self.Xmag, self.Ymag, self.Zmag, self.toggle_style,
                          self.block_size_ctrl]  # New Code
        # New Code 11-10-25

        for h in self.serHlist:
            h.Enable(False)
        
        wSpace = 10
        vpos+=sersize
        
        self.slider = wx.Slider(self.widget_panel, -1, 0, 0, 100,size=(300, -1), style=wx.SL_HORIZONTAL | wx.SL_AUTOTICKS | wx.SL_LABELS )
        wSpacer.Add(self.slider, pos=(vpos,0), span=(0,3), flag=wx.LEFT, border=wSpace)
        self.slider.Enable(False)
        
        vpos+=1
        
        start_text = wx.StaticText(self.widget_panel, label='Select user:')
        wSpacer.Add(start_text, pos=(vpos,0), span=(0,1), flag=wx.LEFT, border=wSpace)
        self.user_drop = wx.Choice(self.widget_panel, size=(100, -1), id=wx.ID_ANY, choices=[' '])
        wSpacer.Add(self.user_drop, pos=(vpos,1), span=(0,1), flag=wx.ALL, border=wSpace)
        self.user_drop.Bind(wx.EVT_CHOICE, self.selectUser)
        
        self.add_user = wx.Button(self.widget_panel, id=wx.ID_ANY, label="Add User")
        wSpacer.Add(self.add_user, pos=(vpos,2), span=(0,1), flag=wx.LEFT, border=wSpace)
        self.add_user.Bind(wx.EVT_BUTTON, self.addUser)
        
        vpos+=1
        
        start_text = wx.StaticText(self.widget_panel, label='Stim on:')
        wSpacer.Add(start_text, pos=(vpos,0), span=(0,1), flag=wx.LEFT, border=wSpace)
        protocol_list = ['First Reach','Pellet Arrival','Pellet Reveal']
        self.protocol = wx.Choice(self.widget_panel, size=(100, -1), id=wx.ID_ANY, choices=protocol_list)
        wSpacer.Add(self.protocol, pos=(vpos,1), span=(0,1), flag=wx.ALL, border=wSpace)
        self.protocol.SetSelection(1)
        self.protocol.Bind(wx.EVT_CHOICE, self.setProtocol)
        
        self.expt_id = wx.TextCtrl(self.widget_panel, id=wx.ID_ANY, value="SessionRef")
        wSpacer.Add(self.expt_id, pos=(vpos,2), span=(0,1), flag=wx.LEFT, border=wSpace)
        
        vpos+=1
        start_text = wx.StaticText(self.widget_panel, label='Automate:')
        wSpacer.Add(start_text, pos=(vpos,0), span=(0,1), flag=wx.LEFT, border=wSpace)
        
        self.auto_pellet = wx.CheckBox(self.widget_panel, id=wx.ID_ANY, label="Pellet")
        wSpacer.Add(self.auto_pellet, pos=(vpos,1), span=(0,1), flag=wx.LEFT, border=wSpace)
        self.auto_pellet.SetValue(0)
        self.auto_pellet.Bind(wx.EVT_CHECKBOX, self.autoPellet)
        self.auto_pellet.Enable(False)
        
        self.auto_stim = wx.CheckBox(self.widget_panel, id=wx.ID_ANY, label="Stimulus")
        wSpacer.Add(self.auto_stim, pos=(vpos,2), span=(0,1), flag=wx.LEFT, border=wSpace)
        self.auto_stim.SetValue(0)
        
        vpos+=1
        start_text = wx.StaticText(self.widget_panel, label='Inspect values within ROIs:')
        wSpacer.Add(start_text, pos=(vpos,0), span=(0,3), flag=wx.LEFT, border=wSpace)
        
        vpos+=1
        
        self.inspect_stim = wx.CheckBox(self.widget_panel, id=wx.ID_ANY, label="Stimulus")
        wSpacer.Add(self.inspect_stim, pos=(vpos,0), span=(0,1), flag=wx.LEFT, border=wSpace)
        self.inspect_stim.SetValue(0)
        self.inspect_stim.Enable(False)
        
        # in MainFrame.__init__, after self.toggle_style:
          # --- Replace the checkbox with a toggle button ---

        # Grant 07-07
        self.inspect_hand = wx.CheckBox(self.widget_panel, id=wx.ID_ANY, label="Hand")
        wSpacer.Add(self.inspect_hand, pos=(vpos,1), span=(0,1), flag=wx.LEFT, border=wSpace)
        self.inspect_hand.SetValue(0)
        
        self.inspect_pellet = wx.CheckBox(self.widget_panel, id=wx.ID_ANY, label="Pellet")
        wSpacer.Add(self.inspect_pellet, pos=(vpos,2), span=(0,1), flag=wx.LEFT, border=wSpace)
        self.inspect_pellet.SetValue(0)
        
        # Now a fresh row for Debug Threshold:
        vpos += 1
        self.debug_thresh = wx.CheckBox(self.widget_panel, id=wx.ID_ANY, label="Debug Threshold")
        wSpacer.Add(self.debug_thresh, pos=(vpos,0), span=(0,2), flag=wx.LEFT, border=wSpace)
        self.debug_thresh.SetValue(False)
        
        # Now a fresh row for Debug Threshold:
        vpos += 1
        self.check_delay = wx.CheckBox(self.widget_panel, id=wx.ID_ANY, label="Check Pellet Delay")
        wSpacer.Add(self.check_delay, pos=(vpos,0), span=(0,2), flag=wx.LEFT, border=wSpace)
        self.check_delay.SetValue(False)
        
        
        

        vpos+=2
        self.compress_vid = wx.Button(self.widget_panel, id=wx.ID_ANY, label="Compress Vids")
        wSpacer.Add(self.compress_vid, pos=(vpos,0), span=(0,1), flag=wx.LEFT, border=wSpace)
        self.compress_vid.Bind(wx.EVT_BUTTON, self.compressVid)
        # self.compress_vid.Enable(False)
        
        self.reach_Count = wx.ToggleButton(self.widget_panel, id=wx.ID_ANY, label="Reset Reach Count", size=(110, -1)) # Grant 04_14
        wSpacer.Add(self.reach_Count, pos=(vpos,1), span=(0,1), flag=wx.LEFT, border=wSpace)  # Grant 04_14
        self.reach_Count.Bind(wx.EVT_TOGGLEBUTTON, self.reachCount)  # Grant 04_14
        #self.play.Enable(False)  # Grant 04_14

        self.quit = wx.Button(self.widget_panel, id=wx.ID_ANY, label="Quit")
        wSpacer.Add(self.quit, pos=(vpos,2), span=(0,1), flag=wx.LEFT, border=wSpace)
        self.quit.Bind(wx.EVT_BUTTON, self.quitButton)
        self.Bind(wx.EVT_CLOSE, self.quitButton)

        self.widget_panel.SetSizer(wSpacer)
        wSpacer.Fit(self.widget_panel)
        self.widget_panel.Layout()
        
        self.disable4cam = [self.minRec, self.update_settings,
                            self.expt_id, self.set_pellet_pos, self.set_roi]
        
        self.onWhenCamEnabled = [self.play, self.rec, self.minRec,
                                 self.update_settings, self.set_pellet_pos, self.set_roi]

        self.liveTimer = wx.Timer(self, wx.ID_ANY)
        self.recTimer = wx.Timer(self, wx.ID_ANY)
        
        # --- Grant Hughes 8-19-2025 , working on stimROI --> Optical Pulses Delay
        #self.figure,self.axes,self.canvas = self.image_panel.getfigure()
        #self.figure.canvas.draw()
        # New Code
        # self.figure,self.axes,self.canvas = self.image_panel.getfigure()  # New Code
        # self._last_draw = 0.0                                             # New Code
        # self._draw_hz   = 30                                              # New Code
        # self.figure.canvas.draw()                                         # New Code
        # --- Grant Hughes 8-19-2025 , working on stimROI --> Optical Pulses Delay


        self.pellet_x = self.system_cfg['pelletXY'][0]
        self.pellet_y = self.system_cfg['pelletXY'][1]
        
        self.is_busy = Value(ctypes.c_byte, 0)
        self.roi = np.asarray(self.system_cfg['roiXWYH'], int)
        self.stimroi = np.asarray(self.system_cfg['stimXWYH'], int)
        self.failCt = 0
        
        self.currAxis = 0
        self.x1 = 0
        self.y1 = 0
        self.im = list()
        self.proto_str = 'none'
        
        self.figure,self.axes,self.canvas = self.image_panel.getfigure()
        
        self.im = list()
        self.delivery_delay = time.time()
        self.frmDims = [0,270,0,360]
        self.camIDlsit = list()
        self.dlc = Value(ctypes.c_byte, 0)
        self.stim_status = Value(ctypes.c_byte, 0)
        self.camaq = Value(ctypes.c_byte, 0)
        self.frmaq = Value(ctypes.c_int, 0)
        self.com = Value(ctypes.c_int, -1)
        self.mVal = Value(ctypes.c_int, 0)
        self.stim_selection = Value(ctypes.c_int, 0)
        self.del_style = Value(ctypes.c_int, 0)
        self.pellet_timing = time.time()
        self.pellet_status = 3
        self.pLoc = list()
        self.croprec = list()
        self.croproi = list()
        self.frame = list()
        self.frameBuff = list()
        self.dtype = 'uint8'
        self.frmGrab = list()
        self.size = self.frmDims[1]*self.frmDims[3]
        self.shape = [self.frmDims[1], self.frmDims[3]]
        frame = np.zeros(self.shape, dtype='ubyte')
        frameBuff = np.zeros(self.size, dtype='ubyte')
        self.markerSize = 6
        self.cropPts = list()    
        self.array4feed = list()
        self.roirec = list()
        self.stimrec = list()
        self.stimAxes = None
        self.trial_reset_count = 0  # Grant, Total trial resets due to early reach
        for ndx, s in enumerate(self.camStrList):
            self.camIDlsit.append(str(self.system_cfg[s]['serial']))
            self.croproi.append(self.system_cfg[s]['crop'])
            self.array4feed.append(Array(ctypes.c_ubyte, self.size))
            self.frmGrab.append(Value(ctypes.c_byte, 0))
            self.frame.append(frame)
            self.frameBuff.append(frameBuff)
            self.im.append(self.axes[ndx].imshow(self.frame[ndx],cmap='gray'))
            self.im[ndx].set_clim(0,255)
            self.points = [-10,-10,1.0]
            
            circle = [patches.Circle((-10, -10), radius=5, fc=[0.8,0,0], alpha=0.0)]
            self.pLoc.append(self.axes[ndx].add_patch(circle[0]))
            
            cpt = self.roi
            rec = [patches.Rectangle((cpt[0],cpt[2]), cpt[1], cpt[3], fill=False, ec = [0.25,0.75,0.25], linewidth=2, linestyle='-',alpha=0.0)]
            self.roirec.append(self.axes[ndx].add_patch(rec[0]))
            
            cpt = self.stimroi
            rec = [patches.Rectangle((cpt[0],cpt[2]), cpt[1], cpt[3], fill=False, ec = [0.5,0.5,0.5], linewidth=2, linestyle='-',alpha=0.0)]
            self.stimrec.append(self.axes[ndx].add_patch(rec[0]))
            
            cpt = self.croproi[ndx]
            self.cropPts.append(cpt)
            rec = [patches.Rectangle((cpt[0],cpt[2]), cpt[1], cpt[3], fill=False, ec = [0.25,0.25,0.75], linewidth=2, linestyle='-',alpha=0.0)]
            self.croprec.append(self.axes[ndx].add_patch(rec[0]))
            
            
            if self.system_cfg['axesRef'] == s:
                self.pelletAxes = self.axes[ndx]
                self.pLoc[ndx].set_center([self.pellet_x,self.pellet_y])
            if self.system_cfg['stimAxes'] == s:
                self.stimAxes = self.axes[ndx]
        
        if self.stimAxes == None:
            self.auto_stim.Enable(False)
            
        self.makeUserList()
        self.figure.canvas.draw()
        
        self.alpha = 0.8
        
        self.canvas.mpl_connect('button_press_event', self.onClick)
        self.Bind(wx.EVT_CHAR_HOOK, self.OnKeyPressed)
        
    
# ༼ つ ◕_◕ ༽つ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ☜༼ ◕_◕ ☜ ༽

#--------- Grant Gughes, 08-21-2025  
#--------- Working on: getting a StimROI TTL to send an actual TTL        
# # New Code
#     def _fire_stim_fast(self, reason="auto"):
#         t = time.perf_counter()
#         if getattr(self, "_stim_ser", None):
#             try:
#                 self._stim_ser.write(b"S")        # 'S' → Leonardo emits TTL immediately
#                 self._stim_ser.flush()            # ensure the byte leaves the host buffer
#                 return True
#             except Exception as e:
#                 print(f"[StimDBG] Serial write failed: {e}; falling back to com=16")
#         self.com.value = 16                        # legacy path via arduinoCtrl
#         return False

#     def _start_stim_latency_test(self):
#         self._stim_test_active   = True
#         self._stim_test_t0       = time.perf_counter()
#         self._stim_test_baseline = None
#         self._stim_test_timeout  = 1.5   # seconds
#         self._stim_test_delta    = int(self.system_cfg.get('stimOpticalRiseDelta', 20))
#         print(f"[StimTEST] armed  t0={self._stim_test_t0:.6f}  riseΔ={self._stim_test_delta}")
 
 # ༼ つ ◕_◕ ༽つ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈  ☜༼ ◕_◕ ☜ ༽
       
    def onKeepOpen(self, event):
        self.keep_open = self.keep_open_btn.GetValue()
    
    def write_user_config(self):
        usrdatadir = os.path.dirname(os.path.realpath(__file__))
        configname = os.path.join(usrdatadir, 'Users', self.user_drop.GetStringSelection() + '_userdata.yaml')
        with open(configname, 'w') as cf:
            ruamelFile = ruamel.yaml.YAML()
            ruamelFile.dump(self.user_cfg, cf)
            
    def addUser(self, event):
        dlg = wx.TextEntryDialog(self, 'Enter new user initials:', 'Add New User')
        if dlg.ShowModal() == wx.ID_OK:
            new_user = dlg.GetValue()
            usrdatadir = os.path.dirname(os.path.realpath(__file__))
            configname = os.path.join(usrdatadir, 'Users', new_user + '_userdata.yaml')
            with open(configname, 'w') as cf:
                ruamelFile = ruamel.yaml.YAML()
                ruamelFile.dump(self.user_cfg, cf)
            prev_user_path = os.path.join(self.userDir,'prev_user.txt')
            usrdata = open(prev_user_path, 'w')
            usrdata.write(new_user)
            usrdata.close()
            self.makeUserList()
                
        dlg.Destroy()
        
    def selectUser(self, event):
        usrdatadir = os.path.dirname(os.path.realpath(__file__))
        configname = os.path.join(usrdatadir, 'Users', self.user_drop.GetStringSelection() + '_userdata.yaml')
        prev_user_path = os.path.join(self.userDir,'prev_user.txt')
        usrdata = open(prev_user_path, 'w')
        usrdata.write(self.user_drop.GetStringSelection())
        usrdata.close()
        ruamelFile = ruamel.yaml.YAML()
        path = Path(configname)
        if os.path.exists(path):
            with open(path, 'r') as f:
                self.user_cfg = ruamelFile.load(f)
        else:
            self.user_cfg = 'none'
            
        self.tone_delay_min.SetValue(str(self.user_cfg['waitMin']))
        self.tone_delay_max.SetValue(str(self.user_cfg['waitMax']))
        self.delay_count.SetValue(str(self.user_cfg['waitCt']))
        self.make_delay_iters()
        self.protocol.SetSelection(self.user_cfg['protocolSelected'])
        self.setProtocol(None)
        self.setDelStyle()
        
        # New Code 11-10-2025
        # default if missing
        if 'blockSize' not in self.user_cfg:  # New Code
            self.user_cfg['blockSize'] = 20   # New Code
        self.block_size_ctrl.SetValue(int(self.user_cfg['blockSize']))  # New Code
        # New Code 11-10-2025

    def setProtocol(self, event):
        self.proto_str = self.protocol.GetStringSelection()
        self.user_cfg['protocolSelected'] = self.protocol.GetSelection()
        self.write_user_config()
        self.stim_selection.value = self.user_cfg['protocolSelected']
        
        if self.com.value < 0:
            return
        self.com.value = 5
        while self.com.value > 0:
            time.sleep(0.01)
        
    def toggleStyle(self, event):
        if self.user_cfg['deliveryStyle'] == 1:
            self.user_cfg['deliveryStyle'] = 0
        else:
            self.user_cfg['deliveryStyle'] = 1
        self.setDelStyle()
        
    def setDelStyle(self):
        if self.user_cfg['deliveryStyle'] == 1:
            self.del_style.value = 1
            self.toggle_style.SetLabel("Style B")
        else:
            self.del_style.value = 0
            self.toggle_style.SetLabel("Style A")
        self.write_user_config()
        
        if self.com.value < 0:
            return
        self.com.value = 15
        while self.com.value > 0:
            time.sleep(0.01)
        
    def makeUserList(self):
        usrdatadir = os.path.dirname(os.path.realpath(__file__))
        self.userDir = os.path.join(usrdatadir, 'Users')
        if not os.path.isdir(self.userDir):
            os.mkdir(self.userDir)
        user_list = [name for name in os.listdir(self.userDir) if name.endswith('.yaml')]
        user_list = [name[:-14] for name in user_list]
        self.current_user = 'Default'
        if not len(user_list):
            user_list = [self.current_user]
        else:
            if 'Default' in user_list:
                user_list.remove('Default')
            user_list = [self.current_user]+user_list
        self.user_drop.SetItems(user_list)
        prev_user_path = os.path.join(self.userDir,'prev_user.txt')
        self.user_drop.SetSelection(0)
        if os.path.isfile(prev_user_path):
            usrdata = open(prev_user_path, 'r')
            self.current_user = usrdata.readline().strip()
            usrdata.close()
            if self.current_user in user_list:
                self.user_drop.SetStringSelection(self.current_user)
        self.selectUser(None)
        
    def autoPellet_v1(self, event):
        if self.auto_pellet.GetValue():
            self.pellet_status = 2
            self.com.value = 9
            while self.com.value > 0:
                time.sleep(0.01)
        else:
            self.com.value = 10
            while self.com.value > 0:
                time.sleep(0.01)
                
    def autoPellet(self, event):
        if self.auto_pellet.GetValue():
            # start a brand new trial, not mid-delay
            self.pellet_status = 0
            self.trial_line_printed = False
            # optionally reset your timers so pelletHandler doesn’t see old timestamps
            self.pellet_timing = time.time()
            self.hand_timing = None

            self.com.value = 9
            while self.com.value > 0:
                time.sleep(0.01)
        else:
            self.com.value = 10
            while self.com.value > 0:
                time.sleep(0.01)

                
    def reachCount(self, event):
        self.reach_number = 0
        self.trial_reset_count = 0 # Grant, adds counter to total times mouse fails trial by hand in handROI
        self.no_pellet_detect_count = 0
        print(f'\n\n')
        print('----------------------------------------------------')
        print('Session Counters RESET')
        print('----------------------------------------------------\n\n')

        
        
    def make_delay_iters(self):
        minval = int(self.tone_delay_min.GetValue())
        maxval = int(self.tone_delay_max.GetValue())
        ctval = int(self.delay_count.GetValue())
        self.delay_values = np.linspace(minval, maxval, ctval)
        np.random.shuffle(self.delay_values)
        self.ordered_delay_values = sorted(self.delay_values)
        #self.first_delay = -1
        self.first_delay = self.delay_values[0]  # Set this here!
        print('----------------------------------------------------------------------------------------------------------------------------')
        print('New Random Delay List:', self.delay_values)
        #print('----------------------------------------------------------------------------------------------------------------------------')




    def comFun(self, event):
      # case 'A': //servoMax
      # case 'B': //servoMin
      # case 'C': //servoBaseVal
      # case 'D': // Set tone duration (ms)
      # case 'F': // Set tone frequency
      # case 'T': // Play tone 
      # case 'E': // No solenoid
      # case 'I': // Solenoid in
      # case 'O': // Solenoid out
      # case 'U': // Solenoids neutral
      # case 'Y': // Trigger solenoid
      # case 'P': // Get proximity reading
      # case 'L': // Load pellets into reservoir
      # case 'R': // Drop elevator to reveal pellet
      # case 'Q': // Raise elevator to load a single pellet
      
        if self.com.value < 0:
            return
        waitval = 0
        while not self.com.value == 0:
            time.sleep(1)
            waitval+=1
            if waitval > 10:
                break
        evobj = event.GetEventObject()
        if self.send_home == evobj:
            self.com.value = 1
        elif self.load_pellet == evobj:
            self.com.value = 2
        elif self.send_pellet == evobj:
            self.com.value = 3
        elif self.trig_release == evobj:
            self.com.value = 4
        elif self.tone_delay_min == evobj:
            self.user_cfg['waitMin'] = int(self.tone_delay_min.GetValue())
            self.write_user_config()
            self.make_delay_iters()
        elif self.delay_count == evobj:
            self.user_cfg['waitCt'] = int(self.delay_count.GetValue())
            self.write_user_config()
            if self.user_cfg['waitCt'] == 1:
                self.tone_delay_max.Enable(False)
            else:
                self.tone_delay_max.Enable(True)
            self.make_delay_iters()
        elif self.tone_delay_max == evobj:
            self.user_cfg['waitMax'] = int(self.tone_delay_max.GetValue())
            self.write_user_config()
            self.make_delay_iters()
        elif self.auto_delay == evobj:
            if self.auto_delay.GetValue():
                self.make_delay_iters()
        elif self.Xmag == evobj:
            self.mVal.value = self.Xmag.GetValue()
            self.com.value = 12
            
        # START Grant 07-10-2025, disabled the automatic pellet ROI movement when changing X,Y posiition in GUI
        elif self.Ymag == evobj:
            self.mVal.value = self.Ymag.GetValue()
            self.com.value = 13
            if self.set_pellet_pos.GetValue():
                self.pellet_x = self.system_cfg['pelletXY'][0] - self.Ymag.GetValue() * self.system_cfg['shiftFactor']
            else:
                self.pellet_x = self.system_cfg['pelletXY'][0] - 0  # hardcoded no visual move
            ndx = self.axes.index(self.pelletAxes)
            self.pLoc[ndx].set_center([self.pellet_x, self.pellet_y])
        elif self.Zmag == evobj:
            self.mVal.value = self.Zmag.GetValue()
            self.com.value = 14
            if self.set_pellet_pos.GetValue():
                self.pellet_y = self.system_cfg['pelletXY'][1] - self.Zmag.GetValue() * self.system_cfg['shiftFactor']
            else:
                self.pellet_y = self.system_cfg['pelletXY'][1] - 0  # hardcoded no visual move
            ndx = self.axes.index(self.pelletAxes)
            self.pLoc[ndx].set_center([self.pellet_x, self.pellet_y])
            
    # -------------------- New Code: single-key handlers --- 12-14-2025  --------------------
    def _hotkey_home(self, event):     # New Code
        self.com.value = 1            # New Code

    def _hotkey_pellet(self, event):   # New Code
        self.com.value = 2            # New Code

    def _hotkey_mouse(self, event):    # New Code
        self.com.value = 3            # New Code

    def _hotkey_release(self, event):  # New Code
        self.com.value = 4            # New Code
        
        # NEW CODE
    def _hotkey_init(self, event):
        # Toggle the Initialize button exactly as a click would
        new_state = not self.init.GetValue()
        self.init.SetValue(new_state)
        self.initCams(event)
    # NEW CODE
    def _hotkey_live(self, event):
        """
        Toggle Live / Stop exactly like clicking the Live button.
        """
        if not self.play.IsEnabled():
            return

        new_state = not self.play.GetValue()
        self.play.SetValue(new_state)
        self.liveFeed(event)


    # NEW CODE
    def _hotkey_record(self, event):
        """
        Toggle Record / Stop exactly like clicking the Record button.
        """
        if not self.rec.IsEnabled():
            return

        new_state = not self.rec.GetValue()
        self.rec.SetValue(new_state)
        self.recordCam(event)

    # -------------------------- 12-14-2025 --------------------------------------------

            
    def setCrop(self, event):
        self.widget_panel.Enable(False)
        
    def OnKeyPressed(self, event):
        # print(event.GetModifiers())
        # print(event.GetKeyCode())
        x = 0
        y = 0
        if event.GetKeyCode() == wx.WXK_RETURN or event.GetKeyCode() == wx.WXK_NUMPAD_ENTER:
            if self.set_pellet_pos.GetValue():
                self.system_cfg['pelletXY'][0] = self.pellet_x
                self.system_cfg['pelletXY'][1] = self.pellet_y
            elif self.set_roi.GetValue():
                self.system_cfg['roiXWYH'] = np.ndarray.tolist(self.roi)
            elif self.set_stim.GetValue():
                self.system_cfg['stimXWYH'] = np.ndarray.tolist(self.stimroi)
            elif self.set_crop.GetValue():
                ndx = self.axes.index(self.cropAxes)
                s = self.camStrList[ndx]
                self.system_cfg[s]['crop'] = np.ndarray.tolist(self.croproi[ndx])
        
            clara.write_config(self.system_cfg)
            self.set_pellet_pos.SetValue(False)
            self.set_roi.SetValue(False)
            self.set_stim.SetValue(False)
            self.set_crop.SetValue(False)
            self.widget_panel.Enable(True)
            self.play.SetFocus()
        elif self.set_pellet_pos.GetValue() or self.set_roi.GetValue() or self.set_crop.GetValue() or self.set_stim.GetValue():
            if event.GetKeyCode() == 314: #LEFT
                x = -1
                y = 0
            elif event.GetKeyCode() == 316: #RIGHT
                x = 1
                y = 0
            elif event.GetKeyCode() == 315: #UP
                x = 0
                y = -1
            elif event.GetKeyCode() == 317: #DOWN
                x = 0
                y = 1
            elif event.GetKeyCode() == 127: #DELETE
                if self.set_crop.GetValue():
                    ndx = self.axes.index(self.cropAxes)
                    self.croproi[ndx][0] = 0
                    self.croproi[ndx][2] = 0
                    for ndx in range(self.camCt):
                        self.croprec[ndx].set_alpha(0)
                    clara.write_config(self.system_cfg)
                    self.set_crop.SetValue(False)
                    self.widget_panel.Enable(True)
                    self.play.SetFocus()
                    self.figure.canvas.draw()
                elif self.set_stim.GetValue():
                    self.system_cfg['stimAxes'] = 'None'
                    self.stimAxes = None
                    for ndx in range(self.camCt):
                        self.stimrec[ndx].set_alpha(0)
                    self.stimroi[0] = 0
                    self.stimroi[2] = 0
                    clara.write_config(self.system_cfg)
                    self.set_stim.SetValue(False)
                    self.widget_panel.Enable(True)
                    self.play.SetFocus()
                    self.figure.canvas.draw()
        else:
            event.Skip()
            
        if self.set_pellet_pos.GetValue():
            self.pellet_x+=x
            self.pellet_y+=y
            self.drawROI()
        elif self.set_roi.GetValue():
            self.roi[0]+=x
            self.roi[2]+=y
            self.drawROI()
        elif self.set_stim.GetValue():
            self.stimroi[0]+=x
            self.stimroi[2]+=y
            self.drawROI()
        elif self.set_crop.GetValue():
            ndx = self.axes.index(self.cropAxes)
            self.croproi[ndx][0]+=x
            self.croproi[ndx][2]+=y
            self.drawROI()
            
            
        if self.set_crop.GetValue():
            ndx = self.axes.index(self.cropAxes)
            self.croproi[ndx][0]+=x
            self.croproi[ndx][2]+=y
            self.drawROI()
            
    def drawROI(self):
        ndx = self.axes.index(self.pelletAxes)
        if self.set_pellet_pos.GetValue():
            self.pLoc[ndx].set_center([self.pellet_x,self.pellet_y])
            self.pLoc[ndx].set_alpha(0.6)
        elif self.set_roi.GetValue():
            self.roirec[ndx].set_x(self.roi[0])
            self.roirec[ndx].set_y(self.roi[2])
            self.roirec[ndx].set_width(self.roi[1])
            self.roirec[ndx].set_height(self.roi[3])
            self.roirec[ndx].set_alpha(0.6)
        elif self.set_stim.GetValue():
            ndx = self.axes.index(self.stimAxes)
            self.stimrec[ndx].set_x(self.stimroi[0])
            self.stimrec[ndx].set_y(self.stimroi[2])
            self.stimrec[ndx].set_width(self.stimroi[1])
            self.stimrec[ndx].set_height(self.stimroi[3])
            self.stimrec[ndx].set_alpha(0.6)
        elif self.set_crop.GetValue():
            ndx = self.axes.index(self.cropAxes)
            self.croprec[ndx].set_x(self.croproi[ndx][0])
            self.croprec[ndx].set_y(self.croproi[ndx][2])
            self.croprec[ndx].set_width(self.croproi[ndx][1])
            self.croprec[ndx].set_height(self.croproi[ndx][3])
            if not self.croproi[ndx][0] == 0:
                self.croprec[ndx].set_alpha(0.6)
        self.figure.canvas.draw()
        
        
    def onClick(self,event):
        if self.set_pellet_pos.GetValue():
            for ndx in range(self.camCt):
                self.pLoc[ndx].set_alpha(0.0)

            self.system_cfg = clara.read_config()
            if self.stimAxes == event.inaxes:
                print('Stimulus camera must not be the pellet-detecting camera')
                self.set_pellet_pos.SetValue(False)
                self.widget_panel.Enable(True)
                return
            ndx = self.axes.index(event.inaxes)
            self.pelletAxes = event.inaxes
            self.system_cfg['axesRef'] = self.camStrList[ndx]
            self.pellet_x = int(event.xdata)
            self.pellet_y = int(event.ydata)
        elif self.set_roi.GetValue():
            for ndx in range(self.camCt):
                self.roirec[ndx].set_alpha(0.0)
                
            self.system_cfg = clara.read_config()
            if self.stimAxes == event.inaxes:
                print('Stimulus camera must not be the pellet-detecting camera')
                self.set_roi.SetValue(False)
                self.widget_panel.Enable(True)
                return
            ndx = self.axes.index(event.inaxes)
            self.pelletAxes = event.inaxes
            self.system_cfg['axesRef'] = self.camStrList[ndx]
            self.roi = np.asarray(self.system_cfg['roiXWYH'], int)
            roi_x = event.xdata
            roi_y = event.ydata
            self.roi = np.asarray([roi_x-self.roi[1]/2,self.roi[1],roi_y-self.roi[3]/2,self.roi[3]], int)
        elif self.set_stim.GetValue():
            for ndx in range(self.camCt):
                self.stimrec[ndx].set_alpha(0.0)
            
            self.system_cfg = clara.read_config()
            if self.pelletAxes == event.inaxes:
                print('Stimulus camera must not be the pellet-detecting camera')
                self.set_stim.SetValue(False)
                self.widget_panel.Enable(True)
                return
            ndx = self.axes.index(event.inaxes)
            self.stimAxes = event.inaxes
            self.system_cfg['stimAxes'] = self.camStrList[ndx]
            self.stimroi = np.asarray(self.system_cfg['stimXWYH'], int)
            roi_x = event.xdata
            roi_y = event.ydata
            self.stimroi = np.asarray([roi_x-self.stimroi[1]/2,self.stimroi[1],roi_y-self.stimroi[3]/2,self.stimroi[3]], int)
        elif self.set_crop.GetValue():
            for ndx in range(self.camCt):
                self.croprec[ndx].set_alpha(0.0)
                
            self.system_cfg = clara.read_config()
            self.cropAxes = event.inaxes
            ndx = self.axes.index(event.inaxes)
            s = self.camStrList[ndx]
            self.croproi[ndx] = self.system_cfg[s]['crop']
            roi_x = event.xdata
            roi_y = event.ydata
            self.croproi[ndx] = np.asarray([roi_x-self.croproi[ndx][1]/2,self.croproi[ndx][1],
                                            roi_y-self.croproi[ndx][3]/2,self.croproi[ndx][3]], int)
        self.drawROI()       
            
    def compressVid(self, event):
        ok2compress = False
        try:
            if not self.mv.is_alive():
                self.mv.terminate()   
                ok2compress = True
            else:
                if wx.MessageBox("Compress when transfer completes?", caption="Abort", style=wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION):
                    while self.mv.is_alive():
                        time.sleep(10)
                    self.mv.terminate()   
                    ok2compress = True
        except:
            ok2compress = True
        
        
        if ok2compress:
            print('\n\n---- Please DO NOT close this GUI until compression is complete!!! ----\n\n')
            self.mv = clara.moveVids()
            self.mv.start()
            while self.mv.is_alive():
                time.sleep(10)
            self.mv.terminate()   
            
            compressThread = compressVideos.CLARA_compress()
            compressThread.start()
            self.compress_vid.Enable(False)
        
    def camReset(self,event):
        self.initThreads()
        self.camaq.value = 2
        self.startAq()
        time.sleep(3)
        self.stopAq()
        self.deinitThreads()
        print('\n*** CAMERAS RESET ***\n')
    
    def runExpt(self,event):
        print('todo')
    def exptID(self,event):
        pass

    # NEW CODE 12-30-2025 ---------------------------------------------------------
    def _start_nonvideo_session(self, mode_tag: str):
        """
        Create session folder + metadata + .log for Live (non-video) or Record.
        For Record you already do this, but we will use it for Live.
        """
        date_string = datetime.datetime.now().strftime("%Y%m%d")
        self.date_string = date_string
        self.current_mode_tag = mode_tag

        base_dir = os.path.join(self.system_cfg['raw_data_dir'], date_string, self.system_cfg['unitRef'])
        os.makedirs(base_dir, exist_ok=True)

        prev_expt_list = [name for name in os.listdir(base_dir) if name.startswith('session')]
        maxSess = 0
        for p in prev_expt_list:
            try:
                sessNum = int(p[-3:])
                maxSess = max(maxSess, sessNum)
            except:
                pass

        file_count = maxSess + 1
        sess_string = f"session{file_count:03d}"
        self.sess_info = sess_string
        self.sess_string = sess_string
        self.sess_dir = os.path.join(base_dir, sess_string)
        os.makedirs(self.sess_dir, exist_ok=True)

        # Session log file (separate name for LIVE vs REC)
        log_path = Path(self.sess_dir) / f"{date_string}_{self.system_cfg['unitRef']}_{sess_string}_{mode_tag}.log"
        configure_logging(log_path)

        # Minimal metadata (so Live sessions have the same bookkeeping)
        self.meta, ruamelFile = clara.metadata_template()
        self.meta['ID'] = self.expt_id.GetValue()
        self.meta['Stim'] = self.proto_str
        self.meta['StartTime'] = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        self.meta['Mode'] = mode_tag  # New Code
        self.meta['MouseInfo'] = getattr(self, "mouse_info", "No mouse info provided")  # New Code 12-30-2025


        meta_name = f"{date_string}_{self.system_cfg['unitRef']}_{sess_string}_{mode_tag}_metadata.yaml"
        self.metapath = os.path.join(self.sess_dir, meta_name)
        clara.write_metadata(self.meta, self.metapath)


    def _save_nonvideo_outputs(self, mode_tag: str):
        """
        Save the same non-video arrays Record saves, but without any video.
        """
        if not hasattr(self, "sess_dir") or self.sess_dir is None:
            return

        delay_list_path = Path(self.sess_dir) / f"{self.date_string}_{self.system_cfg['unitRef']}_{self.sess_string}_{mode_tag}_trial_delays.npy"

        baseline_list_path = Path(self.sess_dir) / f"{self.date_string}_{self.system_cfg['unitRef']}_{self.sess_string}_{mode_tag}_baseline_trial_numbers.npy"
        stim_allowed_list_path = Path(self.sess_dir) / f"{self.date_string}_{self.system_cfg['unitRef']}_{self.sess_string}_{mode_tag}_stim_allowed_trial_numbers.npy"
        washout_list_path = Path(self.sess_dir) / f"{self.date_string}_{self.system_cfg['unitRef']}_{self.sess_string}_{mode_tag}_washout_trial_numbers.npy"

        baseline_tone2_aligned_list_path = Path(self.sess_dir) / f"{self.date_string}_{self.system_cfg['unitRef']}_{self.sess_string}_{mode_tag}_baseline_trial_numbers_tone2_aligned.npy"
        stim_allowed_tone2_aligned_list_path = Path(self.sess_dir) / f"{self.date_string}_{self.system_cfg['unitRef']}_{self.sess_string}_{mode_tag}_stim_allowed_trial_numbers_tone2_aligned.npy"
        washout_list_tone2_aligned_path = Path(self.sess_dir) / f"{self.date_string}_{self.system_cfg['unitRef']}_{self.sess_string}_{mode_tag}_washout_trial_numbers_tone2_aligned.npy"

        np.save(delay_list_path, np.array(self.trial_delays, dtype=np.int32))
        np.save(baseline_list_path, np.array(self.baseline_trials, dtype=np.int32))
        np.save(stim_allowed_list_path, np.array(self.stim_allowed_trials, dtype=object))
        np.save(washout_list_path, np.array(self.washout_trials, dtype=object))

        np.save(baseline_tone2_aligned_list_path, np.array(self.baseline_trials_tone2_aligned, dtype=np.int32))
        np.save(stim_allowed_tone2_aligned_list_path, np.array(self.stim_allowed_trials_tone2_aligned, dtype=object))
        np.save(washout_list_tone2_aligned_path, np.array(self.washout_trials_tone2_aligned, dtype=object))

        print(f"[INFO] Saved non-video data to {self.sess_dir}")

        import logging
        logging.shutdown()
    # NEW CODE 12-30-2025 ---------------------------------------------------------

    def liveFeed(self, event):
        if self.play.GetLabel() == 'Abort':
            self.rec.SetValue(False)
            self.recordCam(event)

            if wx.MessageBox("Are you sure?", caption="Abort", style=wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION):
                shutil.rmtree(self.sess_dir)
                time.sleep(5)
            self.play.SetValue(False)

        elif self.play.GetValue() == True:
            if not self.liveTimer.IsRunning():
                # === NEW 12-31-25 : Mouse info dialog (same as Record) ===
                dlg = wx.TextEntryDialog(
                    self,
                    'Enter mouse information (e.g. Mouse ID, genotype, surgery date):',
                    'Mouse Info',
                    ''
                )
                if dlg.ShowModal() == wx.ID_OK:
                    self.mouse_info = dlg.GetValue().strip()
                    if self.mouse_info == "":
                        self.mouse_info = "No mouse info provided"
                else:
                    self.mouse_info = "Mouse info entry cancelled"
                dlg.Destroy()

                if not self.pellet_x == 0:
                    if not self.roi[0] == 0:
                        self.pellet_timing = time.time()
                        self.pellet_status = 3

                # NEW CODE: start a LIVE session folder + log + metadata (NO VIDEO)
                self._start_nonvideo_session(mode_tag="LIVE")      # New Code 12-30-2025
                self.data_logging_enabled = True                   # New Code 12-30-2025

                            # === NEW: write header into LIVE log ===
                print('----------------------------------------------------------------------')
                print(f'🧬 Mouse Info: {self.mouse_info}')
                print(f"Session Information: {self.date_string}_{self.system_cfg['unitRef']}_{self.sess_string}_LIVE")
                print(f"Session Save Dir: {self.sess_dir}")
                print('----------------------------------------------------------------------\n')

                # OPTIONAL but strongly recommended: reset per-session arrays/counters for Live
                self.trial_delays.clear()                          # New Code 12-30-2025
                self.baseline_trials.clear()                       # New Code 12-30-2025
                self.stim_allowed_trials.clear()                   # New Code 12-30-2025
                self.washout_trials.clear()                        # New Code 12-30-2025
                self.baseline_trials_tone2_aligned.clear()         # New Code 12-30-2025
                self.stim_allowed_trials_tone2_aligned.clear()     # New Code 12-30-2025
                self.washout_trials_tone2_aligned.clear()          # New Code 12-30-2025

                # (If you want Live sessions to start from clean counters)
                self.reachCount(event)                             # New Code 12-30-2025

                self.camaq.value = 1
                self.startAq()
                self.liveTimer.Start(150)

                self.play.SetLabel('Stop')

            for h in self.disable4cam:
                h.Enable(False)

        else:
            if self.liveTimer.IsRunning():
                self.liveTimer.Stop()


            # === NEW: 12-31-2025 stop logging ===
            self.data_logging_enabled = False

            # === NEW:  12-31-2025 print final summary INTO LOG ===
            total_trial_count = self.trial_reset_count + self.reach_number + self.no_pellet_detect_count
            if total_trial_count == 0:
                total_trial_count = 1

            print('\n\n')
            print('───────────────────────────────────────────────')
            print(f'📄 {self.sess_info} LIVE Summary')
            print('───────────────────────────────────────────────')
            print(f" #️⃣     Total Trials:          {total_trial_count}")
            print(f"✔️     Tone-2 Successes:      {self.reach_number} ({(self.reach_number / total_trial_count)*100:.1f}%)")
            print(f"⚠️    Early Reach Resets:    {self.trial_reset_count} ({(self.trial_reset_count / total_trial_count)*100:.1f}%)")
            print(f"🚫    No Pellet Detections:  {self.no_pellet_detect_count} ({(self.no_pellet_detect_count / total_trial_count)*100:.1f}%)")
            print(f'💡     Total Stimulation Epochs: {len(self.stim_allowed_trials)}')
            print(f"💧     Total Washout Epochs: {len(self.washout_trials)}")
            print('───────────────────────────────────────────────\n')

            self._save_nonvideo_outputs(mode_tag="LIVE")           # New Code 12-30-2025

            # NEW CODE (add immediately after entering else)
            # self.data_logging_enabled = False   # New Code 12-30-2025
            print("RECORD STOP")

            self.stopAq()
            time.sleep(2)
            self.play.SetLabel('Live')
            self.rec.Enable(True)
            for h in self.disable4cam:
                h.Enable(True)

        
    def pelletHandler(self, pim, roi):
        # events    0 - release pellet
        #           1 - load pellet
        #           2 - waiting to lose it
        
        # 07-16-2025, grant, checking for pellet causing trial [1]
        if not hasattr(self, 'hand_timing'):
            self.hand_timing = time.time()
            
     
        if self.com.value < 0:
            return
        objDetected = False
        if pim > self.system_cfg['pelletThreshold']:
            objDetected = True
            
        if self.is_busy.value == -1:
            self.auto_pellet.SetValue(0)
            self.autoPellet(event=None)
            dlg = wx.MessageDialog(parent=None,message="Home position failed!",
                                   caption="Warning!", style=wx.OK|wx.ICON_EXCLAMATION)
            dlg.ShowModal()
            dlg.Destroy()
            return
        # checked 
        if self.is_busy.value == 0:
            getNewPellet = False
            if self.del_style.value == 0:
                wait2detect = 2
            else: 
                wait2detect = 2
                # objDetected = True
            # checked 
            if self.pellet_status == 0:
               # print('send to mouse')
                self.com.value = 3
                while self.com.value > 0:
                    time.sleep(0.01)
                self.pellet_timing = time.time()
                self.pellet_status = 1
            # checked 
            elif self.pellet_status == 1:
                if self.del_style.value == 0:
                    if objDetected:
                        self.hand_timing = time.time()
                        self.pellet_timing = time.time()
                        self.pellet_status = 2
                        self.failCt = 0
                        self.com.value = 6
                        # 07-16-2025
                        self.trial_line_printed = False
                    # checked
                    elif (time.time()-self.pellet_timing) > wait2detect:
                        self.failCt+=1
                        self.no_pellet_detect_count += 1
                        print('----------------------------------------------------------------------------------------------------------------------------')
                        total_trial_count = self.trial_reset_count + self.reach_number + self.no_pellet_detect_count
                        if total_trial_count == 0:
                            perecent_no_pellet = 100
                        else:
                            perecent_no_pellet = (self.no_pellet_detect_count / total_trial_count) * 100
                        print(f"[{total_trial_count}] 🚫 No pellet detected in ROI || No Pellet Count: {self.no_pellet_detect_count} ({perecent_no_pellet:.1f}%)")
                        # checked
                        if self.failCt > 3:
                            self.failCt = 0
                            beepList = [1,1,1]
                            self.auto_pellet.SetValue(0)
                            self.autoPellet(event=None)
                            self.pellet_timing = time.time()
                            self.pellet_status = 3
                            # checked
                            for d in beepList: 
                                duration = d  # seconds
                                freq = 940  # Hz
                                winsound.Beep(freq, duration)
                                time.sleep(d)
                        else:
                            getNewPellet = True
                            
                else:
                    self.hand_timing = time.time()
                    self.pellet_timing = time.time()
                    self.pellet_status = 2
                    self.trial_line_printed = False  # <-- ADD THIS LINE
                    
            
            elif self.pellet_status == 2:
                reveal_pellet = False
                
                
                # Grant 07-08 ─── Compute remaining time once ───
                if getattr(self, 'record_start_time', None) is not None:
                    elapsed   = time.time() - self.record_start_time
                    remaining = max(self.totTime - elapsed, 0)
                    m = int(remaining // 60)
                    s = int(remaining % 60)
                else:
                    #m = s = None  # guard if not recording
                    m = 0
                    s = 0
                    
                    
                                    
                #if int(self.delay_count.GetValue()) == 1:
                    #delayval = int(self.tone_delay_min.GetValue()) / 1000
                    #self.curr_trial_delay_ms = int(self.tone_delay_min.GetValue())
                  
                #else:
                    #delayval = self.delay_values[0] / 1000
                    #self.curr_trial_delay_ms = int(self.delay_values[0])
                    
                # Grant Hughes, 8-11-2025,
                if int(self.delay_count.GetValue()) == 1:
                    raw_ms = int(self.tone_delay_min.GetValue())
                else:
                    raw_ms = int(self.delay_values[0])
                
                self.curr_trial_delay_ms = raw_ms  # for logging/saving the intended delay
                
                # Apply calibration: wait for (intended_delay - tone1_duration)
                effective_ms = max(raw_ms - 500, 0)
                delayval = effective_ms / 1000.0

                
                
                
                    
                if not getattr(self, 'trial_line_printed', False):
                    total_trial_count = self.trial_reset_count + self.reach_number + self.no_pellet_detect_count
                    print('----------------------------------------------------------------------------------------------------------------------------')
                    self.trial_line_printed = True
                    

                        
                if self.debug_thresh.GetValue():
                    current_val = roi
                    set_thresh  = self.system_cfg['handThreshold']
                    diff        = current_val - set_thresh
                
                    print(f"HandROI Set Threshold: {set_thresh}   //   Per Trial Threshold= {current_val:.1f},   //   Value from trial reset= {diff:.1f}")
                reveal_pellet = False
                
               
                              


               # 1) If paw is STILL in the hand-ROI, reset immediately
                if roi >= self.system_cfg['handThreshold']:
                    
                    getNewPellet = True
                    self.trial_reset_count += 1
                    total_trial_count = self.trial_reset_count + self.reach_number + self.no_pellet_detect_count
                    self.total_trials = total_trial_count
                    perecent_failed_reaches = (self.trial_reset_count / total_trial_count) * 100
                    if self.check_delay.GetValue():
                            ## --- measure actual waiting ---
                            now_check = time.time()
                            elapsed_check = now_check - self.hand_timing
        #                     Log both intended and actual
                            print(f"[PELLET DELAY] intended delay: {self.curr_trial_delay_ms} ms, actual wait: {elapsed_check*1000:.1f} ms")
                   
                    print(f"[{total_trial_count}] ⚠️   Delay {self.curr_trial_delay_ms} ms || Early Reach Resets: {self.trial_reset_count} ({perecent_failed_reaches:.0f}%) || Trial Number: {total_trial_count} || [REC] {m} min {s:02d} sec remaining")
              

                # 2) Paw is out of the hand-ROI → do your normal delay → reveal logic
                else:
                    # Non-delayed mode
                    if not self.auto_delay.GetValue():
                        #if (time.time() - self.hand_timing) > self.user_cfg['waitAfterHand']:

                        reveal_pellet = True

                    # Auto-delay mode
    
                    if self.hand_timing is not None:
                        if (time.time() - self.hand_timing) > delayval:
                            # rotate delays and reset if we've cycled
                            difference = time.time() - self.hand_timing
                            self.delay_values = np.roll(self.delay_values, shift=-1)
                            if self.first_delay == self.delay_values[0]:
                                self._need_new_delay_list = True   # Grant Hughes, 8-11-25, defer remake until after we log the reveal
                                # self.make_delay_iters()  # Grant Hughes, 8-11-25,
                            reveal_pellet = True

                    # Failsafe: if something goes really wrong, reset after maxWait
                    if (time.time() - self.pellet_timing) > self.user_cfg['maxWait4Hand']:
                        getNewPellet = True
                    

                    
                if reveal_pellet == True: # Reveal pellet
                    self.reach_number += 1
                    # -- Grant Hughes, 8-15-2025 
                    # -- Added single line bellow, trying to get stimROI to send TTL
                    self._stim_armed = True   # New Code
                    
                    # 9-29-2025, New Code gate stim arming by 20-trial blocks of Tone-2 successes
                    #block_size = 5
                   # block_index = (self.reach_number - 1) // block_size
                    #stim_allowed = (block_index % 2 == 1)
                    
                    # New Code 11-10-25
                    # Gate stim arming by N-trial blocks from GUI
                    block_size = int(self.block_size_ctrl.GetValue()) if hasattr(self, 'block_size_ctrl') else int(self.user_cfg.get('blockSize', 20))  # New Code
                    self.block_size_logging = block_size
                    block_index = (self.reach_number - 1) // block_size  # New Code
                    stim_allowed = (block_index % 2 == 1)  # New Code
                    # Trial number within the current block/epoch (1..block_size)
                    trial_in_epoch = ((self.reach_number - 1) % block_size) + 1  # New Code
                                        
                    if block_index == 0:
                        # First block: baseline, no stim
                        stim_allowed = False  # New Code
                        current_epoch = 0     # New Code (optional; useful for logging)
                        current_block = 'Baseline epoch'  # New Code
                    else:
                        # For blocks 1,2,3,...:
                        # block_index: 1,2 -> epoch 1; 3,4 -> epoch 2; etc.
                        current_epoch = min((block_index + 1) // 2, 5)  # cap at epoch 5  # New Code
                    
                        if block_index % 2 == 1:
                            # Odd block_index: stimulation block (1,3,5,7,9)
                            stim_allowed = True  # New Code
                            current_block = f'Stimulation Epoch #{current_epoch}'  # New Code
                        else:
                            # Even block_index: washout block (2,4,6,8,10)
                            stim_allowed = False  # New Code
                            current_block = f'Washout Epoch #{current_epoch}'  # New Code
                    
                    # Optional: human-readable progress label, e.g. "3/20 Stimulation Epoch #1"
                    epoch_progress_label = f"{trial_in_epoch}/{block_size} {current_block}"  # New Code
                                        # New Code 11-10-25

                    self._stim_armed = stim_allowed
                    
                    # Only log during active recording
                    # if self.rec.GetValue():
                    #     self.trial_delays.append(self.curr_trial_delay_ms)

                    # NEW CODE 12-30-2025
                    if self.data_logging_enabled:
                        self.trial_delays.append(self.curr_trial_delay_ms)
                    
                    # Log this trial's delay only once, at reveal time, grant hughes, 8-11-2025
                    #self.trial_delays.append(self.curr_trial_delay_ms)
                    
                    total_trial_count = self.trial_reset_count + self.reach_number + self.no_pellet_detect_count
                    perecent_successful_reaches = (self.reach_number / total_trial_count) * 100
                    #expected_delay = delayval
                    self.com.value = 4
                    if self.check_delay.GetValue():
                            ## --- measure actual waiting ---
                            now_check = time.time()
                            elapsed_check = now_check - self.hand_timing
        #                     Log both intended and actual
                            print(f"[PELLET DELAY] intended delay: {self.curr_trial_delay_ms} ms, actual wait: {elapsed_check*1000:.1f} ms")
                   
                    print(f"[{total_trial_count}] ✔️    Delay {self.curr_trial_delay_ms} ms || {epoch_progress_label} || Tone-2 Success Count: {self.reach_number} ({perecent_successful_reaches:.0f}%) || Trial Number: {total_trial_count} || [REC] {m} min {s:02d} sec remaining")
                   
                    # Only log during active recording
                    #if self.rec.GetValue():
                        #if stim_allowed:
                            #total_trial_count = self.trial_reset_count + self.reach_number + self.no_pellet_detect_count
                            #self.stim_allowed_trials.append(total_trial_count)
                        #else:
                            #total_trial_count = self.trial_reset_count + self.reach_number + self.no_pellet_detect_count
                            #self.washout_trials.append(total_trial_count)
    
                            
                            # Only log during active recording (nested by epoch)
                    # if self.rec.GetValue():  # New Code
                    if self.data_logging_enabled:  # New Code 12-30-2025
                        total_trial_count = self.trial_reset_count + self.reach_number + self.no_pellet_detect_count  # New Code
                        if block_index == 0:
                            self.baseline_trials.append(total_trial_count)
                            self.baseline_trials_tone2_aligned.append(self.reach_number)
                        # Skip baseline (block_index == 0) and only log stim/washout epochs  # New Code
                        if block_index > 0 and current_epoch >= 1:  # New Code
                            if stim_allowed:  # New Code
                                # Ensure list exists for this epoch (1-indexed → 0-indexed)  # New Code
                                while len(self.stim_allowed_trials) < current_epoch:  # New Code
                                    self.stim_allowed_trials.append([])              # New Code
                                    self.stim_allowed_trials_tone2_aligned.append([])  
                                self.stim_allowed_trials[current_epoch - 1].append(total_trial_count)  # New Code
                                self.stim_allowed_trials_tone2_aligned[current_epoch - 1].append(self.reach_number)  # New Code

                            else:  # washout trial  # New Code
                                while len(self.washout_trials) < current_epoch:      # New Code
                                    self.washout_trials.append([]) 
                                    self.washout_trials_tone2_aligned.append([]) # New Code
                                self.washout_trials[current_epoch - 1].append(total_trial_count)  # New Code
                                self.washout_trials_tone2_aligned[current_epoch - 1].append(self.reach_number)  # New Code

                    # Grant Hughes, 8-11-25, NOW, after the reveal line has printed, announce and rebuild the next list if we completed a cycle
                    if getattr(self, "_need_new_delay_list", False):
                        self.make_delay_iters()
                        self._need_new_delay_list = False
                   
                    
                    if self.del_style.value == 1:
                        self.pellet_status = 4
                    else:
                        self.pellet_status = 3
                    self.pellet_timing = time.time()
                    self.delivery_delay = time.time()
                    if self.auto_stim.GetValue() and self.proto_str == 'First Reach':
                        #self.stim_status.value = 1
                        if stim_allowed:
                            self.stim_status.value = 1
                        else:
                            self.stim_status.value = 0
                    #print('revealing pellet')
                    
            elif self.pellet_status == 3: # Test whether to get new pellet
            
            
                # # ༼ つ ◕_◕ ༽つ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ☜༼ ◕_◕ ☜ ༽
                
                # #--------- Grant Gughes, 08-15-2025  
                # #--------- Working on getting a StimROI TTL to send an actual TTL
                
                # if self.auto_stim.GetValue():
                #     # grab stim ROI mean the same way inspect_stim prints it
                #     ndx = self.axes.index(self.stimAxes)
                #     stim_cpt = self.stimroi
                #     stim_val = self.frame[ndx][stim_cpt[2]:stim_cpt[2]+stim_cpt[3],
                #                                 stim_cpt[0]:stim_cpt[0]+stim_cpt[1]].mean()
                    
                # # New Code, 8-18-2025
                #     thr = self.system_cfg.get('stimulusThreshold', self.system_cfg.get('stimThreshold', 300))
                    
                #     #print(f"[StimDBG] threshold={thr}  roi_mean={stim_val:.1f}  armed={getattr(self,'_stim_armed', False)}")

                #     if (stim_val >= thr) and getattr(self, '_stim_armed', False):
                #         #print('\n\n  -- stimulusThreshold PASSED --\n\n')  # New Code
                #         #print(f"[stimTTL] val={stim_val:.1f} thr={thr} armed={self._stim_armed}")  # New Code
                #         # self.com.value = 16  # New Code → arduinoCtrl sends 'S' → main .ino pulses pin 12 for ~5 ms
                #         # while self.com.value > 0:  # New Code
                #         #     time.sleep(0.01)       # New Code
                #         self._stim_armed = False   # New Code  fire once per reveal
                                                            
                # # ༼ つ ◕_◕ ༽つ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈  ☜༼ ◕_◕ ☜ ༽
                
                
                
                if not objDetected:
                    if (time.time()-self.delivery_delay) > self.user_cfg['minTime2Eat']:
                        getNewPellet = True
                elif (time.time()-self.delivery_delay) > self.user_cfg['maxTime2Eat']:
                    getNewPellet = True
                    
                    
            elif self.pellet_status == 4: #style B object detection listener
                if objDetected:
                    self.com.value = 6
                    self.pellet_status = 3
                elif (time.time()-self.pellet_timing) > wait2detect:
                    getNewPellet = True
                    
                
            if getNewPellet:
                self.trial_line_printed = False  # ✅ MOVE IT HERE
                if self.auto_stim.GetValue() and self.proto_str == 'First Reach':
                    self.stim_status.value = 0
                    # ༼ つ ◕_◕ ༽つ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ☜༼ ◕_◕ ☜ ༽
                    
                    #--------- Grant Gughes, 08-15-2025  
                    #--------- Working on getting a StimROI TTL to send an actual TTL
                    self._stim_armed = False  # New Code
                  
                self.com.value = 2
                while self.com.value > 0:
                    time.sleep(0.01)
                self.pellet_status = 0
                self.pellet_timing = time.time()
  
                  
              # ---- only reload/close the door if “Keep door open” is FALSE ----
              #if not getattr(self, 'keep_open', False):
                  # existing reload logic
                  #self.com.value = 2
                  #while self.com.value > 0:
                      #time.sleep(0.01)
                  #self.pellet_status = 0
                  #self.pellet_timing = time.time()
              #else:
         
                  #self.pellet_status = 0
                  #self.pellet_timing = time.time()
    
    
            
    def vidPlayer_v1(self, event):
        # Was the delivery style changed using the physical button?
        if not self.user_cfg['deliveryStyle'] == self.del_style.value:
            self.user_cfg['deliveryStyle'] = self.del_style.value
            self.setDelStyle()
            
        if self.camaq.value == 2:
            return
        for ndx, im in enumerate(self.im):
            if self.frmGrab[ndx].value == 1:
                self.frameBuff[ndx][0:] = np.frombuffer(self.array4feed[ndx].get_obj(), self.dtype, self.size)
                frame = self.frameBuff[ndx][0:self.dispSize[ndx]].reshape([self.aqH[ndx], self.aqW[ndx]])
                self.frame[ndx][self.y1[ndx]:self.y2[ndx],self.x1[ndx]:self.x2[ndx]] = frame
                im.set_data(self.frame[ndx])
                if not self.pellet_x == 0:
                    if not self.roi[0] == 0:
                        if self.inspect_stim.GetValue():
                            if self.system_cfg['stimAxes'] == self.camStrList[ndx]:
                                print('Stimulation ROI - %d' % np.mean(np.sum(frame,axis=0)[:5]))
                        if self.pelletAxes == self.axes[ndx]:
                            span = 6
                            cpt = np.asarray([self.pellet_x-span,span*2+1,self.pellet_y-span,span*2+1], int)
                            pim = self.frame[ndx][cpt[2]:cpt[2]+cpt[3],cpt[0]:cpt[0]+cpt[1]]
                            cpt = self.roi
                            roi = self.frame[ndx][cpt[2]:cpt[2]+cpt[3],cpt[0]:cpt[0]+cpt[1]]
                            if self.inspect_pellet.GetValue():
                                print('Pellet ROI - %d' % np.mean(pim[:]))
                            if self.inspect_hand.GetValue():
                                print('Hand ROI - %d' % np.mean(roi[:]))
                            
                            if self.auto_pellet.GetValue():
                                self.pelletHandler(np.mean(pim[:]),np.mean(roi[:]))
                self.frmGrab[ndx].value = 0
                
        self.figure.canvas.draw()
        

# ༼ つ ◕_◕ ༽つ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ☜༼ ◕_◕ ☜ ༽

#--------- Grant Gughes, 08-15-2025  
#--------- Working on getting a StimROI TTL to send an actual TTL
# Fast StimROI trigger on the stim camera's own frames   
    def vidPlayer_v2(self, event):
        # Sync delivery style if the hardware button changed it
        if not self.user_cfg['deliveryStyle'] == self.del_style.value:
            self.user_cfg['deliveryStyle'] = self.del_style.value
            self.setDelStyle()
    
        if self.camaq.value == 2:
            return
    
        for ndx, im in enumerate(self.im):
            if self.frmGrab[ndx].value == 1:
                # Pull latest frame from shared buffer
                self.frameBuff[ndx][0:] = np.frombuffer(self.array4feed[ndx].get_obj(), self.dtype, self.size)
                frame = self.frameBuff[ndx][0:self.dispSize[ndx]].reshape([self.aqH[ndx], self.aqW[ndx]])
                self.frame[ndx][self.y1[ndx]:self.y2[ndx], self.x1[ndx]:self.x2[ndx]] = frame
    
                # ── Stim ROI: compute on the stim camera's own frames for minimal latency ──
                if self.auto_stim.GetValue() and (self.axes[ndx] == self.stimAxes):
                    cpt = self.stimroi
                    stim_val = self.frame[ndx][cpt[2]:cpt[2]+cpt[3], cpt[0]:cpt[0]+cpt[1]].mean()
                    thr = self.system_cfg.get('stimulusThreshold', self.system_cfg.get('stimThreshold', 300))
    
                    # Always show live values (useful when tuning threshold)
                    print(f"[StimROI] mean={stim_val:.1f}  thr={thr}  armed={getattr(self,'_stim_armed', False)}")

    
                    # Fire TTL as soon as threshold is crossed and we're armed
                    if getattr(self, '_stim_armed', False) and (stim_val >= thr):
                        #print(f"[StimROI] FIRE  mean={stim_val:.1f} ≥ thr={thr}")
                        if hasattr(self, '_fire_stim_fast'):
                            # Preferred: direct, low-latency serial write
                            self._fire_stim_fast("roi")
                        else:
                            # Fallback to existing Arduino command path
                            self.com.value = 16
                        self._stim_armed = False  # one shot per arm
    
                # Update display
                im.set_data(self.frame[ndx])
    
                # Pellet / Hand ROI debug + automation
                if not self.pellet_x == 0 and not self.roi[0] == 0:
                    if self.inspect_stim.GetValue() and (self.system_cfg['stimAxes'] == self.camStrList[ndx]):
                        print('Stimulation ROI (legacy print) - %d' % np.mean(np.sum(frame, axis=0)[:5]))
    
                    if self.pelletAxes == self.axes[ndx]:
                        span = 6
                        cpt = np.asarray([self.pellet_x - span, span*2 + 1, self.pellet_y - span, span*2 + 1], int)
                        pim = self.frame[ndx][cpt[2]:cpt[2]+cpt[3], cpt[0]:cpt[0]+cpt[1]]
                        cpt = self.roi
                        roi = self.frame[ndx][cpt[2]:cpt[2]+cpt[3], cpt[0]:cpt[0]+cpt[1]]
    
                        if self.inspect_pellet.GetValue():
                            print('Pellet ROI - %d' % np.mean(pim[:]))
                        if self.inspect_hand.GetValue():
                            print('Hand ROI - %d' % np.mean(roi[:]))
    
                        if self.auto_pellet.GetValue():
                            self.pelletHandler(np.mean(pim[:]), np.mean(roi[:]))
    
                self.frmGrab[ndx].value = 0
                
        # --- Grant Hughes 8-19-2025, Working on stimROI --> Optical Pulses delay
        _now = time.perf_counter()                                                    # New Code
        if (_now - getattr(self, "_last_draw", 0.0)) >= (1.0 / getattr(self,"_draw_hz",30)):  # New Code
            self.figure.canvas.draw()                                                 # New Code
            self._last_draw = _now  
            
        #self.figure.canvas.draw()
        # --- Grant Hughes 8-19-2025, Working on stimROI --> Optical Pulses delay


  # ༼ つ ◕_◕ ༽つ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈  ☜༼ ◕_◕ ☜ ༽
  
# ༼ つ ◕_◕ ༽つ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ⇊ ☜༼ ◕_◕ ☜ ༽

#--------- Grant Gughes, 08-21-2025  
#--------- Working on getting a StimROI TTL to send an actual TTL
# Fast StimROI trigger on the stim camera's own frames   
    def vidPlayer(self, event):
        
        #  9-29-2025 New Code inside vidPlayer
        
        #block_size = 20
       # block_index = (self.reach_number - 1) // block_size
       # stim_allowed = (block_index % 2 == 1)

        # New Code 11-10-2025
        block_size = int(self.block_size_ctrl.GetValue()) if hasattr(self, 'block_size_ctrl') else int(self.user_cfg.get('blockSize', 20))  # New Code
        block_index = (self.reach_number - 1) // block_size  # New Code
        stim_allowed = (block_index % 2 == 1)  # New Code
        # New Code 11-10-2025


        # Keep delivery style in sync
        if self.user_cfg['deliveryStyle'] != self.del_style.value:
            self.user_cfg['deliveryStyle'] = self.del_style.value
            self.setDelStyle()
    
        if self.camaq.value == 2:
            return
    
        # 1) Process the stim camera FIRST for lowest latency
        order = list(range(len(self.im)))
        try:
            stim_idx = self.axes.index(self.stimAxes) if self.stimAxes is not None else None
        except ValueError:
            stim_idx = None
        if stim_idx is not None and stim_idx in order:
            order.remove(stim_idx)
            order = [stim_idx] + order
    
        # 2) Iterate in chosen order
        for ndx in order:
            im = self.im[ndx]
            if self.frmGrab[ndx].value != 1:
                continue
    
            # Pull latest frame
            self.frameBuff[ndx][0:] = np.frombuffer(self.array4feed[ndx].get_obj(), self.dtype, self.size)
            frame = self.frameBuff[ndx][0:self.dispSize[ndx]].reshape([self.aqH[ndx], self.aqW[ndx]])
            self.frame[ndx][self.y1[ndx]:self.y2[ndx], self.x1[ndx]:self.x2[ndx]] = frame
    
            # ── Stim ROI check on stim camera frames only ──
            if self.auto_stim.GetValue() and (self.axes[ndx] == self.stimAxes):
                cpt = self.stimroi
                stim_val = self.frame[ndx][cpt[2]:cpt[2]+cpt[3], cpt[0]:cpt[0]+cpt[1]].mean()
                thr = self.system_cfg.get('stimulusThreshold', self.system_cfg.get('stimThreshold', 300))
               # print(f"[StimROI] mean={stim_val:.1f}  thr={thr}  armed={getattr(self,'_stim_armed', False)}")

                # immediate fire with 100 ms refractory to avoid double-fires on noisy frames
                now = time.perf_counter()
                last = getattr(self, "_stim_last_fire", 0.0)
                refractory = 0.10
                
                # 9-29-2025, New Code: Added and stim_allowed to line below
                if getattr(self, "_stim_armed", False) and stim_allowed and (stim_val >= thr) and (now - last >= refractory):
                    if hasattr(self, "_fire_stim_fast"):
                        self._fire_stim_fast("roi")
                    else:
                        self.com.value = 16
                    self._stim_armed = False
                    self._stim_last_fire = now  # store monotonic timestamp
                    

    
            # Update display buffer
            im.set_data(self.frame[ndx])
    
            # Pellet/Hand ROI + automation path
            if (self.pellet_x != 0) and (self.roi[0] != 0):
                if self.inspect_stim.GetValue() and (self.system_cfg['stimAxes'] == self.camStrList[ndx]):
                    print('Stimulation ROI (legacy print) - %d' % np.mean(np.sum(frame, axis=0)[:5]))
    
                if self.pelletAxes == self.axes[ndx]:
                    span = 6
                    cpt = np.asarray([self.pellet_x - span, span*2 + 1, self.pellet_y - span, span*2 + 1], int)
                    pim = self.frame[ndx][cpt[2]:cpt[2]+cpt[3], cpt[0]:cpt[0]+cpt[1]]
                    cpt = self.roi
                    roi = self.frame[ndx][cpt[2]:cpt[2]+cpt[3], cpt[0]:cpt[0]+cpt[1]]
    
                    if self.inspect_pellet.GetValue():
                        print('Pellet ROI - %d' % np.mean(pim[:]))
                    if self.inspect_hand.GetValue():
                        print('Hand ROI - %d' % np.mean(roi[:]))
    
                    if self.auto_pellet.GetValue():
                        self.pelletHandler(np.mean(pim[:]), np.mean(roi[:]))
    
            self.frmGrab[ndx].value = 0
    
        # Throttle GUI drawing
        _now = time.perf_counter()
        if (_now - getattr(self, "_last_draw", 0.0)) >= (1.0 / getattr(self, "_draw_hz", 30)):
            self.figure.canvas.draw()
            self._last_draw = _now
  # ༼ つ ◕_◕ ༽つ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈ ⇈  ☜༼ ◕_◕ ☜ ༽

        
# Grant Hughes 07-31-2025 \\ Testing to fix the delay pellet reveal 
# I set liveRate = 50 , which is a drop from liveRate = 250 // but this made the recording keep going when the timer was up. 
# so this new def autoCapture() function is a test for that
    def autoCapture_v1(self, event):
        self.sliderTabs+=self.sliderRate
        msg = '-'
        if (self.sliderTabs > self.slider.GetMax()) and not (msg == 'fail'):
            self.rec.SetValue(False)
            self.recordCam(event)
            self.slider.SetValue(0)
        else:
            self.slider.SetValue(round(self.sliderTabs))
            self.vidPlayer(event)
                
    def autoCapture(self, event):
        # 1) Stop based on real elapsed time
        elapsed = time.time() - self.record_start_time
        if elapsed >= self.totTime:
            # Time’s up — stop recording
            self.rec.SetValue(False)
            self.recordCam(event)
            return
    
        # 2) Otherwise update slider and continue capturing
        self.sliderTabs += self.sliderRate
        if self.sliderTabs > self.slider.GetMax():
            # (This branch is now redundant, but safe to keep)
            self.rec.SetValue(False)
            self.recordCam(event)
        else:
            self.slider.SetValue(round(self.sliderTabs))
            self.vidPlayer(event)
        
    def recordCam(self, event):
        if self.rec.GetValue():
            # NEW CODE 12-30-2025
            self.data_logging_enabled = True
            self.current_mode_tag = "REC"
    
            # New Code: reset per-recording state that must not carry over
            if not hasattr(self, "trial_delays"):  # New Code
                self.trial_delays = [] 
                # These are aligned to All trial counter, meaning it incldues all tone-1 in the count even when no tone-2 occurs
                self.baseline_trials = []
                self.stim_allowed_trials = []
                self.washout_trials = []
                # These are for logging which trial number the event occured on, relative to Tone-2 success counter
                    # This Tone-2 Aligned matches reachCurators trial #, and also is eaiser for plotting since you dont want to plot trials with no tone-2 ie. no reach
                self.baseline_trials_tone2_aligned = []
                self.stim_allowed_trials_tone2_aligned = []  
                self.washout_trials_relative_tone2_aligned = []
            else:                                 # New Code
                self.trial_delays.clear()         # New Code
                self.stim_allowed_trials.clear()
                self.washout_trials.clear()
                self.baseline_trials.clear()
                self.baseline_trials_tone2_aligned.clear()
                self.stim_allowed_trials_tone2_aligned.clear()
                self.washout_trials_tone2_aligned.clear()


            self._need_new_delay_list = False     # New Code
            
            # New Code
            self.reachCount(event)                # keep counters reset after clearing delays
            

            
            # ─────────────────────────────────────────────
            # Grant 07-11-2025: Prompt for Mouse Information
            # ─────────────────────────────────────────────
            dlg = wx.TextEntryDialog(
                self,
                'Enter mouse information (e.g. Mouse ID, genotype, surgery date):',
                'Mouse Info',
                ''
            )
            if dlg.ShowModal() == wx.ID_OK:
                self.mouse_info = dlg.GetValue().strip()
                if self.mouse_info == "":
                    self.mouse_info = "No mouse info provided"
            else:
                self.mouse_info = "Mouse info entry cancelled"
            dlg.Destroy()
        
            print('----------------------------------------------------------------------')
            print(f'🧬 Mouse Info: {self.mouse_info}')
            print('----------------------------------------------------------------------\n')
           
            # Grant 07-11-2025, Resetting reach counters at start of new recording
            self.reachCount(event)
            
            # Grant 07-11-2025, logging the delay values
            #self.delay_values = np.linspace(minval, maxval, ctval)
            self.make_delay_iters()
          

            self.reach_number = 0 # Grant Additon
            
           # Grant 07-08 ─── Record start time & total duration ───
            self.record_start_time = time.time()
            self.totTime = int(self.minRec.GetValue()) * 60  # total seconds

            self.compress_vid.Enable(False)
            self.system_cfg = clara.read_config()
            
            # Grant Hughes, 7-31-2025 \\ working on +500ms delay pellet reveal issue \\ Test #1
            # Change Notes: changed liveRate = 250 to liveRate = 50
            #liveRate = 250
            #liveRate = 50
            # Grant Hughes, 8-19-2025 \\ working on stimROI --> optical pulses latency
            ## Dropped liverate = 50 down to liverate = 1
            liveRate = 250

            
            self.Bind(wx.EVT_TIMER, self.autoCapture, self.recTimer)
            if int(self.minRec.GetValue()) == 0:
                return
            totTime = int(self.minRec.GetValue())*60

            
            for ndx, s in enumerate(self.camStrList):
                camID = str(self.system_cfg[s]['serial'])
                self.camq[camID].put('recordPrep')
                self.camq[camID].put('none')
                self.camq_p2read[camID].get()
            
            spaceneeded = 0
            for ndx, w in enumerate(self.aqW):
                recSize = w*self.aqH[ndx]*3*self.recSet[ndx]*totTime
                spaceneeded+=recSize
                
            self.slider.SetMax(100)
            self.slider.SetMin(0)
            self.slider.SetValue(0)
            self.sliderTabs = 0
            self.sliderRate = 100/(totTime/(liveRate/1000))
        
            date_string = datetime.datetime.now().strftime("%Y%m%d")
            self.date_string = date_string  # <-- store for later use

            base_dir = os.path.join(self.system_cfg['raw_data_dir'], date_string, self.system_cfg['unitRef'])
            if not os.path.exists(base_dir):
                os.makedirs(base_dir)
            freespace = shutil.disk_usage(base_dir)[2]
            if spaceneeded > freespace:
                dlg = wx.MessageDialog(parent=None,message="There is not enough disk space for the requested duration.",
                                       caption="Warning!", style=wx.OK|wx.ICON_EXCLAMATION)
                dlg.ShowModal()
                dlg.Destroy()
                self.rec.SetValue(False)
                return
            
            prev_expt_list = [name for name in os.listdir(base_dir) if name.startswith('session')]
            maxSess = 0;
            for p in prev_expt_list:
                sessNum = int(p[-3:])
                if sessNum > maxSess:
                    maxSess = sessNum
            comp_dir = os.path.join(self.system_cfg['interim_data_dir'], date_string, self.system_cfg['unitRef'])
            if os.path.exists(comp_dir):
                prev_expt_list = [name for name in os.listdir(comp_dir) if name.startswith('session')]
                for p in prev_expt_list:
                    sessNum = int(p[-3:])
                    if sessNum > maxSess:
                        maxSess = sessNum
                        

            
            file_count = maxSess+1
            sess_string = '%s%03d' % ('session', file_count)
            self.sess_info = sess_string
            self.sess_dir = os.path.join(base_dir, sess_string)
            self.sess_string = sess_string  # <-- store for later use


            if not os.path.exists(self.sess_dir):
                os.makedirs(self.sess_dir)
            self.meta,ruamelFile = clara.metadata_template()
                
           
            # 07-09-2025, Grant Hughes, for logging
            log_path = Path(self.sess_dir) / f"{date_string}_{self.system_cfg['unitRef']}_{sess_string}.log"
            configure_logging(log_path)
            recording_duration_min = self.totTime / 60
            max_wait_time = self.ordered_delay_values[-1]
            
            print('----------------------------------------------------------------------')
            print('----------------------------------------------------------------------')
            print(f'🧬 Mouse Info: {self.mouse_info}')
            print('')
            print(f"Session Information: {date_string}_{self.system_cfg['unitRef']}_{sess_string}")
            print(f"Session Save Path: {log_path}")
            print('')
            print(f'Set Recording Duration: {recording_duration_min:.0f} minutes')
            print(f'Delay Pellet Reveal Times (ms): {self.ordered_delay_values}')
            print(f'Max Wait (ms): {max_wait_time:.0f}')
            print('----------------------------------------------------------------------')
            print('----------------------------------------------------------------------\n\n\n')
            

    
                
            self.meta,ruamelFile = clara.metadata_template()
            
            self.meta['duration (s)']=totTime
            self.meta['ID']=self.expt_id.GetValue()
            self.meta['placeholderA']='info'
            self.meta['placeholderB']='info'
            self.meta['Designer']='name'
            self.meta['Stim']=self.proto_str
            self.meta['StartTime']=datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            self.meta['Collection']='info'
            meta_name = '%s_%s_%s_metadata.yaml' % (date_string, self.system_cfg['unitRef'], sess_string)
            self.metapath = os.path.join(self.sess_dir,meta_name)
            usrdatadir = os.path.dirname(os.path.realpath(__file__))
            self.currUsr= self.user_drop.GetStringSelection()
            usrconfigname = os.path.join(usrdatadir,'Users', f'{self.currUsr}_userdata.yaml')
            sysconfigname = os.path.join(usrdatadir, 'systemdata.yaml')
            usrcopyname = '%s_%s_%s_%s_userdata_copy.yaml' % (date_string, self.system_cfg['unitRef'], sess_string, self.currUsr)
            syscopyname = '%s_%s_%s_systemdata_copy.yaml' % (date_string, self.system_cfg['unitRef'], sess_string)
            shutil.copyfile(usrconfigname,os.path.join(self.sess_dir,usrcopyname))
            shutil.copyfile(sysconfigname,os.path.join(self.sess_dir,syscopyname))
            
            
            for ndx, s in enumerate(self.camStrList):
                camID = str(self.system_cfg[s]['serial'])
                name_base = '%s_%s_%s_%s' % (date_string, self.system_cfg['unitRef'], sess_string, self.system_cfg[s]['nickname'])
                path_base = os.path.join(self.sess_dir,name_base)
                self.camq[camID].put(path_base)
                self.camq_p2read[camID].get()
            
            if self.com.value >= 0:
                self.ardq.put('recordPrep')
                name_base = '%s_%s_%s' % (date_string, self.system_cfg['unitRef'], sess_string)
                path_base = os.path.join(self.sess_dir,name_base)
                self.ardq.put(path_base)
                self.ardq_p2read.get()
                
            for h in self.disable4cam:
                h.Enable(False)
            self.protocol.Enable(False)
            
            if not self.recTimer.IsRunning():
                if self.auto_pellet.GetValue():
                    if not self.pellet_x == 0:
                        if not self.roi[0] == 0:
                            self.pellet_timing = time.time()
                            self.hand_timing = time.time()
                            self.pellet_status = 3
                            self.delivery_delay = time.time()
                
                self.camaq.value = 1
                self.startAq()
                self.recTimer.Start(liveRate)
            self.rec.SetLabel('Stop')
            self.play.SetLabel('Abort')
        else:
            self.compress_vid.Enable(True)
            self.com.value = 11
            while self.com.value > 0:
                time.sleep(0.01)
            
            if self.com.value >= 0:
                self.ardq.put('Stop')
            
            self.meta['duration (s)']=round(self.meta['duration (s)']*(self.sliderTabs/100))
            clara.write_metadata(self.meta, self.metapath)
            if self.recTimer.IsRunning():
                self.recTimer.Stop()
                
            # 🟩 Summary log
            total_trial_count = self.trial_reset_count + self.reach_number  + self.no_pellet_detect_count
            if total_trial_count == 0:
                total_trial_count = 1  # avoid divide-by-zero
            print('\n\n')
            print('───────────────────────────────────────────────')
            print(f'📄 {self.sess_info} Recording Summary')
            print('───────────────────────────────────────────────')
            print(f" #️⃣     Total Trials:          {total_trial_count}")
            print(f"✔️     Tone-2 Successes:      {self.reach_number} ({(self.reach_number / total_trial_count)*100:.1f}%)")
            print(f"⚠️    Early Reach Resets:    {self.trial_reset_count} ({(self.trial_reset_count / total_trial_count)*100:.1f}%)")
            print(f"🚫    No Pellet Detections:  {self.no_pellet_detect_count} ({(self.no_pellet_detect_count / total_trial_count)*100:.1f}%)")
            #print(f"🔟    Epoch Sizes:   {self.block_size_logging}")
            print(f'💡     Total Stimulation Epochs: {len(self.stim_allowed_trials)}')
            print(f"💧     Total Washout Epochs: {len(self.washout_trials)}")
            print('───────────────────────────────────────────────\n')
            print('───────────────────────────────────────────────\n\n')
            print('\n\n\n')
            print('───────────────────────────────────────────────')
            print('Epoch Data')
            print('───────────────────────────────────────────────\n\n')
            print('--- All Trials Aligned ---')
            print('\n')
            print("Baseline Trails / Epochs:", self.baseline_trials)
            print('\n')
            print("Optical Stimulation Trials / Epochs:", self.stim_allowed_trials)
            print('\n')
            print("Washout Trials / Epochs:", self.washout_trials)
            print('\n\n\n')
            print('')
            print('--- Tone-2 Aligned Trials ---')
            print('\n')
            print("Baseline Trails / Epochs:", self.baseline_trials_tone2_aligned)
            print('\n')
            print("Optical Stimulation Trials / Epochs:", self.stim_allowed_trials_tone2_aligned)
            print('\n')
            print("Washout Trials / Epochs:", self.washout_trials_tone2_aligned)
            print('\n\n\n')
            print('───────────────────────────────────────────────')
            print('File Save Locations')
            print('───────────────────────────────────────────────\n\n')

            # ✅ Save trial delays array, grant hughes, 8-11-25
            delay_list_path = Path(self.sess_dir) / f"{self.date_string}_{self.system_cfg['unitRef']}_{self.sess_string}_trial_delays.npy"

            baseline_list_path = Path(self.sess_dir) / f"{self.date_string}_{self.system_cfg['unitRef']}_{self.sess_string}_baseline_trial_numbers.npy"
            stim_allowed_list_path = Path(self.sess_dir) / f"{self.date_string}_{self.system_cfg['unitRef']}_{self.sess_string}_stim_allowed_trial_numbers.npy"
            washout_list_path = Path(self.sess_dir) / f"{self.date_string}_{self.system_cfg['unitRef']}_{self.sess_string}_washout_trial_numbers.npy"
                      
            baseline_tone2_aligned_list_path = Path(self.sess_dir) / f"{self.date_string}_{self.system_cfg['unitRef']}_{self.sess_string}_baseline_trial_numbers_tone2_aligned.npy"
            stim_allowed_tone2_aligned_list_path = Path(self.sess_dir) / f"{self.date_string}_{self.system_cfg['unitRef']}_{self.sess_string}_stim_allowed_trial_numbers_tone2_aligned.npy"
            washout_list_tone2_aligned_path = Path(self.sess_dir) / f"{self.date_string}_{self.system_cfg['unitRef']}_{self.sess_string}_washout_trial_numbers_tone2_aligned.npy"

            np.save(delay_list_path, np.array(self.trial_delays, dtype=np.int32))
            
            # stim / washout are now nested per epoch → use dtype=object
            np.save(baseline_list_path, np.array(self.baseline_trials, dtype=np.int32))
            np.save(stim_allowed_list_path, np.array(self.stim_allowed_trials, dtype=object))  # New Code
            np.save(washout_list_path, np.array(self.washout_trials, dtype=object)) 
            # stim / washout are now nested per epoch → use dtype=object
            np.save(baseline_tone2_aligned_list_path, np.array(self.baseline_trials_tone2_aligned, dtype=np.int32))
            np.save(stim_allowed_tone2_aligned_list_path, np.array(self.stim_allowed_trials_tone2_aligned, dtype=object))  # New Code
            np.save(washout_list_tone2_aligned_path, np.array(self.washout_trials_tone2_aligned, dtype=object)) 

           # np.save(stim_allowed_list_path, np.array(self.stim_allowed_trials, dtype=np.int32))
           # np.save(washout_list_path, np.array(self.washout_trials, dtype=np.int32))

            print(f"[INFO] Saved trial delays to {delay_list_path}")
            print('')
            print(f"[INFO] Saved baseline_list_path to {baseline_list_path}")
            print(f"[INFO] Saved stim_allowed_trials to {stim_allowed_list_path}")
            print(f"[INFO] Saved washout_list_path to {washout_list_path}")
            print('')
            print(f"[INFO] Saved baseline_trials_tone2_aligned to {baseline_tone2_aligned_list_path}")
            print(f"[INFO] Saved stim_allowed_trials_tone2_aligned to {stim_allowed_tone2_aligned_list_path}")
            print(f"[INFO] Saved washout_trials_tone2_aligned to {washout_list_tone2_aligned_path}")

                        
           
            # Cleanly close logging
            import logging
            logging.shutdown()
            # 2) Remove any FileHandlers so future prints aren't captured
            root_logger = logging.getLogger()
            for handler in root_logger.handlers[:]:
                if isinstance(handler, logging.FileHandler):
                    root_logger.removeHandler(handler)
                    handler.close()

                
            self.stopAq()
            time.sleep(2)
            
            ok2move = False
            try:
                if not self.mv.is_alive():
                    self.mv.terminate()   
                    ok2move = True
            except:
                ok2move = True
            if self.play == event.GetEventObject():
                ok2move = False
            if ok2move:
                self.mv = clara.moveVids()
                self.mv.start()
            
            self.slider.SetValue(0)
            self.rec.SetLabel('Record')
            self.play.SetLabel('Play')
            self.protocol.Enable(True)
            for h in self.disable4cam:
                h.Enable(True)
    
    def initThreads(self):
        self.camq = dict()
        self.camq_p2read = dict()
        self.cam = list()
        for ndx, camID in enumerate(self.camIDlsit):
            self.camq[camID] = Queue()
            self.camq_p2read[camID] = Queue()
            self.cam.append(spin.multiCam_DLC_Cam(self.camq[camID], self.camq_p2read[camID],
                                               camID, self.camIDlsit,
                                               self.frmDims, self.camaq,
                                               self.frmaq, self.array4feed[ndx], self.frmGrab[ndx],
                                               self.com, self.stim_status))
            self.cam[ndx].start()
            
        for m in self.mlist:
            self.camq[m].put('InitM')
            self.camq_p2read[m].get()
        for s in self.slist:
            self.camq[s].put('InitS')
            self.camq_p2read[s].get()
        
        self.ardq = Queue()
        self.ardq_p2read = Queue()
        self.ard = arduino.arduinoCtrl(self.ardq, self.ardq_p2read, self.frmaq, self.com,
                                       self.is_busy, self.mVal, self.stim_status, self.stim_selection, self.del_style)
        self.ard.start()
        self.ardq_p2read.get()
        
    def deinitThreads(self):
        for n, camID in enumerate(self.camIDlsit):
            self.camq[camID].put('Release')
            self.camq_p2read[camID].get()
            self.camq[camID].close()
            self.camq_p2read[camID].close()
            self.cam[n].terminate()
        if self.com.value >= 0:
            self.ardq.put('Release')
            self.ardq_p2read.get()
            self.ardq.close()
            self.ardq_p2read.close()
            self.ard.terminate()
            
    def startAq(self):
        for m in self.mlist:
            self.camq[m].put('Start')
        for s in self.slist:
            self.camq[s].put('Start')
        for m in self.mlist:
            self.camq[m].put('TrigOff')
        
    def stopAq(self):
        
        self.camaq.value = 0
        for s in self.slist:
            self.camq[s].put('Stop')
            self.camq_p2read[s].get()
        for m in self.mlist:
            self.camq[m].put('Stop')
            self.camq_p2read[m].get()
        
    def updateSettings(self, event):
        self.system_cfg = clara.read_config()
        self.aqW = list()
        self.aqH = list()
        self.recSet = list()
        for n, camID in enumerate(self.camIDlsit):
            try:
                self.camq[camID].put('updateSettings')
                self.camq_p2read[camID].get(timeout=1)
                

                if self.auto_stim.GetValue():
                    self.camq[camID].put('roi')
                elif self.crop.GetValue():
                    self.camq[camID].put('crop')
                else:
                    self.camq[camID].put('full')
                

            
                self.recSet.append(self.camq_p2read[camID].get(timeout=4))
                aqW = self.camq_p2read[camID].get(timeout=1)
                self.aqW.append(int(aqW))
                aqH = self.camq_p2read[camID].get(timeout=1)
                self.aqH.append(int(aqH))
                
            except:
                print('\nTrying to fix.  Please wait...\n')
                self.deinitThreads()
                self.camReset(event)
                self.initThreads()
                self.camq[camID].put('updateSettings')
                self.camq_p2read[camID].get()
                if self.auto_stim.GetValue():
                    self.camq[camID].put('roi')
                elif self.crop.GetValue():
                    self.camq[camID].put('crop')
                else:
                    self.camq[camID].put('full')
            
                self.recSet.append(self.camq_p2read[camID].get())
                aqW = self.camq_p2read[camID].get()
                self.aqW.append(int(aqW))
                aqH = self.camq_p2read[camID].get()
                self.aqH.append(int(aqH))
            print('frame rate ' + self.camStrList[n] + ' : ' + str(round(self.recSet[n])))
            
  
    def initCams(self, event):
        if self.init.GetValue() == True:
            self.Enable(False)
            
            self.initThreads()
            self.updateSettings(event)
            
            self.Bind(wx.EVT_TIMER, self.vidPlayer, self.liveTimer)
            
            self.camaq.value = 1
            self.startAq()
            time.sleep(1)
            self.camaq.value = 0
            self.stopAq()
            self.x1 = list()
            self.x2 = list()
            self.y1 = list()
            self.y2 = list()
            self.h = list()
            self.w = list()
            self.dispSize = list()
            for ndx, im in enumerate(self.im):
                self.frame[ndx] = np.zeros(self.shape, dtype='ubyte')
                self.frameBuff[ndx][0:] = np.frombuffer(self.array4feed[ndx].get_obj(), self.dtype, self.size)
                if self.auto_stim.GetValue() and self.stimAxes == self.axes[ndx]:
                    self.h.append(self.stimroi[3])
                    self.w.append(self.stimroi[1])
                    self.y1.append(self.stimroi[2])
                    self.x1.append(self.stimroi[0])
                    self.set_stim.Enable(False)
                    self.set_crop.Enable(False)
                    self.inspect_stim.Enable(True)
                elif self.crop.GetValue():
                    self.h.append(self.croproi[ndx][3])
                    self.w.append(self.croproi[ndx][1])
                    self.y1.append(self.croproi[ndx][2])
                    self.x1.append(self.croproi[ndx][0])
                    self.set_crop.Enable(False)
                    self.set_stim.Enable(True)
                    self.inspect_stim.Enable(False)
                else:
                    self.h.append(self.frmDims[1])
                    self.w.append(self.frmDims[3])
                    self.y1.append(self.frmDims[0])
                    self.x1.append(self.frmDims[2])
                    self.set_crop.Enable(True)
                    self.set_stim.Enable(True)
                    self.inspect_stim.Enable(False)
                
                self.dispSize.append(self.aqH[ndx]*self.aqW[ndx])
                self.y2.append(self.y1[ndx]+self.aqH[ndx])
                self.x2.append(self.x1[ndx]+self.aqW[ndx])
                
                frame = self.frameBuff[ndx][0:self.dispSize[ndx]].reshape([self.aqH[ndx], self.aqW[ndx]])
                self.frame[ndx][self.y1[ndx]:self.y2[ndx],self.x1[ndx]:self.x2[ndx]] = frame
                im.set_data(self.frame[ndx])
                
                    
                if not self.croproi[ndx][0] == 0:
                    self.croprec[ndx].set_alpha(0.6)

                if not self.pellet_x == 0:
                    if not self.roi[0] == 0:
                        if self.pelletAxes == self.axes[ndx]:
                            self.pLoc[ndx].set_alpha(0.6)
                            self.roirec[ndx].set_alpha(0.6)

                if not self.stimroi[0] == 0:
                    if self.stimAxes == self.axes[ndx]:
                        self.stimrec[ndx].set_alpha(0.6)
            
            self.init.SetLabel('Release')
            self.crop.Enable(False)
            self.auto_stim.Enable(False)
            self.auto_pellet.Enable(True)
            
            for h in self.onWhenCamEnabled:
                h.Enable(True)
            
            if not self.com.value < 0:
                if self.auto_delay.GetValue():
                    self.make_delay_iters()
                self.setProtocol(None)
                self.setDelStyle()
                self.com.value = 7 # block ButtonStyleChange
                while self.com.value > 0:
                    time.sleep(0.01)
                self.com.value = 12 # set X position
                while self.com.value > 0:
                    time.sleep(0.01)
                self.com.value = 13 # set Y position
                while self.com.value > 0:
                    time.sleep(0.01)
                self.com.value = 14 # set Z position
                while self.com.value > 0:
                    time.sleep(0.01)
                self.com.value = 1 # send home
                while self.com.value > 0:
                    time.sleep(0.01)
                    
                
                for h in self.serHlist:
                    h.Enable(True)
            
            self.Enable(True)
            self.figure.canvas.draw()
        else:
            if not self.com.value < 0:
                self.com.value = 8 # allowButtonStyleChange
                while self.com.value > 0:
                    time.sleep(0.01)
                    
            if self.play.GetValue():
                self.play.SetValue(False)
                self.liveFeed(event)
            if self.rec.GetValue():
                self.rec.SetValue(False)
                self.recordCam(event)
            self.init.SetLabel('Enable')
            for h in self.serHlist:
                h.Enable(False)
            for ndx, im in enumerate(self.im):
                self.frame[ndx] = np.zeros(self.shape, dtype='ubyte')
                im.set_data(self.frame[ndx])
                self.croprec[ndx].set_alpha(0)
                self.pLoc[ndx].set_alpha(0)
                self.roirec[ndx].set_alpha(0)
                self.stimrec[ndx].set_alpha(0)
            self.figure.canvas.draw()
            
            self.crop.Enable(True)
            if not self.stimAxes == None:
                self.auto_stim.Enable(True)
            self.set_crop.Enable(False)
            self.set_stim.Enable(False)
            self.auto_pellet.Enable(False)
            self.inspect_stim.Enable(False)
            for h in self.onWhenCamEnabled:
                h.Enable(False)
            
            self.deinitThreads()
        
    def quitButton(self, event):
        """
        Quits the GUI
        """
        print('Close event called')
        if self.play.GetValue():
            self.play.SetValue(False)
            self.liveFeed(event)
        if self.rec.GetValue():
            self.rec.SetValue(False)
            self.recordCam(event)
        if self.init.GetValue():
            self.init.SetValue(False)
            self.initCams(event)
        
        try:
            if not self.mv.is_alive():
                self.mv.terminate()
            else:
                print('File transfer in progress...\n')
                print('Do not record again until transfer completes.\n')
        except:
            pass
        
        try:
            if self.compressThread.is_alive():
                dlg = wx.MessageDialog(parent=None,message="Pausing until previous compression completes!",
                                       caption="Warning!", style=wx.OK|wx.ICON_EXCLAMATION)
                dlg.ShowModal()
                dlg.Destroy()
                while self.compressThread.is_alive():
                    time.sleep(10)
            
            self.compressThread.terminate()   
        except:
            pass
        
        self.statusbar.SetStatusText("")
        self.Destroy()
    
def show():
    app = wx.App()
    MainFrame(None).Show()
    app.MainLoop()

if __name__ == '__main__':
    
    show()
    
    #configure_logging()
    

    # ———— At the very end for logging ————