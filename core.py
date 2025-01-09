"""
Multi-version dropdown updater.
"""

import argparse
import os
import re
import sys

from lxml import etree, html
from packaging.version import InvalidVersion, Version


def compile_pattern(pattern):
    """
    Compile the given regular expression pattern.

    :param pattern: A regular expression pattern to match directory names.
    :return: Compiled regex pattern.
    """
    return re.compile(pattern)


def find_matching_directories(directory, regex):
    """
    Find all matching directories in the given directory based on the regex pattern.

    :param directory: The root directory to search for matching directories.
    :param regex: Compiled regular expression pattern to match directory names.
    :return: List of matching directories.
    """
    return [
        d
        for d in os.listdir(directory)
        if os.path.isdir(os.path.join(directory, d)) and regex.match(d)
    ]


def separate_refs(matching_dirs, refs_order):
    """
    Separate items in refs_order and other items for semantic versioning sorting.

    :param matching_dirs: List of matching directories.
    :param refs_order: List determining the order of items to appear at the beginning.
    :return: Tuple of ordered_refs and remaining_refs.
    """
    ordered_refs = [d for d in refs_order if d in matching_dirs]
    remaining_refs = [d for d in matching_dirs if d not in refs_order]
    return ordered_refs, remaining_refs


def sorting_key(ref):
    """
    Define a custom sorting key function.

    :param ref: Reference to be sorted.
    :return: Tuple for sorting.
    """
    try:
        return (0, Version(ref))
    except InvalidVersion:
        return (1, ref)


def sort_remaining_refs(remaining_refs):
    """
    Sort the remaining items using the custom sorting key
    (semantic versioning first, then alphabetically).

    :param remaining_refs: List of remaining references.
    :return: Sorted list of remaining references.
    """
    remaining_refs.sort(key=sorting_key, reverse=True)
    return remaining_refs


def generate_refs_dict(ordered_refs, base_url):
    """
    Generate the full URLs for the directories.

    :param ordered_refs: List of ordered references.
    :param base_url: The base URL to be used in the hrefs.
    :return: Dictionary of references and their URLs.
    """
    return {ref: f"{base_url}{ref}" for ref in ordered_refs}


def generate_markup(ordered_refs, refs_dict):
    """
    Generate the HTML markup for the drop-down list.

    :param ordered_refs: List of ordered references.
    :param refs_dict: Dictionary of references and their URLs.
    :return: str, Generated HTML markup.
    """
    nav_item = """
    <li class="nav-item dropdown">
    <a href="#" class="nav-link dropdown-toggle"
        data-bs-toggle="dropdown" role="button"
        aria-expanded="false" aria-haspopup="true"
        id="dropdown-versions">Versions</a>
    <div class="dropdown-menu" aria-labelledby="dropdown-versions">
    """
    for ref in ordered_refs:
        nav_item += '<a class="dropdown-item" data-toggle="tooltip" title="" '
        nav_item += f'href="{refs_dict[ref]}">{ref}</a>\n'
    nav_item += "</div></li>"
    return nav_item


def generate_dropdown_list(directory, pattern, refs_order, base_url):
    """
    Generates version drop-down list to be inserted based
    on matching directories in the given directory and refs_order.

    :param directory: The root directory to search for matching directories.
    :param pattern: A regular expression pattern to match directory names.
    :param refs_order: List determining the order of items to appear at the beginning.
    :param base_url: The base URL to be used in the hrefs.
    :return: str, Generated HTML markup.
    """
    regex = compile_pattern(pattern)
    matching_dirs = find_matching_directories(directory, regex)
    ordered_refs, remaining_refs = separate_refs(matching_dirs, refs_order)
    remaining_refs = sort_remaining_refs(remaining_refs)
    ordered_refs.extend(remaining_refs)
    refs_dict = generate_refs_dict(ordered_refs, base_url)
    return generate_markup(ordered_refs, refs_dict)


def find_navbar(tree):
    """
    Find the first <ul> element in the document that contains the class 'navbar-nav'.

    :param tree: lxml HTML tree object.
    :return: First <ul> element with class 'navbar-nav' or None.
    """
    navbar = tree.xpath(
        "//div[@id='navbar']//ul[contains(@class, 'navbar-nav') and contains(@class, 'me-auto')]"
    )
    if not navbar:
        print(
            "No <ul> element with class 'navbar-nav' found in the document.",
            file=sys.stderr,
        )
        return None
    return navbar[0]


def find_navbar_items(navbar):
    """
    Find <li> elements representing items in the navbar.

    :param navbar: The navbar.
    :return: List of <li> elements.
    """
    if navbar or navbar is not None:
        return navbar.xpath('.//li[contains(@class, "nav-item")]')
    return []


def create_versions_dropdown(dropdown_list):
    """
    Create a new element from the drop-down list markup.

    :param dropdown_list: str, HTML markup containing the drop-down list to insert.
    :return: Custom element or None.
    """
    try:
        return html.fromstring(dropdown_list, parser=etree.HTMLParser())
    except Exception as e:
        print(f"Error parsing the drop-down list: {e}", file=sys.stderr)
        return None


def insert_versions_dropdown(tree, dropdown_list):
    """
    Inserts the drop-down list into the navbar.

    :param tree: lxml HTML tree object.
    :param dropdown_list: str, HTML markup containing the drop-down list to insert.
    :return: bool, True if successful, False otherwise.
    """
    navbar = find_navbar(tree)
    if not navbar:
        return False  # No navbar found

    navbar_items = find_navbar_items(navbar)
    if not navbar_items:
        return False  # No navbar items found

    versions_dropdown = create_versions_dropdown(dropdown_list)
    if not versions_dropdown:
        return False  # Failed to create dropdown

    # Find all <li> that contain a <div> with aria-labelledby="dropdown-versions"
    existing_dropdown = navbar.xpath('.//li[div/@aria-labelledby="dropdown-versions"]')

    # If no existing dropdown is found, add the new dropdown to the end of the navbar
    if not existing_dropdown:
        new_li = html.Element("div")
        new_li.append(versions_dropdown)  # Append the new dropdown directly

        # Append the new <li> to the last <li> item in the navbar
        navbar[-1].addnext(new_li)
        return True

    # Remove duplicates by keeping track of IDs or contents
    existing_ids = set()
    for item in existing_dropdown:
        dropdown_id = item.get("id")  # or another identifier if necessary
        if dropdown_id not in existing_ids:
            existing_ids.add(dropdown_id)
        else:
            # Remove the duplicate
            item.getparent().remove(item)

    # Replace the first remaining existing dropdown with the new versions_dropdown
    if existing_dropdown:
        existing_dropdown[0].getparent().replace(
            existing_dropdown[0], versions_dropdown
        )

    return True


def read_file(file_path):
    """
    Read the content of a file.

    :param file_path: Path to the file.
    :return: Content of the file or None.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.", file=sys.stderr)
    except PermissionError:
        print(
            f"Error: Permission denied to read the file '{file_path}'.", file=sys.stderr
        )
    except Exception as e:
        print(
            f"An unexpected error occurred while reading the file '{file_path}': {e}",
            file=sys.stderr,
        )
    return None


def write_file(file_path, content):
    """
    Write content to a file.

    :param file_path: Path to the file.
    :param content: Content to write.
    :return: bool, True if successful, False otherwise.
    """
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    except PermissionError:
        print(
            f"Error: Permission denied to write to the file '{file_path}'.",
            file=sys.stderr,
        )
    except Exception as e:
        print(
            f"An unexpected error occurred while writing to the file '{file_path}': {e}",
            file=sys.stderr,
        )
    return False


def process_single_html_file(file_path, dropdown_list):
    """
    Process a single HTML file, inserting a dropdown list after the last <li> element.

    :param file_path: Path to the HTML file.
    :param dropdown_list: HTML content for the dropdown list.
    :return: bool, True if successful, False otherwise.
    """
    html_contents = read_file(file_path)
    if html_contents is None:
        return False

    try:
        tree = html.fromstring(html_contents)
    except etree.XMLSyntaxError as e:
        print(f"Error parsing the HTML: {e}", file=sys.stderr)
        return False

    success = insert_versions_dropdown(tree, dropdown_list)
    if not success:
        print(f"❌ {file_path}", file=sys.stderr)
        return False

    doctype = "<!DOCTYPE html>\n"
    comment = "<!-- Generated by pkgdown + https://github.com/insightsengineering/r-pkgdown-multiversion -->\n"
    html_content = etree.tostring(tree, encoding="unicode", pretty_print=True, method="html")
    modified_html = doctype + comment + html_content

    if not write_file(file_path, modified_html):
        return False

    print(f"✅ {file_path}")
    return True


def process_html_files_in_directory(directory, pattern, refs_order, base_url):
    """
    Process all HTML files in the given directory,
    inserting a dropdown list after the last <li> element.

    :param directory: The root directory to search for HTML files.
    :param pattern: Regular expression pattern to match directory names.
    :param refs_order: List determining the order of items to appear at the beginning.
    :param base_url: Base URL to be used in the hrefs.
    """
    processed_files = set()
    dropdown_list = generate_dropdown_list(directory, pattern, refs_order, base_url)

    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".html"):
                file_path = os.path.join(root, file)
                if file_path in processed_files:
                    continue

                if process_single_html_file(file_path, dropdown_list):
                    processed_files.add(file_path)


def update_single_search_json(search_json_path, version, base_url):
    """
    Update the URLs in a single search.json file to include the version.

    :param search_json_path: Path to the search.json file.
    :param version: Version to be included in the URLs.
    :param base_url: Base URL to be used in the hrefs.
    :return: bool, True if successful, False otherwise.
    """
    file_content = read_file(search_json_path)
    if file_content is None:
        return False

    url_pattern = re.compile(rf"({re.escape(base_url)})(?!{re.escape(version)})")
    updated_content = url_pattern.sub(f"{base_url}{version}/", file_content)

    if updated_content != file_content:
        if write_file(search_json_path, updated_content):
            print(f"Updated URLs in {search_json_path}")
            return True
        print(f"Failed to update URLs in {search_json_path}")
        return False
    print(f"No URLs to update in {search_json_path}")
    return True


def update_search_json_urls(directory, pattern, base_url):
    """
    Update the URLs in search.json files within the given directory to include the version.

    :param directory: The root directory to search for search.json files.
    :param pattern: Regular expression pattern to match directory names.
    :param base_url: Base URL to be used in the hrefs.
    """
    regex = compile_pattern(pattern)
    matching_dirs = find_matching_directories(directory, regex)

    for current_directory in matching_dirs:
        search_json_path = os.path.join(directory, current_directory, "search.json")
        if not os.path.isfile(search_json_path):
            continue

        update_single_search_json(search_json_path, current_directory, base_url)


def main():
    """Main."""
    parser = argparse.ArgumentParser(
        description="Insert the multi-version drop-down list after the n-th <li>"
        "item in unordered lists in all HTML files within a directory."
    )
    parser.add_argument(
        "directory", help="Path to the directory containing HTML files."
    )
    parser.add_argument(
        "--pattern",
        required=True,
        help="Regular expression pattern to match directory names.",
    )
    parser.add_argument(
        "--refs_order",
        nargs="+",
        required=True,
        help="List determining the order of items to appear at the beginning.",
    )
    parser.add_argument(
        "--base_url", required=True, help="Base URL to be used in the hrefs."
    )

    args = parser.parse_args()

    process_html_files_in_directory(
        args.directory, args.pattern, args.refs_order, args.base_url
    )
    update_search_json_urls(args.directory, args.pattern, args.base_url)


if __name__ == "__main__":
    main()
