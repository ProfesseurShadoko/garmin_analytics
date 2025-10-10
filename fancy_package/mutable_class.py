
from .fancy_string import cstr
from .fancy_context_manager import FancyCM




class MutableClass(FancyCM):
    """
    Base class for classes that need to be muted or indented.
    """
    
    mute_count = 0
    idx = 0
    indent = 0
    
    
    # -------------- #
    # !-- Muting --! #
    # -------------- #
    
    @staticmethod
    def muted() -> bool:
        return MutableClass.mute_count > 0
    
    @staticmethod
    def mute() -> FancyCM:
        MutableClass.mute_count += 1
        
        class MuteContext(FancyCM):
            def __exit__(self, *args):
                MutableClass.unmute()
                super().__exit__(*args)
        
        return MuteContext()
    
    @staticmethod
    def unmute() -> None:
        MutableClass.mute_count -= 1
        
    
    # ------------------- #    
    # !-- Indentation --! #
    # ------------------- #
    
    @staticmethod
    def tab() -> FancyCM:
        MutableClass.indent += 1
        
        class TabContext(FancyCM):
            def __exit__(self, *args):
                MutableClass.untab()
                super().__exit__(*args)
        
        return TabContext()

    @staticmethod
    def untab() -> None:
        MutableClass.indent -= 1
    
    def __enter__(self):
        MutableClass.tab()
        super().__enter__()
    
    def __exit__(self, *args):
        MutableClass.untab()
        super().__exit__(*args)
    
    
    # ------------- #
    # !-- Print --! #
    # ------------- #
    
    @staticmethod
    def print(*args, **kwargs) -> None:
        
        if "ignore_tabs" in kwargs:
            ignore_tabs = kwargs["ignore_tabs"]
            del kwargs["ignore_tabs"]
        else:
            ignore_tabs = False
            
        if "ignore_mute" in kwargs:
            ignore_mute = kwargs["ignore_mute"]
            del kwargs["ignore_mute"]
        else:
            ignore_mute = False
            
        if not 'flush' in kwargs:
            kwargs['flush'] = True
            
        if MutableClass.muted() and not ignore_mute:
            return
        
        if MutableClass.indent > 0 and not ignore_tabs:
            print(" " + ">" * MutableClass.indent, end=" ")
        print(*args, **kwargs)
        
    
    @staticmethod
    def par() -> None:
        MutableClass.print()
        
    
    # ------------- #
    # !-- Utils --! #
    # ------------- #
    
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
    
    @staticmethod
    def date() -> str:
        """
        Returns the current date as a string 'YYYY-MM-DD'.
        """
        from datetime import datetime
        now = datetime.now()
        return now.strftime("%Y-%m-%d")
    
    @staticmethod
    def time_date() -> str:
        """
        Returns the current date and time as a string 'YYYY-MM-DD HH:MM:SS'.
        """
        from datetime import datetime
        now = datetime.now()
        return now.strftime("%Y-%m-%d %H:%M:%S")
    
    
    
    
    
    
    # --------------- #
    # !-- Jupyter --! #
    # --------------- #
    
    def __repr__(self) -> str:
        return "" # avoid displaying in Notebooks, if a message is at the end of the cell
    
    

if __name__ == "__main__":
    # run these tests with python -m fancy_package.mutable_class
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
    
    MutableClass.par()
    with MutableClass():
        MutableClass.print("This should be indented.")
        with MutableClass():
            MutableClass.print("This should be more indented.")
        MutableClass.print("This should be indented.")
        
    MutableClass.par()
    MutableClass.print("Testing time and date functions:")
    with MutableClass():
        MutableClass.print(f"Current date: {MutableClass.date()}")
        MutableClass.print(f"Current time and date: {MutableClass.time_date()}")
        MutableClass.print(f"123.456 seconds is {MutableClass.time(123.456)}")
    
    MutableClass.print("Done!")
    
    
    
        
        
        
    
