class GainOverflow(RuntimeError):
    """The gain is trying to be set to a value that is not allowed."""

    ...


class ComponentNotFound(IndexError):
    """Registry looked for a component, but it wasn't registered."""

    ...


class MultipleComponentsFound(IndexError):
    """Registry looked for a single component, but found more than one."""

    ...


class InvalidComponentLabel(TypeError):
    """Registry looked for a component, but the label provided is not vlaid."""

    ...


class FileNotWritable(IOError):
    """Output file is available but does not have write intent."""

    ...


class XDIFilenameKeyNotFound(KeyError):
    """The format string for an XDI filename has unknown placeholders."""

    ...


class InvalidPV(ValueError):
    """A process variable path or similar is expected, but the path
    provided is not valid.

    """

    ...


class DocumentNotFound(RuntimeError):
    """An attempt was made to retrieve a document from the mongodb database,
    but the requested document was not available."""

    ...
