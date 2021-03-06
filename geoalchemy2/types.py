"""
This module includes the :class:`geoalchemy2.types.Geometry` and
:class:`geoalchemy2.types.Geography` to use when defining geometry
and geography columns, respectively.

Reference
---------
"""

from sqlalchemy.types import UserDefinedType
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql.base import ischema_names

from .comparator import BaseComparator, Comparator
from .elements import WKBElement, RasterElement


class _GISType(UserDefinedType):
    """
    The base class for :class:`geoalchemy2.types.Geometry` and
    :class:`geoalchemy2.types.Geography`.

    This class defines ``bind_expression`` and ``column_expression`` methods
    that wrap column expressions in ``ST_GeomFromText``, ``ST_GeogFromText``,
    or ``ST_AsBinary`` calls.

    This class also defines the ``result_processor`` method, so that WKB values
    received from the database are converted to
    :class:`geoalchemy2.elements.WKBElement` objects.

    Constructor arguments:

    ``geometry_type``

        The geometry type.

        Possible values are:

          * ``"GEOMETRY"``,
          * ``"POINT"``,
          * ``"LINESTRING"``,
          * ``"POLYGON"``,
          * ``"MULTIPOINT"``,
          * ``"MULTILINESTRING"``,
          * ``"MULTIPOLYGON"``,
          * ``"GEOMETRYCOLLECTION"``
          * ``"CURVE"``.

       The latter is actually not supported with
       :class:`geoalchemy2.types.Geography`.

       Default is ``"GEOMETRY"``.

    ``srid``

        The SRID for this column. E.g. 426. Default is ``-1``.

    ``dimension``

        The dimension of the geometry. Default is ``2``.

    ``spatial_index``

        Indicate if a spatial index should be created. Default is ``True``.

    ``management``

        Indicate if the ``AddGeometryColumn`` and ``DropGeometryColumn``
        managements functions should be called when adding and dropping the
        geometry column. Should be set to ``True`` for PostGIS 1.x. Default is
        ``False``. Note that this option has no effect for
        :class:`geoalchemy2.types.Geography`.

    """

    name = None
    """ Name used for defining the main geo type (geometry or geography)
        in CREATE TABLE statements. Set in subclasses. """

    from_text = None
    """ The name of ST_*FromText function for this type.
        Set in subclasses. """

    comparator_factory = Comparator
    """ This is the way by which spatial operators are defined for
        geometry/geography columns. """

    def __init__(self, geometry_type='GEOMETRY', srid=-1, dimension=2,
                 spatial_index=True, management=False):
        self.geometry_type = geometry_type.upper()
        self.srid = int(srid)
        self.dimension = dimension
        self.spatial_index = spatial_index
        self.management = management

    def get_col_spec(self):
        return '%s(%s,%d)' % (self.name, self.geometry_type, self.srid)

    def column_expression(self, col):
        return func.ST_AsBinary(col, type_=self)

    def result_processor(self, dialect, coltype):
        def process(value):
            if value is not None:
                return WKBElement(value, srid=self.srid)
        return process

    def bind_expression(self, bindvalue):
        return getattr(func, self.from_text)(bindvalue, type_=self)


class Geometry(_GISType):
    """
    The Geometry type.

    Creating a geometry column is done like this::

        Column(Geometry(geometry_type='POINT', srid=4326))

    See :class:`geoalchemy2.types._GISType` for the list of arguments that can
    be passed to the constructor.

    """

    name = 'geometry'
    """ Type name used for defining geometry columns in ``CREATE TABLE``. """

    from_text = 'ST_GeomFromText'
    """ The ``FromText`` geometry constructor. Used by the parent class'
        ``bind_expression`` method. """


class Geography(_GISType):
    """
    The Geography type.

    Creating a geography column is done like this::

        Column(Geography(geometry_type='POINT', srid=4326))

    See :class:`geoalchemy2.types._GISType` for the list of arguments that can
    be passed to the constructor.

    """

    name = 'geography'
    """ Type name used for defining geography columns in ``CREATE TABLE``. """

    from_text = 'ST_GeogFromText'
    """ The ``FromText`` geography constructor. Used by the parent class'
        ``bind_expression`` method. """


class Raster(UserDefinedType):
    """
    The Raster column type.

    Creating a raster column is done like this::

        Column(Raster)

    This class defines the ``result_processor`` method, so that raster values
    received from the database are converted to
    :class:`geoalchemy2.elements.RasterElement` objects.

    Constructor arguments:

    ``spatial_index``

        Indicate if a spatial index should be created. Default is ``True``.

    """

    comparator_factory = BaseComparator
    """
    This is the way by which spatial operators and functions are
    defined for raster columns.
    """

    def __init__(self, spatial_index=True):
        self.spatial_index = spatial_index

    def get_col_spec(self):
        return 'raster'

    def result_processor(self, dialect, coltype):
        def process(value):
            if value is not None:
                return RasterElement(value)
        return process


# Register Geometry and Geography to SQLAlchemy's Postgres reflection
# subsystem.
ischema_names['geometry'] = Geometry
ischema_names['geography'] = Geography
ischema_names['raster'] = Raster
