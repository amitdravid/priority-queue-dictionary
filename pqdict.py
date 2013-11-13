"""Copyright (c) 2012 Nezar Abdennur

This module contains code adapted from the Python implementation of the heapq
module, which was written by Kevin O'Connor and augmented by Tim Peters and
Raymond Hettinger.

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
the Software, and to permit persons to whom the Software is furnished to do so,
subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""

"""Priority Queue Dictionary -- An indexed priority queue data structure.

Stores a set of prioritized hashable elements. Can be used as an updatable
schedule.

The priority queue is implemented as a binary heap, which supports:         
    - O(1) access to the top priority element        
    - O(log n) removal of the top priority element     
    - O(log n) insertion of a new element

In addition, an internal dictionary or "index" maps elements to their position
in the heap array. This index is kept up-to-date when the heap is manipulated.
As a result, PQD also supports:          
    - O(1) lookup of an arbitrary element's priority key     
    - O(log n) removal of an arbitrary element          
    - O(log n) updating of an arbitrary element's priority key

The standard heap operations used internally (here, called "sink" and "swim")
are based on the code in the python heapq module.* These operations are extended
to maintain the internal dictionary.

* The names of the methods in heapq (sift up/down) seem to refer to the motion
of the items being compared to, rather than the item being operated on as is
normally done in textbooks (i.e. bubble down/up, instead). I stuck to the
textbook convention, but using the sink/swim nomenclature from Sedgewick et al:
the way I like to think of it, an item that is too "heavy" (low-priority) should 
sink down the tree, while one that is too "light" should float or swim up.

Implementation details:
    - heap (list): stores (dkey,pkey) pairs as "entries" (entry objects) that
      implement __lt__ which defines how their pkeys are compared
    - position (dict): maps each dkey to the index of its entry in the heap

""" 
__author__ = ('Nezar Abdennur', 'nabdennur@gmail.com')  
__all__ = ['PQDict', 'PQDictEntry', 'sort_by_value']

from collections import Mapping, MutableMapping
from abc import ABCMeta, abstractmethod

class PQDictEntry(object):
    """
    Abstract class that defines the heap elements that back a PQDict.

    Subclass to customize the ranking behavior of the priority queue. Since the 
    heap algorithms of PQDict use the "<" comparator to compare entries, 
    subclasses must implement __lt__.

    """
    __metaclass__ = ABCMeta
    def __init__(self, dkey, pkey):
        self.dkey = dkey
        self.pkey = pkey

    @abstractmethod
    def __lt__(self, other):
        return NotImplemented

    def __eq__(self, other):
        return self.pkey == other.pkey

    def __repr__(self):
        return self.__class__.__name__ + \
            "(%s: %s)" % (repr(self.dkey), self.pkey)

    # pkey = property(get_pkey, set_pkey)

class _MinEntry(PQDictEntry):
    """
    Defines entries for a PQDict backed by a min-heap.

    """
    __init__ = PQDictEntry.__init__
    __eq__ = PQDictEntry.__eq__

    def __lt__(self, other):
        return self.pkey < other.pkey

class _MaxEntry(PQDictEntry):
    """
    Defines entries for a PQDict backed by a max-heap.

    """
    __init__ = PQDictEntry.__init__
    __eq__ = PQDictEntry.__eq__

    def __lt__(self, other):
        return self.pkey > other.pkey


class PQDict(MutableMapping):
    """
    Maps dictionary keys (dkeys) to priority keys (pkeys). Maintains an
    internal heap so that the highest priority item can always be obtained in
    constant time. The mapping is mutable so items may be added, removed and
    have their priorities updated without breaking the heap.

    """
    create_entry = _MinEntry

    __eq__ = MutableMapping.__eq__
    __ne__ = MutableMapping.__ne__
    keys = MutableMapping.keys
    values = MutableMapping.values
    items = MutableMapping.items
    get = MutableMapping.get
    clear = MutableMapping.clear
    update = MutableMapping.update
    setdefault = MutableMapping.setdefault

    def __init__(self, *args, **kwargs):
        """
        Same input signature as dict:
            Accepts at most one positional argument:
                - a sequence/iterator of (dkey, pkey) pairs
                - a mapping object
            Accepts keyword arguments

        The default priority ordering for entries is in decreasing pkey value
        (i.e., a min-pq: SMALLER pkey values have a HIGHER rank).

        """
        if len(args) > 1:
            raise TypeError('Too many arguments')

        self._heap = []
        self._position = {}

        pos = 0
        if args:
            if isinstance(args[0], Mapping):
                seq = args[0].items()
            else:
                seq = args[0]
            for dkey, pkey in seq:
                entry = self.create_entry(dkey, pkey)
                self._heap.append(entry)
                self._position[dkey] = pos
                pos += 1
        if kwargs:
            for dkey, pkey in kwargs.items():
                entry = self.create_entry(dkey, pkey)
                self._heap.append(entry)
                self._position[dkey] = pos
                pos += 1
        self._heapify()

    @classmethod
    def minpq(cls, *args, **kwargs):
        pq = cls()
        pq.create_entry = _MinEntry
        pq.__init__(*args, **kwargs)
        return pq

    @classmethod
    def maxpq(cls, *args, **kwargs):
        pq = cls()
        pq.create_entry = _MaxEntry
        pq.__init__(*args, **kwargs)
        return pq

    @classmethod
    def custompq(cls, entrytype, *args, **kwargs):
        pq = cls()
        if issubclass(entrytype, PQDictEntry):
            pq.create_entry = entrytype
        else:
            raise TypeError('Custom entry class must be a subclass of' \
                            'PQDictEntry')
        pq.__init__(*args, **kwargs)
        return pq

    @classmethod
    def fromfunction(cls, iterable, pkeygen): #instead of fromkeys
        """
        Provide a key function that determines priorities by which to heapify
        the elements of an iterable into a PQD.

        """
        return cls( (dkey, pkeygen(dkey)) for dkey in iterable )

    def __len__(self):
        """
        Return number of items in the PQD.

        """
        return len(self._heap)

    def __contains__(self, dkey):
        """
        Return True if dkey is in the PQD else return False.

        """
        return dkey in self._position

    def __iter__(self):
        """
        Return an iterator over the dictionary keys of the PQD. The order 
        of iteration is undefined! Use iterkeys() to iterate over dictionary 
        keys sorted by priority.

        """
        for entry in self._heap:
            yield entry.dkey

    def __getitem__(self, dkey):
        """
        Return the priority of dkey. Raises a KeyError if not in the PQD.

        """
        return self._heap[self._position[dkey]].pkey #raises KeyError

    def __setitem__(self, dkey, pkey):
        """
        Assign priority to dictionary key.

        """
        heap = self._heap
        position = self._position
        try:
            pos = position[dkey]
        except KeyError:
            # add new entry:
            # put the new entry at the end and let it bubble up
            n = len(self._heap)
            self._heap.append(self.create_entry(dkey, pkey))
            self._position[dkey] = n
            self._swim(n)
        else:
            # update existing entry:
            # bubble up or down depending on pkeys of parent and children
            heap[pos].pkey = pkey
            parent_pos = (pos - 1) >> 1
            child_pos = 2*pos + 1
            if parent_pos > -1 and heap[pos] < heap[parent_pos]:
                self._swim(pos)
            elif child_pos < len(heap):
                other_pos = child_pos + 1
                if (other_pos < len(heap) 
                        and not heap[child_pos] < heap[other_pos]):
                    child_pos = other_pos
                if heap[child_pos] < heap[pos]:
                    self._sink(pos)

    def __delitem__(self, dkey):
        """
        Remove item. Raises a KeyError if dkey is not in the PQD.

        """
        heap = self._heap
        position = self._position
        pos = position.pop(dkey) #raises appropriate KeyError

        # Take the very last entry and place it in the vacated spot. Let it
        # sink or swim until it reaches its new resting place.
        entry_to_delete = heap[pos]
        end = heap.pop(-1)
        if end is not entry_to_delete:
            heap[pos] = end
            position[end.dkey] = pos

            parent_pos = (pos - 1) >> 1
            child_pos = 2*pos + 1
            if parent_pos > -1 and heap[pos] < heap[parent_pos]:
                self._swim(pos)
            elif child_pos < len(heap):
                other_pos = child_pos + 1
                if (other_pos < len(heap) and
                        not heap[child_pos] < heap[other_pos]):
                    child_pos = other_pos
                if heap[child_pos] < heap[pos]:
                    self._sink(pos)
        del entry_to_delete

    def __copy__(self):
        """
        Return a new PQD with the same dkeys associated with the same priority
        keys.

        """
        from copy import copy
        other = self.__class__()
        # Entry objects are mutable and should not be shared by different PQDs.
        other._heap = [copy(entry) for entry in self._heap]
        # It's safe to just copy the _position dict (dkeys->int)
        other._position = copy(self._position)
        return other
    copy = __copy__

    def __repr__(self):
        things = ', '.join(['%s: %s' % (repr(entry.dkey), entry.pkey) 
                                for entry in self._heap])
        return self.__class__.__name__ + '({' + things  + '})'

    __marker = object()
    def pop(self, dkey, default=__marker):
        """
        If dkey is in the PQD, remove it and return its priority key, else 
        return default. If default is not given and dkey is not in the PQD, a 
        KeyError is raised.

        """
        heap = self._heap
        position = self._position

        try:
            pos = position.pop(dkey) #raises appropriate KeyError
        except KeyError:
            if default is self.__marker:
                raise
            return default
        else:
            entry_to_delete = heap[pos]
            pkey = entry_to_delete.pkey
            end = heap.pop(-1)
            if end is not entry_to_delete:
                heap[pos] = end
                position[end.dkey] = pos

                parent_pos = (pos - 1) >> 1
                child_pos = 2*pos + 1
                if parent_pos > -1 and heap[pos] < heap[parent_pos]:
                    self._swim(pos)
                elif child_pos < len(heap):
                    other_pos = child_pos + 1
                    if (other_pos < len(heap) 
                            and not heap[child_pos] < heap[other_pos]):
                        child_pos = other_pos
                    if heap[child_pos] < heap[pos]:
                        self._sink(pos)
            del entry_to_delete
            return pkey

    def popitem(self):
        """
        Extract top priority item. Raises KeyError if PQD is empty.

        """
        heap = self._heap
        position = self._position

        try:
            end = heap.pop(-1)
        except IndexError:
            raise KeyError('PQDict is empty')

        if heap:
            entry = heap[0]
            heap[0] = end
            position[end.dkey] = 0
            self._sink(0)
        else:
            entry = end
        del position[entry.dkey]
        return entry.dkey, entry.pkey

    def additem(self, dkey, pkey):
        """
        Add a new item. Raises KeyError if item is already in the PQD.

        """
        if dkey in self._position:
            raise KeyError(dkey)
        self[dkey] = pkey

    def updateitem(self, dkey, new_pkey):
        """
        Update the priority key of an existing item. Raises KeyError if item is
        not in the PQD.

        """
        if dkey not in self._position:
            raise KeyError(dkey)
        self[dkey] = new_pkey

    # def replacewith(self, dkey, pkey, target=None):
    #     """
    #     Equivalent to removing an item followed by inserting a new one, but 
    #     faster. Default item to remove is the top priority item.

    #     """
    #     heap = self._heap
    #     position = self._position

    #     if not heap:
    #         raise KeyError

    #     if target is not None:
    #         target = heap[0]

    #     if dkey in self and dkey is not target:
    #         raise KeyError

    #     pos = position.pop(target) #raises appropriate KeyError
    #     target_pkey = heap[pos].pkey
    #     position[dkey] = pos
    #     heap[pos].dkey = dkey
    #     self.updateitem(dkey, pkey)
    #     return target, target_pkey

    def pushpopitem(self, dkey, pkey):
        """
        Equivalent to inserting a new item followed by removing the top priority 
        item, but faster.

        """
        heap = self._heap
        position = self_position
        entry = self.create_entry(dkey, key)

        if heap and heap[0] < entry:
            entry, heap[0] = heap[0], entry
            self._sink(0)

        return entry.dkey, entry.pkey

    def peek(self):
        """
        Get top priority item.

        """
        try:
            entry = self._heap[0]
        except IndexError:
            raise KeyError
        return entry.dkey, entry.pkey

    def iterkeys(self):
        """
        Destructive heapsort iterator over dictionary keys, ordered by priority
        key.

        """
        try:
            while True:
                yield self.popitem()[0]
        except KeyError:
            return

    def itervalues(self):
        """
        Destructive heapsort iterator over priority keys.

        """
        try:
            while True:
                yield self.popitem()[1]
        except KeyError:
            return

    def iteritems(self):
        """
        Destructive heapsort iterator over items, ordered by priority key.

        """
        try:
            while True:
                yield self.popitem()
        except KeyError:
            return

    def _heapify(self):
        n = len(self._heap)
        for pos in reversed(range(n//2)):
            self._sink(pos)

    def _sink(self, top=0):
        # "Sink-to-the-bottom-then-swim" algorithm (Floyd, 1964)
        # Tends to reduce the number of comparisons when inserting "heavy" items
        # at the top, e.g. during a heap pop. See heapq for more details.
        heap = self._heap
        position = self._position
        endpos = len(heap)

        # Grab the top entry
        pos = top
        entry = heap[pos]

        # Sift up a chain of child nodes
        child_pos = 2*pos + 1
        while child_pos < endpos:
            # Choose the smaller child.
            other_pos = child_pos + 1
            if other_pos < endpos and not heap[child_pos] < heap[other_pos]:
                child_pos = other_pos
            child_entry = heap[child_pos]

            # Move it up one level.
            heap[pos] = child_entry
            position[child_entry.dkey] = pos

            # Next level
            pos = child_pos
            child_pos = 2*pos + 1

        # We are left with a "vacant" leaf. Put our entry there and let it swim 
        # until it reaches its new resting place.
        heap[pos] = entry
        position[entry.dkey] = pos
        self._swim(pos, top)

    def _swim(self, pos, top=0):
        heap = self._heap
        position = self._position

        # Grab the entry from its place
        entry = heap[pos]

        # Sift parents down until we find a place where the entry fits.
        while pos > top:
            parent_pos = (pos - 1) >> 1
            parent_entry = heap[parent_pos]
            if entry < parent_entry:
                heap[pos] = parent_entry
                position[parent_entry.dkey] = pos
                pos = parent_pos
                continue
            break

        # Put entry in its new place
        heap[pos] = entry
        position[entry.dkey] = pos

def sort_by_value(mapping, reverse=False):
    """
    Takes an arbitrary mapping and, treating the values as priority keys, sorts
    its items by priority via heapsort using a PQDict.

    Returns:
        a list of the dictionary items sorted by value

    """
    if reverse:
        pq = PQDict.maxpq(mapping)
    else:
        pq = PQDict(mapping)
    return [item for item in pq.iteritems()]