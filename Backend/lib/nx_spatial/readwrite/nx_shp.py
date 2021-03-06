"""
*********
Shapefile
*********

Generates a networkx.DiGraph from point and line shapefiles.

Point geometries are translated into nodes, lines into edges. Coordinate tuples
are used as keys. Attributes are preserved, line geometries are simplified into
start and end coordinates. Accepts a single shapefile or directory of many
shapefiles.

"The Esri Shapefile or simply a shapefile is a popular geospatial vector
data format for geographic information systems software. It is developed
and regulated by Esri as a (mostly) open specification for data
interoperability among Esri and other software products."
See http://en.wikipedia.org/wiki/Shapefile for additional information.

"""
__author__ = """Ben Reilly (benwreilly@gmail.com)"""
#    Copyright (C) 2004-2010 by
#    Ben Reilly <benwreilly@gmail.com>
#    All rights reserved.

__all__ = ['read_shp', 'write_shp']

import networkx as nx

def read_shp(path):
    """Generates a networkx.DiGraph from shapefiles. 

    "The Esri Shapefile or simply a shapefile is a popular geospatial vector
    data format for geographic information systems software [1]_."

    Parameters
    ----------
    path : file or string
       File, directory, or filename to read.

    Returns
    -------
    G : NetworkX graph

    Examples
    --------
    G=nx.read_shp('test.shp')
    
    References
    ----------
    .. [1] http://en.wikipedia.org/wiki/Shapefile
    """
    try:
        from osgeo import ogr
    except ImportError:
        raise ImportError("read_shp requires OGR: http://www.gdal.org/")
    
    net = nx.DiGraph()
    
    def getfieldinfo(lyr, feature, flds):
            f = feature
            # hack to get around bug in ogr >=1.6
            f.GetFieldAsDate = f.GetFieldAsDateTime
            return [f.GetField(f.GetFieldIndex(x)) for x in flds]
            
    def addlyr(lyr, fields):
        for findex in xrange(lyr.GetFeatureCount()):
            f = lyr.GetFeature(findex)
            flddata = getfieldinfo(lyr, f, fields)
            g = f.geometry()
            attributes = dict(zip(fields, flddata))
            attributes["ShpName"] = lyr.GetName()
            if g.GetGeometryType() == ogr.wkbPoint:
                net.add_node((g.GetPoint_2D(0)), attributes)
            if g.GetGeometryType() == ogr.wkbLineString:
                attributes["Wkb"] = g.ExportToWkb()
                attributes["Wkt"] = g.ExportToWkt()
                attributes["Json"] = g.ExportToJson()
                last = g.GetPointCount() - 1
                net.add_edge(g.GetPoint_2D(0), g.GetPoint_2D(last), attributes)                
    if isinstance(path, str):
        shp = ogr.Open(path)
        lyrcount = shp.GetLayerCount() #multiple layers indicate a directory
        for lyrindex in xrange(lyrcount):
            lyr = shp.GetLayerByIndex(lyrindex)
            flds = [x.GetName() for x in lyr.schema]
            addlyr(lyr, flds)
    return net
    
def write_shp(G, outdir):
    """Writes a networkx.DiGraph to two shapefiles, edges and nodes. 

    "The Esri Shapefile or simply a shapefile is a popular geospatial vector
    data format for geographic information systems software [1]_."

    Parameters
    ----------
    outdir : directory path
       Output directory for the two shapefiles.

    Returns
    -------
    None

    Examples
    --------
    nx.write_shp(digraph, '~/shapefiles')
    
    References
    ----------
    .. [1] http://en.wikipedia.org/wiki/Shapefile
    """
    try:
        from osgeo import ogr
    except ImportError:
        raise ImportError("write_shp requires OGR: http://www.gdal.org/")

    def netgeometry(key, data):
        if data.has_key('Wkb'):
            geom = ogr.CreateGeometryFromWkb(data['Wkb'])
        elif data.has_key('Wkt'):
            geom = ogr.CreateGeometryFromWkt(data['Wkt'])
        elif type(key[0]) == 'tuple': # edge keys are packed tuples
            geom = ogr.Geometry(ogr.wkbLineString)
            _from, _to = key[0], key[1]
            geom.SetPoint(0, *_from)
            geom.SetPoint(1, *_to)
        else:
            geom = ogr.Geometry(ogr.wkbPoint)
            geom.SetPoint(0, *key)
        return geom

    def create_feature(geometry, lyr):
        feature = ogr.Feature(lyr.GetLayerDefn())
        feature.SetGeometry(g)
        lyr.CreateFeature(feature)
        feature.Destroy()

    drv = ogr.GetDriverByName("ESRI Shapefile")
    shpdir = drv.CreateDataSource(outdir)
    nodes = shpdir.CreateLayer("nodes", None, ogr.wkbPoint)
    for n in G:
        data = G.node[n].values() or [{}]
        g = netgeometry(n, data[0])
        create_feature(g, nodes)
    edges = shpdir.CreateLayer("edges", None, ogr.wkbLineString)
    for e in G.edges():
        data = G.get_edge_data(*e)
        g = netgeometry(e, data)
        create_feature(g, edges)
        
    nodes, edges = None, None

# fixture for nose tests
def setup_module(module):
    from nose import SkipTest
    try:
        import ogr
    except:
        raise SkipTest("OGR not available")

