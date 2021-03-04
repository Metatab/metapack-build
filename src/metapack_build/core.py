# Copyright (c) 2019 Civic Knowledge. This file is licensed under the terms of the
# Revised BSD License, included in this distribution as LICENSE
from shutil import rmtree

from metapack.cli.core import prt, type_map, warn, write_doc
from metapack.util import get_materialized_data_cache


class skip_iterator(object):
    """An iterator which skips rows from another iterator exponentially"""

    def __init__(self, iterator, skip_start=5000) -> None:
        super().__init__()
        self.iterator = iterator
        self.next_skip = 1
        self._skip_counter = self.next_skip
        self._skip_velocity = .001
        self._skip_acceleration = 0
        self._skip_start = int(skip_start)

    def __iter__(self):
        for n, e in enumerate(self.iterator):

            if n < self._skip_start:
                yield e
            else:
                self._skip_counter -= 1
                if self._skip_counter == 0:
                    yield e
                    self._skip_counter = int(self.next_skip)

                    self.next_skip *= (1 + self._skip_velocity)


def process_schemas(mt_file, resource=None, cache=None, clean=False, report_found=True, force=False, min_rows=5000,
                    allow_codes=True):
    from metapack import MetapackDoc, MetapackResourceUrl, MetapackDocumentUrl

    if isinstance(mt_file, MetapackDoc):
        doc = mt_file
        write_doc_to_file = False
    else:
        doc = MetapackDoc(mt_file)
        write_doc_to_file = True

    try:
        if clean:
            doc['Schema'].clean()
        else:
            doc['Schema']

    except KeyError:
        doc.new_section('Schema', ['DataType', 'AltName', 'Description'])

    schemas_processed = 0

    for r in doc['Resources'].find('Root.Resource'):

        if resource and r.name != resource:
            continue

        schema_term = r.schema_term

        col_count = len(list(r.columns()))
        datatype_count = sum(1 for c in r.columns() if c['datatype'])

        if schema_term and col_count == datatype_count and force is False:
            if report_found:
                prt("Found table for '{}'; skipping".format(r.schema_name))
            continue

        if col_count != datatype_count:
            prt("Found table for '{}'; but {} columns don't have datatypes"
                .format(r.schema_name, col_count - datatype_count))

        schemas_processed += 1

        rr = r.resolved_url

        rmtree(get_materialized_data_cache(doc), ignore_errors=True)

        if isinstance(rr, MetapackDocumentUrl):
            warn('{} is a MetapackDocumentUrl; skipping', r.name)
        elif isinstance(rr, MetapackResourceUrl):
            _process_metapack_resource(doc, r, force)
        else:
            _process_normal_resource(doc, r, force, skip_start=min_rows, allow_codes=allow_codes)

    if write_doc_to_file and schemas_processed:
        write_doc(doc, mt_file)


def _process_normal_resource(doc, r, force, skip_start=5000, allow_codes=True):
    """Process a resource that requires reading the file; not a metatab resource"""

    from rowgenerators.exceptions import SourceError, SchemaError
    from requests.exceptions import ConnectionError
    from itertools import islice

    from rowgenerators.source import SelectiveRowGenerator
    from tableintuit import TypeIntuiter

    schema_term = r.schema_term

    try:
        if force:
            rg = r.raw_row_generator
        else:
            rg = r.row_generator

    except SchemaError:
        rg = r.raw_row_generator
        warn("Failed to build row processor table, using raw row generator")

    # Take only the first 250K rows, and then skip through them.
    # For 250,000 rows, the routine will analyze about 10K
    slice = skip_iterator(islice(rg, 250000), skip_start=skip_start)

    headers, start, end = r._get_start_end_header()

    si = SelectiveRowGenerator(slice, header_lines=headers, start=start, end=end)

    try:
        ti = TypeIntuiter().run(si)

    except SourceError as e:
        warn("Failed to process resource '{}'; {}".format(r.name, e))
        return
    except ConnectionError as e:
        warn("Failed to download resource '{}'; {}".format(r.name, e))
        return
    except UnicodeDecodeError as e:
        warn("Text encoding error for resource '{}'; {}".format(r.name, e))
        return

    if schema_term:

        prt("Updating table '{}' ".format(r.schema_name))

        # Existing columns
        orig_columns = {e['name'].lower() if e['name'] else '': e for e in r.schema_columns or {}}

        # Remove existing columns, so add them back later, possibly in a new order
        for child in list(schema_term.children):
            schema_term.remove_child(child)

    else:
        prt("Adding table '{}' ".format(r.schema_name))
        schema_term = doc['Schema'].new_term('Table', r.schema_name)
        orig_columns = {}

    for i, c in enumerate(ti.to_rows()):

        raw_alt_name = alt_col_name(c['header'], i)
        alt_name = raw_alt_name if raw_alt_name != c['header'] else ''

        kwargs = {}

        if alt_name:
            kwargs['AltName'] = alt_name

        datatype = type_map.get(c['resolved_type'], c['resolved_type'])

        # If the field has codes, it is probably an integer, with a few
        # strings
        if c['has_codes'] and not allow_codes:
            datatype = 'text' if c['unicode'] else 'string'

        schema_term.new_child('Column', c['header'],
                              datatype=datatype,
                              # description = get_col_value(c['header'].lower(),'description'),
                              has_codes='T' if c['has_codes'] else '',
                              **kwargs)

    update_resource_properties(r, orig_columns=orig_columns, force=force)

    return ti


def _process_metapack_resource(doc, r, force):
    remote_resource = r.resolved_url.resource

    if not remote_resource:
        warn('Metatab resource could not be resolved from {}'.format(r.resolved_url))
        return

    remote_st = remote_resource.schema_term

    schema_term = r.schema_term

    if schema_term:

        prt("Updating table '{}' ".format(r.schema_name))

        # Remove existing columns, so add them back later, possibly in a new order
        for child in list(schema_term.children):
            schema_term.remove_child(child)

    else:
        prt("Adding table '{}' ".format(r.schema_name))
        schema_term = doc['Schema'].new_term('Table', r.schema_name)

    for c in remote_st.children:
        schema_term.add_child(c)


def update_schema_properties(doc, force=False):
    for r in doc['Resources'].find('Root.Resource'):
        update_resource_properties(r, force=False)


def update_resource_properties(r, orig_columns={}, force=False):
    """Get descriptions and other properties from this, or upstream, packages, and add them to the schema. """

    added = []

    schema_term = r.schema_term

    if not schema_term:
        warn("No schema term for ", r.name)
        return

    prt("Processing schema {}".format(r.name))

    rg = r.row_generator

    # Get columns information from the schema, or, if it is a package reference,
    # from the upstream schema

    upstream_columns = {e['name'].lower() if e['name'] else '': e for e in r.columns() or {}}

    # Just from the local schema
    schema_columns = {e['name'].lower() if e['name'] else '': e for e in r.schema_columns or {}}

    # Ask the generator if it can provide column descriptions and types
    generator_columns = {e['name'].lower() if e['name'] else '': e for e in rg.columns or {}}

    def get_col_value(col_name, value_name):

        v = None

        if not col_name:
            return None

        for d in [generator_columns, upstream_columns, orig_columns, schema_columns]:
            v_ = d.get(col_name.lower(), {}).get(value_name)
            if v_:
                v = v_

        return v

    # Look for new properties
    extra_properties = set()
    for d in [generator_columns, upstream_columns, orig_columns, schema_columns]:
        for k, v in d.items():
            for kk, vv in v.items():
                extra_properties.add(kk)

    # Remove the properties that are already accounted for
    extra_properties = extra_properties - {'pos', 'header', 'name', ''}

    # Add any extra properties, such as from upstream packages, to the schema.

    for ep in extra_properties:
        r.doc['Schema'].add_arg(ep)

    for c in schema_term.find('Table.Column'):

        for ep in extra_properties:
            t = c.get_or_new_child(ep)
            v = get_col_value(c.name, ep)
            if v:
                t.value = v
                added.append((c.name, ep, v))

    prt('Updated schema for {}. Set {} properties'.format(r.name, len(added)))


def alt_col_name(name, i=None):
    import re

    if not name:

        if not i:
            i == '_noid'

        return 'col{}'.format(i)

    return re.sub('_+', '_', re.sub(r'[^\w_]', '_', str(name)).lower()).rstrip('_')


def new_search_index():
    return []
