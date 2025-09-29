DATA PIPELINE: VIDEO CREATION ---> VISUALIZATION OF REACH OUTCOMES

* conda activate data_aq for video acquisition
* conda activate dlc for all other scripts

IMPORTANT: systemdata.yaml configuration file
FIRST TIME: Duplicate systemdata_default.yaml; name the new file as systemdata.yaml

-- Alter systemdata content to match serial numbers of cameras being used

-- if using 3 cameras, add extra cam

------ rename cam and nickname
 
------ set ismaster to false
  
------ set stimAxes to stimCam (cannot be master)

-- if using 2 cameras, set stimAxes to None

-- Define master and peripheral cameras (true or false)

-- Ensure that unitRef matches the computer name

-- raw_data_dir will be the local data space

-- compressed_data_dir is where compressed videos and associated files are sent upon compression

-- Ensure correct COM port is selected

------ Use Arduino IDE to confirm

-- axesRef sets the camera used for pellet and hand ROI

 1. multiCam_RT_videoAcquisition_v4

    ---	PURPOSE:
	- Control Pellet Delivery system and acquire behavior videos
 	
    ---	OPERATION:
	1. Select User
	    * Add new user if first time acquiring on the machine
	2. initialize cameras and arduino
	3. send pellet dispenser to mouse position
	4a. press pellet roi to adjust position
	    * alter the red dot position to cover the pellet
	4b. press hand roi to adjust position
	    * alter green box position near the pellet cover
	4c. if using 3 cameras, press stimROI to place
	    * ignore if 2 Cameras 
	    * alter grey box position appropriately
	    * press delete key while selected to remove 
	5. If desired, change settings within Users\<user>_userdata.yaml or within GUI
		* deliveryStyle: 0 = reveal pellet then move to mouse
		* deliveryStyle: 1 = move to mouse then reveal pellet
	6. press live to get camera live stream (start video acquisition)
	7. press record to begin video recording
	8. dispense pellet by...
	    1. Clicking 'pellet' checkbox to enable automated delivery
	    2. Pressing handheld button connected to the pellet delivery system
	    3. clicking on GUI events to control each subprocess of delivery
	9. press stop to end video
	10. press "release" to stop camera acquisition 
	11. press compress to compress videos from .avi to .mp4
	    * raw data, and output directories are defined within systemdata.yaml

    ---	 Dependencies:
	- spinnaker
	- data_aq environment
	- arduinoCtrl_v5.py
	- multiCam_DLC_PySpin_v2.py
	- multiCam_DLC_utils_v2.py
	- compressVideos_v3.py
	- reach-training\PythonScripts\systemdata.yaml
	- reach-training\PythonScripts\Users\<user>_userdata.yaml

    ---	 Considerations:
	1. Serial numbers of cameras must be appropriately set within system.yaml file
	2. Sync cable ensures synchronization of cameras
	    *One camera must be designated master; receives the 'primary' end of the sync cable
	3. Unplug and replug the cameras into the computer if lights on camera are solid green
	   * indicates the cameras were not released properly
	4. 


 2. multiCam_DLC_videoExplorer_v3


    ---	PURPOSE:
	- Create DLC project, label frames, train a neural network, visualize network accuracy, batch analyze, and batch find reach events

    ---	Operation:

	** Skip to step 6 if loading existing training set
	1. Press "Add User" if first time, otherwise, select appropriate user from dropdown
		- type in your initials
	2. Create "New Training Set"
		- Load initial video
	3. Go to Documents\<training set name>
	4. Change config.yaml parameters in text editor (reference Examples\video_explorer_dlc_config.yaml as example)
		- change list of "bodyparts" to desired labels
		- set "default_net_type" to resnet_50 (or other pretrained CNN)
		- set "default_augmenter" to default
		- set "iteration" to 0
	5. Press "Load Config File" and navigate to project folder 
		- may need to exit GUI if first time loading config
	6. Press "Load Videos" if not already visible
	7. Press "Label"
	8. Create a marker
		- Select the bodypart (in the lower left of the GUI)
		- click on the frame to place the marker
	9. Repeat for all visible bodyparts (present in the config file)
		- Press Omit to remove selected markers
	10. When labeling is finished, press "Train" to train the network
	11. After training is complete, press "Analyze" to run network inference on the currently loaded video
		- once analysis is complete, check the box marked "Load Analysis Labels" to load inferred labels and assess the accuracy of the network
		- if sufficient, go to step 17.
			- otherwise, continue to step 12.  
	12. Click "Review Mode" to load all labeled frames (from all videos)
		- Correct any labeling errors here
		- * Only single camera view will be displayed
		- * GUI will stall for ~3s when new video is reached
		- Disable review mode to add novel frames/videos
	13. Add 1 to "iteration" in config file (ex. 0-->1) 
	14. Retrain the network
	15. Load a video and analyze to confirm network accuracy
		- when prompted, select the newest network to display updated labels
		- Check the "Load Analysis Labels" checkbox
	16. Reiterate through steps 13-15 until sufficient analysis is acquired
	17. Check the "Select Dates" checkbox if analysis is desired over a specific set of videos
	18. Press "Batch analyze" to analyze and find reach events for a defined set of videos
		- Verify "Root Path" is the parent directory where all videos are stored (single folder above folders named by date)
		- If "Select Dates" is checked
			- "Date Min" is an 8 digit date (YYYYMMDD) defining the first day of videos to be analyzed
			- "Date Max" is an 8 digit date (YYYYMMDD) defining the last day of videos to be analyzed
			- Analysis will only be run on videos not previously analyzed
				- Must delete existing dlc files if overwrite is desired
		- Otherwise analysis will be run on all videos that have not been analyzed previously (by the network being used)
		- Previous setting are stored in C:\Users\<User>\Documents\DLC_Users\<user_initials>\<user_initials>.yaml

    --- TIPS/SHORTCUTS:
	- When a label marker is selected, use the arrow keys for minute positioning changes
	- Jump to a specific frame by typing the frame number into the "Start Frame Index" text box
	- When no label is selected, use the right and left arrow keys to adjust scrubbing speed
		- Space bar will pause/play the video
	- When no label is selected, use the up and down arrow keys to jump forwards/backwards a single frame
	- Use "Grab" to select all existing labels(from analysis) and include them in the current project
	- Use the "Find" dropdown menu and arrows to quickly jump between labeled frames

    ---	 Dependencies:
	- deeplabcut
	- dlc environment
	- multiCam_DLC_utils_v2.py
	- reach-training\PythonScripts\systemdata.yaml
	- C:\Users\<User>\Documents\DLC_Users\<user_initials>\<user_initials>.yaml
	- Nvidia CUDA and cuDNN (ask Ben to install if not already)
		- follow guide of https://medium.com/@gokulprasath100702/a-guide-to-enabling-cuda-and-cudnn-for-tensorflow-on-windows-11-a89ce11863f1
		- files found on Isilon server: Data\BR\Reach_training_windows_install

    ---	 Considerations:
	- Begin by labeling 150-200 frames, attempting an even distribution of bodyparts labeled
		- Iteratively train, analyze, review, and label again, until sufficient network accuracy is reached 
		- Load new videos every 25-30 labeled frames if possible
	- Labels surrounded by a white border are included in the current project, black border suggest the video has been previously
	  analyzed with a pre-existing network
	- Reference Examples\labeling_considerations.pptx for examples of the following:
		- Only label frames including desired behavior 
			- disperse labeling throughout behavioral epochs
		- Aim for absolute consistency in labels across all frames 
			- ex. all "Hand" labels should be placed in the same position on the hand
		- Include a diverse range of frames 
			- Many different bodypart orientations, positions, lighting, visibility, etc. 
		- If one label is created, all visible bodyparts (present in config file) must be labeled
			- Front and Side views are independent of one another
		- Consider creating multiple labels for bodyparts that take on multiple unique orientations
			- ex. "Hand" = SdH_Flat, SdH_Spread, and SdH_Grab
			- Later merged into a single "Hand" label


 3. Reach_Curator_py38_v2

    ---	PURPOSE:
	- Display and alter reach events/outcomes 

    ---	 Operation:

	** If loading existing curation, skip to step 3
	1. If new curation set, select "new curation" from Curation File dropdown, then press "Load Config File"
		- Enter name for curation set (NO SPACES)
		- If text entry box does not appear, manually delete the "new curation" folder and .yaml file from C:\Users\<User>\Documents\Curators folder
			- Repeat step 1.
	2. Manually navigate to C:\Users\<User>\Documents\Curators\<curation_name>.yaml
		- Change "bodyparts:" key to list of bodyparts labeled in the video_explorer
			- Can be found in <path_to_DLCTrainingSet>\config.yaml file, under "bodyparts:"
		- Change "results directory" to C:\Users\<User>\Documents\Curators\<curation_name>
		- Change "raw data directory" to <path_to_root_video_folder>; parent directory where all videos are stored (single folder above folders named by date)
		- Add list of sessions under "session list:" key 
			- example format = 20240215_christie2P_session013 or 20240707_christielab_session001
			- *should be the beginning of .mp4 file names
	3. If loading existing set, select <curation_name> from Curation File dropdown, then press "Load Config File"
	4. Press "Load Videos" to select a video from the session list created in the <curation_name>.yaml file
		- If multiple networks were used to analyze the video, select the appropriate network from thepopup window
	5. If desired, check the "Load Labels" checkbox to overlay "Hand" and "Pellet" filtered tracking data.
	6. Navigate through the video to find all desired reach events
		- For instructions and increased efficiency, reference TIPS/SHORTCUTS section below 
	7. If event timing of an event needs to be changed, align the center line of the scroll bar with the event line.
		- Drag the event right or left as necessary
	8. If the outcome of reachEnd needs to be changed, align the center line of the scroll bar with the reachEnd line.
		- Select an action category from the options in the lower left.
	9. To place a new reach, scroll to a position outside of an existing reach (after reachEnd and/or before reachInit)
		- Press "Place Reach"
	10. To remove a reach, align the center line of the scroll bar with a reach event line (reachInit, reachMax, or reachEnd)
		- Press "Remove Reach"
	
	** If results do not appear as expected:
		1. Ensure step 4 was completed correctly (if multiple DLC analyses run on same video)
		2. Read "Considerations" section below

    --- TIPS/SHORTCUTS:
	- Jump to a specific frame by typing the frame number into the "Start Frame Index" text box
	- Drag right or left on the scroll bar to manually scrub
	- When no label is selected, use the right and left arrow keys to adjust scrubbing speed
		- Space bar will pause/play the video
	- When no label is selected, use the up and down arrow keys to jump forwards/backwards a single frame
	- Use the "Find" dropdown menu and arrows to quickly jump between labeled frames or behavioral epochs (ex. reach_init, pellet_delivery, etc.)

    ---	 Dependencies:
	- dlc environment
	- multiCam_DLC_utils_v2.py
	- reach-training\PythonScripts\systemdata.yaml
	- C:\Users\<User>\Documents\Curators\<curation_name>.yaml

    ---	 Considerations:
	1. All curation data is stored within Documents\Curators folder
	2. When a video is loaded, reach events are stored in a .xlsx file within Curators\<project_name> (along with all alterations)
		- Subsequent loading of video will reference .xlsx file
		- If new reach finding is run after video has been loaded, manually delete the appropriate .xlsx files or create a new curation set
	3. Known bug in "Show Analysis" checkbox.
