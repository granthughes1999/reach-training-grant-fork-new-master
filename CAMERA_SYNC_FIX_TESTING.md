# Camera BNC Sync Cable Fix - Testing Guide

## Problem Fixed
This update addresses the issue where the GUI cannot connect to FLR cameras when the BNC sync cable is plugged into the master camera. Previously:
- GUI would not connect/initialize with sync cable connected
- Only master camera showed video when sync cable was plugged in during operation
- Unplugging the sync cable would restore all camera feeds

## Changes Made

### 1. Camera Initialization Timing (`multiCam_DLC_PySpin_v2_extStim.py`)
- **Master Camera Init**: Added 0.5s stabilization delay after configuring trigger output on Line1
- **Slave Camera Init**: Added 0.1s delay before configuring trigger input on Line3
- **Acquisition Start**: Added 0.1s delay in master camera before enabling trigger output

### 2. GUI Initialization Sequence (`multiCam_RT_videoAcquisition_v5.py`)
- **Thread Init**: Added 0.5s delay between master and slave camera initialization
- **Acquisition Start**: Modified to start master cameras first, wait 0.3s, then start slave cameras
- **Diagnostic Logging**: Added status messages to track initialization progress

## Testing Instructions

### Prerequisites
- 3 FLR cameras physically connected
- BNC sync cables connected (1 master, 2 slaves)
- Master camera has BNC sync cable plugged into main BNC port

### Test 1: Initial Connection with Sync Cable Connected
1. Ensure all BNC sync cables are connected
2. Start the GUI application: `python multiCam_RT_videoAcquisition_v5.py`
3. Click "Initialize" button
4. **Expected Result**: All 3 cameras should initialize successfully
5. **Look for**: Console messages showing:
   - "Master camera [serial] initialized with hardware trigger output on Line1"
   - "Slave camera [serial] initialized with hardware trigger input on Line3"
6. **Verify**: No timeout or connection errors

### Test 2: Live Feed with Sync Cable Connected
1. After successful initialization from Test 1
2. Click "Live" button to start video feed
3. **Expected Result**: All 3 camera views should display live video
4. **Look for**: Console message "Master camera trigger output stabilizing before starting slave cameras..."
5. **Verify**: All cameras update at the same frame rate (synchronized)

### Test 3: Recording with Sync Cable Connected  
1. After successful live feed from Test 2
2. Click "Record" button
3. Let it record for 30 seconds
4. Click "Stop" to end recording
5. **Expected Result**: Video files created for all 3 cameras
6. **Verify**: All video files have same frame count (±1 frame tolerance)

### Test 4: Repeated Initialize/Release Cycles
1. With sync cables connected, click "Initialize"
2. Wait for initialization to complete
3. Click "Release"
4. Wait 5 seconds
5. Repeat steps 1-4 five times
6. **Expected Result**: All cycles should succeed without errors
7. **Verify**: No degradation or timeout issues over multiple cycles

### Test 5: Compare with/without Sync Cable
1. **With sync cable**: Perform Tests 1-3
2. Document: initialization time, any console warnings/errors
3. **Without sync cable**: Unplug BNC cables, perform Tests 1-3
4. Document: initialization time, any console warnings/errors
5. **Expected Result**: Both scenarios should work, with sync cable may add ~1s initialization time

## Troubleshooting

### If cameras still fail to initialize with sync cable:
1. Check console output for specific error messages
2. Verify BNC cable connections are secure
3. Try increasing delays:
   - In `multiCam_DLC_PySpin_v2_extStim.py`, line 93: change `time.sleep(0.5)` to `time.sleep(1.0)`
   - In `multiCam_RT_videoAcquisition_v5.py`, line 3277: change `time.sleep(0.5)` to `time.sleep(1.0)`
   - In `multiCam_RT_videoAcquisition_v5.py`, line 3343: change `time.sleep(0.3)` to `time.sleep(0.5)`

### If only master camera shows video:
1. Check that slave cameras initialized successfully (look for console messages)
2. Verify trigger cables are connected to correct ports (Line3 on slaves)
3. Try stopping and restarting acquisition (Release then Initialize again)

### If frame synchronization is off:
1. This fix addresses initialization timing, not frame sync accuracy
2. Frame sync is controlled by the BNC hardware trigger signal
3. Verify camera frame rates are set identically in `systemdata.yaml`

## Success Criteria
✅ All cameras initialize successfully with BNC sync cables connected  
✅ Live feed shows all cameras with synchronized frames  
✅ Recording produces valid video files for all cameras  
✅ No console errors or timeout messages  
✅ Initialization completes within 5-10 seconds  

## Reporting Issues
If problems persist after this fix:
1. Capture full console output (initialization through first 10 seconds of live feed)
2. Note specific error messages
3. Document: camera serial numbers, OS version, PySpin SDK version
4. Include: timing of when issue occurs (init, live feed start, during recording)

## Technical Details

### Why These Delays Fix the Issue
Hardware trigger signals on BNC cables need time to stabilize. The previous code had a race condition:
1. Master camera would configure Line1 output
2. Slave cameras would immediately try to read Line3 input
3. But the electrical signal on the BNC cable wasn't stable yet
4. Slaves would fail to detect trigger or timeout waiting

By adding delays:
- Master camera's trigger output has time to reach stable electrical levels
- Slave cameras don't try to read until signal is ready
- This eliminates the race condition that caused connection failures

### Timing Breakdown
- **0.5s after master init**: Allows trigger output circuit to stabilize
- **0.1s before slave trigger config**: Brief settling time after camera init
- **0.5s between master/slave thread init**: Ensures all masters are configured before any slave starts
- **0.3s between master/slave acquisition**: Allows master to begin triggering before slaves listen

Total added latency: ~1.5 seconds to initialization, negligible during operation
