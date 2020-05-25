Using Invoke
============

The Metapack build process uses pyinvoke to manage multiple packages in a collection, and to provide additional ``make`` style functions for individual packages.

New packages, created with :program:`mp new` automatically get a :file:`tasks.py` file, which loads several functions.

You can add a :file:`tasks.py` file to a directory that contains packages to manage all of the packages.

Configuration
-------------

Configure invoke functions by adding a block to the :file:`.metapack.yaml` file

.. code-block:: yaml

    wordpress:
        data.sandiegodata.org:
            url: https://data.sandiegodata.org/xmlrpc.php
            user: foouser
            password:  foobarfoobarfoobar

    invoke:
        s3_bucket: library.metatab.org
        wp_site: data.sandiegodata.org
