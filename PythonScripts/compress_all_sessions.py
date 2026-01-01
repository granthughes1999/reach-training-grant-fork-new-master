
import shutil
import subprocess
from pathlib import PurePath
import cv2
import multiCam_DLC_utils_v2 as clara  # Must be in your path
import gc
import time
from tqdm import tqdm

import os
import glob

from pathlib import PurePath

# ⚙️ Setup: Load user config and paths
user_cfg = clara.read_config()
read_dir = user_cfg['interim_data_dir']
write_dir = user_cfg['compressed_data_dir']
unit_ref = user_cfg['unitRef']
final_dir = user_cfg['final_data_dir']
print(f"Loaded paths for unit: {unit_ref}")
print('')
print(f'read_dir: {read_dir}')
print(f'write_dir: {write_dir}')
print(f'unit_ref: {unit_ref}')
print(f'final_dir: {final_dir}')

# 📁 Discover all AVI videos to compress

def get_video_dirs():
    dirlist, destlist = [], []
    prev_date_list = [name for name in os.listdir(read_dir)]
    
    for date in prev_date_list:
        src_dir = os.path.join(read_dir, date, unit_ref)
        dest_dir = os.path.join(write_dir, date, unit_ref)
        if os.path.exists(src_dir):
            for sess in os.listdir(src_dir):
                dirlist.append(os.path.join(src_dir, sess))
                destlist.append(os.path.join(dest_dir, sess))
    
    return dirlist, destlist

dirlist, destlist = get_video_dirs()
print(f"Found {len(dirlist)} directories with videos.")
print(f'Verify raw files: {dirlist}')
print(f'Verify Compression Destination: {destlist}')

# 🧪 Function to compare frame counts

def test_vids(v, dest_path):
    try:
        vid_a = cv2.VideoCapture(v)
        frames_a = int(vid_a.get(cv2.CAP_PROP_FRAME_COUNT))
        vid_b = cv2.VideoCapture(dest_path)
        frames_b = int(vid_b.get(cv2.CAP_PROP_FRAME_COUNT))
        return (frames_a == frames_b) and (frames_a > 0)
    except:
        return False

# new test
def test_vids(v, dest_path):
    try:
        vid_a = cv2.VideoCapture(v)
        vid_b = cv2.VideoCapture(dest_path)
        frames_a = int(vid_a.get(cv2.CAP_PROP_FRAME_COUNT))
        frames_b = int(vid_b.get(cv2.CAP_PROP_FRAME_COUNT))
        vid_a.release()
        vid_b.release()
        return (frames_a == frames_b) and (frames_a > 0)
    except:
        return False


    # 🗜️ Compress and replace .avi with .mp4 using ffmpeg

def compress_videos_in_dir(src_dir, dest_dir):
    


    # old code
    # avi_list = glob.glob(os.path.join(src_dir, '*.avi'))


    # New Code
    cam_patterns = [
        "*_frontCam-*.avi",
        "*_stimCam-*.avi",
        "*_sideCam-*.avi",
    ]
    avi_list = []
    for pat in cam_patterns:
        avi_list.extend(sorted(glob.glob(os.path.join(src_dir, pat))))
    # include any other AVIs not matching the three cams (keeps backward compatibility)
    remaining = set(glob.glob(os.path.join(src_dir, '*.avi'))) - set(avi_list)
    avi_list.extend(sorted(remaining))
    # New Code

    if not avi_list:
        return

    os.makedirs(dest_dir, exist_ok=True)
    processes = []

    for v in avi_list:
        vid_name = PurePath(v)
        dest_path = os.path.join(dest_dir, vid_name.stem + '.mp4')

        if not test_vids(v, dest_path):  # Don't recompress if valid
            env = os.environ.copy()
            env["PATH"] = r"C:\ffmpeg\bin;" + env["PATH"]
            cmd = f'ffmpeg -y -i "{v}" -c:v libx264 -preset veryfast -vf format=yuv420p -c:a copy -crf 17 -loglevel quiet "{dest_path}"'
            print(f"Compressing: {vid_name.name} ➜ {vid_name.stem}.mp4 ")
            processes.append(subprocess.Popen(cmd, env=env, shell=True))

    # Wait for all compressions to finish
    for p in processes:
        p.wait()

    # Validate and remove successful .avi
    for v in avi_list:
        vid_name = PurePath(v)
        dest_path = os.path.join(dest_dir, vid_name.stem + '.mp4')
        if test_vids(v, dest_path):
            #os.remove(v)
            print(f"✅ Compressed: {vid_name.name}")
        else:
            print(f"❌ Compression failed: {vid_name.name}")

            # 🧹 Copy non-avi files (e.g., YAML metadata)
    
    # ✅ Cleanup: Clear system-level file locks
    import gc
    gc.collect()
    print('Cleared videos from temporary memory')

def copy_metadata(src_dir, dest_dir):
    os.makedirs(dest_dir, exist_ok=True)
    metafiles = glob.glob(os.path.join(src_dir, '*'))
    for m in metafiles:
        if '.avi' not in m:
            mname = PurePath(m).name
            mdest = os.path.join(dest_dir, mname)
            if not os.path.isfile(mdest):
                shutil.copyfile(m, mdest)




def estimate_compression_all_sessions(base_dir):
    session_dirs = glob.glob(os.path.join(base_dir, '*', '*', 'session*'))  # e.g. RawData/20250415/christielab/session001
    total_size = 0
    total_files = 0

    print("📦 Estimated compression job across all sessions:\n")

    for session in session_dirs:
        avi_files = glob.glob(os.path.join(session, '*.avi'))
        if not avi_files:
            continue

        session_size = 0
        print(f"📁 Session: {session}")
        for avi in avi_files:
            size_mb = os.path.getsize(avi) / (1024 * 1024)
            size_gb = size_mb /1000
            session_size += size_mb
            print(f"  • {os.path.basename(avi)} — {size_mb:.2f} MB --> {size_gb:.2F} GB")

        est_time = len(avi_files) * 8  # ~8s per video
        print(f"  🧮 Session total: {session_size:.2f} MB")
        print(f"  ⏱️  Estimated time: ~{est_time:.1f} seconds ({est_time/60:.1f} min)\n")

        # Actual Historical Compression time for 467.54 GB // 13 minutes
        compress_time_min = 13 
        file_size_total = 467.5
        gb_compressed_per_min =  file_size_total/ compress_time_min 
        gb_compressed_every_10_min = gb_compressed_per_min * 10
        print(f'Compression Speed: (( {gb_compressed_per_min:.0f} gb )) per 1 Minute')
        print(f'Compression Speed: (( {gb_compressed_every_10_min:.0f} gb )) per 10 Minute')

        total_size += session_size
        total_size_gb = total_size /1000
        est_compress_time = total_size_gb
        total_files += len(avi_files)

    
    estimated_compression_time_min = (total_size_gb /gb_compressed_per_min )
    estimated_compression_time_min
    print("🔚 Final summary:")
    print(f"🔢 Total files: {total_files}")
    print(f"📂 Total size: {total_size:.2f} MB") 
    print(f"📂 Total size: {total_size_gb:.2f} GB") 
    print(f"⏱️  Estimated total Compression time: ({estimated_compression_time_min:.1f} minutes)")
    return total_size_gb, estimated_compression_time_min

# Example usage:
total_size_gb, estimated_compression_time_min = estimate_compression_all_sessions(read_dir)


# Usage
print(f'\n')
print(f"📂 Total size: {total_size_gb:.2f} GB") 
print(f"⏱️ Estimated total Compression time: ({estimated_compression_time_min:.1f} minutes)") 
print(f'\n\n')




for src_dir, dest_dir in zip(dirlist, destlist):
    compress_videos_in_dir(src_dir, dest_dir)
    copy_metadata(src_dir, dest_dir)
# Clear files from background
gc.collect()
time.sleep(1)  # Let the OS finish background cleanup
print("\n🎉 All video compression completed.")
print('Files cleared from background memory')

