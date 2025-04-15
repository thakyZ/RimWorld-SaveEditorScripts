#!/usr/bin/env python3

# cSpell:ignore ideos

"""
A script to remove extra/duplicate precepts from a single or all ideologies.
"""

import shutil
import sys
from argparse import ArgumentParser, Namespace
from collections.abc import Iterable
from pathlib import Path
from typing import Any, TypeVar, overload

from elementpath import Selector
from elementpath.xpath3 import XPath3Parser
from lxml.etree import XMLParser, fromstring, tostring
from lxml.etree import _Element as Element
from lxml.etree import _ElementTree as ElementTree
from rich import inspect
from rich import print as pprint
from rich.prompt import Confirm

HEADER: str = '<?xml version="1.0" encoding="utf-8" ?>'
T = TypeVar("T")


def append_many(list_one: list[T], list_two: list[T]) -> list[T]:
    """Appends many items from one list two another list, and returns the joined list.

    Args:
        list_one (list[T]): A list of items to append another list to.
        list_two (list[T]): A list of items to append to the first list.

    Returns:
        list[T]: The outcome of both lists being appended to eachother.
    """
    for item in list_two:
        list_one.append(item)
    return list_one


class DuplicatePreceptCollection:
    """A collection of duplicate precepts."""

    names: dict[str, int] = {}
    def_names: dict[str, int] = {}
    names_to_defs: dict[str, list[str]] = {}
    defs_to_names: dict[str, str] = {}

    def items(self) -> Iterable[tuple[str, int]]:
        """Gets an iterable of each duplicate precepts' names and definition names.

        Returns:
            Iterable[tuple[str, int]]: The iterable of all duplicate precepts' names and definition
                names.
        """
        names_list: list[tuple[str, int]] = list(self.names.items())
        def_names_list: list[tuple[str, int]] = list(self.def_names.items())
        append_many(names_list, def_names_list)
        return names_list

    @overload
    def count(self, def_name: str) -> int:  # unused
        """Returns a count of the amount of a duplicate precept name.

        Args:
            def_name (str): The definition name of the duplicate precept.

        Returns:
            int: The count of duplicate precepts with that name.
        """

    @overload
    def count(self, name: str) -> int:
        """Returns a count of the amount of a duplicate precept name.

        Args:
            name (str): The name of the duplicate precept.

        Returns:
            int: The count of duplicate precepts with that name.
        """

    def count(self, **kwargs: str) -> int:  # type: ignore[misc]
        """Returns a count of the amount of a duplicate precept name.

        Args:
            name (str): The name of the duplicate precept.
            def_name (str): The definition name of the duplicate precept.

        Returns:
            int: The count of duplicate precepts with that name.

        Raises:
            ValueError: Raised when both or neither of def_name and name are specified.
            ArithmeticError: Raised when we reach a point that should not have been obtained.
        """

        def_name: str | None = None
        if "def_name" in kwargs:
            def_name = kwargs["def_name"]

        name: str | None = None
        if "name" in kwargs:
            name = kwargs["name"]

        if (def_name is None and name is None) or (def_name is not None and name is not None):
            raise ValueError("One parameter must be specified, def_name or name")

        if name is not None:
            if name not in self.names:
                return 1
            return self.names[name]

        if def_name is not None:
            if def_name not in self.def_names:
                return 1
            return self.def_names[def_name]

        raise ArithmeticError("We should not have gotten here.")

    def append(self, def_name: str, name: str) -> None:
        """Appends a new duplicate precept & definition name to the collection.

        Args:
            def_name (str): The duplicate precept definition name.
            name (str): The duplicate precept name.
        """
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
        """An internal method to remove a duplicate precept from the name pool.

        Args:
            def_name (str | None, optional): _description_. Defaults to None.
            name (str | None, optional): _description_. Defaults to None.

        Raises:
            ValueError: Raised when both or neither of def_name and name are specified.
        """
        if (def_name is None and name is None) or (def_name is not None and name is not None):
            raise ValueError("One parameter must be specified, def_name or name")
        if def_name is not None:
            if def_name in self.def_names and self.def_names[def_name] > 0:
                self.def_names[def_name] = self.def_names[def_name] - 1
        if name is not None:
            if name in self.names and self.names[name] > 0:
                self.names[name] = self.names[name] - 1

    @overload
    def remove(self, def_name: str) -> None:
        """Removes a duplicate precept from the name pool.

        Args:
            def_name (str): The precept definition name to match to remove from the name pool.
        """

    @overload
    def remove(self, name: str) -> None:  # Unused.
        """Removes a duplicate precept from the name pool.

        Args:
            name (str): The precept name to match to remove from the name pool.
        """

    def remove(self, **kwargs: str) -> None:  # type: ignore[misc]
        """Removes a duplicate precept from the name pool.

        Args:
            def_name (str): The precept definition name to match to remove from the name pool.
            name (str): The precept name to match to remove from the name pool.

        Raises:
            ValueError: Raised when both or neither of def_name and name are specified.
        """

        def_name: str | None = None
        if "def_name" in kwargs:
            def_name = kwargs["def_name"]

        name: str | None = None
        if "name" in kwargs:
            name = kwargs["name"]

        if (def_name is None and name is None) or (def_name is not None and name is not None):
            raise ValueError("One parameter must be specified, def_name or name")

        if def_name is not None:
            self.__remove__(def_name=def_name)
            self.__remove__(name=self.defs_to_names[def_name])

        if name is not None:
            self.__remove__(name=name)
            for _def_name in self.names_to_defs[name]:
                self.__remove__(def_name=_def_name)


def firstline(text: str) -> str:
    """Gets the contents of the first line in a multiline string.

    Args:
        text (str): The text to get the first line contents of.

    Returns:
        str: The contents of the first line in the text.
    """
    return text.splitlines()[0]


def insert_firstline(text: str, new_line: str) -> str:
    """Inserts a new line at the first line in a multiline string

    Args:
        text (str): The contents of the string to prepend a line to.
        new_line (str): The contents of the line to prepend to the text.

    Returns:
        str: The completed text with the new_line appended to the beginning.
    """
    is_carriage_return = "\n"
    if "\r\n" in text:
        is_carriage_return = "\r\n"
    return f"{new_line}{is_carriage_return}{text}"


def search_xml_tree_for_ideos(root: Element) -> Element | None:
    """Uses XPath to search for the node that contains all the ideologies.

    Args:
        root (Element): The root xml document.

    Returns:
        Element | None: The element that contains all the ideologies. Or none if not found.
    """
    xpath: str = "/savegame/game/world/ideoManager/ideos"
    selector = Selector(xpath, parser=XPath3Parser)
    found: list[Element] | None = selector.select(root)
    if found is not None and len(found) >= 1:
        return found[0]
    return None


def search_xml_tree_for_precepts(root: Element) -> Element | None:
    """Gets the list of precepts in an ideo

    Args:
        root (Element): _description_

    Returns:
        Element | None: _description_
    """
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
    """Cleans duplicate precepts

    Args:
        duplicate_precepts (DuplicatePreceptCollection): _description_
        found_precept (Element): _description_
        found_precepts (list[Element]): _description_
        ideo_name (str): _description_
    """
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
            pprint(f"Failed to remove extra precept for {key}, we have {value - 1} more")


def parse_precepts(found_precept: Element, found_precepts: list[Element], ideo_name: str) -> None:
    """Parses each precept

    Args:
        found_precept (Element): _description_
        found_precepts (list[Element]): _description_
        ideo_name (str): _description_
    """
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


def parse_ideo(found_ideos: list[Element]) -> None:
    """Parses each ideology

    Args:
        found_ideos (list[Element]): _description_
    """
    for ideo_index, ideo_element in enumerate(found_ideos):
        ideo_name_element: Element | None = ideo_element.find("name")
        if ideo_name_element is None:
            pprint(f"[red]Failed to find ideo name for ideo at position {ideo_index}[/red]")
            continue
        ideo_name: str | None = ideo_name_element.text
        if ideo_name is None:
            pprint(
                f"[red]Failed to find ideo name (inner text) for ideo at position{ideo_index}[/red]"
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


def backup_save_file(file_path: Path) -> None:
    """Backs up the save file without overwriting a already existing file.

    Args:
        file_path (Path): The path to the file to backup.
    """
    backup_file = f"{file_path}.bak"
    last_index = 1
    while Path(backup_file).exists():
        backup_file = f"{backup_file}.{last_index}"
        last_index = last_index + 1
    shutil.move(file_path, backup_file)


def main() -> None:
    """The main method for this script.

    Raises:
        FileNotFoundError: _description_
    """
    parser = ArgumentParser(
        prog="Remove Extra Precepts",
        description="Removes extra precepts from a RimWorld save file.",
        epilog="Created by Neko Boi Nick.",
    )
    parser.add_argument("file", help="A path to a save file to modify.")
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

    parse_ideo(found_ideos)
    backup_save_file(file_path)

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
