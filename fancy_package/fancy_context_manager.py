
import traceback as tb
from .fancy_string import cstr



class FancyCM:
    """
    Fancy Context Manager.
    
    TODO: enable to possiblity of 'and' operator when using multiple context managers.
    """
    lvl = 0
    
    def __enter__(self):
        FancyCM.lvl += 1
    
    def __exit__(self, exc_type, exc_value, traceback):
        FancyCM.lvl -= 1
        if exc_type and FancyCM.lvl == 0:
            print(f"Exception occurred: {cstr(exc_type.__name__):r} ({cstr(exc_value):y})")
            tb.print_tb(traceback)



if __name__ == '__main__':
    
    with FancyCM():
        print("This was printed inside the context manager")
        with FancyCM():
            print("This was printed inside the nested context manager. Now an error will occure.")
            x = 1/0
            print("This will not be printed.")
    
