from param_space import ParamSpace, points_map, unit_map, contract_point, point_region, update_point, MappedFunction

class V: #Vertex
    def __init__(self, id):
        self.id = id

    def __repr__(self):
        return 'V({})'.format(self.id)

class E: #Edge (directed)
    def __init__(self, v1, v2):
        self.v1 = v1
        self.v2 = v2

class G: #Graph
    def __init__(self, vs, es):
        self.vs = vs
        self.es = es

#define an example graph g
v1, v2, v3, v4, v5 = V(1), V(2), V(3), V(4), V(5)
e1, e2, e3, e4 = E(v1, v2), E(v2, v3), E(v3, v4), E(v3, v5)

g = G([v1, v2, v3, v4, v5], [e1, e2, e3, e4])

#the space of all vertices in g
vertex_space = ParamSpace({'v1': g.vs})

#the space of all pairs of vertices in g
vertex_pair_space = vertex_space.add({'v2': g.vs})

# does the point in vertex-pair space correspond to a given edge in g?
def is_edge(point, graph):
    return any(e.v1 == point.key['v1'] and e.v2 == point.key['v2'] for e in graph.es)

#map from pairs of vertices to true/false. true indicates the pair is an edge
edge_map = vertex_pair_space.lift_function(is_edge)(
    points_map(vertex_pair_space),
    unit_map(vertex_pair_space, g))

reachable_in_1_map = edge_map #alias for base reachability case

#max possible computation steps to determine reachability between two vertices (e.g. the graph is a linked list)
max_steps = len(g.vs)

#param space of the computational steps for determining reachability
steps_space = ParamSpace({'steps': list(range(1, max_steps + 1))})
reachable_space = vertex_pair_space.union(steps_space)

def reachable_in_x(point, reachable_in_1_map, reachable_in_x_map):
    x = point.key['steps']
    
    # check for the base case of first comp. step
    if x == 1:
        return reachable_in_1_map[contract_point(point, vertex_pair_space)]

    # check if this pair is already known to be reachable in one fewer comp step
    if reachable_in_x_map[update_point(point, {'steps': x - 1})]:
        return True

    # find all points with edges leading to the target, v2.
    frontier_points = point_region(vertex_pair_space, {'v2': point.key['v2']})
    for fp in frontier_points:
        if not reachable_in_1_map[fp]:
            continue #not an edge

        #if that point is known to be reachable, then we know v2 is reachable
        if reachable_in_x_map[
                update_point(point, {
                    'steps': x - 1,
                    'v2': fp.key['v1']})]:
            return True
    return False

reachable_in_x_map = MappedFunction(reachable_space.lift_function(reachable_in_x))
reachable_in_x_map.arg_maps = (
    points_map(reachable_space),
    unit_map(reachable_space, reachable_in_1_map),
    unit_map(reachable_space, reachable_in_x_map))

if __name__ == '__main__':
    print('reachable in 2:')
    for p in point_region(reachable_space, {'steps': 2}):
        if reachable_in_x_map[p]:
            print(p.key['v1'], 'is known to reach', p.key['v2'], 'within 2 steps')

    print('reachable in 4:')
    for p in point_region(reachable_space, {'steps': 4}):
        if reachable_in_x_map[p]:
            print(p.key['v1'], 'is known to reach', p.key['v2'], 'within 4 steps')