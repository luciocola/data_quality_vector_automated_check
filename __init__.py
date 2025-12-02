"""
UMM STAC Liability/Claim Converter Plugin
"""


def classFactory(iface):
    """Load UMMSTACConverter class from file umm_stac_converter.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    from .umm_stac_converter import UMMSTACConverter
    return UMMSTACConverter(iface)
