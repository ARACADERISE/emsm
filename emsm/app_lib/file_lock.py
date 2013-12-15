#!/usr/bin/python3
# Benedikt Schmitt <benedikt@benediktschmitt.de>


# Modules
# ------------------------------------------------
import time
import atexit
import os

try:
    import msvcrt
except ImportError:
    msvcrt = None

try:
    import fcntl
except ImportError:
    fcntl = None


# Data
# ------------------------------------------------
__all__ = ["Timeout", "FileLock"]


# Exceptions
# ------------------------------------------------
class Timeout(Exception):
    """
    Raised when the lock could not be acquired in *timeout*
    seconds.
    """

    def __init__(self, lock_file):
        self.lock_file = lock_file
        return None

    def __str__(self):
        temp = "The file lock '{}' could not be acquired."\
               .format(self.lock_file)
        return temp


# Classes
# ------------------------------------------------
class BaseFileLock(object):
    """
    Implements the base class of a file lock.

    Usage:
    >>> with BaseFileLock("afile"):
            pass
            
    or if you need to specify a timeout:
    
    >>> with BaseFileLock("afile").acquire(5):
            pass
    """

    def __init__(self, lock_file):
        self._lock_file = lock_file
        self._lock_file_fd = None

        atexit.register(self.release)
        return None

    lock_file = property(lambda self: self._lock_file)
    
    # Platform dependent locking
    # --------------------------------------------

    def _acquire(self):
        """
        Platform dependent. If the file lock could be
        acquired, self._lock_file_fd holds the file descriptor
        of the lock file.
        """
        raise NotImplementedError()            

    def _release(self):
        """
        Releases the lock and sets self._lock_file_fd to None.
        """
        raise NotImplementedError()
    
    # Platform independent methods
    # --------------------------------------------
    
    def is_locked(self):
        """
        Returns true, if the object holds the file lock.
        """
        return self._lock_file_fd is not None
    
    def acquire(self, timeout=None, poll_intervall=0.05):
        """
        Tries every *poll_intervall* seconds to acquire the lock.
        If the lock could not be acquired after *timeout* seconds,
        a Timeout exception will be raised.
        If *timeout* is ``None``, there's no time limit.
        """
        # Breaks if waited timeout seconds for the lock
        # or if the lock has been acquired.
        start_time = time.time()
        
        while not self.is_locked(): 
            self._acquire()

            if timeout is not None and time.time() - start_time > timeout:
                raise Timeout(self._lock_file)
            else:
                time.sleep(poll_intervall)
        return self    

    def release(self):
        """
        Releases the file lock.
        """
        if self.is_locked():
            self._release()
        return None
    
    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.release()
        return None

    def __del__(self):
        self.release()
        return None


# Windows locking mechanism
if msvcrt:
    class FileLock(BaseFileLock):
        
        def _acquire(self):
            open_mode = os.O_RDWR | os.O_CREAT | os.O_TRUNC
            fd = os.open(self._lock_file, open_mode)

            try:
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            except OSError:
                os.close(fd)
            else: 
                self._lock_file_fd = fd
            return None
                
        def _release(self):
            msvcrt.locking(self._lock_file_fd, msvcrt.LK_UNLCK, 1)        
            os.close(self._lock_file_fd)     
            self._lock_file_fd = None
            
            try:
                os.remove(self._lock_file)
            # Probably another instance of the application
            # that acquired the file lock.
            except OSError:
                pass
            return None

# Unix locking mechanism
elif fcntl:
    class FileLock(BaseFileLock):
        
        def _acquire(self):
            open_mode = os.O_RDWR | os.O_CREAT | os.O_TRUNC
            fd = os.open(self._lock_file, open_mode)

            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except (IOError, OSError):
                os.close(fd)
            else: 
                self._lock_file_fd = fd
            return None
            
        def _release(self):
            fcntl.flock(self._lock_file_fd, fcntl.LOCK_UN)        
            os.close(self._lock_file_fd)
            self._lock_file_fd = None
            
            try:
                os.remove(self._lock_file)
            # Probably another instance of the application
            # that acquired the file lock.
            except OSError:
                pass
            return None

# Lock is not available
else:
    raise ImportError("The file lock is not available for your OS")
        
    
# Main
# ------------------------------------------------
if __name__ == "__main__":
    # Run multiple instances of this script to test it.
    lock = FileLock("lock")
    print("entering")
    with lock.acquire():
        print("entered")
        time.sleep(5)
    print("left")
