class ComponentNotFound(IndexError):
    """Registry looked for a component, but it wasn't registered."""

    ...


class InvalidComponentLabel(TypeError):
    """Registry looked for a component, but the label provided is not vlaid."""

    ...
