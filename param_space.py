from itertools import product

from collections import abc, defaultdict

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

        key_diff = self.spec.keys().difference(other_space.spec.keys())
        for key in key_diff:
            new_spec[key] = other_space.spec[key]

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

    def get_value(self, point):
        if point.pspace != self.pspace:
            raise TypeError('point must be in the same param space as the map')
        return self.map[point]

    def set_value(self, point, value):
        if point.pspace != self.pspace:
            raise TypeError('point must be in the same param space as the map')
        self.map[point] = value

    def __repr__(self):
        return 'Map<{}>'.format(repr(self.map))

class Function:
    def __init__(self, pspace, func):
        self.pspace = pspace
        self.func = func

    def call(self, *arg_maps):
        result_map = {}
        for p in self.pspace.points():
            args = [arg_map.get_value(p) for arg_map in arg_maps]
            result_map[p] = self.func(*args)
        return self.pspace.make_map(result_map)

    def __call__(self, *arg_maps):
        return self.call(*arg_maps)

#### convenience stuff

def keys_map(pspace):
    keys_map = {}
    for p in pspace.points():
        keys_map[p] = p.key
    return pspace.make_map(keys_map)


def unit_map(pspace, unit=None):
    unit_map = {}
    for p in pspace.points():
        unit_map[p] = unit
    return pspace.make_map(unit_map)

class MappedFunction:
    unevaluated = object()

    def __init__(self, function, *arg_maps):
        self.function = function
        self.cache_map = unit_map(self.function.pspace, unit=unevaluated)
        self.arg_maps = arg_maps

    @property
    def pspace(self):
        return self.function.pspace

    def get_value(self, point):
        if point.pspace != self.pspace:
            raise TypeError('point must be in the same param space as the map')
        value = self.cache_map.get_value(point)
        if value is unevaluated:
            args = [arg_map.get_value(point) for arg_map in self.arg_maps]
            value = self.function.func(*args)
            self.cache_map.set_value(point, value)

        return value

def expand_point(point1, pspace2):
    extra_space = pspace2.difference(point1.pspace)
    for p in extra_space.points():
        new_key = p.key.copy()
        new_key.update(point1.key)
        yield pspace2.make_point(new_key)

def expand_map(map1, pspace2):
    new_map_dict = {}
    for point1 in map1.pspace.points():
        for point2 in expand_point(point1, pspace2):
            new_map_dict[point2] = map1.get_value(point1)
    return pspace2.make_map(new_map_dict)

def contract_point(point2, pspace1):
    new_key_dict = {}
    for k in pspace1.spec:
        new_key_dict[k] = point2.key[k]
    return pspace1.make_point(new_key_dict)

def contract_map(map2, pspace1):
    extra_space = map2.pspace.difference(pspace1)
    
    extra_map_dict = defaultdict(dict)

    for point2 in map2.pspace.points():
        extra_point = contract_point(point2, extra_space)
        point1 = contract_point(point2, pspace1)
        extra_map_dict[point1][extra_point] = map2.get_value(point2)

    extra_map_dict2 = {k: extra_space.make_map(v) for (k, v) in extra_map_dict.items()}
    return pspace1.make_map(extra_map_dict2)

