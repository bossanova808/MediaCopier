import os, shutil, sys
import platform
import ctypes
import logging
from pprint import pprint

################################################################################
### Should work cross platform
# https://stackoverflow.com/questions/51658/cross-platform-space-remaining-on-volume-using-python

def get_free_space_gb(folder):
    """ Return folder/drive free space (in bytes)
    """
    if platform.system() == 'Windows':
        free_bytes = ctypes.c_ulonglong(0)
        ctypes.windll.kernel32.GetDiskFreeSpaceExW(ctypes.c_wchar_p(folder), None, None, ctypes.pointer(free_bytes))
        return free_bytes.value/1024/1024/1024
    else:
        st = os.statvfs(folder)
        return st.f_bavail * st.f_frsize/1024/1024/1024

################################################################################
### like os.listdir, but with full paths returned
### Returns a list of files and folders in a directory *with full paths*

def listdirPaths(d):
  return [os.path.join(d, f) for f in os.listdir(d)]


################################################################################
### List only the files in a folder, not directories
### Returns a list of files *with full paths*

def listfiles(path):
  return [os.path.join(path, filename) for filename in os.listdir(path)
  if os.path.isfile(os.path.join(path, filename))]

################################################################################
### Faster folder copier
### returns nothing

def copyFolder(src, dst):
  shutil.copytree(src,dst)

################################################################################
### Get Size of dir to check it all copied ok
### returns size in bytes

def getSize(start_path = '.'):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(start_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total_size += os.path.getsize(fp)
    return total_size

################################################################################
### Faster file copier
### returns nothing

def copyFile(src, dst, buffer_size=10485760, perserveFileDate=True):
    '''
    Copies a file to a new location. Much faster performance than Apache Commons due to use of larger buffer
    @param src:    Source File
    @param dst:    Destination File (not file path)
    @param buffer_size:    Buffer size to use during copy
    @param perserveFileDate:    Preserve the original file date
    '''
    #    Check to make sure destination directory exists. If it doesn't create the directory
    dstParent, dstFileName = os.path.split(dst)
    if(not(os.path.exists(dstParent))):
        os.makedirs(dstParent)

    #    Optimize the buffer for small files
    buffer_size = min(buffer_size,os.path.getsize(src))
    if(buffer_size == 0):
        buffer_size = 1024

    if shutil._samefile(src, dst):
        raise shutil.Error("`%s` and `%s` are the same file" % (src, dst))
    for fn in [src, dst]:
        try:
            st = os.stat(fn)
        except OSError:
            # File most likely does not exist
            pass
        else:
            # XXX What about other special files? (sockets, devices...)
            if shutil.stat.S_ISFIFO(st.st_mode):
                raise shutil.SpecialFileError("`%s` is a named pipe" % fn)
    if os.path.isdir(src):
        shutil.copytree(src, dst)
    else: 
        with open(src, 'rb') as fsrc:
            with open(dst, 'wb') as fdst:
                shutil.copyfileobj(fsrc, fdst, buffer_size)

    if(perserveFileDate):
        shutil.copystat(src, dst)


def getFreeSpace(folder):
    """ Return folder/drive free space (in bytes)
    """
    if platform.system() == 'Windows':
        free_bytes = ctypes.c_ulonglong(0)
        ctypes.windll.kernel32.GetDiskFreeSpaceExW(ctypes.c_wchar_p(folder), None, None, ctypes.pointer(free_bytes))
        return free_bytes.value
    else:
        return os.statvfs(folder).f_bfree



