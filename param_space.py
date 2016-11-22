from itertools import product

from joblib import Parallel, delayed

from collections import abc

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
            yield Point(self, key)

    def drop(self, names):
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
            l1 =  self.spec.get(key, [])
            l2 = other_space.spec.get(key, [])

            merged = list(set(l1 + l2))
            new_spec[key] = merged

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
        return repr(self.key)

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
        return repr(self.map)

class Func:
    def __init__(self, pspace, func):
        self.pspace = pspace
        self.func = func

    def call(self, *arg_maps):
        result_map = {}
        for p in self.pspace.points():
            args = [arg_map.get_value(p) for arg_map in arg_maps]
            result_map[p] = self.func(*args)
        return Map(self.pspace, result_map)

    def parallel_call(self, *arg_maps):
        points = list(self.pspace.points())
        jobs = []
        for p in points:
            args = [arg_map.get_value(p) for arg_map in arg_maps]
            jobs.append(delayed(self.func)(*args))
        results = Parallel(n_jobs=-1)(jobs)
        result_map = {}
        for p, result in zip(points, results):
            result_map[p] = result

        return Map(self.pspace, result_map)

#### convenience stuff

def keys_map(pspace):
    keys_map = {}
    for p in pspace.points():
        keys_map[p] = p.key
    return Map(pspace, keys_map)


def unit_map(pspace, unit=None):
    unit_map = {}
    for p in pspace.points():
        unit_map[p] = unit
    return Map(pspace, unit_map)
