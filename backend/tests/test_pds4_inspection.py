from fastapi.testclient import TestClient

from app.ingestion.pds4 import inspect_pds4_label
from app.main import app

client = TestClient(app)
LABEL = b"""<?xml version="1.0"?>
<Product_Observational xmlns="http://pds.nasa.gov/pds4/pds/v1">
<Identification_Area><logical_identifier>urn:nasa:pds:demo</logical_identifier><version_id>1.0</version_id><title>Demo product</title><information_model_version>1.21</information_model_version><modification_date>2026-11-12</modification_date></Identification_Area>
<Observation_Area><Time_Coordinates><start_date_time>2026-11-12T00:00:00Z</start_date_time></Time_Coordinates></Observation_Area>
<File_Area_Observational><File><file_name>image.img</file_name><file_size>4096</file_size></File><Array_2D_Image><axes>2</axes><data_type>UnsignedByte</data_type><Axis_Array><axis_name>Line</axis_name><elements>64</elements><sequence_number>1</sequence_number></Axis_Array></Array_2D_Image></File_Area_Observational>
</Product_Observational>"""


def test_namespaced_label_extracts_identification_and_array_metadata():
    response = client.post("/api/v1/datasets/pds4/inspect", files={"file": ("demo.xml", LABEL, "application/xml")})
    assert response.status_code == 200
    body = response.json()
    assert body["root_element"] == "Product_Observational"
    assert body["identification_area"]["logical_identifier"] == "urn:nasa:pds:demo"
    assert body["file_areas"][0]["file"]["file_name"] == "image.img"
    assert body["file_areas"][0]["arrays"][0]["axis_arrays"][0]["elements"] == "64"
    assert "authoritative PDS4 schema" in body["limitations"][0]


def test_optional_sections_can_be_absent():
    result = inspect_pds4_label(b"<Product_Observational/>", "minimal.xml")
    assert result.identification_area == {}
    assert result.observation_area == {}
    assert result.file_areas == []


def test_malformed_xml_is_rejected():
    response = client.post("/api/v1/datasets/pds4/inspect", files={"file": ("broken.xml", b"<broken>", "application/xml")})
    assert response.status_code == 422


def test_dtd_and_entity_declarations_are_rejected():
    payload = b'<!DOCTYPE foo [<!ENTITY x "expanded">]><foo>&x;</foo>'
    response = client.post("/api/v1/datasets/pds4/inspect", files={"file": ("unsafe.xml", payload, "application/xml")})
    assert response.status_code == 400


def test_oversized_label_is_rejected():
    payload = b" " * (5 * 1024 * 1024 + 1)
    response = client.post("/api/v1/datasets/pds4/inspect", files={"file": ("large.xml", payload, "application/xml")})
    assert response.status_code == 413


def test_non_xml_filename_is_rejected():
    response = client.post("/api/v1/datasets/pds4/inspect", files={"file": ("science.img", LABEL, "application/octet-stream")})
    assert response.status_code == 415


def test_path_like_filename_is_rejected():
    response = client.post("/api/v1/datasets/pds4/inspect", files={"file": ("../label.xml", LABEL, "application/xml")})
    assert response.status_code == 400
