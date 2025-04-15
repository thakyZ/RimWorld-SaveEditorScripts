#!/usr/bin/env python3

"""
A script to remove extra/duplicate precepts from a single or all ideologies.
"""

# import os
import shutil
import sys
from argparse import ArgumentParser, Namespace
from pathlib import Path
from typing import Any, TypeVar
from collections.abc import Iterable
from elementpath import Selector
from elementpath.xpath3 import XPath3Parser
from lxml.etree import (
    XMLParser,
    fromstring,
    tostring,
)
from lxml.etree import (
    _Element as Element,
)
from lxml.etree import (
    _ElementTree as ElementTree,
)
from rich import inspect
from rich import print as pprint
from rich.prompt import Confirm

HEADER: str = '<?xml version="1.0" encoding="utf-8" ?>'
T = TypeVar("T")


def append_many(list_one: list[T], list_two: list[T]) -> list[T]:
    for item in list_two:
        list_one.append(item)
    return list_one


class DuplicatePreceptCollection:
    """A collection of duplicate precept"""

    names: dict[str, int] = {}
    def_names: dict[str, int] = {}
    names_to_defs: dict[str, list[str]] = {}
    defs_to_names: dict[str, str] = {}

    def __init__(self):
        super().__init__()

    def items(self) -> Iterable[tuple[str, int]]:
        names_list: list[tuple[str, int]] = list(self.names.items())
        def_names_list: list[tuple[str, int]] = list(self.def_names.items())
        append_many(names_list, def_names_list)
        return names_list

    def count(self, name: str) -> int:
        if name not in self.names:
            raise KeyError(f"Entry {name} not found.")
        return self.names[name]

    def append(self, def_name: str, name: str) -> None:
        if name in self.names:
            self.names[name] = self.names[name] + 1
        else:
            self.names[name] = 1
        if def_name in self.def_names:
            self.def_names[def_name] = self.def_names[def_name] + 1
        else:
            self.def_names[def_name] = 1
        if name not in self.names_to_defs:
            self.names_to_defs[name] = [def_name]
        if name in self.names_to_defs:
            self.names_to_defs[name].append(def_name)
        if def_name not in self.defs_to_names:
            self.defs_to_names[def_name] = name

    def __remove__(self, def_name: str | None = None, name: str | None = None) -> None:
        if (def_name is None and name is None) or (
            def_name is not None and name is not None
        ):
            raise ValueError("One parameter must be specified, def_name or name")
        if def_name is not None:
            if def_name not in self.def_names:
                raise KeyError(f"Entry {def_name} not found.")
            if self.def_names[def_name] > 0:
                self.def_names[def_name] = self.def_names[def_name] - 1
        if name is not None:
            if name not in self.names:
                raise KeyError(f"Entry {name} not found.")
            if self.names[name] > 0:
                self.names[name] = self.names[name] - 1

    def remove(self, def_name: str) -> None:
        self.__remove__(def_name=def_name)
        self.__remove__(name=self.defs_to_names[def_name])


def firstline(text: str) -> str:
    """Gets the contents of the first line in a multiline string"""
    return text.splitlines()[0]


def insert_firstline(text: str, new_line: str) -> str:
    """Inserts a new line at the first line in a multiline string"""
    is_carriage_return = "\n"
    if "\r\n" in text:
        is_carriage_return = "\r\n"
    return f"{new_line}{is_carriage_return}{text}"


def search_xml_tree_for_ideos(root: Element) -> Element | None:
    """Gets the list of ideologies"""
    xpath: str = "/savegame/game/world/ideoManager/ideos"
    selector = Selector(xpath, parser=XPath3Parser)
    found: list[Element] | None = selector.select(root)
    if found is not None and len(found) >= 1:
        return found[0]
    return None


def search_xml_tree_for_precepts(root: Element) -> Element | None:
    """Gets the list of precepts in an ideo"""
    xpath: str = "precepts"
    selector = Selector(xpath, parser=XPath3Parser)
    found: list[Element] | None = selector.select(root)
    if found is not None and len(found) >= 1:
        return found[0]
    return None


def clean_precepts(
    duplicate_precepts: DuplicatePreceptCollection,
    found_precept: Element,
    found_precepts: list[Element],
    ideo_name: str,
) -> None:
    """Cleans duplicate precepts"""
    for precept_index, precept_element in enumerate(found_precepts):
        if "Class" in precept_element.attrib.keys():
            continue
        precept_name_element: Element | None = precept_element.find("name")
        if precept_name_element is None:
            pprint(
                "[red]Failed to find name element for precept at position"
                f"{precept_index} in ideo {ideo_name}[/red]"
            )
            continue
        precept_name: str | None = precept_name_element.text
        if precept_name is None:
            pprint(
                "[red]Failed to find name (inner text) for precept at position"
                f"{precept_index} in ideo {ideo_name}[/red]"
            )
            continue
        precept_def_element: Element | None = precept_element.find("def")
        if precept_def_element is None:
            pprint(
                "[red]Failed to find def name for precept at position"
                f"{precept_index} in ideo {ideo_name}[/red]"
            )
            continue
        precept_def: str | None = precept_def_element.text
        if precept_def is None:
            pprint(
                "[red]Failed to find def name (inner text) for precept at position"
                f"{precept_index} in ideo {ideo_name}[/red]"
            )
            continue
        if (
            precept_name in duplicate_precepts.names
            and precept_def in duplicate_precepts.def_names
            and duplicate_precepts.count(name=precept_name) > 1
        ):
            if (
                Confirm.ask(
                    f"Remove precept {precept_name} with def {precept_def} from ideo {ideo_name}?",
                    default=True,
                )
                is True
            ):
                found_precept.remove(precept_element)
                duplicate_precepts.remove(def_name=precept_def)
    for key, value in duplicate_precepts.items():
        if value > 1:
            pprint(
                f"Failed to remove extra precept for {key}, we have {value - 1} more"
            )


def parse_precepts(
    found_precept: Element, found_precepts: list[Element], ideo_name: str
) -> None:
    """Parses each precept"""
    precept_cache: list[str] = []
    duplicate_precepts = DuplicatePreceptCollection()
    for precept_index, precept_element in enumerate(found_precepts):
        if "Class" in precept_element.attrib.keys():
            continue
        precept_name_element: Element | None = precept_element.find("name")
        if precept_name_element is None:
            pprint(
                "[red]Failed to find name element for precept at position"
                f"{precept_index} in ideo {ideo_name}[/red]"
            )
            continue
        precept_name: str | None = precept_name_element.text
        if precept_name is None:
            pprint(
                "[red]Failed to find name (inner text) for precept at position"
                f"{precept_index} in ideo {ideo_name}[/red]"
            )
            continue
        precept_def_element: Element | None = precept_element.find("def")
        if precept_def_element is None:
            pprint(
                "[red]Failed to find def element for precept at position"
                f"{precept_index} in ideo {ideo_name}[/red]"
            )
            continue
        precept_def: str | None = precept_def_element.text
        if precept_def is None:
            pprint(
                "[red]Failed to find def name (inner text) for precept at position"
                f"{precept_index} in ideo {ideo_name}[/red]"
            )
            continue
        if precept_name in precept_cache:
            duplicate_precepts.append(precept_def, precept_name)
        precept_cache.append(precept_name)

    clean_precepts(duplicate_precepts, found_precept, found_precepts, ideo_name)


def parse_ideo(found_ideo: Element, found_ideos: list[Element]) -> None:
    """Parses each ideology"""
    for ideo_index, ideo_element in enumerate(found_ideos):
        ideo_name_element: Element | None = ideo_element.find("name")
        if ideo_name_element is None:
            pprint(
                f"[red]Failed to find ideo name for ideo at position {ideo_index}[/red]"
            )
            continue
        ideo_name: str | None = ideo_name_element.text
        if ideo_name is None:
            pprint(
                "[red]Failed to find ideo name (inner text) for ideo at position"
                f"{ideo_index}[/red]"
            )
            continue
        found_precept: Element | None = search_xml_tree_for_precepts(ideo_element)
        if found_precept is None:
            pprint(f"[red]No precepts node found in ideo {ideo_name}[/red]")
            continue
        found_precepts: list[Element] | None = found_precept.findall("li")
        if found_precepts is None:
            pprint(f"[red]No precepts found in ideo {ideo_name}[/red]")
            continue
        parse_precepts(found_precept, found_precepts, ideo_name)


def main() -> None:
    """The main method for this script."""
    parser = ArgumentParser(
        prog="Remove Extra Precepts",
        description="Removes extra precepts from a RimWorld save file.",
        epilog="Created by Neko Boi Nick.",
    )
    parser.add_argument("file")
    parsed: Namespace = parser.parse_args()

    file_path = Path(parsed.file)

    if not file_path.exists():
        raise FileNotFoundError(f"File not found at path {file_path}")

    file_contents: bytes | None = None
    xml_parser = XMLParser(encoding="utf8", huge_tree=True)

    with file_path.open("rb") as file_read:
        file_contents = file_read.read()

    root: ElementTree | Any = fromstring(file_contents, xml_parser)

    if root is None:
        pprint("[red]Failed to parse xml file[/red]")
        sys.exit(1)

    if not isinstance(root, Element):
        pprint("[red]Root element is not an instance of Element")
        inspect(root)
        sys.exit(1)

    found_ideo: Element | None = search_xml_tree_for_ideos(root)

    if found_ideo is None:
        pprint("[red]No ideos node found on provided save file[/red]")
        sys.exit(1)

    found_ideos: list[Element] | None = found_ideo.findall("li")

    if found_ideos is None:
        pprint("[red]No ideos found on provided save file[/red]")
        sys.exit(1)

    parse_ideo(found_ideo, found_ideos)
    shutil.move(file_path, f"{file_path}.bak")

    if not isinstance(root, Element):
        pprint("[red]Root element is not an instance of Element")
        sys.exit(1)

    new_file_contents: bytes | str = tostring(root, encoding="utf8")

    if isinstance(new_file_contents, bytes):
        new_file_contents = new_file_contents.decode()

    if not firstline(new_file_contents).startswith(HEADER):
        insert_firstline(new_file_contents, HEADER)

    if new_file_contents == file_contents:
        pprint("[yellow]:warning: No Changes![/yellow]")
        sys.exit(0)

    with file_path.open("w", encoding="utf8") as file_write:
        file_write.write(new_file_contents)

    pprint("[green]Done![/green]")
    sys.exit(0)


if __name__ == "__main__":
    main()
