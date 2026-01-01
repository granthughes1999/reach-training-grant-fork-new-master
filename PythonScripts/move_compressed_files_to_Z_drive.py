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


def move_compressed_sessions(write_dir, final_dest,view_skipped=False):
    session_dirs = glob.glob(os.path.join(write_dir, '*', '*', 'session*'))
    print(f"📦 Preparing to copy {len(session_dirs)} session folders...\n")

    skip_counter = 0
    backup_counter = 0
    for session_path in session_dirs:
        rel_path = os.path.relpath(session_path, write_dir)  # keeps subfolder structure
        dest_path = os.path.join(final_dest, rel_path)

        if os.path.exists(dest_path):
            if view_skipped:
                skip_counter += 1
                print(f"⚠️  Skipping existing: {dest_path}") # set view_skipped=True if you want to look as the specfic files its passing over (because they are already backed up) 
            skip_counter += 1
            continue

        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        print(f"📁 Copying: {session_path} ➜ {dest_path}")
        shutil.copytree(session_path, dest_path)
        backup_counter += 1
    print('=======================================================================')
    print(f'⚠️{skip_counter} files were skipped. because they allready had backups')
    print('')
    print("\n✅ All eligible session folders have been copied!")
    print(f'📂 {backup_counter} session(s) were copied')


estimated_transfer_time_min = (total_size_gb /gb_transfer_per_min )
print(f'⏱️ Estimated Transfer Time: {estimated_transfer_time_min:.0f} Minute(s)\n\n')

move_compressed_sessions(write_dir, final_dir,view_skipped=False)

print('\a')
import winsound
winsound.Beep(1000, 2000)  # 1000 Hz for 0.5 seconds
