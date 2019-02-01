import collections

class _Node:
    __slots__ = ["k", "v", "prev", "next"]
    def __init__(self, k, v, prev, next):
        self.k = k
        self.v = v
        self.prev = prev
        self.next = next
    
class LRUCache(collections.MutableMapping):
    def __insertInList(self, k, v):
        if self.first is None:
            newNode = _Node(k, v, None, None)
            self.first = newNode;
            self.last = newNode;
            return newNode
        else:
            newNode = _Node(k, v, self.first, None)
            self.first.next = newNode
            self.first = newNode
            return newNode
        
    def __moveToFirst(self, node):
        if self.first == node: #first, do nothing
            return
        
        if self.last == node: #last, but not first. the single element in list case is covered by the above case
            #remove from last, change second to last's links
            self.last = node.next
            self.last.prev = None
        else:
            #remove from current position, change links of neighbors
            node.prev.next = node.next
            node.next.prev = node.prev
            
        #move to first position, change own links
        node.prev = self.first
        node.next = None
        #changes to formerly first element
        self.first.next = node
        self.first = node
            
    def __removeLastFromList(self):
        if self.last is None:
            return None
        
        if self.last.next is not None:
            self.last.next.prev = None
        temp = self.last
        self.last = self.last.next
        return temp
            
    def __removeFromList(self, node):
        if node.next is not None: node.next.prev = node.prev
        if node.prev is not None: node.prev.next = node.next
        if self.first == node: self.first = node.prev
        if self.last == node: self.last = node.next
        
    def __init__(self, capacity, args=[]):
        self.first = None
        self.last = None
        self.lastKey = None
        self.dictionary = dict()
        self.capacity = max(1, capacity)
        for k, v in args:
            self[k] = v
        
    def __len__(self):
        return len(self.dictionary)
            
    def __iter__(self):
        return self.iterkeys()
    
    def __contains__(self, k):
        return k in self.dictionary
    
    def __getitem__(self, k):
        node = self.dictionary[k]#will raise key error on failure
        self.__moveToFirst(node)
        return node.v
    
    def __setitem__(self, k, v):
        node = self.dictionary.get(k, None)
        if node is None:
            node = self.__insertInList(k, v)
            self.dictionary[k] = node
        else:
            node.v = v
            self.__moveToFirst(node)
            
        if len(self.dictionary) > self.capacity:
            node = self.__removeLastFromList()
            del self.dictionary[node.k]
            
    def __delitem__(self, k):
        node = self.dictionary[k] #will raise key error on failure
        self.__removeFromList(node)
        del self.dictionary[k]
        
    def iteritems(self):
        currentNode = self.first
        while currentNode is not None:
            yield currentNode.k, currentNode.v
            currentNode = currentNode.prev
            
    def iterkeys(self):
        currentNode = self.first
        while currentNode is not None:
            yield currentNode.k
            currentNode = currentNode.prev
            
    def itervalues(self):
        currentNode = self.first
        while currentNode is not None:
            yield currentNode.v
        currentNode = currentNode.prev
        
    def clear(self):
        self.first = self.last = None
        self.dictionary.clear()
        
    def copy(self):
        new = LRUCache(self.capacity)
        currentNode = self.last
        while currentNode is not None:
            new[currentNode.k] = currentNode.v
            currentNode = currentNode.next
        return new
    
    def items(self):
        return list(self.iteritems())
    
    def keys(self):
        return list(self.iterkeys())
    
    def values(self):
        return list(self.itervalues())