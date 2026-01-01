# 📄 File Notes

#     This script reads in the systemdata.yaml file located in the same directory as the notebook.

#     It uses the interim_data_dir and compressed_data_dir paths specified in that YAML file.

#     It then runs the same compression logic used by multiCam_RT_videoAcquisition_v5.py.

#     Specifically, it searches for .avi files inside interim_data_dir, compresses them into .mp4 files using ffmpeg, and saves them to the corresponding folder inside compressed_data_dir.

#     Important: Unlike the compression button in multiCam_RT_videoAcquisition_v5.py, this notebook does not immediately delete the .avi files. Instead, it compresses and moves them first so you can manually verify the .mp4 output.

#     Once you're satisfied with the .mp4 files, simply run the final cell in this notebook to delete the corresponding .avi files from interim_data_dir.

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




def compare_raw_vs_compressed(raw_base_dir, comp_base_dir, unit='christielab'):
    raw_sessions = glob.glob(os.path.join(raw_base_dir, '*', unit, 'session*'))
    results = []

    for raw_session in raw_sessions:
        comp_session = raw_session.replace(raw_base_dir, comp_base_dir)
        raw_avi_files = glob.glob(os.path.join(raw_session, '*.avi'))
        comp_mp4_files = glob.glob(os.path.join(comp_session, '*.mp4'))
        comp_mp4_names = {PurePath(f).stem for f in comp_mp4_files}

        for avi in raw_avi_files:
            avi_name = PurePath(avi).stem
            has_match = avi_name in comp_mp4_names
            results.append((avi_name, has_match, raw_session))

    print("🎞️ Comparison of .avi and .mp4 files across sessions:")
    for name, match, session in results:
        status = "✅ MATCHED" if match else "❌ MISSING .mp4"
        
        print(f"{status}: {name}  ({session})")

    return results  # Optional: for inspection

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


def delete_matched_avi_files(results,delete_avi_videos=False):
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
