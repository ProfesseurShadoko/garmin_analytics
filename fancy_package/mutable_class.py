


from .fancy_string import cstr
from .fancy_context_manager import FancyCM




class MutableClass:
    """
    Implements a class that can be muted, i.e. the method .print of the class can be disabled. 
    Also implements the possibility of tabing.
    
    Properties:
        - muted: Returns True if the class is muted, False otherwise
    
    Methods:
        - mute: Mutes the class
        - unmute: Unmutes the class
        - print: Prints the message if the class is not muted
    
    Static Methods:
        - time: Transforms a number of seconds into a string 'hh:mm:ss'
        
    Context Manager:
        - see silence() method
    """
    
    mute_count = 0
    idx = 0
    indent = 0
    
    
    ##############
    ### MUTING ###
    ##############
    
    @classmethod
    def muted(cls:type) -> bool:
        """
        Checks if the class is muted, that is if the mute() function has been called more times than the unmute() function.
        """
        return cls.mute_count > 0

    @classmethod
    def mute(cls:type) -> FancyCM:
        """
        Mutes the class. The class will not print any message until the unmute() function is called.
        Can be used as a context manager. At the exit of the cm, the class will be automatically unmuted.
        """
        cls.mute_count += 1
        
        class MuteContext(FancyCM):
            def __exit__(self, *args):
                cls.unmute()
                super().__exit__(*args)
        
        return MuteContext()
                
    
    @classmethod
    def unmute(cls:type, force:bool = False) -> None:
        """
        Decrease the mute count of the class. If force, the mute count is set to 0 directly, unmuting the class, even if 'mute' was called several times before.
        """
        if force:
            cls.mute_count = 0
            
        cls.mute_count -= 1
        cls.mute_count = max(0,cls.mute_count)
        
    
    ############
    ### TABS ###
    ############
    
    @staticmethod
    def tab() -> None:
        """
        Increases the indent for every class inheriting from MutableClass. Unlike mute, this is not a classmethod but a static method.
        Can be used as a context manager. At the exit of the cm, the class will be automatically unmuted.
        """
        MutableClass.indent += 1
        class TabContext(FancyCM):
            def __exit__(self, *args):
                MutableClass.untab()
                super().__exit__(*args)
        
        return TabContext()
    
    @staticmethod
    def untab() -> None:
        """
        Decreases the indent for every class inheriting from MutableClass.
        """
        MutableClass.indent -= 1
        MutableClass.indent = max(0,MutableClass.indent)
        
    
    #############
    ### PRINT ###
    #############
    
    @classmethod
    def print(cls:type, *args, **kwargs) -> None:
        """
        Same arguments as standard print function. Prints the message if the class is not muted.
        Added argument: ignore_tabs (bool): if True, the tabs will not be printed.
        """
        if cls.muted():
            return
        
        if not 'flush' in kwargs:
            kwargs['flush'] = True
        if MutableClass.indent > 0 and not kwargs.get('ignore_tabs', False):
            print(" " + ">" * MutableClass.indent, end=" ")
        if 'ignore_tabs' in kwargs:
            del kwargs['ignore_tabs']
            
        print(*args, **kwargs)
    
    @classmethod
    def par(cls:type) -> None:
        """
        Prints an empty line, if and only if the class is not muted.
        """
        cls.print()
        
    
    
    ####################
    ### Time display ###
    ####################
    
    
    @staticmethod
    def time(seconds:float) -> str:
        """
        Transforms a number of seconds into a string 'hh:mm:ss'.
        """
        if seconds >= 60:
            seconds = int(seconds)
            hrs = seconds // 3600
            seconds %= 3600
            mins = seconds // 60
            seconds %= 60
            return f"{hrs:02d}:{mins:02d}:{seconds:02d}"
        else:
            return f"{seconds:.3f}s"


if __name__ == "__main__":
    MutableClass.print("This message will be printed.")
    MutableClass.mute()
    MutableClass.print("This message will not be printed.")
    MutableClass.unmute()
    MutableClass.print("This should be the second message.")
    
    with MutableClass.mute():
        MutableClass.print("This message will not be printed.")
        with MutableClass.mute():
            MutableClass.print("This message will not be printed.")
        MutableClass.print("This message will not be printed.")
    
    MutableClass.print("This should be the third message. Now, we test tabs.")
    MutableClass.tab()
    MutableClass.print("This should be indented.")
    MutableClass.untab()
    MutableClass.print("This should not be indented.")
    
    with MutableClass.tab():
        MutableClass.print("This should be indented.")
        with MutableClass.tab():
            MutableClass.print("This should be more indented.")
        MutableClass.print("This should be indented.")
    MutableClass.print("This should not be indented.")
    MutableClass.print("Done!")
    
        
        
        
    
