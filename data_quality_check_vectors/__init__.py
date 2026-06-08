"""QGIS plugin entry point for Data Quality Check for Vectors."""


def classFactory(iface):
    """Load DataQualityCheckVectors class from data_quality_check_vectors."""
    from .data_quality_check_vectors import DataQualityCheckVectors
    return DataQualityCheckVectors(iface)
