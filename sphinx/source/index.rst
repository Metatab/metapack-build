==============
metapack-build
==============

Install
=======

Install the Metapack package from PiPy with:

.. code-block:: bash

    $ pip install metapack-build

Quick Start
===========

Generate a new Metapack package with examples:

.. code-block:: bash

    $ mp new -o metatab.org -d tutorial -L -E -T "Quickstart Example Package"

You now have a Metapack package in the :file:`metatab.org-tutorial` directory,
with two example data resources. Build the data packages with:

.. code-block:: bash

    $ mp build metatab.org-tutorial/ -f -e -z

Now the :file:`metatab.org-tutorial/_packages` directory has a Zip, Excel and
Filesystem package, along with links to each package's unversioned name.

Explore the schema for one of the built packages with:

.. code-block:: bash

    $ cd metatab.org-tutorial/_packages/
    $ mp info -s metatab.org-tutorial-1.zip#random_names

And dump a sample of the data for a resource in a table format:

.. code-block:: bash

    $ mp run -T metatab.org-tutorial-1.zip#random_names

Also, open the Excel package (metatab.org-tutorial-1.xlsx) to see the pretty
formatting of the metadata, and the generated HTML documentation in
:file:`metatab.org-tutorial-1/index.html`

That's just a quick preview of how the system works. For more details see
:doc:`build/GettingStarted`.



Contents
========

.. toctree::
   :maxdepth: 2

   Getting Started <build/GettingStarted>
   Generating rows with functions <build/GeneratingRows>    
   Altering rows with transforms <build/Transforms>   
   Geographic data <build/Geographic>
   Basic Data Wranging <build/WranglingPackages> 
   License <license>
   Authors <authors>
   Changelog <changelog>
   Module Reference <api/modules>


CLI Commands
============

.. toctree::
   :maxdepth: 2

   commands


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

.. _toctree: http://www.sphinx-doc.org/en/master/usage/restructuredtext/directives.html
.. _reStructuredText: http://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html
.. _references: http://www.sphinx-doc.org/en/stable/markup/inline.html
.. _Python domain syntax: http://sphinx-doc.org/domains.html#the-python-domain
.. _Sphinx: http://www.sphinx-doc.org/
.. _Python: http://docs.python.org/
.. _Numpy: http://docs.scipy.org/doc/numpy
.. _SciPy: http://docs.scipy.org/doc/scipy/reference/
.. _matplotlib: https://matplotlib.org/contents.html#
.. _Pandas: http://pandas.pydata.org/pandas-docs/stable
.. _Scikit-Learn: http://scikit-learn.org/stable
.. _autodoc: http://www.sphinx-doc.org/en/stable/ext/autodoc.html
.. _Google style: https://github.com/google/styleguide/blob/gh-pages/pyguide.md#38-comments-and-docstrings
.. _NumPy style: https://numpydoc.readthedocs.io/en/latest/format.html
.. _classical style: http://www.sphinx-doc.org/en/stable/domains.html#info-field-lists
