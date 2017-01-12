from itertools import product

from collections import abc, defaultdict

from functools import partial

class ParamSpace:
    def __init__(self, spec):
        self.spec = self.validate_spec(spec)

    def validate_spec(self, spec):
        if not isinstance(spec, dict):
            raise TypeError('spec must be a dict')
        spec = spec.copy()
        for k, v in spec.items():
            if not isinstance(k, str):
                raise TypeError('spec keys must be strings. Got '+repr(k))
            if not isinstance(v, list):
                raise TypeError('spec values must be lists of categories. Got '+repr(v))
            for category in v:
                if not isinstance(category, abc.Hashable):
                    raise TypeError('spec categories must be hashable. Got '+repr(category))
        return spec

    def points(self):
        items = list(self.spec.items())
        names = [k for k, v in items]
        categories = [v for k, v in items]

        for values in product(*categories):
            key = dict(zip(names, values))
            yield self.make_point(key)

    def drop(self, names):
        if isinstance(names, str):
            raise TypeError('names must be an iterable of strings, and not a single string')
        new_spec = self.spec.copy()
        for name in names:
            if name not in new_spec:
                raise TypeError('Name not present in spec: '+repr(name))
            del new_spec[name]

        return ParamSpace(new_spec)

    def add(self, spec):
        spec = self.validate_spec(spec)
        new_spec = self.spec.copy()
        new_spec.update(spec)
        return ParamSpace(new_spec)

    def subspace(self, names):
        if isinstance(names, str):
            raise TypeError('names must be an iterable of strings, and not a single string')
        new_spec = {}

        for name in names:
            if name not in self.spec:
                raise TypeError('Cannot create subspace containing {}: not present in current spec'.format(name))
            new_spec[name] = self.spec[name][:]
        return ParamSpace(new_spec)

    def union(self, other_space):
        new_spec = {}
        key_union = self.spec.keys() | other_space.spec.keys()
        for key in key_union:
            l1 = self.spec.get(key, [])
            l2 = other_space.spec.get(key, [])
            new_vals = l1 or l2
            if l1 and l2 and set(l1) != set(l2):
                raise TypeError('Cannot union spaces: different values for same key: {}'.format(key))
            new_spec[key] = new_vals

        return ParamSpace(new_spec)

    def intersection(self, other_space):
        new_spec = {}
        key_intersection = self.spec.keys() & other_space.spec.keys()

        for key in key_intersection:
            l1 = self.spec.get(key, [])
            l2 = other_space.spec.get(key, [])
            if set(l1) != set(l2):
                raise TypeError('Cannot get intersection: different values for same key: {}'.format(key))
            new_spec[key] = l1
            
        return ParamSpace(new_spec)

    def difference(self, other_space):
        new_spec = {}

        try:
            self.intersection(other_space)
        except TypeError as e:
            raise TypeError('TypeError when trying to get difference') from e

        key_diff = self.spec.keys() - other_space.spec.keys()
        for key in key_diff:
            new_spec[key] = self.spec[key]

        return ParamSpace(new_spec)

    def __eq__(self, other_space):
        if self.spec.keys() != other_space.spec.keys():
            return False

        for k in self.spec:
            l1 = self.spec[k]
            l2 = other_space.spec[k]

            if set(l1) != set(l2):
                return False
        return True

    def __len__(self):
        product = 1
        for v in self.spec.values():
            product *= len(v)
            
        return product
    
    def __repr__(self):
        return 'ParamSpace<{}>'.format(repr(self.spec))
    
    def lift_function(self, func):
        return Function(self, func)

    def make_point(self, key):
        return Point(self, key)
    
    def make_map(self, map):
        return Map(self, map)

class Point:
    def __init__(self, pspace, key):
        self.pspace = pspace
        self.key = self.validate_key(key)

    def validate_key(self, key):
        if not isinstance(key, dict):
            raise TypeError('key must be a dict')
        key = key.copy()
        for n, v in self.pspace.spec.items():
            if n not in key:
                raise TypeError('Name missing from key: '+n)
            if key[n] not in v:
                raise TypeError('Invalid value for '+n+': '+repr(key[n]))
        return key

    def __hash__(self):
        return hash(frozenset((k, v) for (k, v) in self.key.items() if k in self.pspace.spec))

    def __eq__(self, other_point):
        if self.pspace != other_point.pspace:
            return False

        for n in self.pspace.spec:
            v1 = self.key[n]
            v2 = other_point.key[n]
            if v1 != v2:
                return False
        return True

    def distance(self, other_point):
        if self.pspace != other_point.pspace:
            raise TypeError("can't get distance from point in another param space")
    
        dists = []
        for k, v in self.pspace.spec.items():
            pos1 = v.index(self.key[k])
            pos2 = v.index(other_point.key[k])
            dist = abs(pos2 - pos1)
            dists.append(dist)
        
        return sum(dist**2 for dist in dists)**0.5
            
    def __repr__(self):
        return 'Point<{}>'.format(repr(self.key))

class Map:
    def __init__(self, pspace, map):
        self.pspace = pspace
        self.map = self.validate_map(map)

    def validate_map(self, map):
        if not isinstance(map, dict):
            raise TypeError('map must be a dict')
        map = map.copy()
        for p in self.pspace.points():
            if p not in map:
                raise TypeError('point '+repr(p)+' not present in map')
        return map

    def __getitem__(self, point):
        if point.pspace != self.pspace:
            raise TypeError('point must be in the same param space as the map')
        return self.map[point]     

    def __setitem__(self, point, value):
        if point.pspace != self.pspace:
            raise TypeError('point must be in the same param space as the map')
        self.map[point] = value

    def __repr__(self):
        return 'Map<{}>'.format(repr(self.map))

class Function:
    def __init__(self, pspace, function):
        self.pspace = pspace
        self.function = function

    def __call__(self, *arg_maps):
        result_map = {}
        for p in self.pspace.points():
            args = [arg_map[p] for arg_map in arg_maps]
            result_map[p] = self.function(*args)
        return self.pspace.make_map(result_map)

#### convenience stuff

def keys_map(pspace):
    if not isinstance(pspace, ParamSpace):
        raise TypeError('pspace must be a ParamSpace, got {}'.format(pspace))
    
    keys_map = {}
    for p in pspace.points():
        keys_map[p] = p.key
    return pspace.make_map(keys_map)


def unit_map(pspace, unit=None):
    if not isinstance(pspace, ParamSpace):
        raise TypeError('pspace must be a ParamSpace, got {}'.format(pspace))
    
    unit_map = {}
    for p in pspace.points():
        unit_map[p] = unit
    return pspace.make_map(unit_map)

class MappedFunction:
    unevaluated = object()

    def __init__(self, function, *arg_maps):
        self.function = function
        self.cache_map = unit_map(self.function.pspace, unit=self.unevaluated)
        self.arg_maps = arg_maps

    @property
    def pspace(self):
        return self.function.pspace

    def __getitem__(self, point):
        if point.pspace != self.pspace:
            raise TypeError('point must be in the same param space as the map')
        value = self.cache_map[point]
        if value is self.unevaluated:
            args = [arg_map[point] for arg_map in self.arg_maps]
            value = self.function.function(*args)
            self.cache_map[point] = value

        return value

def expand_point(point1, pspace2):
    extra_space = pspace2.difference(point1.pspace)
    for p in extra_space.points():
        new_key = p.key.copy()
        new_key.update(point1.key)
        yield pspace2.make_point(new_key)
        
def contract_point(point2, pspace1):
    new_key_dict = {}
    for k in pspace1.spec:
        new_key_dict[k] = point2.key[k]
    return pspace1.make_point(new_key_dict)

def stack_map(map2, pspace1):
    extra_space = map2.pspace.difference(pspace1)
    
    extra_map_dict = defaultdict(dict)

    for point2 in map2.pspace.points():
        extra_point = contract_point(point2, extra_space)
        point1 = contract_point(point2, pspace1)
        extra_map_dict[point1][extra_point] = map2[point2]

    extra_map_dict2 = {k: extra_space.make_map(v) for (k, v) in extra_map_dict.items()}
    return pspace1.make_map(extra_map_dict2)

def unstack_map(map1, pspace2):
    new_map_dict = {}
    
    extra_space = pspace2.difference(map1.pspace)
    
    for point1 in map1.pspace.points():
        for point2 in expand_point(point1, pspace2):
            extra_point = contract_point(point2, extra_space)
            new_map_dict[point2] = map1[point1][extra_point]
    
    return pspace2.make_map(new_map_dict)

def collapse_map(map1):
    # infer pspace2 then call expand
    v = map1[next(map1.pspace.points())]
    if not isinstance(v, Map):
        return map1
    else:
        v = collapse_map(v)
        pspace2 = map1.pspace.union(v.pspace)
        return unstack_map(map1, pspace2)

def kwd_apply(function):
    def func(kwds):
        return function(**kwds)
    return func

# demo
if __name__ == '__main__':
    #see it's great now instead of:
    #for i in range(10):
    #    print(i)
    
    #you just do:
    s1 = ParamSpace({'i': list(range(10))})
    
    def f(i):
        return i
    
    print(s1.lift_function(kwd_apply(f))(keys_map(s1)))
    
    # also instead of:
    #for i in range(10):
    #    for j in range(5):
    #        print(i * j)
            
    #you just do:
    s2 = ParamSpace({'i': list(range(10)), 'j': list(range(5))})
    # (or):
    s2 = s1.add({'j': list(range(5))})
    
    def f(i, j):
        return i * j
    
    print(s2.lift_function(kwd_apply(f))(keys_map(s2)))
    
    #plus you can do this weird stacking/unstacking thing that doesn't really have an expression in for loops
    #it's kind of like reordering the nesting order of multiple for loops
    km = keys_map(s2)
    
    stacked_km1 = stack_map(km, s2.subspace(['j']))
    print(s2.subspace(['j']).lift_function(s2.subspace(['i']).lift_function(kwd_apply(f)))(stacked_km1))
    
    stacked_km2 = stack_map(km, s2.subspace(['i']))
    print(s2.subspace(['i']).lift_function(s2.subspace(['j']).lift_function(kwd_apply(f)))(stacked_km2))
    
    #this library is actually very, very useful and good in my professional work as a real developer (and you should love me)

    #tree traversal demo
    class T:
        def __init__(self, v=None, cs=None):
            if cs is not None:
                cs = list(cs)
                for c in cs:
                    if not isinstance(c, T):
                        raise TypeError('child node must be a T. got {}'.format(c))

            self.v = v
            self.cs = cs

        def depth_first(self):
            yield self
            if self.cs is not None:
                for c in self.cs:
                    yield from c.depth_first()

        def breadth_first(self):
            from collections import deque
   
            frontier = deque([self])
            while frontier:
                node = frontier.popleft()
                yield node.v
                if node.cs is not None:
                    frontier.extend(node.cs)

        def __repr__(self):
            return 'T({})'.format(self.v)

        def __eq__(self, o):
            if self.v != o.v:
                return False
            if self.cs != o.cs:
                return False
            return True

        def __hash__(self):
            if self.cs is None:
                return hash(self.v) + hash(None)
            return hash(self.v) + hash(tuple(self.cs))
        
    t1 = \
    T(1, [
        T(2, [
            T(3), T(4), T(5, [T(6, [T(7)])])
        ]),
        T(8),
        T(9),
        T(10, [T(11, [T(12)])])
    ])

    all_nodes = list(t1.depth_first())
    from random import shuffle
    shuffle(all_nodes) # to show we don't need it in any particular order

    s = ParamSpace({
        't1': all_nodes,
        't2': all_nodes
    })

    #recover the tree structure
    def get_child_index(t1, t2):
        if t1.cs is None or t2 not in t1.cs:
            return None
        return t1.cs.index(t2)

    child_index_map = s.lift_function(kwd_apply(get_child_index))(keys_map(s))

    #demo: identify only the leaf nodes
    def is_leaf(child_map):
        return all(child_map[p] is None for p in child_map.pspace.points())

    stacked_child_index_map = stack_map(child_index_map, s.subspace(['t1']))
    leaf_map = s.subspace(['t1']).lift_function(is_leaf)(stacked_child_index_map)

    print('leaf map:')
    print(leaf_map)

    #demo: build a structural copy (very good and useful)
    def set_child(key, child_index, new_nodes):
        if child_index is None:
            return
        parent_id = key['t1'].v
        child_id = key['t2'].v
        if parent_id not in new_nodes:
            new_nodes[parent_id] = T(parent_id, None)
        if child_id not in new_nodes:
            new_nodes[child_id] = T(child_id, None)

        if new_nodes[parent_id].cs is None:
            new_nodes[parent_id].cs = []

        child_list_len = len(new_nodes[parent_id].cs)
        if child_list_len <= child_index:
            diff = child_index + 1 - child_list_len
            new_nodes[parent_id].cs.extend([None]*diff)

        new_nodes[parent_id].cs[child_index] = new_nodes[child_id]

    new_nodes = {}
    s.lift_function(set_child)(keys_map(s), child_index_map, unit_map(s, new_nodes))

    new_nodes[1] == t1

    print('original root node:')
    print(list(t1.depth_first()))

    print('identical new root node:')
    print(list(new_nodes[1].depth_first()))
    
    # demo: compute depth of the tree's deepest branch (using the child index map as input)
    # uses a MappedFunction to cache results so we don't do unnecessary repeats
    def branch_depth(key, child_index, node_depth_map):
        #is this a parent-child relation? if not, depth is 1
        if child_index is None:
            return 1
        
        parent_point = s.subspace(['t1']).make_point({'t1': key['t2']})
        
        #check if the child is known to be a leaf
        if leaf_map[parent_point]:
            return 2
        #finally, do the slow way of checking all children of the child
        return 1 + node_depth_map[parent_point] #1 + max(depth_map[p] for p in expand_point(parent_point, s))

    s_reduced = s.subspace(['t1'])

    def node_depth(key, depth_map):
        parent_point = s_reduced.make_point(key)
        return max(depth_map[p] for p in expand_point(parent_point, s))


    depth_map = MappedFunction(s.lift_function(branch_depth))
    node_depth_map = MappedFunction(s_reduced.lift_function(node_depth))
    
    depth_map.arg_maps = (keys_map(s), child_index_map, unit_map(s, node_depth_map))
    node_depth_map.arg_maps = (keys_map(s_reduced), unit_map(s_reduced, depth_map))
    

    print('max depth is:')
    print(max(node_depth_map[p] for p in s_reduced.points()))
