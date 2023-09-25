# Copyright (c) 2017 Civic Knowledge. This file is licensed under the terms of the
# Revised BSD License, included in this distribution as LICENSE

"""
Row generating functions for use in the pylib package of data packages.
"""

# The class used to be here, and still gets referenced here

from metapack_build.core import alt_col_name


def convert_col(v):
    # The replacement of '_' may be necessary for some datasets
    # to ensure that similar columns from different datasets are aligned.
    return alt_col_name(v, 0)  # .replace('_', '')


def copy_reference(resource, doc, env, *args, **kwargs):
    """A row-generating function that yields from a reference. This permits an upstream package to be
    copied and modified by this package, while being formally referenced as a dependency

    The function will generate rows from a reference that has the same name as the resource term
    """

    yield from doc.reference(resource.name)


def copy_reference_group(resource, doc, env, *args, **kwargs):
    """
    A Row generating function that copies all of the references that have the same 'Group' argument as this reference

    This version collects columns names from the set of references and outputs a combined set, matching
    input to outputs by name. Use copy_reference_group_s to skip all of that and just match by position. The
    column names are converted to lowercase all-alphanumeric strings, removing special characters, so
    'school_code' and 'SchoolCode' will match as the same column

    The 'RefArgs' argument is a comma seperated list of arguments from the references that will be prepended to each
    row.

    For Example:

    Section: References:
    Reference: ...file1.csv
    Reference.Name subgroup1
    Reference.Group: subgroups
    Reference.Year: 2015

    Reference: ...file2.csv
    Reference.Name subgroup2
    Reference.Group: subgroups
    Reference.Year: 2016


    Section: Resources
    Datafile: python:metapack_build.rowgenerator#copy_reference_group
    Datafile.Name: subgroups
    Datafile.Group: subgroups
    DataFile.RefArgs: Year

    When the ``subgroups`` resource runs, it will iterate over both of the references ``subgroup1`` and ``subgroup2``.
    The ``RefArgs`` value in the resource will case the ``copy_reference_group`` routine to add the ``Year`` value
    from the references to the iteration for each reference, so ``subgroup1`` will have an extra column with the
    year value 2016, and ``subgroup2`` will have the year value of 2016.

    There are three versions of this routine, with different behavior:

    - ``copy_reference_group`` will create a combined schema from all of the input schemas, aligning columns
    from difference references by name.
    - ``copy_reference_group_s`` will align columns by position, ignoring the column names.
    - ``copy_reference_group_schema`` will use a schema ( based on the name of the reference, or a ``schema`` argument
    for the reference ) to translate the column names, then it will align columns based on the name.

    :param resource:
    :param doc:
    :param env:
    :param args:
    :param kwargs:
    :return:
    """

    all_headers = []

    # Combine all of the headers into a list of tuples by position
    for ref in doc.references():
        if ref.get_value('Group') == resource.get_value('Group'):
            for row in ref.iterrowproxy():
                all_headers.append(list(convert_col(e) for e in list(row.keys())))

                break

    # For each position, add the headers that are not already in the header set.
    # this merges the headers from all datasets, maintaining the order. mostly.

    headers = []
    for e in zip(*all_headers):
        for c in set(e):
            c = convert_col(c)
            if c not in headers:
                headers.append(c)
    if resource.get_value('RefArgs'):
        ref_args = [e.strip() for e in resource.get_value('RefArgs').strip().split(',')]
    else:
        ref_args = []

    yield [convert_col(e) for e in ref_args] + headers

    for ref in doc.references():
        if ref.get_value('Group') == resource.get_value('Group'):
            ref_args_values = [ref.get_value(e) for e in ref_args]

            for row in ref.iterdict:
                row = {convert_col(k): v for k, v in row.items()}
                yield ref_args_values + [row.get(c) for c in headers]


def copy_reference_group_s(resource, doc, env, *args, **kwargs):
    """
    A Row generating function that copies all of the references that have the same 'Group' argument as this reference

    Like copy_reference_group but just uses the output schema, and matches columns by position
    The 'RefArgs' argument is a comma seperated list of arguments from the references that will be prepended to each
    row.

    :param resource:
    :param doc:
    :param env:
    :param args:
    :param kwargs:
    :return:
    """

    if resource.get_value('RefArgs'):
        ref_args = [e.strip() for e in resource.get_value('RefArgs').strip().split(',')]
    else:
        ref_args = []

    header = None

    for i, ref in enumerate(doc.references()):

        if ref.get_value('Group') == resource.get_value('Group'):
            ref_args_values = [ref.get_value(e) for e in ref_args]

            for j, row in enumerate(ref):
                if j == 0:
                    if not header:
                        header = ref_args + row
                        yield header
                else:
                    yield ref_args_values + row


def copy_reference_group_schema(resource, doc, env, *args, **kwargs):
    """
    Like copy_reference_group, but translates header names using a schema, from
    the column name to the AltName. ( The schema is for the source reference,
    not for the output )

    :param resource:
    :param doc:
    :param env:
    :param args:
    :param kwargs:
    :return:
    """

    all_headers = []

    # Combine all of the headers into a list of tuples by position
    for ref in doc.references():
        if ref.get_value('Group') == resource.get_value('Group'):

            header_map = {e['name']: e['header'] for e in ref.schema_columns}

            for row in ref.iterrowproxy():  # expanded comprehension to catch errors
                h = []
                try:
                    for e in list(row.keys()):
                        h.append(header_map[e])
                except KeyError as ex:
                    raise KeyError(
                        f"Error accessing key '{e}' in header_map '{list(header_map.keys())}'  for '{ref.name}'") \
                        from ex

                all_headers.append(h)
                break

    # For each position, add the headers that are not already in the header set.
    # this merges the headers from all datasets, maintaining the order. mostly.

    headers = []
    for e in zip(*all_headers):
        for c in set(e):
            if c not in headers:
                headers.append(c)

    if resource.get_value('RefArgs'):
        ref_args = [e.strip() for e in resource.get_value('RefArgs').strip().split(',')]
    else:
        ref_args = []

    yield [e for e in ref_args] + headers

    for ref in doc.references():
        if ref.get_value('Group') == resource.get_value('Group'):
            ref_args_values = [ref.get_value(e) for e in ref_args]
            header_map = {e['header']: e['name'] for e in ref.schema_columns}

            for row in ref.iterdict:
                yield ref_args_values + [row.get(header_map.get(c, 'NONE')) for c in headers]
