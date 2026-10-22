"""Usable copper area of the board: the real outline (outer edge minus any
cutouts, e.g. the speaker hole), shrunk by a margin. Everything that drops
vias or tracks by itself checks against this."""
import pcbnew
from shapely.geometry import Polygon

_cache = {}


def usable(b, margin):
    key = (id(b), round(margin, 3))
    if key not in _cache:
        o = pcbnew.SHAPE_POLY_SET()
        b.GetBoardPolygonOutlines(o)
        polys = []
        for i in range(o.OutlineCount()):
            ring = lambda ch: [(pcbnew.ToMM(ch.CPoint(k).x), pcbnew.ToMM(ch.CPoint(k).y)) for k in range(ch.PointCount())]
            polys.append(Polygon(ring(o.Outline(i)), [ring(o.Hole(i, h)) for h in range(o.HoleCount(i))]))
        from shapely.ops import unary_union
        _cache[key] = unary_union(polys).buffer(-margin)
    return _cache[key]
