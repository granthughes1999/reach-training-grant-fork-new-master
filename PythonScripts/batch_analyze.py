# -*- coding: utf-8 -*-
"""
Created on Wed Dec 13 10:40:48 2023

@author: reynoben
"""


import multiCam_DLC_utils_v2 as clara
import findReachEvents_v2 as fre
import os
import wx


def analVids(config_path, vid_tag, root_path, date_min, date_max, scorer, unitRef, first_session=False):
    video_list = []
    dated_vid_list = []
    for foldername in os.listdir(root_path):
        if foldername.isdigit() and len(foldername) == 8:
            folder_path = os.path.join(root_path, foldername)
            scorer_path = os.path.join(folder_path, unitRef)
            print(unitRef)
            print(scorer_path)
            
            if os.path.exists(scorer_path):
               for root, dirs, files in os.walk(scorer_path):
                    if (date_min is None and date_max is None):
                        video_list.extend(os.path.join(root, f) for f in files if f.endswith(vid_tag))
                    elif (date_min <= foldername and foldername <= date_max):
                        if first_session:
                            dated_vid_list.extend(os.path.join(root, f) for f in files if f.endswith(vid_tag) and "session001" in f and "stimCam" not in f)
                        else:
                            dated_vid_list.extend(os.path.join(root, f) for f in files if f.endswith(vid_tag) and "stimCam" not in f)
                        print(os.path.join(root, f) for f in files if f.endswith(vid_tag))

    if (date_min is None and date_max is None):
        vid2anal = video_list
    else:
        vid2anal = dated_vid_list
    video_list_str = "\n".join(vid2anal)
    message = f'Analysis Will be Ran On:.\n\nDesired .mp4 files:\n{vid2anal}'
    print(f'vid2anal:{vid2anal}')
    dialog = wx.MessageDialog(None, message, 'Continue with Analysis?', wx.YES_NO | wx.ICON_QUESTION)
    result = dialog.ShowModal()
    if result == wx.ID_YES:
        print("Running analysis")
        clara.analyze_videos_CLARA(config_path, vid2anal, crp=None) #run analysis on either novel or dated vids
        if (date_min is None and date_max is None):
            print('Analysis Completed for all novel videos!')
        else:
            print(f'Analysis Completed for all videos from {date_min} to {date_max}!')
    else: 
        print("Analysis Cancelled")
    dialog.Destroy()
    


def findReachEvents(dlc_seg, vid_tag, root_path, date_min, date_max, scorer, unitRef, first_session=False):
    sess_list_full = []
    dated_sess_list = []
    for foldername in os.listdir(root_path):
        if foldername.isdigit() and len(foldername) == 8:# and foldername >= date_min and foldername <= date_max:
            folder_path = os.path.join(root_path, foldername)
            scorer_path = os.path.join(folder_path, unitRef)
            if os.path.exists(scorer_path):
                sess_list = [name for name in os.listdir(scorer_path)]
                if len(sess_list):
                    for sessname in sess_list:
                        if first_session:
                            if sessname == 'session001':
                                sess_dir = os.path.join(scorer_path, sessname)
                                if (date_min is None and date_max is None):
                                    sess_list_full.append(sess_dir)
                                elif (date_min <= foldername and foldername <= date_max):
                                    dated_sess_list.append(sess_dir)
                        else:
                            sess_dir = os.path.join(scorer_path, sessname)
                            if (date_min is None and date_max is None):
                                sess_list_full.append(sess_dir)
                            elif (date_min <= foldername and foldername <= date_max):
                                dated_sess_list.append(sess_dir)
                else:
                    wx.MessageBox('No Sessions Found!', 'ERROR', wx.ICON_ERROR)

    if date_max == None and date_min == None:
        FRE_execute(sess_list_full, vid_tag, dlc_seg)
        wx.MessageBox('Analysis and Reach finding Completed for all novel videos!', 'Success', wx.OK | wx.ICON_INFORMATION) 
    else:
        FRE_execute(dated_sess_list, vid_tag, dlc_seg)
        wx.MessageBox(f'Analysis and Reach finding Completed for videos from {date_min} to {date_max}!', 'Success', wx.OK | wx.ICON_INFORMATION) 
          
def FRE_execute(sess_list, vid_tag, dlc_seg):
    print(sess_list)
    for session in sess_list:
        print(session)
        fre.filter_data(session, vid_tag, dlc_seg)
        fre.find_reach_events(session, vid_tag)
   