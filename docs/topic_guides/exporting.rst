Exporting Data
==============

Data are exported through the tiled client.

Installing Mime-Types
---------------------

Tiled specifies data formats using MIME-types. Some custom types may
be defined in the associated Tiled server
(e.g. ``application/x-nexus`` for NeXus data formatted HDF5 files).

In order for Firefly to recognize file extensions for custom
MIME-types, these definitions must be installed locally on the client
machine. The following commands can be used from the repository
directory on a standard Linux machine, assuming user MIME-types get
installed to ``$HOME/.local/share/mime``.

.. code-block:: bash

    find . -name "*.xml" -type f -exec xdg-mime install {} ';'
    update-mime-database $HOME/.local/share/mime

