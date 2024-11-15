

from .fancy_string import cstr
from .mutable_class import MutableClass
from typing import Literal




class Message(MutableClass):
    """
    Inherits from MutableClass.
    
    Methods:
        __init__(...): Constructor. Displays the message.
        listen(cls, ...): Defines which messages should be displayed, depending on their importance.
    
    Parent Methods:
        mute: Mutes the class
        unmute: Unmutes the class
        tab: Adds a tabulation to all upcoming messages. Can be used as a context manager.
        silence: Mutes the class for the duration of the context manager. At the exit of the cm, the class will be automatically unmuted.
    """
    
    _active = ['i', '#', '?', '!']
    
    def __init__(self, msg:str, type:Literal['#', '?', '!', 'i'] = 'i') -> None:
        
        assert isinstance(msg, str), f"msg must be a string, not {msg.__class__}"
        assert type in ['#', '?', '!', 'i'], f"type must be one of '#', '?', '!', 'i', not {type}"
        self.msg = msg
        self.type = type
        
        self._display()
    
    
    def _display(self) -> None:
        if not self.type in self._active:
            return
        
        self.print(
            self._get_prefix(), self.msg
        )
        
    def _get_prefix(self) -> str:
        return {
            '#': cstr('[#]').green(),
            'i': cstr('[i]').cyan(),
            '?': cstr('[?]').yellow(),
            '!': cstr('[!]').red()
        }[self.type]
    
    @classmethod
    def listen(cls:type, lvl:int=0) -> None:
        """
        Defines which messages should be displayed, depending on their importance.
        
        Args:
            lvl (int): The level of importance of the message. 0 lets all messages be displayed, 1 only warnings and errors, 2 only errors.
        """
        cls._active = {
            0: ['i', '#', '?', '!'],
            1: ['?', '!'],
            2: ['!']
        }[lvl]



if __name__ == '__main__':
    Message("This is a success message", "#")
    Message("This is an info message", "i")
    Message("This is a warning message", "?")
    Message("This is an error message", "!")
    Message.par()
    Message.listen(1)
    Message("This is a success message. It should not be displayed.", "#")
    Message("This is a warning. It should be displayed.", "?")
    
    Message.listen()
    Message.par()
    
    with Message.tab():
        Message("This message should be indented.")
    Message("This message should not be indented.")
    Message.par()
    
    
    
    
    
    
    
    
