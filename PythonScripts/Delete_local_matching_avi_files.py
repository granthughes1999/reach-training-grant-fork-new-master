

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


def list_avi_to_delete(results):
    to_delete = []

    for name, matched, session in results:
        if matched:
            avi_path = os.path.join(session, name + '.avi')
            if os.path.exists(avi_path):
                to_delete.append(avi_path)

    print(f"\n🧹 {len(to_delete)} .avi files are safe to delete:\n")
    for path in to_delete:
        print(f"🗑️ {path}")
    
    return to_delete  # So you can manually delete or loop over them
results = compare_raw_vs_compressed(read_dir, write_dir)
avi_files_to_delete = list_avi_to_delete(results)

# After compressing or verifying videos
gc.collect()
time.sleep(1)  # Let the OS finish background cleanup

def delete_matched_avi_files(results, delete_avi_videos=False):
    if delete_avi_videos:
        matched_files = [(name, session) for name, matched, session in results if matched]
        deleted = []

        print(f"🔍 Attempting to delete {len(matched_files)} matched .avi files...\n")

        for name, session in tqdm(matched_files, desc="🧹 Deleting", unit="file"):
            avi_path = os.path.join(session, name + '.avi')
            if os.path.exists(avi_path):
                try:
                    start = time.time()
                    os.remove(avi_path)

                    # New Code: wait up to 120s for confirmation
                    timeout = 120
                    while os.path.exists(avi_path) and (time.time() - start) < timeout:
                        time.sleep(1)

                    if os.path.exists(avi_path):
                        print(f"⏭️ Skipped (not deleted after {timeout}s): {avi_path}")
                        continue

                    elapsed = time.time() - start
                    print(f"✅ Deleted: {avi_path} ({elapsed:.2f} s)")
                    deleted.append(avi_path)

                except Exception as e:
                    import traceback
                    print(f"❌ Error deleting {avi_path}: {e}")
                    traceback.print_exc()

        print(f"\n🧼 Done! Deleted {len(deleted)} files.")
        return deleted
    else:
        print('⚠️Fail safe activated⚠️')
        print('Are you sure you want to delete the raw .avi files?')
        print(' ')
        print('✅ if Yes, simply run this cell again and it will delete all .avi files that have a .mp4 copy')
        print('❌ if No, do not re-run this cell')


results = compare_raw_vs_compressed(read_dir, write_dir)
delete_matched_avi_files(results,delete_avi_videos = True)

# Commpletion Sound
print('\a')
import winsound
winsound.Beep(1000, 500)  # 1000 Hz for 0.5 seconds


