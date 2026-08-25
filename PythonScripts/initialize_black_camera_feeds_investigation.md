# Initialize Black Camera Feeds Investigation

Date: 2026-07-01

## Issue Summary

After pressing **Initialize** in `multiCam_RT_videoAcquisition_v5.py`, the GUI should connect to the Arduino UNO-R4 and three cameras. Current behavior:

- If the Arduino connects, the GUI appears to connect to cameras, but the displayed camera feeds stay black.
- If the Arduino fails to connect, all three camera feeds are visible.
- The Arduino works in the Arduino IDE Serial Monitor.
- All three cameras work in SpinView.

No Python or Arduino source files were changed during this investigation.

## Most Likely Root Cause

The Arduino sketch and Python Arduino controller disagree about the command-completion marker.

Current Arduino sketch:

- `Arduino-control/homecage_pellet_UNOR4_v3_OldBoard_GRANT_1Top_v2/homecage_pellet_UNOR4_v3_OldBoard_GRANT_1Top_v2.ino`
- Around line 606, the old `%` completion marker is commented out.
- Around line 607, the sketch now sends `ACK`.

Current Python Arduino controller:

- `PythonScripts/arduinoCtrl_v5.py`
- Around line 99, the worker only clears `self.is_busy.value` when an incoming serial line ends with `%`.
- Around lines 247-248, `comFun()` marks the Arduino busy after it receives the immediate `!` echo/ack and clears `self.com.value`.

This means the first Arduino command after Initialize can appear to complete, but the Python side never receives the old `%` marker needed to set `is_busy` back to 0. The next queued Arduino command can then sit forever because the Arduino worker only calls `comFun()` when `is_busy == 0`.

## Why This Matches The Symptom

In `multiCam_RT_videoAcquisition_v5.py`, `initCams()` does this after the camera test acquisition:

1. Updates the image objects with frames from the shared camera buffers.
2. If Arduino is connected, sends a sequence of Arduino commands:
   - `com = 7`
   - `com = 12`
   - `com = 13`
   - `com = 14`
   - `com = 1`
3. Waits in blocking loops after each command:
   - `while self.com.value > 0: time.sleep(0.01)`
4. Only after that, re-enables the GUI and calls:
   - `self.figure.canvas.draw()`

If the Arduino connects, the command sequence runs. Because `ACK` no longer clears `is_busy`, the second or later command can block before the canvas draw happens. The image panes therefore remain at their initial black display state even though the camera processes may have acquired frames.

If the Arduino fails to connect, `self.com.value` is negative, so the Arduino command block is skipped. The GUI reaches `self.figure.canvas.draw()`, and the camera frames become visible. This explains the observed Arduino-dependent behavior.

## Secondary Issues Found

### Shared Display Buffers

In `multiCam_RT_videoAcquisition_v5.py` around lines 901-916, `frame` and `frameBuff` are created once before the camera loop, then appended repeatedly:

- `self.frame.append(frame)`
- `self.frameBuff.append(frameBuff)`

That means all camera display slots initially reference the same NumPy arrays. Later code often overwrites whole entries, so it may not always break display, but it is fragile and can make camera-pane symptoms harder to interpret.

### Blocking GUI Waits

`initCams()` uses blocking `while self.com.value > 0` loops on the GUI thread. Any Arduino command parser mismatch or missed serial response can freeze the GUI before it redraws. Even after fixing the marker mismatch, these waits should have timeouts or become non-blocking.

### Possible Hardware/Timing Interaction

The Arduino serial open resets the UNO-R4. Camera initialization and the 1-second test acquisition happen after a fixed 2-second Arduino wait. If any Arduino output is physically tied into the camera sync/TTL wiring, the board reset or output state could also affect camera trigger lines. However, the `%` vs `ACK` mismatch is a much stronger code-level explanation for the exact "Arduino connected means black GUI" symptom.

## Proposed Changes To Try

### Change Set A: Restore The Original Arduino Completion Marker

Smallest test:

1. In the Arduino sketch, restore `Serial.println('%');`.
2. Optionally remove or comment out `Serial.println("ACK");`.
3. Re-upload the sketch to the UNO-R4.
4. Test Initialize again.

Expected result:

- Python receives `%`.
- `arduinoCtrl_v5.py` clears `is_busy`.
- The Initialize command sequence completes.
- The GUI reaches `self.figure.canvas.draw()`.

Risk:

- Low. This restores the protocol expected by the Python code.

### Change Set B: Make Python Accept Both `%` And `ACK`

More flexible software-side fix:

1. In `arduinoCtrl_v5.py`, update the serial-read logic so `self.is_busy.value = 0` when either:
   - the received line ends with `%`, or
   - the received line contains `ACK`.
2. Keep support for `%` for backward compatibility with older Arduino sketches.

Expected result:

- Current `ACK` sketch works.
- Older `%` sketches still work.

Risk:

- Low to moderate. Need to be careful not to treat unrelated serial text as command completion.

### Change Set C: Add Timeouts To Initialize Arduino Command Waits

Robustness fix:

1. Replace each blocking `while self.com.value > 0` wait in `initCams()` with a helper that has a timeout.
2. If a command times out, log a warning, clear or mark the command state, and let the GUI redraw instead of staying black/frozen.

Expected result:

- A serial protocol problem cannot prevent the camera canvas from drawing.
- The GUI reports which Arduino command failed.

Risk:

- Moderate. Need to choose whether timeout should clear `com` to 0 or mark Arduino unavailable.

### Change Set D: Draw Camera Frames Before Post-Initialize Arduino Motions

User-facing mitigation:

1. Move `self.figure.canvas.draw()` earlier, immediately after the camera test frame buffers are copied into the image panes.
2. Then run the Arduino positioning/home commands.

Expected result:

- Even if Arduino commands stall, the camera frames appear first.

Risk:

- Low for display, but it does not fix the underlying serial/busy-state mismatch.

### Change Set E: Allocate Per-Camera Display Arrays

Cleanup/future-proofing:

1. Move creation of `frame = np.zeros(...)` and `frameBuff = np.zeros(...)` inside the camera loop.
2. Append a distinct array for each camera.

Expected result:

- Each camera pane owns its own display buffer.
- Avoids accidental cross-camera overwrites.

Risk:

- Low.

## Recommended Trial Order

1. Try Change Set A first because it is the smallest and directly matches the current Python protocol.
2. If keeping `ACK` is preferred, try Change Set B instead.
3. Add Change Set C next so the GUI cannot freeze silently on future Arduino serial issues.
4. Add Change Sets D and E as cleanup/hardening after the main behavior is confirmed.

## Useful Test After Applying A Or B

During Initialize, watch for whether the GUI reaches the final redraw and whether the serial command sequence gets past:

- `com = 7`
- `com = 12`
- `com = 13`
- `com = 14`
- `com = 1`

If the camera panes appear after fixing the marker mismatch, the root cause is confirmed.

## Follow-Up: Master Streams, Secondary Cameras Timeout

After the first camera-side fixes, the remaining behavior is different from the original Arduino-dependent black-pane symptom:

- `cam2` / serial `22234360` / `frontCam` is configured as `ismaster: true`.
- Whichever camera is configured as master shows live video.
- The two secondary cameras stay black.
- The secondary cameras report repeated `Frame acquisition timeout` messages and then stop their own acquisition after 5 consecutive timeouts.
- This happens during Live/Record whether stimulus mode is on or off.

Interpretation:

- Individual cameras are working, because each one can display video when made master.
- The GUI display path and camera-save loop are not the primary remaining failure.
- The secondaries are armed for external trigger and are waiting for pulses that they are not seeing.
- The most likely remaining issue is the sync trigger path: either the Python trigger input line does not match the physical sync cable wiring, the master output line is not reaching the secondaries, or the sync cable/FLIR GPIO wiring expects a different line/edge configuration.

Camera-side changes already applied:

1. Master cameras now keep `AcquisitionFrameRateEnable = True`; secondary cameras set `AcquisitionFrameRateEnable = False`.
2. The master output line is explicitly configured as `Line1` output with `Counter0Active`.
3. Secondary trigger activation is now `RisingEdge` instead of `AnyEdge`.
4. Secondary timeout no longer clears the shared acquisition flag, so one failed secondary should not stop the master.
5. Video writer frame rate now uses the configured camera frame rate instead of hard-coded 30 fps.

Current test change:

1. Secondary trigger input changed from `TriggerSource_Line3` to `TriggerSource_Line0` in `multiCam_DLC_PySpin_v2_extStim.py`.
2. Keep `cam2` / serial `22234360` as the only master and test Initialize plus Live again.

Expected result if this is the correct physical input line:

- `sideCam` and `stimCam` should stop reporting frame acquisition timeouts.
- Their GUI feeds should become visible during Live.
- Their recorded videos should no longer be zero seconds.

If `Line0` still fails:

1. Add a small configurable setting in `systemdata.yaml` for each secondary camera trigger input, for example `triggerLine: Line0` or `triggerLine: Line3`, so Line0/Line3 can be tested without editing code.
2. Add a temporary diagnostic/free-run mode for secondary cameras to confirm the live display and video writer still work independently of hardware sync.
3. Inspect the FLIR sync cable mapping and SpinView line-status/trigger configuration to confirm which physical pin reaches each secondary trigger input.

## Diagnostic Trial: Secondary Free-Run

The `Line0` test produced the same result as `Line3`: master visible, secondaries black, secondary acquisition timeouts. That means the failure is probably not just the specific input enum in Python.

Temporary diagnostic changes:

1. Added `syncDiagnosticFreeRunSecondaries: true` to `systemdata.yaml`.
2. Added `syncSecondaryTriggerSource: Line3` to `systemdata.yaml` so the normal sync trigger line can be changed without editing code later.
3. When `syncDiagnosticFreeRunSecondaries` is true, secondary cameras initialize with `TriggerMode = Off`.
4. In that diagnostic mode, secondary cameras also enable `AcquisitionFrameRateEnable`, because they are no longer being externally paced by the master.

Expected diagnostic outcome:

- If all three feeds appear, the GUI/display/save path is good and the remaining problem is the master-to-secondary hardware trigger path.
- If the secondaries are still black even in free-run mode, the issue is deeper in the per-camera process, camera initialization order, shared buffers, or GUI display/update path.

Important:

- This is not the final synchronized-recording configuration.
- Before real synchronized recording, set `syncDiagnosticFreeRunSecondaries: false` again after the diagnostic result is known.

## BNC Cable Observation

Additional hardware observation:

- With the BNC sync cable connected, Initialize shows only the configured master feed.
- With the BNC sync cable unplugged from the shared sync-pulse path, Initialize shows all three camera feeds.
- In that unplugged state, Live/Record still only keeps the master moving, while the secondary feeds freeze.
- The master no longer stops after the previous 25-second playback symptom because secondary timeout no longer clears the shared acquisition flag.

Interpretation:

- The connected sync cable is actively affecting the secondary cameras during the Initialize preview.
- The secondary trigger inputs are probably being held in a state that prevents normal acquisition, or the master sync output is not producing the edge/level the secondary cameras expect.
- Since unplugging the cable changes Initialize behavior, the remaining synchronized-acquisition bug is likely electrical/trigger-state related rather than a basic camera enumeration or GUI display bug.

Code follow-up from this observation:

1. In diagnostic free-run mode, secondaries now remain `TriggerMode = Off` after a preview/Live/Record stop.
2. Previously, the worker always restored `TriggerMode = On` after `EndAcquisition()`, which could make Initialize preview work once and then make Live/Record freeze the secondaries again.

Next diagnostic expectation:

- With `syncDiagnosticFreeRunSecondaries: true`, Live should keep all three camera feeds moving even after Initialize.
- If that works, the code path is usable and the real fix should focus on master output line, secondary trigger input, trigger polarity, and BNC/sync-cable wiring.

## Diagnostic Result: Free-Run Works, Sync Cable Breaks SpinView

Result:

- With `syncDiagnosticFreeRunSecondaries: true` and the BNC sync cable unplugged, Initialize plus Live showed all three camera feeds moving.
- With the sync cable plugged into the BNC path, even SpinView cannot load the camera feeds.

Conclusion:

- The remaining problem is not the Python GUI display loop, camera process startup, camera enumeration, or video writer.
- The failure is downstream of software, in the external sync cable/BNC/GPIO electrical path or in the camera line configuration that interacts with that path.
- Since SpinView also fails with the cable connected, the sync cable is likely holding one or more camera lines in a bad electrical state, shorting/loading the line, using the wrong input/output pins, or driving the wrong polarity/voltage/ground reference.

Recommended next hardware checks:

1. Leave `syncDiagnosticFreeRunSecondaries: true` only for software testing; do not use it for synchronized recording.
2. Test each camera in SpinView with the sync cable connected one camera at a time to identify whether one branch/camera/cable leg causes the failure.
3. Verify the BNC/sync cable maps the master output line to secondary input lines, not output-to-output or input-to-power.
4. Check that all cameras share the correct ground/reference through the sync wiring.
5. Check whether the secondary input line needs pull-up/pull-down, inverted trigger activation, or a different physical line than the one assumed in Python.
6. Once SpinView can show the cameras with the sync cable connected, return `syncDiagnosticFreeRunSecondaries` to `false` and retest synchronized acquisition in the GUI.

## Updated Result: GUI Launch Can Leave Cameras Locked

Correction from later testing:

- SpinView can load all cameras whether the sync cables are plugged in or unplugged, as long as the behavior GUI has not first attempted a bad synchronized launch.
- After one behavior-GUI launch with sync cables connected, the slave cameras fail and then SpinView cannot load the cameras until the USB cameras are unplugged/replugged.

Interpretation:

- The sync cable may still be part of the trigger failure, but the camera lockout is caused by the behavior GUI not fully releasing cameras after the failed acquisition path.
- The important software bug is in the timeout/release cleanup path.
- After persistent secondary timeouts, the camera worker waits for a final queue message before ending acquisition. If that message is `Release`, the old code could consume it as a stop message, acknowledge the parent process, and skip the actual `cam.DeInit()` cleanup.

Cleanup fix applied:

1. Added a shared `release_camera_resources()` cleanup helper in `multiCam_DLC_PySpin_v2_extStim.py`.
2. Direct `Release` messages now deinitialize the camera, clear the camera list, release the PySpin system instance, acknowledge, and exit the worker loop.
3. If `Release` arrives while the worker is waiting at the end of a failed acquisition, it now performs the same cleanup instead of treating `Release` as a plain stop.
4. Trigger/line restore writes after `EndAcquisition()` are now guarded so a PySpin node error does not prevent cleanup.

Expected result:

- A bad synchronized GUI launch may still fail to acquire slave frames, but closing/releasing the GUI should no longer leave cameras locked from SpinView.
- The terminal should print `Camera <serial>: Deinitialized successfully` for each camera during release.

## Release Test Result: Cameras DeInit But SpinView Still Cannot Stream

Result:

- With sync cables connected, Initialize showed only the configured master feed.
- Release printed `Camera <serial>: Deinitialized successfully` for all three cameras.
- Release also printed `PySpin system release error: Spinnaker: Can't clear a camera because something still holds a reference to the camera [-1004]`.
- After closing the behavior GUI, SpinView could connect to cameras but could not show live feeds.

Interpretation:

- The release path is reaching `cam.DeInit()`, but it was still leaving PySpin references behind.
- SpinView being able to connect but not stream is also consistent with cameras being left in `TriggerMode = On` after the behavior GUI exits. In that state, SpinView can open the device, but the camera may wait for external triggers instead of free-running.

Cleanup follow-up applied:

1. Release now explicitly sets `TriggerMode = Off` before `cam.DeInit()`.
2. The worker now drops the local `cam` reference before clearing the camera list.
3. The main GUI now waits briefly for each camera process to exit after `Release` and only calls `terminate()` if that process does not exit.

Expected next release output:

- `Camera <serial>: TriggerMode set to Off before release`
- `Camera <serial>: Deinitialized successfully`
- No `Can't clear a camera because something still holds a reference` error.

Expected next SpinView result:

- After a failed behavior-GUI synchronized launch and Release, SpinView should be able to connect and stream without unplugging/replugging the cameras.

Confirmed result:

- This cleanup fix worked. After a bad behavior-GUI session, the cameras can now always be opened and streamed in SpinView without unplugging/replugging USB.

Remaining issue:

- The cleanup/lockout bug is fixed.
- The synchronized acquisition bug remains: with sync cables connected, only the configured master camera streams in the behavior GUI while secondary cameras time out.

## Intermittent Sync Success

Additional observation:

- Without changing code or wiring, the behavior GUI can sometimes load all three cameras with sync cables attached, but not often.

Interpretation:

- This makes a hard wrong-serial or completely broken camera path less likely.
- Intermittent success is consistent with a race/timing problem, marginal trigger electrical state, trigger polarity sensitivity, or startup ordering issue.
- The current `startAq()` sequence queues `Start` to the master and secondary cameras, then immediately sends `TrigOff` to the master. There is no handshake confirming the secondary cameras have reached `BeginAcquisition()` and are armed before the master begins free-running.

Recommended next software trial:

1. Change acquisition startup so secondary cameras receive `Start` first.
2. Have each camera worker acknowledge after successful `cam.BeginAcquisition()`.
3. Wait for all secondary acknowledgements.
4. Start the master camera.
5. Only then send `TrigOff` to the master.

Expected result:

- If the issue is startup ordering, all three cameras should load much more reliably with sync cables attached.
- If the issue remains intermittent or fails the same way, focus moves back to trigger polarity/line electrical state rather than startup order.

Implemented:

- Camera workers now send `started` after successful `cam.BeginAcquisition()`.
- `startAq()` now starts secondary cameras first, waits for their `started` acknowledgements, starts the master camera, waits for the master's `started` acknowledgement, and only then sends `TrigOff` to the master.
- If a camera does not acknowledge start within 5 seconds, the GUI logs a warning instead of hanging indefinitely.

## New Cable Setup: StimCam Unsynced

New hardware setup:

- One master camera.
- One synced secondary camera.
- `stimCam` has no sync line attached.

Implemented:

1. Added `syncFreeRunStimCam: true` to `systemdata.yaml`.
2. Added `syncDiagnosticFreeRunSecondaries: false` so only the stim camera free-runs, not all secondary cameras.
3. Added `syncSecondaryTriggerSource: Line3` so the synced secondary input line remains configurable.
4. In `multiCam_DLC_PySpin_v2_extStim.py`, if a camera is the configured `stimAxes` camera and `syncFreeRunStimCam` is true, it initializes with hardware trigger disabled.
5. That unsynced stim camera keeps `AcquisitionFrameRateEnable = True`, so it free-runs at its configured frame rate.
6. The non-stim secondary camera still uses the hardware trigger path and should remain synchronized to the master.

Expected result:

- Master camera streams.
- One non-stim secondary camera streams from the sync line.
- `stimCam` streams without sync and should not produce sync timeout errors due to missing cable.

Important:

- `stimCam` will not be frame-locked to the master/synced pair in this mode.
- Use timestamps or a visible timing event if `stimCam` timing must be aligned precisely afterward.
