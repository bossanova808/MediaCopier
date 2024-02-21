import os
import shutil
import platform
import ctypes


def get_free_space_gb(folder):
    """
        Return folder/drive free space (in bytes)
        Should work cross platform
        https://stackoverflow.com/questions/51658/cross-platform-space-remaining-on-volume-using-python
    """
    if platform.system() == 'Windows':
        free_bytes = ctypes.c_ulonglong(0)
        ctypes.windll.kernel32.GetDiskFreeSpaceExW(ctypes.c_wchar_p(folder), None, None, ctypes.pointer(free_bytes))
        return free_bytes.value / 1024 / 1024 / 1024
    else:
        st = os.statvfs(folder)
        return st.f_bavail * st.f_frsize / 1024 / 1024 / 1024


def list_of_directory_paths_for(d):
    """
        Returns a list of files and folders in a directory *with their full paths*
        i.e. like os.listdir, but with full paths returned
    """
    return [os.path.join(d, f) for f in os.listdir(d)]


def list_files(path):
    """
        List only the files in a folder, not directories
        Returns a list of files *with full paths*
    """
    return [os.path.join(path, filename) for filename in os.listdir(path)
            if os.path.isfile(os.path.join(path, filename))]


def copy_folder(src, dst):
    """
        Faster folder copier
        Returns nothing
    """
    shutil.copytree(src, dst)


def get_directory_size_in_bytes(start_path='.'):
    """
        Get size of dir to check it all copied ok
        Returns size in bytes
    """
    total_size = 0
    for dir_path, dir_names, filenames in os.walk(start_path):
        for f in filenames:
            fp = os.path.join(dir_path, f)
            total_size += os.path.getsize(fp)
    return total_size


def copy_file(src, dst, buffer_size=10485760, preserve_file_date=True):
    """
        Copies a file to a new location. Much faster performance than Apache Commons due to use of larger buffer
        @param src:    Source File
        @param dst:    Destination File (not file path)
        @param buffer_size:    Buffer size to use during copy
        @param preserve_file_date:    Preserve the original file date
    """

    #    Check to make sure destination directory exists. If it doesn't create the directory
    dst_parent, dst_file_name = os.path.split(dst)
    if not os.path.exists(dst_parent):
        os.makedirs(dst_parent)

    #    Optimize the buffer for small files
    buffer_size = min(buffer_size, os.path.getsize(src))
    if buffer_size == 0:
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
        with open(src, 'rb') as f_src:
            with open(dst, 'wb') as f_dst:
                shutil.copyfileobj(f_src, f_dst, buffer_size)

    if preserve_file_date:
        shutil.copystat(src, dst)


def get_free_space(folder):
    """
        Return folder/drive free space (in bytes)
    """
    if platform.system() == 'Windows':
        free_bytes = ctypes.c_ulonglong(0)
        ctypes.windll.kernel32.GetDiskFreeSpaceExW(ctypes.c_wchar_p(folder), None, None, ctypes.pointer(free_bytes))
        return free_bytes.value
    else:
        return os.statvfs(folder).f_bfree
