from __future__ import annotations

from app.schemas.normalized_documents import (
    ProductDatasheetDocument,
    ProductDatasheetFields,
)
from app.services.document_processing.normalizers.base import (
    BaseDocumentNormalizer,
    extract_integer,
    extract_integer_before_unit,
    parse_dimensions_mm,
    split_list_value,
)


class ProductDatasheetNormalizer(BaseDocumentNormalizer):
    document_type = "PRODUCT_DATASHEET"

    field_aliases = {
        "oem_name": ("OEM", "OEM name", "OEM legal name", "Manufacturer"),
        "brand": ("Brand", "Product brand"),
        "model": ("Model", "Product model", "Model name"),
        "sku": ("SKU", "Product SKU", "Model SKU"),
        "product_type": ("Product type", "Equipment type", "Device type"),
        "scanning_speed": (
            "Scanning speed",
            "Scan speed",
            "Rated scanning speed",
        ),
        "optical_resolution": (
            "Optical resolution",
            "Scanner optical resolution",
        ),
        "adf_capacity": (
            "ADF capacity",
            "Automatic document feeder capacity",
            "Feeder capacity",
        ),
        "recommended_daily_volume": (
            "Recommended daily volume",
            "Daily volume",
            "Recommended daily duty cycle",
        ),
        "supported_modes": (
            "Supported modes",
            "Scanning modes",
            "Colour modes",
        ),
        "maximum_document_size": (
            "Maximum document size",
            "Max document size",
            "Maximum media size",
        ),
        "paper_detection": (
            "Paper detection",
            "Double-feed detection",
            "Paper feed detection",
        ),
        "usb": ("USB", "USB interface", "USB connectivity"),
        "network": ("Network", "Network interface", "Ethernet"),
        "driver": ("Driver", "Driver support", "Scanner driver"),
        "integration": ("Integration", "Integration support", "SDK"),
        "image_processing": (
            "Image processing",
            "Image processing features",
            "Image enhancement",
        ),
    }

    def normalize(self) -> ProductDatasheetDocument:
        scanning_speed = self.value("scanning_speed")
        width_mm, height_mm = parse_dimensions_mm(
            self.value("maximum_document_size")
        )
        adf_capacity = self.value("adf_capacity")
        daily_volume = self.value("recommended_daily_volume")

        return ProductDatasheetDocument(
            source_file=self.extraction.file_name,
            fields=ProductDatasheetFields(
                oem_name=self.value("oem_name"),
                brand=self.value("brand"),
                model=self.value("model"),
                sku=self.value("sku"),
                product_type=self.value("product_type"),
                scanning_speed_ppm=extract_integer_before_unit(
                    scanning_speed, "ppm"
                ),
                duplex_speed_ipm=extract_integer_before_unit(
                    scanning_speed, "ipm"
                ),
                optical_resolution_dpi=extract_integer_before_unit(
                    self.value("optical_resolution"), "dpi"
                ),
                adf_capacity_sheets=(
                    extract_integer_before_unit(adf_capacity, "sheets", "sheet")
                    or extract_integer(adf_capacity)
                ),
                recommended_daily_volume_pages=(
                    extract_integer_before_unit(daily_volume, "pages", "page")
                    or extract_integer(daily_volume)
                ),
                supported_modes=split_list_value(
                    self.value("supported_modes")
                ),
                maximum_document_width_mm=width_mm,
                maximum_document_height_mm=height_mm,
                paper_detection=self.value("paper_detection"),
                usb=self.value("usb"),
                network=self.value("network"),
                driver=self.value("driver"),
                integration=self.value("integration"),
                image_processing_features=split_list_value(
                    self.value("image_processing")
                ),
            ),
        )
