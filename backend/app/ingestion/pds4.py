"""Safe, bounded inspection of PDS4 XML labels (metadata only)."""
import re
import xml.etree.ElementTree as ET
from typing import Annotated, Any

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

MAX_LABEL_BYTES = 5 * 1024 * 1024
MAX_XML_NODES = 100_000
MAX_XML_DEPTH = 128
FORBIDDEN_DECLARATION = re.compile(rb"<!\s*(?:DOCTYPE|ENTITY)\b", re.IGNORECASE)
router = APIRouter(prefix="/datasets/pds4", tags=["scientific-data-ingestion"])


class PDS4LabelInspection(BaseModel):
    file_name: str
    label_size_bytes: int
    root_element: str
    identification_area: dict[str, Any]
    observation_area: dict[str, Any]
    file_areas: list[dict[str, Any]]
    product_class: str | None = None
    inspection_scope: str = "XML label structure and selected metadata only"
    limitations: list[str] = [
        "This does not validate the label against an authoritative PDS4 schema.",
        "Referenced science-data files are not opened, checked, or authenticated.",
        "Scientific values, coordinate systems, time systems, and calibrations are not validated.",
        "Successful inspection is not evidence of scientific suitability or mission readiness.",
    ]


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def element_text(node: ET.Element | None) -> str | None:
    if node is None:
        return None
    value = " ".join("".join(node.itertext()).split())
    return value or None


def child(node: ET.Element, name: str) -> ET.Element | None:
    return next((item for item in node if local_name(item.tag) == name), None)


def child_text(node: ET.Element, name: str) -> str | None:
    return element_text(child(node, name))


def inspect_pds4_label(xml_bytes: bytes, file_name: str) -> PDS4LabelInspection:
    if not xml_bytes:
        raise HTTPException(status_code=422, detail="PDS4 label is empty")
    if len(xml_bytes) > MAX_LABEL_BYTES:
        raise HTTPException(status_code=413, detail="PDS4 label exceeds the 5 MiB inspection limit")
    if FORBIDDEN_DECLARATION.search(xml_bytes):
        raise HTTPException(status_code=400, detail="DTD and entity declarations are not accepted")

    try:
        root = ET.fromstring(xml_bytes)
    except (ET.ParseError, RecursionError) as error:
        raise HTTPException(status_code=422, detail=f"Malformed or excessively nested XML label: {error}") from error

    root_name = local_name(root.tag)
    if not root_name.startswith("Product_"):
        raise HTTPException(status_code=422, detail="XML root element is not a PDS4 Product_* label")

    count = 0
    stack = [(root, 1)]
    while stack:
        node, depth = stack.pop()
        count += 1
        if count > MAX_XML_NODES:
            raise HTTPException(status_code=413, detail="XML label contains too many elements")
        if depth > MAX_XML_DEPTH:
            raise HTTPException(status_code=413, detail="XML label nesting is too deep")
        stack.extend((item, depth + 1) for item in node)

    identification = next((n for n in root.iter() if local_name(n.tag) == "Identification_Area"), None)
    observation = next((n for n in root.iter() if local_name(n.tag) == "Observation_Area"), None)
    id_keys = ("logical_identifier", "version_id", "title", "information_model_version", "modification_date")
    id_data = {
        key: child_text(identification, key)
        for key in id_keys
    } if identification is not None else {}
    id_data = {key: value for key, value in id_data.items() if value is not None}

    obs_data: dict[str, Any] = {}
    if observation is not None:
        for key in ("Time_Coordinates", "Investigation_Area", "Observing_System", "Target_Identification", "Mission_Area"):
            node = child(observation, key)
            if node is not None:
                values = {
                    local_name(item.tag): element_text(item)
                    for item in node
                    if len(item) == 0 and element_text(item) is not None
                }
                obs_data[key] = values or (element_text(node) or "present")

    file_areas = []
    for area in (n for n in root.iter() if local_name(n.tag) == "File_Area_Observational"):
        file_node = child(area, "File")
        file_info = {}
        if file_node is not None:
            for key in ("file_name", "file_size", "file_records", "records", "record_length"):
                value = child_text(file_node, key)
                if value is not None:
                    file_info[key] = value
        arrays = []
        for array in area:
            array_name = local_name(array.tag)
            if not array_name.startswith("Array"):
                continue
            info: dict[str, Any] = {"element": array_name}
            for key in ("axes", "data_type", "scaling_factor", "value_offset", "description"):
                value = child_text(array, key)
                if value is not None:
                    info[key] = value
            axes = []
            for axis in (n for n in array if local_name(n.tag) == "Axis_Array"):
                axis_info = {
                    key: child_text(axis, key)
                    for key in ("axis_name", "elements", "sequence_number")
                }
                axes.append({key: value for key, value in axis_info.items() if value is not None})
            if axes:
                info["axis_arrays"] = axes
            arrays.append(info)
        file_areas.append({"file": file_info, "arrays": arrays})

    product_class = (
        root_name
        if root_name.startswith("Product_")
        else next(
            (local_name(n.tag) for n in root.iter() if local_name(n.tag).startswith("Product_")),
            None,
        )
    )
    return PDS4LabelInspection(
        file_name=file_name,
        label_size_bytes=len(xml_bytes),
        root_element=local_name(root.tag),
        identification_area=id_data,
        observation_area=obs_data,
        file_areas=file_areas,
        product_class=product_class,
    )


@router.post("/inspect", response_model=PDS4LabelInspection)
async def inspect_uploaded_pds4_label(file: Annotated[UploadFile, File()]) -> PDS4LabelInspection:
    """Inspect a small PDS4 XML label; referenced science data are never uploaded."""
    name = file.filename
    if not name or "/" in name or "\\" in name or name in {".", ".."}:
        await file.close()
        raise HTTPException(status_code=400, detail="Upload must have a plain file name")
    if not name.lower().endswith((".xml", ".lbl")):
        await file.close()
        raise HTTPException(status_code=415, detail="Upload a PDS4 XML label (.xml or .lbl)")
    try:
        data = await file.read(MAX_LABEL_BYTES + 1)
    finally:
        await file.close()
    return inspect_pds4_label(data, name)
