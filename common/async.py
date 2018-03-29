# -*- coding: utf-8 -*-
# @Author: Maximus
# @Date:   2018-03-19 19:12:45
# @Last Modified by:   Maximus
# @Last Modified time: 2018-03-28 10:59:31
from multiprocessing import Queue
from multiprocessing.queues import Empty
from functools import partial
from threading import Event, Lock, Thread

from sublime import set_timeout


class AsyncResult(object):
    result = None
    failed = None

    def __init__(self):
        self.event = Event()

    def get(self, timeout=None):
        self.event.wait(timeout)
        if timeout is None:
            if self.failed:
                raise self.result
            return self.result
        else:
            return self.event.is_set(), self.result

    def capture(self, f):
        ''' Execute f() and save its result. '''
        try:
            self.result = f()
        except Exception as e:
            self.failed = True
            self.result = e
        else:
            self.failed = False
        finally:
            self.event.set()


class WorkerThread(object):
    thread = None

    def __init__(self, timeout=5):
        self.timeout = timeout
        self.queue = Queue()
        self.lock = Lock()

    def main(self):
        while True:
            try:
                f, result = self.queue.get(True, self.timeout)
            except Empty:
                # Time to clean up this thread, make sure not to miss anything.
                with self.lock:
                    # Something may have arrived just after Empty was raised.
                    # Check again, this time holding a critical section.
                    if self.queue.empty():
                        self.thread = None
                        break
            else:
                if result is None:
                    f()
                else:
                    result.capture(f)

    def call(self, _f, *args, **kwargs):
        ''' Execute _f(*args, **kwargs) in a worker thread associated with this
        object. Returns AsyncResult which can be used to wait for posted call
        to complete and get its result.
        '''

        # Prepare request.
        forget = kwargs.pop('_forget', False)
        _f = partial(_f, *args, **kwargs)
        if forget:
            result = None
        else:
            result = AsyncResult()

        # Post the request.
        with self.lock:
            self.queue.put((_f, result))

            # If there was no thread to handle the request (the last one timed
            # out or exited abnormally) than create a new one.
            if self.thread is None or not self.thread.is_alive():
                self.thread = Thread(target=self.main)
                self.thread.start()

        return result

    def schedule(self, _f, *args, **kwargs):
        ''' Same as call, but does not return AsyncResult. '''
        kwargs['_forget'] = True
        self.call(_f, *args, **kwargs)


# Default worker thread.
async_worker = WorkerThread()


def run_after_loading(view, func):
    """Run a function after the view has finished loading"""
    def run():
        if view.is_loading():
            set_timeout(run, 10)
        else:
            # add an additional delay, because it might not be ready
            # even if the loading function returns false
            set_timeout(func, 10)
    run()

# UI worker thread, safe to call Sublime API here.
# @apply
# class ui_worker(object):
#     ''' Provides the same interface as WorkerThread, but uses UI thread where
#     it's safe to call ST2 APIs.
#     '''

#     def call(self, _f, *args, **kwargs):
#         result = AsyncResult()
#         set_timeout(partial(result.capture, partial(_f, *args, **kwargs)), 0)
#         return result

#     def schedule(self, _f, *args, **kwargs):
#         set_timeout(partial(_f, *args, **kwargs), 0)
