
from .fancy_string import cstr
from .mutable_class import MutableClass
import time
from .task import Task
from .message import Message
from .status import MemoryView, TODO # TODO: create an function 'mute_all' to mute all children of MutableClass


class ProgressBar(MutableClass):
    
    current_instance = None

    
    def __init__(self, lst, size:int=None, new_line:bool = False) -> None:
        """
        Simple iterator that prints the progress of the iteration and the remaining time.
        
        Args:
            lst: iterable or iterator object (list, range, enumerate, zip, np.array, etc.)
            size: The size of the list. If the object is an iterator, it may not have a __len__ magic method. In this case, provide the size of the iterator.
            new_line: whether to print the progress on the same line ('\r') or on a new line ('\n'). If on a new line, other mutable classes wont be muted.
        
        Returns:
            iterator
        """
        super().__init__()
        ProgressBar.current_instance = self
        
        if size is None:
            if not hasattr(lst,'__len__'):
                ProgressBar.print(cstr("[!]").red(),"Warning: unable to iterate over the object of type {type(lst)}. This may be because it is an iterator without a __len__ magic method. In this case, you can provide an argument 'size'.")
                ProgressBar.print(cstr("[!]").red(),"Trying to convert to list (which might be time and memory consuming)...")
                lst = list(lst)
                
            self.max = len(lst)
        else:
            self.max = size
        
            
        assert hasattr(lst,'__iter__'), "The object provided is not iterable."
        self.list = lst.__iter__()
        
        self.count = 0
        self.start_time = time.time()
        
        self.previous_print = ""
        
        self.new_line = new_line
        
        if not self.new_line:
            MutableClass.mute()
        
    
    def __iter__(self) -> 'ProgressBar':
        return self
    
    def __next__(self):
        if self.max==0:
            raise StopIteration()
        
        self.show()
        self.count += 1 # update the progress
        
        try:
            return next(self.list)
        except StopIteration:
            if not self.new_line:
                MutableClass.unmute()
            self.print(
                cstr("[%]").magenta(),
                " Done!" + " "*50,
            )
            raise(StopIteration())
    
    def show(self) -> None:
        next_print = cstr(
            f"[{round(self.count/self.max * 100):02d}%] "
        ).magenta()
        
        if self.count == 0:
            next_print += "Time remaining: \\"
        else:
            time_of_one_iteration = (time.time()-self.start_time)/self.count
            remaining_time = time_of_one_iteration * (self.max-self.count)
            next_print += f"Time remaining: {self.time(remaining_time)}"
        
        if next_print != self.previous_print:
            self.previous_print = next_print
            
            MutableClass.unmute()
            self.print(
                next_print + " "*10,
                end=("\r" if not self.new_line else "\n")
            )
            MutableClass.mute()
            
        
    @staticmethod
    def whisper(msg:str):
        """
        Print a message without affecting the progress bar. Progress bar will be reprinted after the message.
        """
        if ProgressBar.current_instance is None:
            MutableClass.unmute()
            ProgressBar.print(cstr("[%]").magenta(), msg)
            MutableClass.mute()
            return
        
        # 1. Erase the current progress bar
        MutableClass.unmute()
        ProgressBar.current_instance.print("\r" + " "*len(ProgressBar.current_instance.previous_print), end="\r")
        ProgressBar.current_instance.print(cstr("[%]").magenta(), msg)
        ProgressBar.current_instance.show()
        MutableClass.mute()
        

if __name__ == '__main__':
    
    with Task("Computing something heavy", new_line=True):
        for i in ProgressBar(range(100), size=100):
            time.sleep(0.05)
            if i==50:
                ProgressBar.whisper("Halfway there!")
        
    with Task("Computing something heavy again", new_line=True):
        for i in ProgressBar(range(3), new_line=True):
            time.sleep(0.5)
            if i==1:
                ProgressBar.whisper("Halfway there!")
            
    
    Message("Success!", "#")
