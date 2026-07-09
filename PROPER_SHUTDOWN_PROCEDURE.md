# Proper GUI Shutdown Procedure

## Normal Shutdown (Recording → Close GUI)

### ✅ CORRECT Procedure (Prevents Camera Stuck Issues)

**Step-by-step from recording to closed GUI:**

1. **Stop Recording**
   - Click **"Stop"** button in GUI
   - Wait for recording to finish (progress bar completes)
   - Console shows: "Past record check" or similar

2. **Release Cameras** 
   - Click **"Release"** button in GUI
   - **CRITICAL:** Wait for console messages showing cameras released:
     ```
     Camera 12345678: Deinitialized successfully
     Camera 23456789: Deinitialized successfully
     Camera 34567890: Deinitialized successfully
     ```
   - **DO NOT skip this wait** - this is where most problems occur

3. **Close GUI**
   - Now safe to close the GUI application
   - Use the X button or File → Exit

**Total time: ~5-10 seconds**

---

## During Live View (No Recording)

**Step-by-step from live view to closed GUI:**

1. **Stop Live View** (if enabled)
   - Click **"Live"** button to toggle off (or it may be called "Stop")
   - Wait 1-2 seconds for live feed to stop

2. **Release Cameras**
   - Click **"Release"** button
   - **CRITICAL:** Wait for console confirmation:
     ```
     Camera 12345678: Deinitialized successfully
     Camera 23456789: Deinitialized successfully
     Camera 34567890: Deinitialized successfully
     ```

3. **Close GUI**
   - Now safe to close the application

---

## ❌ WRONG Procedures (Causes Stuck Cameras)

### Don't Do This:
1. ❌ Click Stop → immediately close GUI (skips Release)
2. ❌ Click Release → close GUI before waiting for "Deinitialized" messages
3. ❌ Force close GUI with Task Manager while recording
4. ❌ Close GUI without clicking Release button
5. ❌ Unplug cameras before releasing them in GUI

### Why These Cause Problems:
- Cameras remain in streaming state
- Internal buffers not cleared
- Sync state corrupted
- USB connection not properly closed
- Requires power cycle to recover

---

## Troubleshooting Console Messages

### ✅ Good Messages (Safe to Close)
```
Camera 12345678: Deinitialized successfully
StimSerial CLosed
```

### ⚠️ Warning Messages (Wait Longer)
```
Camera 12345678: Still streaming during release, ending acquisition
Camera 12345678: Error ending acquisition: ...
```
**Action:** Wait 5 more seconds, then close GUI

### ❌ Error Messages (Problem Occurred)
```
Camera 12345678: Error during deinit: ...
Camera cleanup error: ...
```
**Action:** Close GUI, then follow recovery procedure (unplug cameras, wait 2-3 min, replug)

---

## Quick Reference Card

**Normal Shutdown:**
```
Recording/Live → Stop → Release → Wait for "Deinitialized" → Close GUI
                                    ↑
                            CRITICAL STEP
                          (don't skip this!)
```

**If You Forget to Release:**
```
1. Cameras will have solid green lights (stuck streaming)
2. Next time you open GUI, cameras won't initialize
3. Recovery: Unplug USB → wait 30s → replug → try again
4. If still stuck: Unplug all → wait 2-3 min → replug
```

---

## Best Practices

### Always Do:
- ✅ Click Stop before Release
- ✅ Click Release before closing GUI
- ✅ Wait for console confirmation of "Deinitialized successfully"
- ✅ Check console for any error messages before closing

### Never Do:
- ❌ Close GUI while recording
- ❌ Close GUI without releasing cameras
- ❌ Force close with Task Manager (unless frozen)
- ❌ Unplug cameras while GUI is running

---

## Special Cases

### GUI Frozen/Crashed During Recording

If GUI becomes unresponsive:

1. **Don't force close immediately** - give it 30 seconds to respond
2. If still frozen after 30s, check Task Manager CPU usage:
   - High CPU = still processing, wait longer
   - Low CPU = truly frozen, can force close

3. **After force close:**
   - Cameras will be stuck in streaming state
   - Follow recovery procedure:
     - Unplug all camera USB cables
     - Wait 2-3 minutes (for capacitor discharge)
     - Replug USB cables
     - Open GUI and try again

### Power Loss During Recording

If power is lost or computer crashes:

1. Cameras will remain in stuck state
2. On next startup:
   - Cameras may have solid green lights
   - GUI won't be able to initialize them

3. **Recovery:**
   - Unplug all camera USB cables
   - Wait 2-3 minutes
   - Replug USB cables
   - Open GUI

---

## Verification After Shutdown

**How to know you shut down correctly:**

Next time you open the GUI:
- ✅ Cameras initialize quickly (5-10 seconds)
- ✅ Console shows "Buffer handling set to NewestOnly"
- ✅ No error messages about cameras still streaming
- ✅ Live view works immediately

**Signs of improper shutdown:**
- ❌ Cameras won't initialize
- ❌ Error: "Camera is already streaming"
- ❌ Cameras have solid green lights (should blink then go steady)
- ❌ Timeout errors when starting live view

---

## Updated Software Benefits

**With the new code (multiCam_DLC_PySpin_v2_extStim.py):**

Even if shutdown is done incorrectly:
- ✅ Next startup will detect stuck cameras
- ✅ Will attempt to end streaming automatically
- ✅ Better error messages guide you to solution
- ✅ Less likely to require full power cycle

**Console will show:**
```
Camera 12345678: Still streaming during release, ending acquisition
Camera 12345678: Deinitialized successfully
```

This automatic recovery wasn't in the old code!

---

## Summary

**Simple rule:** 
```
Stop → Release → Wait → Close
```

**Critical part:** Wait for "Deinitialized successfully" messages before closing GUI.

**If you mess up:** Unplug cameras → wait 2-3 minutes → replug → try again.

**With new code:** Better automatic recovery, clearer error messages, less likely to get stuck.
