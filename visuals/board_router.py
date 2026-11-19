# -*- coding: utf-8 -*-
"""Grid router for the point-to-point board map. Wires never share a segment:
each grid cell may carry one horizontal and one vertical wire (a crossing),
turns only happen on free cells, and wires never pass between adjacent IC pins."""
import heapq, math
from itertools import permutations
from board_layout import W, H

D4 = [(1, 0), (0, 1), (-1, 0), (0, -1)]
JOINED = {'TACT': {2: 1, 4: 3}, 'DISP': {3: 8}}  # pin -> pin it is internally joined to

def cid(x, y): return y * (W + 1) + x

class Grid:
    def __init__(self, parts, rails):
        N = (W + 1) * (H + 1)
        self.block = bytearray(N); self.soft = [0] * N
        self.hu = bytearray(N); self.vu = bytearray(N); self.lock = bytearray(N)
        self.pin, self.rail, self.front, self.errors, self.deg2 = {}, {}, {}, [], set()
        for p in parts.values():
            x0, y0, x1, y1 = p['body']
            for y in range(math.ceil(y0), math.floor(y1) + 1):
                for x in range(math.ceil(x0), math.floor(x1) + 1):
                    if 0 <= x <= W and 0 <= y <= H:
                        if p['kind'] == 'DISP': self.soft[cid(x, y)] += 2
                        else: self.block[cid(x, y)] = 1
        for p in parts.values():
            for n, q in p['pins'].items():
                c = cid(q['x'], q['y'])
                if c in self.pin: self.errors.append('pin overlap %s.%s / %s.%s' % (p['ref'], n, self.pin[c][1], self.pin[c][2]))
                if self.block[c]: self.errors.append('pin %s.%s inside a body' % (p['ref'], n))
                self.pin[c] = (q['net'], p['ref'], n)
            if p['kind'] in ('DIP14', 'DIP16', 'DISP', 'TO92', 'TO220', 'TACT'):
                pts = {(q['x'], q['y']) for q in p['pins'].values()}
                for (x, y) in pts:  # cells between adjacent pins of one row are off-limits
                    for dx, dy in ((1, 0), (0, 1)):
                        if (x + 2 * dx, y + 2 * dy) in pts: self.block[cid(x + dx, y + dy)] = 1
        for name, net, o, f, s, e in rails:
            for t in range(s, e + 1):
                x, y = (t, f) if o == 'h' else (f, t)
                c = cid(x, y)
                if c in self.pin and self.pin[c][0] != net:
                    self.errors.append('SHORT: %s.%s on rail %s' % (self.pin[c][1], self.pin[c][2], name))
                if self.block[c] and c not in self.pin: self.errors.append('rail %s crosses a body at %d,%d' % (name, x, y))
                self.rail[c] = (net, o, name)
        self.near = bytearray(N)
        for c in self.pin:
            x, y = c % (W + 1), c // (W + 1)
            for dx, dy in D4:
                if 0 <= x + dx <= W and 0 <= y + dy <= H: self.near[cid(x + dx, y + dy)] = 1

    def occupied(self, c): return self.hu[c] or self.vu[c] or self.lock[c] or c in self.rail

    def route(self, src, goal_cells, shapes, net, relax=False):
        sx, sy = src
        def h(x, y):
            best = 1e9
            for s in shapes:
                if s[0] == 'pt': d = abs(x - s[1]) + abs(y - s[2])
                elif s[0] == 'h': d = abs(y - s[1]) + max(0, s[2] - x, x - s[3])
                else: d = abs(x - s[1]) + max(0, s[2] - y, y - s[3])
                best = min(best, d)
            return best
        start = cid(sx, sy)
        own = {start} | (set(goal_cells) if len(goal_cells) == 1 else set())
        allow = {cid(q % (W + 1) + dx, q // (W + 1) + dy) for q in own for dx, dy in D4}
        g = {(start, 4): 0}; prev = {}
        pq = [(h(sx, sy), 0, start, 4)]
        while pq:
            f, gc, c, d = heapq.heappop(pq)
            if gc > g.get((c, d), 1e18): continue
            if c in goal_cells and c != start:
                path = [c]; k = (c, d)
                while k in prev: k = prev[k]; path.append(k[0])
                return [(q % (W + 1), q // (W + 1)) for q in reversed(path)]
            x, y = c % (W + 1), c // (W + 1)
            occ = c != start and self.occupied(c)
            for nd, (dx, dy) in enumerate(D4):
                if d != 4 and nd == (d + 2) % 4: continue
                if occ and d != 4 and nd != d and not relax: continue
                nx, ny = x + dx, y + dy
                if not (0 <= nx <= W and 0 <= ny <= H): continue
                n = cid(nx, ny)
                if self.block[n] and n not in goal_cells: continue
                horiz = nd in (0, 2)
                goal = n in goal_cells
                if n in self.pin and not goal: continue
                cost = 1.0 + self.soft[n]
                if d != 4 and nd != d: cost += 2.5
                fr = self.front.get(n)
                if fr is not None and not goal:
                    if fr not in own: continue
                elif not goal:
                    if self.near[n] and n not in allow:
                        if not relax: continue
                        cost += 10
                    if self.lock[n]: continue
                    if (self.hu[n] if horiz else self.vu[n]):
                        if not relax: continue
                        cost += 25
                    if n in self.rail:
                        if (self.rail[n][1] == 'h') == horiz:
                            if not relax: continue
                            cost += 25
                        cost += 1
                    if self.hu[n] or self.vu[n]: cost += 1
                    for ax, ay in D4:
                        a = (nx + ax, ny + ay)
                        if 0 <= a[0] <= W and 0 <= a[1] <= H:
                            ac = cid(*a)
                            if ac in self.pin and self.pin[ac][0] != net: cost += 2.5
                    side = ((nx, ny - 1), (nx, ny + 1)) if horiz else ((nx - 1, ny), (nx + 1, ny))
                    for a in side:
                        if 0 <= a[0] <= W and 0 <= a[1] <= H and (self.hu if horiz else self.vu)[cid(*a)]: cost += 0.7
                ng = gc + cost
                if ng < g.get((n, nd), 1e18):
                    g[(n, nd)] = ng; prev[(n, nd)] = (c, d)
                    heapq.heappush(pq, (ng + h(nx, ny), ng, n, nd))
        return None

    def commit(self, path, end_on_rail):
        ends = [cid(*path[0]), cid(*path[-1])]
        for i in range(1, len(path) - 1):
            (ax, ay), (bx, by), (cx, cy) = path[i - 1], path[i], path[i + 1]
            c = cid(bx, by)
            if i <= 2 and ends[0] in self.deg2 and c not in self.pin: self.front[c] = ends[0]; continue
            if i >= len(path) - 3 and ends[1] in self.deg2 and c not in self.pin: self.front[c] = ends[1]; continue
            h1, h2 = ay == by, by == cy
            if h1 and h2: self.hu[c] = 1
            elif not h1 and not h2: self.vu[c] = 1
            else: self.lock[c] = 1; self.hu[c] = 1; self.vu[c] = 1
        if end_on_rail: self.lock[ends[1]] = 1

def simplify(path):
    pts = [path[0]]
    for i in range(1, len(path) - 1):
        a, b, c = path[i - 1], path[i], path[i + 1]
        if (a[0] == b[0] == c[0]) or (a[1] == b[1] == c[1]): continue
        pts.append(b)
    pts.append(path[-1])
    return pts

def chain(nodes, single=lambda nd: False):
    """Shortest open path through all nodes (Manhattan), so every pin carries at most 2 wires.
    Pins reachable from one side only (IC/display pins) are preferred as path ends."""
    if len(nodes) <= 2: return nodes
    dist = lambda a, b: abs(a['x'] - b['x']) + abs(a['y'] - b['y'])
    best = None
    for s in range(len(nodes)):
        rest = [i for i in range(len(nodes)) if i != s]
        for perm in permutations(rest):
            order = [nodes[s]] + [nodes[i] for i in perm]
            L = sum(dist(order[i], order[i + 1]) for i in range(len(order) - 1))
            L += 6 * sum(1 for nd in order[1:-1] if single(nd))
            if best is None or L < best[0]: best = (L, order)
    return best[1]
