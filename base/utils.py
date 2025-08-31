import ctypes
import glob
import os
import platform
import re
import shutil

from .console import console
from models.store import store


# Mimic an os.DirEntry so functions below return more uniformly
# https://stackoverflow.com/a/57439730/4599061
class PseudoDirEntry:
    def __init__(self, path):
        import os, os.path
        self.path = os.path.realpath(path)
        self.name = os.path.basename(self.path)
        self.is_dir = os.path.isdir(self.path)
        self.stat = lambda: os.stat(self.path)
        self.mtime = os.path.getmtime(self.path)

def subfolders_of_path(path):
    """
    Returns a list of the immediate subfolders of a given path
    (as f.path and f.name)
    :param path:
    :return: list: a list of the immediate subfolders of a given path (f.path and f.name)
    """
    return [f for f in os.scandir(path) if f.is_dir()]


def subfolders_of_path_recursive(path):
    """
    Returns a list of the all subfolders (recursively) of a given path
    (as list of {f.path, f.name})
    :param path:
    :return: [PseudoDirEntry] list of PseudoDirEntry of subfolders for the given path
    """
    folders = glob.glob(f"{path}/**/", recursive=True)
    temp = []
    for folder in folders:
        temp.append(PseudoDirEntry(folder))
    return temp



def video_files_in_path_recursive(path):
    """
    Using the list of video files extensions from the store, recursively find and return a list of all video files as PseudoDirEntry objects
    (equivalent to os.DirEntry)
    :param path:
    :return: [PseudoDirEntry] list of PseudoDirEntry of video files (f.name, f.path etc)
    """
    video_files = []
    for file_ext in store.video_file_extensions:
        video_files.extend(glob.glob(f"{path}/**/*{file_ext}"))
    temp = []
    for video in video_files:
        temp.append(PseudoDirEntry(video))
    return temp

def sxxexx_video_files_in_path(path, sxxexx):
    sxxexx_files = []
    for file_ext in store.video_file_extensions:
        sxxexx_files.extend(glob.glob(f"{path}/**/*{sxxexx}*{file_ext}"))
    temp = []
    for video in sxxexx_files:
        temp.append(PseudoDirEntry(video))
    return temp

def list_of_folder_contents_as_paths(d):
    """
    Returns a list of files and folders in a directory *with their full paths*
    i.e. like os.listdir, but with full paths returned
    """
    return [os.path.join(d, f) for f in os.listdir(d)]


def list_of_files(path):
    """
    List only the files in a folder, not subdirectories
    Returns a list of files *with full paths*
    """
    return [os.path.join(path, filename) for filename in os.listdir(path)
            if os.path.isfile(os.path.join(path, filename))]


def copy_folder(src, dst):
    """
    Faster folder copier, and copies attributes & dates etc
    Returns nothing
    """
    shutil.copytree(src, dst)


def folder_size_in_bytes(start_path='.'):
    """
    Get size of dir e.g. to check it all copied OK
    Returns size in bytes
    """
    total_size = 0
    for dir_path, dir_names, filenames in os.walk(start_path):
        for f in filenames:
            fp = os.path.join(dir_path, f)
            total_size += os.path.getsize(fp)
    return total_size


def free_space_in_bytes(folder):
    """
    Return folder/drive free space (in bytes)
    Cross-platform
    https://stackoverflow.com/questions/51658/cross-platform-space-remaining-on-volume-using-python
    (This is rather archaic but still works)
    """
    if platform.system() == 'Windows':
        free_bytes = ctypes.c_ulonglong(0)
        ctypes.windll.kernel32.GetDiskFreeSpaceExW(ctypes.c_wchar_p(folder), None, None, ctypes.pointer(free_bytes))
        return free_bytes.value
    else:
        st = os.statvfs(folder)
        return st.f_bavail * st.f_frsize


def free_space_in_gigabytes(folder):
    """
    Return folder/drive free space (in gigabytes)
    """
    calulated_bytes = free_space_in_bytes(folder)
    return calulated_bytes / 1024 / 1024 / 1024


def extract_sxxexx(incoming: str):
    """
    Match an SxxExx pattern in a string (i.e. series and episode details from a video file name)
    :param incoming: str containing SxxExx or sxxexx within, e.g. 'Whatever - S01E01 - WEB-DL_1080p.mkv'
    :return: None, if no match, or the found substring sxxexx, season_string, season_int, episode_string, episode_int
    """
    match = re.search('([Ss][0-9]+)([Ee][0-9]+)', incoming)
    if not match:
        console.log(f"Could not parse sxxexx from {incoming}", style="danger")
        return None
    sxxexx = match.group(0)
    season_string = match.group(1)[1:]
    season_int = int(season_string)
    episode_string = match.group(2)[1:]
    episode_int = int(episode_string)
    return sxxexx, season_string, season_int, episode_string, episode_int

# NO LONGER USED - DELETE LATER
# def copy_file(src, dst, buffer_size=10485760, preserve_file_date=True):
#     """
#     Copies a file to a new location. Much faster performance than Apache Commons due to use of larger buffer
#     @param src:    Source File
#     @param dst:    Destination File (not file path)
#     @param buffer_size:    Buffer size to use during copy
#     @param preserve_file_date:    Preserve the original file date
#     """
#
#     #    Check to make sure destination directory exists. If it doesn't create the directory
#     dst_parent, dst_file_name = os.path.split(dst)
#     if not os.path.exists(dst_parent):
#         os.makedirs(dst_parent)
#
#     #    Optimize the buffer for small files
#     buffer_size = min(buffer_size, os.path.getsize(src))
#     if buffer_size == 0:
#         buffer_size = 1024
#
#     # noinspection PyProtectedMember
#     if shutil._samefile(src, dst):
#         raise shutil.Error("`%s` and `%s` are the same file" % (src, dst))
#     for fn in [src, dst]:
#         try:
#             st = os.stat(fn)
#         except OSError:
#             # File most likely does not exist
#             pass
#         else:
#             # XXX What about other special files? (sockets, devices...)
#             if shutil.stat.S_ISFIFO(st.st_mode):
#                 raise shutil.SpecialFileError("`%s` is a named pipe" % fn)
#     if os.path.isdir(src):
#         shutil.copytree(src, dst)
#     else:
#         with open(src, 'rb') as f_src:
#             with open(dst, 'wb') as f_dst:
#                 shutil.copyfileobj(f_src, f_dst, buffer_size)
#
#     if preserve_file_date:
#         shutil.copystat(src, dst)
