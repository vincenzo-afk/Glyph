import os
import sys

import pytest

import config
from conftest import write_docx, write_pdf
from extractors import _mark_stale, extract_file


def ex(path):
    return extract_file(path, path.parent, config)


def test_txt_csv(tmp_path):
    (tmp_path / "a.txt").write_text("hello")
    (tmp_path / "b.csv").write_text("x,y\n1,2,3\n")
    assert ex(tmp_path / "a.txt").text == "hello"
    t = ex(tmp_path / "b.csv").text
    assert "y: 2" in t and "3" in t         # ragged row keeps its extra cell


def test_pdf(tmp_path):
    write_pdf(tmp_path / "a.pdf", "junction 94 C")
    assert "94" in ex(tmp_path / "a.pdf").text


def test_docx_tables_only_and_entities(tmp_path):
    write_docx(tmp_path / "a.docx",
               "<w:tbl><w:tr><w:tc><w:t>Q&amp;A</w:t></w:tc><w:tc><w:t>7</w:t></w:tc></w:tr></w:tbl>")
    t = ex(tmp_path / "a.docx").text
    assert "Q&A" in t and "|" in t and "7" in t


def test_xlsx_empty_sheet(tmp_path):
    import openpyxl
    wb = openpyxl.Workbook()
    wb.active.append(["k", 5])
    wb.create_sheet("blank")
    wb.save(tmp_path / "a.xlsx")
    r = ex(tmp_path / "a.xlsx")
    assert r.ok and "k | 5" in r.text

