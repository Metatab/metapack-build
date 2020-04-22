# Copyright (c) 2017 Civic Knowledge. This file is licensed under the terms of the
# MIT License, included in this distribution as LICENSE

"""
CLI program for managing packages
"""

import argparse

from metapack import Downloader
from metapack.cli.core import (MetapackCliMemo, prt, update_name, warn,
                               write_doc)
from metapack_build.core import process_schemas, update_schema_properties

downloader = Downloader.get_instance()


def update(subparsers):
    """
    Update a Metapack package or Metatab file.

    The update program cleans and re-organizes a Metatab file.

    Package Name
    ------------

    -n/--name updates the package name, based on the Origin, Dataset, Time Space,
    Grain, Version and Variant terms

    -I//--increment increments the version number, then runs --name

    Properties
    ----------

    -P/--promote move child properties into arg properties. So, it a resource has a
    child property of 'Root.Name', the -P option will move all of the Root.Name
    values in the Resource section into a Name column

    -p/--schema-properties will, for resources that reference metatab package,
    take all of the resource properties ( Name, Description, etc ) and add them
    to the Resources in the current package

    -D/--Descriptions will  import descriptions references and resources that
    are Metab packages from the source package into this one.

    Schema
    ------

    -s/--schema will iterate over the first 5,000 rows in each of the datafiles,
    creating a schema for the datafile. It will skip resources that already have
    a schema.

    -A/--alt-name move the AltName properties in the schema into the column names,
    removing the AltName property column.

    -X/--clean-properties will remove any arg properties in a section that have
    no values. For instance, this will remove the Description arg property if
    no Descriptions are set.


    """

    parser = subparsers.add_parser(
        'update',
        help='Update a metatab file or metatpack package',
        description=update.__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.set_defaults(run_command=run_update)

    parser.set_defaults(handler=None)

    parser.add_argument('-n', '--name', action='store_true', default=False,
                        help="Update the Name from the Datasetname, Origin and Version terms")

    parser.add_argument('-I', '--increment', action='store_true', default=False,
                        help="Increment the version number, then update with --name")

    parser.add_argument('-V', '--version',
                        help="Set the version number for single valued version, or the Patch for semantic versions. ")

    parser.add_argument('-s', '--schemas', default=False, action='store_true',
                        help='Rebuild the schemas for files referenced in the resource section')

    parser.add_argument('-r', '--rows', default=5000, type=int,
                        help='With --schema, the minimum number of rows to process for identifying types')

    parser.add_argument('-d', '--no-codes', default=False, action='store_true',
                        help='With --schema, number columns that have codes ( occasional strings) are typed as strings')

    parser.add_argument('-p', '--schema-properties', default=False, action='store_true',
                        help='Load schema properties from generators and upstream sources')

    parser.add_argument('-P', '--promote',
                        help="Promote child terms to arg properties. Argument is a section name,  "
                             " * for all sections, or RR for Resources and References ")

    parser.add_argument('-D', '--descriptions', action='store_true', default=False,
                        help='Import descriptions for package references')

    parser.add_argument('-A', '--alt-name', default=False, action='store_true',
                        help='Move AltNames to column name')

    parser.add_argument('-X', '--clean-properties', default=False, action='store_true',
                        help='Remove unused columns in the schema, like AltName')

    parser.add_argument('-c', '--categories', default=False, action='store_true',
                        help='Update categories, creating a new categories.csv metadata file')

    parser.add_argument('-C', '--clean', default=False, action='store_true',
                        help='Clean schema before processing')

    parser.add_argument('-F', '--force', action='store_true', default=False,
                        help='Force the operation')

    parser.add_argument('-G', '--coverage', action='store_true', default=False,
                        help='Calculate spatial and temporal coverage')

    parser.add_argument('metatabfile', nargs='?',
                        help="Path or URL to a metatab file. If not provided, defaults to 'metadata.csv' ")


def run_update(args):
    m = MetapackCliMemo(args, downloader)

    m.doc  # Trigger an error if the doc can't be found

    if m.args.schemas:
        update_schemas(m)

    if m.args.schema_properties:
        update_schema_props(m)

    if m.args.clean_properties:
        clean_properties(m)

    if m.args.alt_name:
        move_alt_names(m)

    if m.args.categories:
        update_categories(m)

    if m.args.descriptions:
        update_descriptions(m)

    if m.args.promote:
        update_promote(m)

    if m.mtfile_url.scheme == 'file' and m.args.name:
        mod_version = m.args.version if m.args.version \
            else '+' if m.args.increment \
            else False

        update_name(m.mt_file, fail_on_missing=True, force=m.args.force,
                    mod_version=mod_version)

    if m.args.coverage:
        update_coverage(m)


def increment_version(m):
    pass


def update_schemas(m):
    update_name(m.mt_file, fail_on_missing=False, report_unchanged=False)

    resource = m.get_resource()

    force = m.args.force

    if m.resource:
        if not resource:
            warn("Resource {} is not in metadata".format(m.resource))
        else:
            force = True

    process_schemas(m.mt_file, resource=m.resource, cache=m.cache,
                    clean=m.args.clean, force=force, min_rows=m.args.rows,
                    allow_codes=not m.args.no_codes)


def update_schema_props(m):
    doc = m.doc

    update_schema_properties(doc, force=m.args.force)

    write_doc(doc)


def clean_properties(m):
    doc = m.doc

    doc.clean_unused_schema_terms()

    write_doc(doc)


def update_descriptions(m):
    doc = m.doc

    for ref in doc.resources():
        ref['Description'] = ref.description

        print(ref.name, id(ref))
        print("Updated '{}' to '{}'".format(ref.name, ref.description))

    for ref in doc.references():
        ref.find_first('Description')  # Is this necessary?

        print(ref.name, id(ref), ref.description)

    write_doc(doc)


def update_categories(m):
    import metapack as mp

    doc = mp.MetapackDoc()
    doc['Root'].get_or_new_term('Root.Title', 'Schema and Value Categories')
    doc.new_section('Schema', ['Description', 'Ordered'])

    update_resource_categories(m, m.get_resource(), doc)

    doc.write_csv('categories.csv')


def update_resource_categories(m, resource, doc):
    columns = resource.row_generator.columns

    tab = doc['Schema'].new_term('Root.Table', m.get_resource().name)

    for col in columns:

        doc_col = tab.new_child('Column', col.get('name'), description=col.get('description'))

        if col.get('ordered'):
            doc_col.new_child('Column.Ordered', 'true')

        for k, v in col.get('values', {}).items():
            doc_col.new_child('Column.Value', k, description=v)

    doc.cleanse()  # Creates Modified and Identifier

    return doc


def move_alt_names(m):
    doc = m.doc

    for t in doc['Schema'].find('Root.Table'):
        moved = 0
        for c in t.find('Table.Column'):

            altname = c.get('AltName')
            if altname:

                if not c.get('Description'):
                    c.description = (c.name or '').replace('\n', ' ')

                c.name = altname.value
                c.remove_child(altname)

                moved += 1

        prt("Moved {} names in '{}'".format(moved, t.name))

    write_doc(doc)


def promote_terms(self, terms="*.*"):
    """Move all leaf terms into the arg properties"""

    def yield_leaves(t):

        for c in t.children:
            yield from yield_leaves(c)
        else:
            if t.parent_term_lc != 'root':
                yield t

    moved = []

    for arg in set(l.record_term for t in self for l in yield_leaves(t)):
        if arg not in self.args:
            moved.append(arg)
            self.add_arg(arg)

    return moved


def update_promote(m):
    sections = m.args.promote

    if not sections or sections == 'RR':
        sections = ['resources', 'references']
    elif sections == '*':
        sections = [e.lower() for e in m.doc.sections.keys()]
    else:
        sections = [sections.lower()]

    for section_name, section in m.doc.sections.items():
        if section_name.lower() in sections:
            for arg in promote_terms(section):
                prt("Move {} to header in section {} ".format(arg, section_name))

    write_doc(m.doc)


def resource_time(r):
    from dateutil.relativedelta import relativedelta
    from dateutil.parser import parse as parse_dt
    if r.get_value('year'):
        t = r.get_value('year')
        return parse_dt(t + '0101'), relativedelta(year=1)
    elif r.get_value('month'):
        t = r.get_value('month')
        return parse_dt(t + '01'), relativedelta(month=1)
    return None, None


def update_coverage(m):
    raise NotImplementedError()
