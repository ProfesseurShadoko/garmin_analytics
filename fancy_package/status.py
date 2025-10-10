


from .mutable_class import MutableClass
from .fancy_string import cstr
import psutil, os

class MemoryView(MutableClass):
    
    def __init__(self):
        tot_ram = self.get_memory_available() + self.get_memory_usage()
        memory_usage = self.get_memory_usage()/tot_ram
        color_letter = 'g' if memory_usage < 0.5 else 'y' if memory_usage < 0.8 else 'r'
        memory_usage_percent = f"{cstr(f'{memory_usage:.0%}'):{color_letter}}"
        
        self.print(
            f"{cstr('[M]').blue()} Current memory usage: {self.get_memory_usage():.2f} GB / {tot_ram:.2f} GB ({memory_usage_percent})"
        )
    
    
    def get_memory_usage(self) -> float:
        """
        Returns the current memory usage of the process in MB.
        """
        process = psutil.Process(os.getpid())
        memory = process.memory_info().rss / (1024 ** 3)  # in GB
        return memory
    
    def get_memory(self) -> float:
        """
        Returns the available memory in GB.
        """
        memory = psutil.virtual_memory().total / (1024 ** 3)  # in GB
        return memory
    
    def get_memory_available(self) -> float:
        """
        Returns the available memory in GB.
        """
        memory = psutil.virtual_memory().available / (1024 ** 3)  # in GB
        return memory
    
    
class TODO(MutableClass):
    def __init__(self, message: str, complete:bool = False):
        prefix = '[x]' if complete else '[ ]'
        color = 'g' if complete else 'r'
        
        self.print(
            f"{cstr(prefix):{color}} TODO: {message}"
        )
        

class DateTime(MutableClass):
    def __init__(self):
        self.print(f"{cstr('[D]').magenta()} {self.time_date()}")
        

if __name__ == "__main__":
    from .message import Message
    
    with Message("Displaying memory usage:"):
        MemoryView()
        
    Message.par()
    with Message("Making TODO list:"):
        TODO("This is a test TODO item.")
        TODO("This is a completed TODO item.", complete=True)
        
    Message.par()
    with Message("Displaying current date and time:"):
        DateTime()