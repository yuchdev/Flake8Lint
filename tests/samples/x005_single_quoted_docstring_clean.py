'''Module using triple single-quoted docstrings throughout (no X005).'''


def greet(name: str) -> str:
    '''Return a greeting for the given name.'''
    return f"Hello, {name}"


class Repository:
    '''In-memory store of string records.'''

    def add(self, item: str):
        '''Append an item to the internal record list.'''
        self._items = [item]
