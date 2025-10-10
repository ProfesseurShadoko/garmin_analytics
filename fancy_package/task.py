
from .mutable_class import MutableClass
from .fancy_string import cstr
from .fancy_context_manager import FancyCM   
from typing import Literal
import time


class Task(MutableClass):
    """
    Inherits from MutableClass and FancyCM. Must be used as a context manager.
    Fancy way of printing a task that is being executed. Displays the time taken to execute the task when it is completed.
    """
    
    running_tasks = []
    last_task_runtime = None
    
    def __init__(self, msg:str, new_line:bool = True) -> None:
        """
        Args:
            msg: The message to be printed. 
            new_line (bool): whether to print the progress on the same line ('') or on a new line ('\n'). If intermediate messages or tasks are printed, it is better to use new_line=True.
        """
        self._new_line = new_line
        self.msg = msg
    
        
    def _complete(self) -> None:
        Task.last_task_runtime = time.time() - self.start_time
        
        if self._new_line:
            self.print(
                cstr('[~]').blue(), "Task completed after:", cstr(self.time(Task.last_task_runtime)).blue()
            )
        else:
            self.print(
                f" ({cstr(self.time(time.time()-self.start_time)).blue()})", ignore_tabs=True
            )
    
    def _abort(self) -> None:        
        if not self._new_line:
            self.print() # we might still be on the line of the first print statement of the Task function, don't stay on the same line

        self.print(
            cstr('[!]').red(), "Task aborted after:", cstr(self.time(time.time()-self.start_time)).red()
        )
        
        # assert self.__class__.running_tasks.pop() == self, "The task was not removed from the list of running tasks. This should not happen."
    
    
    #######################
    ### Context Manager ###
    #######################
    
    def __enter__(self):
        self.__class__.running_tasks.append(self)
        self.print(
            cstr('[~]').blue(), self.msg, end='\n' if self._new_line else ' '
        )
        self.start_time = time.time()
        super().__enter__() # add to the indentation level
    
    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            self._complete()
        else:
            self._abort()
        super().__exit__(exc_type, exc_value, traceback) # rmeoves the indentation level and handles the exception if any
        
    
    
        


if __name__ == '__main__':
    
    from .message import Message
    Message("Testing task class.")
    
    with Task("Computing something heavy", new_line=False):
        time.sleep(1)
    
    with Task("Computing many things"):
        for i in range(3):
            if i==1:
                Task.mute()
                Message.mute()
                
            with Task(f"Computing thing {i+1}", new_line=False):
                time.sleep(1)
            Message(f"Computation {i+1}/3 successful", "#")
            Task.unmute()
            Message.unmute()
    
    with Task("Computing something brocken"):
        time.sleep(1)
        x = 1/0
